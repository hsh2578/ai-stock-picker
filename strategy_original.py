"""
전략 A: 노션 원본 — MA 돌파 + RS 상대강도

노션 프로젝트 그대로의 에이전트 구성입니다.
- 매크로 에이전트: MA/RS 중 어떤 필터가 유리한지 제안
- 종목 조사 에이전트: 범용 리서치 (사업, 뉴스, 긍정, 리스크)
- 메인 에이전트: Top10 선정
"""

from openai.types.shared import Reasoning
from agents import Agent, WebSearchTool, ModelSettings

import config
from tools import get_ma_cross_candidates, get_relative_strength_candidates


def _model_settings():
    return ModelSettings(reasoning=Reasoning(effort=config.AI_REASONING_EFFORT))


# 1. 매크로 애널리스트
macro_agent = Agent(
    name="macro_agent_original",
    model=config.AI_MODEL,
    model_settings=_model_settings(),
    instructions=(
        "너는 한국 주식 시장의 장세를 분석하는 매크로 애널리스트다.\n"
        "오늘 한국 주식 시장의 전반적 분위기와 최근 며칠의 흐름을 간단히 해석하라.\n"
        "특히 오늘은 이동평균선 돌파가 유리한지, 상대주가 기준이 유리한지, 둘 다 볼지 제안하라.\n"
        "이동평균선을 추천하면 short_window와 long_window를 제안하고,\n"
        "상대주가를 추천하면 lookback_days를 제안하라.\n"
        "반드시 JSON 하나만 반환하라.\n"
        '형식은 {"market_view":..., "preferred_filters":[...], '
        '"ma_params":{"short_window":..., "long_window":...}, '
        '"rs_params":{"lookback_days":...}, "why":...} 로 고정하라.'
    ),
    tools=[WebSearchTool()],
)

macro_tool = macro_agent.as_tool(
    tool_name="analyze_market_context",
    tool_description="오늘 한국 시장 분위기와 어떤 정량 필터가 유리한지 브리핑",
)


# 2. 종목 조사 에이전트 (범용)
candidate_research_agent = Agent(
    name="research_agent_original",
    model=config.AI_MODEL,
    model_settings=_model_settings(),
    instructions=(
        "너는 개별 종목을 조사하는 리서치 애널리스트다.\n"
        "입력으로 받은 종목의 사업 내용, 최근 뉴스 흐름, 긍정 요인, 리스크 요인을 정리하라.\n"
        "WebSearchTool을 활용하되, 검색은 꼭 필요한 범위에서만 수행하라.\n"
        "반드시 JSON 하나만 반환하라.\n"
        '형식은 {"business":..., "news":..., "positive":..., "risk":..., "summary":...} 로 고정하라.'
    ),
    tools=[WebSearchTool()],
)

candidate_research_tool = candidate_research_agent.as_tool(
    tool_name="research_candidate",
    tool_description="개별 종목의 사업 내용, 최근 뉴스 흐름, 핵심 리스크를 조사해 요약",
)


# 3. 메인 에이전트
stock_picker_agent = Agent(
    name="stock_picker_original",
    model=config.AI_MODEL,
    model_settings=_model_settings(),
    instructions=(
        "너는 한국 주식 시장에서 오늘의 Top10 종목을 선정하는 총괄 애널리스트다.\n"
        "가장 먼저 analyze_market_context 툴을 호출해 오늘 장세 브리핑을 받아라.\n"
        "필요한 정량 툴을 호출해 후보군을 계산하라.\n"
        "후보가 너무 많으면 먼저 10~15개 수준으로 압축하라.\n"
        "정말 애매한 종목만 research_candidate 툴로 추가 조사하라.\n"
        "판단에 추가 정보가 필요하다면 웹서치 툴을 이용해 조사하고 판단하라.\n"
        "최종적으로 Top10 종목만 JSON 하나로 반환하라.\n"
        '형식은 {"top10": [{"code":..., "name":..., "reason":..., '
        '"risk":..., "confidence":..., "path":...}, ...]} 로 고정하라.'
    ),
    tools=[
        WebSearchTool(),
        macro_tool,
        get_ma_cross_candidates,
        get_relative_strength_candidates,
        candidate_research_tool,
    ],
)
