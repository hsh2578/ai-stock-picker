"""
테마/모멘텀 전략 에이전트 — 3개의 AI 에이전트

1. 매크로 애널리스트: 오늘 시장 상황 브리핑
2. 종목 조사 에이전트: 테마/뉴스 모멘텀 분석
3. 메인 에이전트 (Stock Picker): 최종 Top10 선정

정량 필터: 거래량 급증+수급 (테마 시작) + RS 상대강도 (모멘텀 확인)
"""

from openai.types.shared import Reasoning
from agents import Agent, WebSearchTool, ModelSettings

import config
from tools import (
    get_volume_surge_candidates,
    get_relative_strength_candidates,
)


def _model_settings():
    """공통 모델 설정을 반환합니다."""
    return ModelSettings(
        reasoning=Reasoning(effort=config.AI_REASONING_EFFORT)
    )


# ============================================
# 1. 매크로 애널리스트 에이전트
# ============================================

macro_agent = Agent(
    name="macro_agent_theme",
    model=config.AI_MODEL,
    model_settings=_model_settings(),
    instructions=(
        "너는 한국 주식 시장의 장세를 분석하는 매크로 애널리스트다.\n"
        "오늘 한국 주식 시장의 전반적 분위기와 최근 며칠의 흐름을 간단히 해석하라.\n"
        "특히 오늘은 테마/모멘텀 장세인지, 조정 국면인지 판단하라.\n"
        "거래량 급증 필터가 유리한지, 상대주가(RS) 기준이 유리한지, 둘 다 볼지 제안하라.\n"
        "거래량 급증을 추천하면 surge_ratio(기본 2배 이상)와 avg_days, max_return_pct(기본 40%, 이미 급등한 종목 제외)를 제안하고,\n"
        "상대주가를 추천하면 lookback_days를 제안하라.\n"
        "반드시 JSON 하나만 반환하라.\n"
        '형식은 {"market_view":..., "preferred_filters":[...], '
        '"volume_params":{"surge_ratio":..., "avg_days":..., "max_return_pct":...}, '
        '"rs_params":{"lookback_days":...}, "why":...} 로 고정하라.'
    ),
    tools=[WebSearchTool()],
)

macro_tool = macro_agent.as_tool(
    tool_name="analyze_market_context",
    tool_description="오늘 한국 시장 분위기와 어떤 정량 필터가 유리한지 브리핑",
)


# ============================================
# 2. 종목 조사 에이전트 (테마/뉴스 모멘텀)
# ============================================

candidate_research_agent = Agent(
    name="research_agent_theme",
    model=config.AI_MODEL,
    model_settings=_model_settings(),
    instructions=(
        "너는 개별 종목의 테마와 뉴스 모멘텀을 분석하는 애널리스트다.\n"
        "입력으로 받은 종목에 대해 다음을 분석하라:\n"
        "1. 어떤 테마에 연결되어 있는지\n"
        "2. 해당 테마의 촉매(catalyst)가 무엇인지 — 정책/실적/뉴스/루머 중 어느 것인지\n"
        "3. 이 종목이 테마의 주도주인지 후발주인지\n"
        "4. 테마의 지속성과 단기 조정 가능성\n"
        "WebSearchTool을 활용하되, 검색은 꼭 필요한 범위에서만 수행하라.\n"
        "반드시 JSON 하나만 반환하라.\n"
        '형식은 {"theme":..., "catalyst":..., "leader_or_follower":..., '
        '"theme_durability":..., "correction_risk":..., "momentum_summary":...} 로 고정하라.'
    ),
    tools=[WebSearchTool()],
)

candidate_research_tool = candidate_research_agent.as_tool(
    tool_name="research_candidate",
    tool_description="개별 종목의 테마 연결성, 뉴스 모멘텀, 조정 가능성을 조사해 요약",
)


# ============================================
# 3. 메인 에이전트 (Stock Picker)
# ============================================

