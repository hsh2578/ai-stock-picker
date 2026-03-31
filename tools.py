"""
정량 분석 툴 - 에이전트가 호출하는 종목 스크리닝 도구

[노션 원본용]
1. get_ma_cross_candidates: 이동평균선 돌파 종목 찾기

[테마/모멘텀용]
2. get_volume_surge_candidates: 거래량 급증 종목 찾기 (수급+시총 포함)

[공통]
3. get_relative_strength_candidates: 상대강도 상위 종목 찾기
"""

import json

from tqdm import tqdm
from agents import function_tool

import data_collector
from kis_client import get_investor_trend


# main.py에서 유니버스 생성 후 이 모듈에 주입합니다.
symbol_map: dict = {}   # {종목코드: 종목명}
marcap_map: dict = {}   # {종목코드: 시가총액(원)}


# ============================================
# 내부 준비 함수 (에이전트가 직접 호출하지 않음)
# ============================================

def add_indicators(price_df):
    """이동평균선과 거래대금을 가격 데이터에 추가합니다."""
    work_df = price_df.copy()
    work_df["ma5"]   = work_df["Close"].rolling(5).mean()
    work_df["ma20"]  = work_df["Close"].rolling(20).mean()
    work_df["ma60"]  = work_df["Close"].rolling(60).mean()
    work_df["ma100"] = work_df["Close"].rolling(100).mean()
    work_df["value"] = work_df["Close"] * work_df["Volume"]
    return work_df


def is_ma_cross_up(price_df, short_window=5, long_window=20):
    """단기 이동평균선이 장기 이동평균선을 오늘 처음 상향 돌파했는지 확인합니다."""
    if len(price_df) < long_window + 2:
        return False
    work_df = price_df.copy()
    work_df["short_ma"] = work_df["Close"].rolling(short_window).mean()
    work_df["long_ma"]  = work_df["Close"].rolling(long_window).mean()
    prev_row = work_df.iloc[-2]
    last_row = work_df.iloc[-1]
    return (prev_row["short_ma"] <= prev_row["long_ma"]) and (last_row["short_ma"] > last_row["long_ma"])


def calculate_relative_strength(price_df, lookback_days=20):
    """최근 lookback_days 동안 얼마나 올랐는지 비율로 반환합니다."""
    if len(price_df) < lookback_days + 1:
        return 0.0
    recent_return = price_df["Close"].iloc[-1] / price_df["Close"].iloc[-lookback_days - 1] - 1
    return float(recent_return)


def calculate_volume_surge(price_df, avg_days=20):
    """오늘 거래량이 최근 N일 평균 대비 몇 배인지 계산합니다."""
    if len(price_df) < avg_days + 1:
        return 0.0
    avg_volume = price_df["Volume"].iloc[-(avg_days + 1):-1].mean()
    if avg_volume == 0:
        return 0.0
    today_volume = price_df["Volume"].iloc[-1]
    return float(today_volume / avg_volume)


# ============================================
# 정량 툴: MA 돌파 (노션 원본용)
# ============================================

@function_tool
def get_ma_cross_candidates(short_window: int, long_window: int, limit: int = 30) -> str:
    """이동평균선 상향 돌파 조건을 만족하는 후보 종목 목록 반환"""
    rows = []

    for code, price_df in tqdm(data_collector.ohlcv_cache.items(), desc="MA 후보 계산", unit="종목"):
        try:
            if is_ma_cross_up(price_df, short_window=short_window, long_window=long_window):
                price_df_ind = add_indicators(price_df)
                rows.append({
                    "code":        code,
                    "name":        symbol_map.get(code, code),
                    "close":       int(price_df_ind["Close"].iloc[-1]),
                    "volume":      int(price_df_ind["Volume"].iloc[-1]),
                    "value":       float(price_df_ind["value"].iloc[-1]),
                    "filter_path": f"ma_cross_{short_window}_{long_window}",
                })
        except Exception:
            continue

    rows = sorted(rows, key=lambda x: (x["value"], x["volume"]), reverse=True)
    return json.dumps(rows[:limit], ensure_ascii=False)


# ============================================
# 정량 툴: 거래량 급증 (테마/모멘텀용)
# ============================================

