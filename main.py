"""
메인 실행 파일 - 두 가지 전략으로 Top10 종목 추천

전략 A (노션 원본): MA 돌파 + RS 상대강도 → Top10
전략 B (테마/모멘텀): 거래량 급증 + RS + 수급 분석 → Top10

두 전략의 결과를 나란히 비교할 수 있습니다.
"""

import asyncio
import json
import os
import re
import sys
from datetime import datetime

# Windows 터미널 인코딩 문제 해결
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import config
os.environ["OPENAI_API_KEY"] = config.OPENAI_API_KEY

from agents import Runner
from kis_client import get_universe
from data_collector import download_all_ohlcv


def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def parse_result(raw_output, symbol_map):
    """에이전트 출력을 JSON으로 파싱합니다."""
    parsed = raw_output
    if isinstance(parsed, str):
        try:
            parsed = json.loads(parsed)
        except json.JSONDecodeError:
            try:
                # ```json ... ``` 블록 먼저 시도
                code_block = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', parsed, re.DOTALL)
                if code_block:
                    parsed = json.loads(code_block.group(1))
                else:
                    # 전체에서 JSON 추출
                    match = re.search(r'\{.*\}', parsed, re.DOTALL)
                    if match:
                        parsed = json.loads(match.group())
                    else:
                        return None
            except (json.JSONDecodeError, Exception):
                return None
    return parsed


def print_top10(parsed, symbol_map, universe_set):
    """Top10 결과를 출력합니다."""
    if not parsed or "top10" not in parsed:
        print("결과를 파싱할 수 없습니다.")
        return

    for i, item in enumerate(parsed["top10"], 1):
        code = item.get("code", "")
        name = item.get("name", symbol_map.get(code, ""))
        reason = item.get("reason", "")
        risk = item.get("risk", "")
        confidence = item.get("confidence", "")
        path = item.get("path", "")

        warning = ""
        if code and code not in universe_set:
            warning = " [주의: 유니버스 밖 종목]"

        print(f"[{i}] {name} ({code}){warning}")
        print(f"    선정 이유: {reason}")
        print(f"    리스크:   {risk}")
        print(f"    확신도:   {confidence}")
        print(f"    선정 경로: {path}")
        print(f"    {'─'*50}")


async def run_strategy(agent, strategy_name):
    """에이전트를 실행하고 결과를 반환합니다."""
    print(f"\n  [{strategy_name}] 에이전트 실행 중...")
    result = await Runner.run(agent, "오늘의 Top10 종목을 추천해줘.", max_turns=30)
    return result.final_output


