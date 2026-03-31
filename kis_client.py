"""
한국투자증권 API 클라이언트
- 토큰 발급 및 관리
- API 호출 (Rate Limit 포함)
- 종목 마스터 다운로드
- 개별 종목 일봉(OHLCV) 조회
"""

import os
import ssl
import tempfile
import threading
import time
import urllib.request
import zipfile
from datetime import datetime, timedelta

import pandas as pd
import requests

import config


# ============================================
# 1. API 연결 기반 (토큰, Rate Limiter)
# ============================================

session = requests.Session()


class RateLimiter:
    """초당 최대 호출 수를 제한하는 장치입니다.
    한투 API는 초당 18건까지 허용하므로, 그 이상 호출하면 차단됩니다.
    """

    def __init__(self, max_per_sec):
        self.min_interval = 1.0 / max_per_sec
        self.lock = threading.Lock()
        self.last = 0.0

    def wait(self):
        with self.lock:
            now = time.monotonic()
            gap = self.last + self.min_interval - now
            if gap > 0:
                time.sleep(gap)
            self.last = time.monotonic()


limiter = RateLimiter(config.KIS_RATE_LIMIT)

# 토큰 캐시 (한 번 발급하면 23시간 동안 재사용)
_token = None
_token_expires_at = None
_token_lock = threading.Lock()


