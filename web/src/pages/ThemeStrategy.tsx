import { useEffect, useState } from 'react';
import StockCard from '../components/StockCard';
import MetaInfo from '../components/MetaInfo';
import type { Top10Result } from '../types';

function getDateString(dateStr?: string): string {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return `${d.getFullYear()}년 ${d.getMonth() + 1}월 ${d.getDate()}일`;
}

function ThemeStrategy() {
  const [result, setResult] = useState<Top10Result | null>(null);

  useEffect(() => {
    fetch(import.meta.env.BASE_URL + 'data/top10_result.json')
      .then(res => res.json())
      .then(data => setResult(data))
      .catch(() => {});
  }, []);

  const stocks = result?.strategy_b_theme ?? [];
  const dateLabel = getDateString(result?.meta?.run_date);

  return (
    <div className="min-h-screen">
      {/* 네비 */}
      <nav className="nav-bar px-4 md:px-8 py-3">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg flex items-center justify-center text-white text-xs font-bold"
              style={{ background: 'var(--accent)' }}>AI</div>
            <span className="font-semibold text-sm" style={{ color: 'var(--text-strong)' }}>AI Stock Picker</span>
          </div>
          <span className="text-xs" style={{ color: 'var(--text-muted)' }}>테마/모멘텀 전략</span>
        </div>
      </nav>

      {/* 히어로 헤더 — 날짜 강조 */}
      <header className="py-10 px-4 text-center" style={{ background: 'var(--bg-header)' }}>
        {dateLabel && (
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full mb-4"
            style={{ background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.15)' }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.7)" strokeWidth="2">
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/>
              <line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
            </svg>
            <span className="text-sm font-semibold text-white">{dateLabel} 종목 추천</span>
          </div>
        )}
        <h1 className="text-2xl md:text-3xl font-bold text-white mb-2">
          AI Top 10 추천 종목
        </h1>
        <p className="text-sm text-white/50">
          거래량 급증 + RS 상대강도 + 수급 분석 기반
        </p>
        {stocks.length > 0 && (
          <p className="text-sm mt-2 font-semibold text-white/80">{stocks.length}개 종목 추천</p>
        )}
      </header>

      {/* 데이터 기준 날짜 — 참고 사이트 스타일 */}
      <div className="max-w-5xl mx-auto px-4 md:px-8 pt-5 pb-2">
        <div className="flex flex-wrap items-center gap-3 text-sm">
          {dateLabel && (
            <span style={{ color: 'var(--text-muted)' }}>
              데이터 기준: {dateLabel}
            </span>
          )}
          {stocks.length > 0 && result?.meta && (
            <span className="font-semibold" style={{ color: 'var(--accent)' }}>
              {stocks.length}개 종목 / {result.meta.universe_count.toLocaleString()}개 중
            </span>
          )}
        </div>
      </div>

      {/* 본문 */}
      <main className="max-w-5xl mx-auto px-4 md:px-8 py-4">
        {result?.meta && <MetaInfo meta={result.meta} />}

        {stocks.length === 0 ? (
          <div className="card-flat p-8 text-center">
            <p className="text-lg mb-2" style={{ color: 'var(--text-strong)' }}>데이터가 없습니다</p>
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
              테마/모멘텀 전략을 먼저 실행해주세요: <code>python main.py theme</code>
            </p>
          </div>
        ) : (
          stocks.map((stock, i) => (
            <StockCard key={stock.code} rank={i + 1} stock={stock} />
          ))
        )}
      </main>

      {/* 푸터 */}
      <footer className="mt-12 pb-8 text-center">
        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
          한국투자증권 API · OpenAI Agents SDK
        </p>
        <p className="text-[11px] mt-1" style={{ color: 'var(--text-muted)' }}>
          투자의 책임은 본인에게 있습니다. AI 추천은 참고 자료일 뿐 투자 조언이 아닙니다.
        </p>
      </footer>
    </div>
  );
}

export default ThemeStrategy;
