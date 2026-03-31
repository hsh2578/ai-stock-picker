"""
데이터 수집기 - 유니버스 전체 종목의 주가 데이터를 병렬로 다운로드하고 캐싱합니다.

캐시 전략 (3단계):
1. 오늘 이미 받았으면 → 디스크에서 바로 로드 (0초)
2. 어제 캐시가 있으면 → 오늘 하루치만 증분 다운로드 (2~3분)
3. 캐시가 아예 없으면 → 250일치 전체 다운로드 (20~30분)
"""

import os
import pickle
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

import pandas as pd
from tqdm import tqdm

import config
from kis_client import get_stock_ohlcv


# 메모리 캐시 (실행 중 tools.py에서 참조)
ohlcv_cache: dict = {}

# 디스크 캐시 경로
CACHE_FILE = os.path.join(config.CACHE_DIR, "ohlcv_cache.pkl")
CACHE_META_FILE = os.path.join(config.CACHE_DIR, "ohlcv_meta.pkl")


def _load_meta():
    """캐시 메타 정보를 읽습니다."""
    if not os.path.exists(CACHE_META_FILE):
        return None
    try:
        with open(CACHE_META_FILE, "rb") as f:
            return pickle.load(f)
    except Exception:
        return None


def _load_from_disk():
    """디스크에서 캐시를 불러옵니다."""
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE, "rb") as f:
            return pickle.load(f)
    except Exception:
        return None


def _save_to_disk(cache_data):
    """캐시를 디스크에 저장합니다."""
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(cache_data, f)
    with open(CACHE_META_FILE, "wb") as f:
        pickle.dump({"date": datetime.today().strftime("%Y%m%d")}, f)


def _incremental_update(existing_cache, universe_codes):
    """기존 캐시에 오늘 하루치 데이터만 추가합니다.

    원리:
    - 기존 캐시의 각 종목에서 마지막 날짜를 확인
    - 그 다음날 ~ 오늘까지만 API로 받아서 이어붙이기
    - 새로 유니버스에 들어온 종목은 전체 다운로드
    """
    updated_cache = {}
    end_date = datetime.today().strftime("%Y%m%d")
    cutoff = (datetime.today() - timedelta(days=config.OHLCV_DAYS))

    # 기존 캐시에 있는 종목: 증분만 받기
    existing_codes = set(existing_cache.keys()) & set(universe_codes)
    # 신규 종목: 전체 다운로드
    new_codes = set(universe_codes) - set(existing_cache.keys())

    def _fetch_incremental(code):
        """기존 데이터 이후 ~ 오늘까지만 받아서 합치기"""
        old_df = existing_cache[code]
        last_date = old_df.index.max()
        next_day = (last_date + timedelta(days=1)).strftime("%Y%m%d")

        if next_day > end_date:
            # 이미 오늘 데이터까지 있음 → 기존 그대로
            return code, old_df

        try:
            new_df = get_stock_ohlcv(code, next_day, end_date)
            if new_df.empty:
                return code, old_df

            # 기존 + 신규 합치기, 오래된 데이터 잘라내기
            merged = pd.concat([old_df, new_df])
            merged = merged[~merged.index.duplicated(keep="last")]
            merged = merged.sort_index()
            merged = merged[merged.index >= cutoff]
            return code, merged
        except Exception:
            return code, old_df

    def _fetch_full(code):
        """신규 종목은 250일치 전체 다운로드"""
        start_date = cutoff.strftime("%Y%m%d")
        try:
            df = get_stock_ohlcv(code, start_date, end_date)
            if not df.empty:
                return code, df
        except Exception:
            pass
        return code, None

    # 1) 기존 종목 증분 업데이트
    if existing_codes:
        print(f"기존 종목 증분 업데이트: {len(existing_codes)}개")
        with ThreadPoolExecutor(max_workers=config.KIS_MAX_WORKERS) as executor:
            futures = {executor.submit(_fetch_incremental, c): c for c in existing_codes}
            with tqdm(total=len(existing_codes), desc="증분 업데이트", unit="종목") as pbar:
                for future in as_completed(futures):
                    code, df = future.result()
                    if df is not None:
                        updated_cache[code] = df
                    pbar.update(1)

    # 2) 신규 종목 전체 다운로드
    if new_codes:
        print(f"신규 종목 전체 다운로드: {len(new_codes)}개")
        with ThreadPoolExecutor(max_workers=config.KIS_MAX_WORKERS) as executor:
            futures = {executor.submit(_fetch_full, c): c for c in new_codes}
            with tqdm(total=len(new_codes), desc="신규 다운로드", unit="종목") as pbar:
                for future in as_completed(futures):
                    code, df = future.result()
                    if df is not None:
                        updated_cache[code] = df
                    pbar.update(1)

    return updated_cache


def download_all_ohlcv(universe_codes):
    """유니버스 전체 종목의 주가 데이터를 다운로드합니다.

    캐시 전략:
    1. 오늘 캐시 있음 → 바로 로드 (0초)
    2. 과거 캐시 있음 → 증분 업데이트 (2~3분)
    3. 캐시 없음     → 전체 다운로드 (20~30분)
    """
    global ohlcv_cache

    today = datetime.today().strftime("%Y%m%d")
    meta = _load_meta()

    # ── 1) 오늘 이미 받았으면 바로 로드 ──
    if meta and meta.get("date") == today:
        print("오늘 이미 다운로드한 캐시가 있습니다. 디스크에서 불러옵니다...")
        disk_data = _load_from_disk()
        if disk_data and len(disk_data) > 0:
            ohlcv_cache = disk_data
            print(f"캐시 로드 완료: {len(ohlcv_cache)}개 종목")
            return ohlcv_cache

    # ── 2) 과거 캐시가 있으면 증분 업데이트 ──
    if meta and meta.get("date"):
        old_date = meta["date"]
        disk_data = _load_from_disk()
        if disk_data and len(disk_data) > 0:
            days_old = (datetime.today() - datetime.strptime(old_date, "%Y%m%d")).days
            print(f"이전 캐시 발견: {old_date} ({days_old}일 전, {len(disk_data)}개 종목)")
            print(f"증분 다운로드로 오늘 데이터까지 업데이트합니다.")
            ohlcv_cache = _incremental_update(disk_data, universe_codes)
            print(f"증분 업데이트 완료: {len(ohlcv_cache)}개 종목")
            _save_to_disk(ohlcv_cache)
            return ohlcv_cache

    # ── 3) 캐시가 없으면 전체 다운로드 ──
    end_date = today
    start_date = (datetime.today() - timedelta(days=config.OHLCV_DAYS)).strftime("%Y%m%d")
    ohlcv_cache = {}

    def _fetch_one(code):
        try:
            df = get_stock_ohlcv(code, start_date, end_date)
            if not df.empty:
                return code, df
        except Exception:
            pass
        return code, None

    print(f"캐시 없음. 전체 다운로드 시작: {len(universe_codes)}개 종목 (약 20~30분)")

    with ThreadPoolExecutor(max_workers=config.KIS_MAX_WORKERS) as executor:
        futures = {executor.submit(_fetch_one, code): code for code in universe_codes}
        with tqdm(total=len(universe_codes), desc="전체 다운로드", unit="종목") as pbar:
            for future in as_completed(futures):
                code, df = future.result()
                if df is not None:
                    ohlcv_cache[code] = df
                pbar.update(1)

    print(f"다운로드 완료: {len(ohlcv_cache)}개 종목 / 전체 {len(universe_codes)}개")
    _save_to_disk(ohlcv_cache)
    print("디스크 캐시 저장 완료")

    return ohlcv_cache