def get_access_token():
    """한투 API 접속 토큰을 발급받습니다. 이미 유효한 토큰이 있으면 재사용합니다."""
    global _token, _token_expires_at
    with _token_lock:
        now = datetime.now()
        if _token and _token_expires_at and now < _token_expires_at - timedelta(minutes=5):
            return _token

        resp = session.post(
            f"{config.KIS_BASE_URL}/oauth2/tokenP",
            headers={"Content-Type": "application/json"},
            json={
                "grant_type": "client_credentials",
                "appkey": config.KIS_APP_KEY,
                "appsecret": config.KIS_APP_SECRET,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        _token = data["access_token"]
        _token_expires_at = now + timedelta(hours=23)
        return _token


def _make_headers(tr_id):
    """API 호출에 필요한 헤더를 생성합니다."""
    return {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {get_access_token()}",
        "appkey": config.KIS_APP_KEY,
        "appsecret": config.KIS_APP_SECRET,
        "tr_id": tr_id,
        "custtype": "P",
    }


def api_get(api_url, tr_id, params):
    """한투 API GET 요청을 보냅니다. Rate Limit을 자동으로 지킵니다."""
    limiter.wait()
    resp = session.get(api_url, headers=_make_headers(tr_id), params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


# ============================================
# 2. 종목 마스터 (코스피/코스닥 전체 종목 리스트)
# ============================================

TMP_DIR = tempfile.gettempdir()


def _download_and_parse_mst(url, zip_name, mst_name, tail_len, field_specs, field_names, market):
    """한투에서 제공하는 종목 마스터 파일(zip)을 다운로드하고 파싱합니다."""
    ssl._create_default_https_context = ssl._create_unverified_context
    zip_path = os.path.join(TMP_DIR, zip_name)
    mst_path = os.path.join(TMP_DIR, mst_name)

    urllib.request.urlretrieve(url, zip_path)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(TMP_DIR)
    if os.path.exists(zip_path):
        os.remove(zip_path)

    part1_rows, part2_lines = [], []
    with open(mst_path, "r", encoding="cp949") as f:
        for line in f:
            head = line[: len(line) - tail_len]
            code = head[0:9].rstrip()
            name = head[21:].strip()
            part1_rows.append([code, name])
            part2_lines.append(line[-tail_len:])

    df1 = pd.DataFrame(part1_rows, columns=["단축코드", "한글명"])
    tmp_path = os.path.join(TMP_DIR, f"_{market}_p2.tmp")
    with open(tmp_path, "w") as wf:
        for row in part2_lines:
            wf.write(row)
    df2 = pd.read_fwf(tmp_path, widths=field_specs, names=field_names, dtype=str)
    os.remove(tmp_path)
    if os.path.exists(mst_path):
        os.remove(mst_path)

    df = pd.concat([df1.reset_index(drop=True), df2.reset_index(drop=True)], axis=1)
    df["Market"] = market
    return df


def _load_master():
    """코스피 + 코스닥 전체 마스터를 불러와 ETF/SPAC/거래정지 등을 제외합니다."""
    kospi_specs = [2,1,4,4,4,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,9,5,5,1,1,1,2,1,1,1,2,2,2,3,1,3,12,12,8,15,21,2,7,1,1,1,1,1,9,9,9,5,9,8,9,3,1,1,1]
    kospi_cols = [
        "그룹코드","시가총액규모","지수업종대분류","지수업종중분류","지수업종소분류",
        "제조업","저유동성","지배구조지수종목","KOSPI200섹터업종","KOSPI100",
        "KOSPI50","KRX","ETP","ELW발행","KRX100",
        "KRX자동차","KRX반도체","KRX바이오","KRX은행","SPAC",
        "KRX에너지화학","KRX철강","단기과열","KRX미디어통신","KRX건설",
        "Non1","KRX증권","KRX선박","KRX섹터_보험","KRX섹터_운송",
        "SRI","기준가","매매수량단위","시간외수량단위","거래정지",
        "정리매매","관리종목","시장경고","경고예고","불성실공시",
        "우회상장","락구분","액면변경","증자구분","증거금비율",
        "신용가능","신용기간","전일거래량","액면가","상장일자",
        "상장주수","자본금","결산월","공모가","우선주",
        "공매도과열","이상급등","KRX300","KOSPI","매출액",
        "영업이익","경상이익","당기순이익","ROE","기준년월",
        "시가총액","그룹사코드","회사신용한도초과","담보대출가능","대주가능",
    ]
    kosdaq_specs = [2,1,4,4,4,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,9,5,5,1,1,1,2,1,1,1,2,2,2,3,1,3,12,12,8,15,21,2,7,1,1,1,1,9,9,9,5,9,8,9,3,1,1,1]
    kosdaq_cols = [
        "그룹코드","시가총액규모","지수업종대분류","지수업종중분류","지수업종소분류",
        "제조업","저유동성","지배구조지수종목","KOSDAQ150섹터업종","KRX",
        "ETP","KRX100","KRX자동차","KRX반도체","KRX바이오",
        "KRX은행","SPAC","KRX에너지화학","KRX철강","단기과열",
        "KRX미디어통신","KRX건설","Non1","KRX증권","KRX선박",
        "KRX섹터_보험","기준가","매매수량단위","시간외수량단위","거래정지",
        "정리매매","관리종목","시장경고","경고예고","불성실공시",
        "우회상장","락구분","액면변경","증자구분","증거금비율",
        "신용가능","신용기간","전일거래량","액면가","상장일자",
        "상장주수","자본금","결산월","공모가","우선주",
        "공매도과열","이상급등","KRX300","매출액","영업이익",
        "경상이익","당기순이익","ROE","기준년월","시가총액",
        "그룹사코드","회사신용한도초과","담보대출가능","대주가능",
    ]

    kospi = _download_and_parse_mst(
        "https://new.real.download.dws.co.kr/common/master/kospi_code.mst.zip",
        "kospi_code.zip", "kospi_code.mst", 228, kospi_specs, kospi_cols, "KOSPI",
    )
    kosdaq = _download_and_parse_mst(
        "https://new.real.download.dws.co.kr/common/master/kosdaq_code.mst.zip",
        "kosdaq_code.zip", "kosdaq_code.mst", 222, kosdaq_specs, kosdaq_cols, "KOSDAQ",
    )

    all_df = pd.concat([kospi, kosdaq], ignore_index=True)
    all_df["Code"] = all_df["단축코드"].astype(str).str.zfill(6)
    all_df["Name"] = all_df["한글명"]
    all_df["_marcap_eok"] = pd.to_numeric(all_df["시가총액"], errors="coerce").fillna(0)

    # 필터: 순수 주식만 남기기
    is_numeric_code = all_df["단축코드"].astype(str).str.match(r"^\d{6}$")
    is_not_etp = all_df.get("ETP", pd.Series("N", index=all_df.index)).astype(str).str.strip() != "Y"
    is_not_spac = all_df.get("SPAC", pd.Series("N", index=all_df.index)).astype(str).str.strip() != "Y"
    is_not_suspended = all_df.get("거래정지", pd.Series("N", index=all_df.index)).astype(str).str.strip() != "Y"
    is_not_cleanup = all_df.get("정리매매", pd.Series("N", index=all_df.index)).astype(str).str.strip() != "Y"

    etp_brand_prefixes = [
        "TIGER","KODEX","KINDEX","KOSEF","KBSTAR","ARIRANG","HANARO","SOL","ACE",
        "TIMEFOLIO","FOCUS","WOORI","PLUS","RISE","TREX","SMART","BNK","마이티","파워","히어로","에셋플러스",
    ]
    etp_name_keywords = ["ETN","ETF","레버리지","인버스"]
    etp_prefix_pat = "^(?:" + "|".join(etp_brand_prefixes) + ")"
    etp_keyword_pat = "|".join(etp_name_keywords)
    name_str = all_df["Name"].astype(str).str.strip()
    is_not_etp_by_name = ~(
        name_str.str.contains(etp_prefix_pat, case=False, na=False)
        | name_str.str.contains(etp_keyword_pat, case=False, na=False)
    )

    stock_mask = is_numeric_code & is_not_etp & is_not_etp_by_name & is_not_spac & is_not_suspended & is_not_cleanup
    return all_df[stock_mask].copy()


def get_universe(min_market_cap=None):
    """투자 유니버스를 생성합니다. 시가총액 기준으로 필터링합니다.

    Returns:
        codes: 종목코드 리스트
        symbol_map: {종목코드: 종목명} 딕셔너리
        universe_df: 유니버스 DataFrame
    """
    if min_market_cap is None:
        min_market_cap = config.MIN_MARKET_CAP

    stocks_only = _load_master()
    all_symbols = dict(zip(stocks_only["Code"], stocks_only["Name"]))
    min_cap_eok = min_market_cap / 1_0000_0000

    filtered = stocks_only[stocks_only["_marcap_eok"] >= min_cap_eok].copy()
    filtered = filtered.sort_values("_marcap_eok", ascending=False)
    filtered["Marcap"] = (filtered["_marcap_eok"] * 1_0000_0000).astype("int64")

    codes = filtered["Code"].tolist()
    universe_df = filtered[["Code", "Name", "Market", "Marcap"]].reset_index(drop=True)
    return codes, all_symbols, universe_df


# ============================================
# 3. 개별 종목 일봉 데이터 (OHLCV)
# ============================================

def get_stock_ohlcv(code, start_date, end_date):
    """종목 하나의 일봉 데이터를 가져옵니다.

    Args:
        code: 종목코드 (6자리 문자열)
        start_date: 시작일 (YYYYMMDD)
        end_date: 종료일 (YYYYMMDD)

    Returns:
        DataFrame (index=date, columns=[Open,High,Low,Close,Volume,Change])
    """
    api_url = f"{config.KIS_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
    tr_id = "FHKST03010100"
    code6 = str(code).zfill(6)
    start_clean = start_date.replace("-", "")
    end_clean = end_date.replace("-", "")

    all_rows = []
    seen_dates = set()
    cursor_end = end_clean

    for _ in range(15):
        if start_clean > cursor_end:
            break

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": code6,
            "FID_INPUT_DATE_1": start_clean,
            "FID_INPUT_DATE_2": cursor_end,
            "FID_PERIOD_DIV_CODE": "D",
            "FID_ORG_ADJ_PRC": "1",  # 수정주가 (액면분할/무상증자 반영)
        }
        data = api_get(api_url, tr_id, params)
        if data.get("rt_cd") != "0":
            break

        items = data.get("output2", [])
        if not items:
            break

        new_count = 0
        oldest_date = None
        for item in items:
            dt_str = item.get("stck_bsop_date", "")
            if not dt_str or dt_str in seen_dates:
                continue
            seen_dates.add(dt_str)
            try:
                all_rows.append({
                    "date": dt_str,
                    "Open": int(item.get("stck_oprc", 0)),
                    "High": int(item.get("stck_hgpr", 0)),
                    "Low": int(item.get("stck_lwpr", 0)),
                    "Close": int(item.get("stck_clpr", 0)),
                    "Volume": int(item.get("acml_vol", 0)),
                })
                new_count += 1
                if oldest_date is None or dt_str < oldest_date:
                    oldest_date = dt_str
            except Exception:
                continue

        if new_count == 0:
            break
        if oldest_date and oldest_date <= start_clean:
            break
        if oldest_date:
            prev = datetime.strptime(oldest_date, "%Y%m%d") - timedelta(days=1)
            cursor_end = prev.strftime("%Y%m%d")
        else:
            break

    if not all_rows:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume", "Change"])

    price_df = pd.DataFrame(all_rows)
    price_df["date"] = pd.to_datetime(price_df["date"], format="%Y%m%d")
    price_df = price_df.drop_duplicates(subset=["date"]).sort_values("date").set_index("date")
    price_df.index = price_df.index.normalize()
    price_df["Change"] = price_df["Close"].pct_change().fillna(0.0)

    # 데이터 품질 검증: 종가 0원, 거래량 0인 비정상 행 제거
    price_df = price_df[(price_df["Close"] > 0) & (price_df["Volume"] > 0)]

    return price_df


# ============================================
# 4. 투자자별 매매 동향 (수급 데이터)
# ============================================

def get_investor_trend(code, days=5):
    """특정 종목의 최근 N일간 투자자별(외국인/기관/개인) 순매수 데이터를 조회합니다.

    Args:
        code: 종목코드 (6자리)
        days: 조회 기간 (기본 5일)

    Returns:
        dict: {foreign_net, institution_net, individual_net, foreign_trend, institution_trend, detail}
    """
    code6 = str(code).zfill(6)

    investor_url = f"{config.KIS_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-investor"
    tr_id = "FHKST01010900"

    try:
        data = api_get(
            investor_url, tr_id,
            {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": code6,
            },
        )

        if data.get("rt_cd") != "0":
            return {"error": f"API 오류: {data.get('msg1', '')}"}

        items = data.get("output", [])
        if not items:
            return {"error": "데이터 없음"}

        # 최근 N일만 추출
        recent = items[:days]

        foreign_net = 0
        institution_net = 0
        individual_net = 0
        detail = []

        def _safe_int(val, default=0):
            try:
                s = str(val).strip()
                return int(s) if s else default
            except (ValueError, TypeError):
                return default

        for item in recent:
            f_buy = _safe_int(item.get("frgn_ntby_qty", 0))   # 외국인 순매수량
            i_buy = _safe_int(item.get("orgn_ntby_qty", 0))    # 기관 순매수량
            p_buy = _safe_int(item.get("prsn_ntby_qty", 0))    # 개인 순매수량

            foreign_net += f_buy
            institution_net += i_buy
            individual_net += p_buy

            detail.append({
                "date": item.get("stck_bsop_date", ""),
                "foreign": f_buy,
                "institution": i_buy,
                "individual": p_buy,
            })

        def _trend(net):
            if net > 0:
                return "순매수"
            elif net < 0:
                return "순매도"
            return "중립"

        return {
            "foreign_net": foreign_net,
            "institution_net": institution_net,
            "individual_net": individual_net,
            "foreign_trend": _trend(foreign_net),
            "institution_trend": _trend(institution_net),
            "detail": detail,
        }
    except Exception as e:
        return {"error": str(e)}