stock_picker_agent = Agent(
    name="stock_picker_theme",
    model=config.AI_MODEL,
    model_settings=_model_settings(),
    instructions=(
        "너는 한국 주식 시장에서 테마/모멘텀 기반으로 오늘의 Top10 종목을 선정하는 총괄 애널리스트다.\n"
        "가장 먼저 analyze_market_context 툴을 호출해 오늘 장세 브리핑을 받아라.\n"
        "거래량 급증 필터(get_volume_surge_candidates)를 반드시 호출하라. 이 필터를 통과한 종목만 Top10 후보 자격이 있다.\n"
        "RS 필터(get_relative_strength_candidates)는 시장 전체 모멘텀 참고용으로만 활용하라. RS에서만 나온 종목은 Top10에 넣지 마라.\n"
        "거래량 급증 필터 결과에 다음 데이터가 모두 포함되어 있으니 활용하라:\n"
        "- surge_ratio: 거래량 급증 배수.\n"
        "- rs_score: 최근 20일 상대강도. RS가 높을수록 모멘텀이 강한 종목.\n"
        "- foreign_5d/institution_5d/individual_5d: 5일 순매수량 합계.\n"
        "- foreign_today/institution_today/individual_today: 오늘 하루 순매수량.\n"
        "- 5일 합계와 오늘 숫자를 직접 비교해서 수급의 방향, 크기, 전환 여부를 종합 판단하라.\n"
        "- 순매수량의 절대 크기도 중요하다. 외국인 100주 매수와 100만주 매수는 전혀 다른 신호다.\n"
        "- 오늘 하루 순매수량이 5일 합계 대비 급증했다면, 그날 큰 자금이 새로 유입된 것이므로 강한 매수 신호다.\n"
        "- marcap_eok: 시가총액(억원). 소형주(시총 5천억 미만)는 테마 반응이 크지만 변동성도 크다. 대형주는 안정적이지만 테마 반응이 느리다.\n"
        "수급과 모멘텀을 종합해서 후보를 압축하라.\n"
        "후보는 모두 research_candidate 툴로 테마 연결성과 모멘텀 지속성을 확인하라.\n"
        "종목 조사 결과의 catalyst(촉매)와 leader_or_follower(주도주/후발주) 정보를 다음과 같이 활용하라:\n"
        "- 주도주를 후발주보다 우선하라.\n"
        "- 촉매가 정책/실적이면 지속성이 높고, 루머이면 리스크가 높다.\n"
        "테마가 불분명하거나 일회성 급등으로 판단되면 후보에서 제외하라.\n"
        "제외된 만큼 남은 후보에서 추가로 조사해 반드시 10개를 채워라.\n"
        "판단에 추가 정보가 필요하다면 웹서치 툴을 이용해 조사하고 판단하라.\n"
        "\n"
        "순위 결정 기준 (위에서 아래로 중요도 순):\n"
        "1. 테마 지속성 — 테마가 구조적이고 지속 상승 가능한 종목이 최상위. 일회성 이벤트는 하위.\n"
        "2. 수급 — 외국인/기관이 돈을 넣고 있는 종목 상위. 개인만 매수하면 하위.\n"
        "3. 촉매 강도 — 정책/실적 > 뉴스 > 루머. 촉매가 강할수록 상위.\n"
        "4. 주도주 여부 — 같은 테마면 주도주가 후발주보다 상위.\n"
        "5. 리스크 대비 기대수익 — 리스크 대비 상승 여력이 큰 종목 상위.\n"
        "6. 진입 타이밍 — 아직 초입인 종목이 이미 많이 오른 종목보다 상위.\n"
        "7. 시총 대비 변동성 — 같은 조건이면 유동성 좋은 종목 상위.\n"
        "Top10 모든 종목을 1위부터 10위까지 순위를 정하라. 1위가 가장 매력적이고, 10위가 가장 덜 매력적이어야 한다.\n"
        "반드시 10개를 반환하라.\n"
        '형식은 {"top10": [{"code":..., "name":..., "reason":..., '
        '"risk":..., "confidence":..., "path":...}, ...]} 로 고정하라.'
    ),
    tools=[
        WebSearchTool(),
        macro_tool,
        get_volume_surge_candidates,      # 수급 + 시총 포함
        get_relative_strength_candidates,
        candidate_research_tool,
    ],
)
