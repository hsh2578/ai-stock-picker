import { Link } from 'react-router-dom';
import { useEffect, useState } from 'react';
import type { Top10Result } from '../types';

function Home() {
  const [result, setResult] = useState<Top10Result | null>(null);

  useEffect(() => {
    fetch(import.meta.env.BASE_URL + 'data/top10_result.json')
      .then(r => r.json()).then(d => setResult(d)).catch(() => {});
  }, []);

  const lastUpdated = result?.meta?.run_date
    ? new Date(result.meta.run_date).toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' })
    : null;

  const strategies = [
    {
      id: 'theme', path: '/theme',
      icon: <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>,
      color: '#3b82f6',
      title: '테마/모멘텀 전략',
      desc: '거래량 급증 + RS 상대강도 + 수급 분석',
      badge: { text: '커스텀', type: 'success' as const },
      count: result?.strategy_b_theme?.length,
    },
    {
      id: 'original', path: '/original',
      icon: <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg>,
      color: '#8b5cf6',
      title: '노션 원본 전략',
      desc: 'MA 이동평균선 돌파 + RS 상대강도',
      badge: { text: '원본', type: 'info' as const },
      count: result?.strategy_a_original?.length,
    },
    {
      id: 'compare', path: '/compare',
      icon: <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/></svg>,
      color: '#f59e0b',
      title: '전략 비교',
      desc: '두 전략 결과 비교 · 겹치는 종목 확인',
      badge: { text: '비교', type: 'warning' as const },
    },
  ];

  return (
    <div className="min-h-screen">
      {/* 네비 */}
      <nav className="nav-bar px-4 md:px-8 py-3">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg flex items-center justify-center text-white text-xs font-bold"
              style={{ background: 'var(--accent)' }}>AI</div>
            <span className="font-semibold text-sm" style={{ color: 'var(--text-strong)' }}>Stock Picker</span>
          </div>
          {lastUpdated && (
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>업데이트: {lastUpdated}</span>
          )}
        </div>
      </nav>

      {/* 히어로 */}
      <header className="py-12 px-4 text-center" style={{ background: 'var(--bg-header)' }}>
        <h1 className="text-3xl md:text-4xl font-bold text-white mb-3">AI Top 10 종목 추천</h1>
        <p className="text-white/60 text-base">AI 에이전트가 매일 분석하는 오늘의 추천 종목</p>
        {result?.meta && (
          <p className="text-white/40 text-sm mt-2">
            유니버스 {result.meta.universe_count.toLocaleString()}개 종목 · {result.meta.model}
          </p>
        )}
      </header>

      {/* 카드 그리드 */}
      <main className="max-w-5xl mx-auto px-4 md:px-8 -mt-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {strategies.map(s => (
            <Link key={s.id} to={s.path} className="card block p-5" style={{ borderTop: `3px solid ${s.color}` }}>
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center"
                  style={{ background: `${s.color}12`, color: s.color }}>
                  {s.icon}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="font-bold text-sm" style={{ color: 'var(--text-strong)' }}>{s.title}</h2>
                    <span className={`badge badge-${s.badge.type}`}>{s.badge.text}</span>
                  </div>
                </div>
              </div>
              <p className="text-xs mb-3" style={{ color: 'var(--text-light)' }}>{s.desc}</p>
              {s.count !== undefined && (
                <div className="flex items-center gap-1">
                  <span className="text-lg font-black" style={{ color: s.color }}>{s.count}</span>
                  <span className="text-xs" style={{ color: 'var(--text-muted)' }}>개 종목 추천</span>
                </div>
              )}
              {s.count === undefined && s.id === 'compare' && (
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>양쪽 실행 후 비교 가능</span>
              )}
            </Link>
          ))}
        </div>
      </main>

      {/* 푸터 */}
      <footer className="mt-16 pb-8 text-center">
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

export default Home;
