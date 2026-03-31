"""
설정 파일 - .env에서 API 키를 불러오고 프로젝트 전역 설정을 관리합니다.
"""

import os
from dotenv import load_dotenv

# .env 파일에서 환경변수 로드
load_dotenv()

# --- API 키 ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
KIS_APP_KEY = os.getenv("KIS_APP_KEY", "")
KIS_APP_SECRET = os.getenv("KIS_APP_SECRET", "")

# --- 한국투자증권 API ---
KIS_BASE_URL = "https://openapi.koreainvestment.com:9443"
KIS_RATE_LIMIT = 18          # 초당 최대 API 호출 수
KIS_MAX_WORKERS = 8           # 병렬 다운로드 스레드 수

# --- 유니버스 설정 ---
MIN_MARKET_CAP = 200_000_000_000   # 시가총액 최소 2천억 원
OHLCV_DAYS = 250                    # 주가 데이터 수집 기간 (일)

# --- AI 모델 설정 ---
AI_MODEL = "gpt-5-mini"            # 기본 모델
AI_REASONING_EFFORT = "medium"      # 추론 강도: low / medium / high

# --- 캐시 설정 ---
CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)


def validate_keys():
    """API 키가 제대로 설정되었는지 확인합니다."""
    missing = []
    if not OPENAI_API_KEY or "여기에" in OPENAI_API_KEY:
        missing.append("OPENAI_API_KEY")
    if not KIS_APP_KEY or "여기에" in KIS_APP_KEY:
        missing.append("KIS_APP_KEY")
    if not KIS_APP_SECRET or "여기에" in KIS_APP_SECRET:
        missing.append("KIS_APP_SECRET")

    if missing:
        print("=" * 50)
        print("아직 API 키가 설정되지 않았습니다!")
        print(f"  .env 파일에서 다음 키를 입력하세요: {', '.join(missing)}")
        print("=" * 50)
        return False
    return True