@function_tool
def get_volume_surge_candidates(surge_ratio: float = 2.0, avg_days: int = 20, max_return_pct: float = 40.0, min_value_eok: float = 10.0, limit: int = 30) -> str:
    """거래량이 급증했지만 아직 급등 초입인 종목을 찾습니다.
    조건:
    - 거래량 surge_ratio배 이상
    - 최근 5일 수익률 max_return_pct% 미만 (꼭대기 제외)
    - 당일 양봉 (종가 > 시가, 매도 폭탄 제외)
    - 거래대금 min_value_eok억 원 이상 (노이즈 제외)
    각 후보에 외국인/기관/개인 수급 데이터도 포함합니다.
    """
    rows = []

    for code, price_df in tqdm(data_collector.ohlcv_cache.items(), desc="거래량 급증 계산", unit="종목"):
        try:
            # 거래량 급증 체크
            surge = calculate_volume_surge(price_df, avg_days=avg_days)
            if surge < surge_ratio:
                continue

            today = price_df.iloc[-1]

            # 당일 양봉 체크 (종가 > 시가 = 매수세 우위)
            if today["Close"] <= today["Open"]:
                continue

            # 거래대금 최소 기준 (노이즈 제외)
            value = float(today["Close"] * today["Volume"])
            if value < min_value_eok * 1_0000_0000:
                continue

            # 최근 5일 수익률 제한 (이미 급등한 종목 제외)
            if len(price_df) >= 6:
                return_5d = (price_df["Close"].iloc[-1] / price_df["Close"].iloc[-6] - 1) * 100
            else:
                return_5d = 0.0

            if return_5d >= max_return_pct:
                continue

            marcap = marcap_map.get(code, 0)
            marcap_eok = round(marcap / 1_0000_0000) if marcap else 0
            # RS 점수도 함께 계산 (추가 API 호출 없음)
            rs_20 = calculate_relative_strength(price_df, lookback_days=20)
            rows.append({
                "code":         code,
                "name":         symbol_map.get(code, code),
                "marcap_eok":   marcap_eok,
                "surge_ratio":  round(surge, 2),
                "rs_score":     round(rs_20, 4),
                "return_5d":    round(return_5d, 2),
                "close":        int(today["Close"]),
                "volume":       int(today["Volume"]),
                "value_eok":    round(value / 1_0000_0000, 1),
                "change":       round(float(today.get("Change", 0)) * 100, 2),
                "filter_path":  f"volume_surge_{surge_ratio}x_{avg_days}d",
            })
        except Exception:
            continue

    rows = sorted(rows, key=lambda x: (x["surge_ratio"], x["value_eok"]), reverse=True)
    top_rows = rows[:limit]

    # 상위 후보에 수급 데이터 추가: 5일 합계 + 오늘 (추세+전환 판단용)
    print(f"상위 {len(top_rows)}개 종목 수급 데이터 조회 중...")
    for row in tqdm(top_rows, desc="수급 조회", unit="종목"):
        try:
            trend = get_investor_trend(row["code"], days=5)
            if "error" not in trend:
                row["foreign_5d"] = trend.get("foreign_net", 0)
                row["institution_5d"] = trend.get("institution_net", 0)
                row["individual_5d"] = trend.get("individual_net", 0)
                detail = trend.get("detail", [])
                if detail:
                    latest = detail[0]
                    row["foreign_today"] = latest.get("foreign", 0)
                    row["institution_today"] = latest.get("institution", 0)
                    row["individual_today"] = latest.get("individual", 0)
            else:
                row["foreign_5d"] = "조회실패"
        except Exception:
            row["foreign_5d"] = "조회실패"

    return json.dumps(top_rows, ensure_ascii=False)


# ============================================
# 정량 툴 2: 상대강도 RS (모멘텀 확인)
# ============================================

@function_tool
def get_relative_strength_candidates(lookback_days: int, limit: int = 30) -> str:
    """최근 lookback_days 기준 상대적으로 강한 종목 상위 목록 반환.
    RS가 높다는 것은 시장 대비 강하게 올랐다는 뜻입니다.
    """
    rows = []

    for code, price_df in tqdm(data_collector.ohlcv_cache.items(), desc="RS 후보 계산", unit="종목"):
        try:
            score = calculate_relative_strength(price_df, lookback_days=lookback_days)
            today = price_df.iloc[-1]
            value = float(today["Close"] * today["Volume"])
            rows.append({
                "code":        code,
                "name":        symbol_map.get(code, code),
                "rs_score":    round(score, 4),
                "close":       int(today["Close"]),
                "volume":      int(today["Volume"]),
                "value":       value,
                "filter_path": f"relative_strength_{lookback_days}",
            })
        except Exception:
            continue

    rows = sorted(rows, key=lambda x: (x["rs_score"], x["value"]), reverse=True)
    return json.dumps(rows[:limit], ensure_ascii=False)