async def run():
    # ── Step 1: API 키 확인 ──
    print_header("Step 1: API 키 확인")
    if not config.validate_keys():
        return
    print("API 키 확인 완료!")

    # ── Step 2: 유니버스 생성 ──
    print_header("Step 2: 투자 유니버스 생성")
    codes, symbol_map, universe_df = get_universe()
    print(f"유니버스 종목 수: {len(codes)}개")
    print(f"시가총액 기준: {config.MIN_MARKET_CAP / 1_0000_0000:,.0f}억 원 이상")
    print(f"\n시총 상위 5개 종목:")
    print(universe_df.head().to_string(index=False))

    # symbol_map + marcap_map을 정량 툴에 주입
    import tools
    tools.symbol_map = symbol_map
    tools.marcap_map = dict(zip(universe_df["Code"], universe_df["Marcap"]))

    # ── Step 3: 주가 데이터 다운로드 ──
    print_header("Step 3: 주가 데이터 다운로드")
    ohlcv_data = download_all_ohlcv(codes)

    if len(ohlcv_data) == 0:
        print("주가 데이터를 받지 못했습니다. KIS API 키를 확인하세요.")
        return

    # ── Step 4: 전략 선택 ──
    universe_set = set(codes)

    # 커맨드라인 인자로 전략 선택 (기본: both)
    # python main.py original  → 노션 원본만
    # python main.py theme     → 테마/모멘텀만
    # python main.py both      → 둘 다 (기본)
    strategy_arg = sys.argv[1] if len(sys.argv) > 1 else "both"

    results = {}

    # ── 전략 A: 노션 원본 ──
    if strategy_arg in ("original", "both"):
        try:
            print_header("전략 A: 노션 원본 (MA 돌파 + RS)")
            print(f"모델: {config.AI_MODEL} / 추론: {config.AI_REASONING_EFFORT}")

            from strategy_original import stock_picker_agent as agent_a
            raw_a = await run_strategy(agent_a, "노션 원본")
            parsed_a = parse_result(raw_a, symbol_map)

            if parsed_a:
                results["strategy_a_original"] = parsed_a["top10"]

            print_header("전략 A 결과: 노션 원본 Top 10")
            print_top10(parsed_a, symbol_map, universe_set)
        except Exception as e:
            print(f"\n전략 A 실행 중 오류 발생: {e}")
            print("전략 B로 계속 진행합니다.\n")

    # ── 전략 B: 테마/모멘텀 ──
    if strategy_arg in ("theme", "both"):
        try:
            print_header("전략 B: 테마/모멘텀 (거래량 급증 + RS + 수급)")
            print(f"모델: {config.AI_MODEL} / 추론: {config.AI_REASONING_EFFORT}")

            from strategy_theme import stock_picker_agent as agent_b
            raw_b = await run_strategy(agent_b, "테마/모멘텀")
            parsed_b = parse_result(raw_b, symbol_map)

            if parsed_b:
                results["strategy_b_theme"] = parsed_b["top10"]

            print_header("전략 B 결과: 테마/모멘텀 Top 10")
            print_top10(parsed_b, symbol_map, universe_set)
        except Exception as e:
            print(f"\n전략 B 실행 중 오류 발생: {e}")

    # ── 두 전략 겹치는 종목 표시 ──
    if strategy_arg == "both" and len(results) == 2:
        codes_a = {item["code"] for item in results["strategy_a_original"]}
        codes_b = {item["code"] for item in results["strategy_b_theme"]}
        overlap = codes_a & codes_b

        print_header("두 전략에 모두 포함된 종목")
        if overlap:
            for code in overlap:
                name = symbol_map.get(code, code)
                print(f"  ★ {name} ({code})")
            print(f"\n  → {len(overlap)}개 종목이 양쪽 모두에서 추천됨 (강한 신호)")
        else:
            print("  겹치는 종목이 없습니다. 두 전략의 관점이 다릅니다.")

    # ── 실시간 주가 데이터 추가 (캐시에서 직접 조회) ──
    import data_collector
    for strategy_key in results:
        for item in results[strategy_key]:
            code = item.get("code", "")
            if code in data_collector.ohlcv_cache:
                df = data_collector.ohlcv_cache[code]
                if len(df) >= 2:
                    today_close = df.iloc[-1]["Close"]
                    yesterday_close = df.iloc[-2]["Close"]
                    item["close"] = int(today_close)
                    if yesterday_close > 0:
                        item["change_pct"] = round((today_close / yesterday_close - 1) * 100, 2)
                    else:
                        item["change_pct"] = 0.0
            # 시가총액 추가
            marcap = tools.marcap_map.get(code, 0)
            if marcap:
                item["marcap_eok"] = round(marcap / 1_0000_0000)

    # ── 결과 저장 ──
    output = {
        "meta": {
            "run_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "model": config.AI_MODEL,
            "reasoning_effort": config.AI_REASONING_EFFORT,
            "universe_count": len(codes),
            "ohlcv_cached_count": len(ohlcv_data),
            "min_market_cap": config.MIN_MARKET_CAP,
            "strategy": strategy_arg,
        },
        **results,
    }

    output_path = os.path.join(config.CACHE_DIR, "top10_result.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n결과가 {output_path} 에 저장되었습니다.")


if __name__ == "__main__":
    asyncio.run(run())
