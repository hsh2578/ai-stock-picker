import { useEffect, useState } from 'react';
import PageLayout from '../components/PageLayout';
import type { Top10Result, StockItem } from '../types';

function Compare() {
  const [result, setResult] = useState<Top10Result | null>(null);

  useEffect(() => {
    fetch(import.meta.env.BASE_URL + 'data/top10_result.json')
      .then(res => res.json())
      .then(data => setResult(data))
      .catch(() => {});
  }, []);

  const themeStocks = result?.strategy_b_theme ?? [];
  const originalStocks = result?.strategy_a_original ?? [];

  const themeCodes = new Set(themeStocks.map(s => s.code));
  const originalCodes = new Set(originalStocks.map(s => s.code));
  const overlapCodes = [...themeCodes].filter(c => originalCodes.has(c));

  const overlapStocks: StockItem[] = overlapCodes.map(code =>
    themeStocks.find(s => s.code === code) ?? originalStocks.find(s => s.code === code)!
  );

  const hasData = themeStocks.length > 0 || originalStocks.length > 0;

  return (
    <PageLayout
      icon={
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="3" width="7" height="9" rx="1"/>
          <rect x="14" y="3" width="7" height="5" rx="1"/>
          <rect x="14" y="12" width="7" height="9" rx="1"/>
          <rect x="3" y="16" width="7" height="5" rx="1"/>
        </svg>
      }
      title="전략 비교"
      description="두 전략의 결과를 나란히 비교합니다"
      badge={{ text: '비교', type: 'warning' }}
      lastUpdated={result?.meta?.run_date}
    >
      {!hasData ? (
        <div className="card-static p-8 text-center">
          <p className="text-lg mb-2" style={{ color: 'var(--color-text-primary)' }}>데이터가 없습니다</p>
          <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
            두 전략을 모두 실행해주세요: <code>python main.py both</code>
          </p>
        </div>
      ) : (
        <>
          {/* 겹치는 종목 */}
          <section className="mb-8">
            <h2 className="text-xl font-bold mb-4" style={{ color: 'var(--color-text-primary)' }}>
              두 전략에 모두 포함된 종목
              {overlapStocks.length > 0 && (
                <span className="badge badge-success ml-2">강한 신호 {overlapStocks.length}개</span>
              )}
            </h2>
            {overlapStocks.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {overlapStocks.map(stock => (
                  <div key={stock.code} className="card-static p-4">
                    <div className="flex items-center gap-2 mb-1">
                      <span style={{ color: 'var(--color-success)' }}>★</span>
                      <span className="font-semibold" style={{ color: 'var(--color-text-primary)' }}>{stock.name}</span>
                      <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>{stock.code}</span>
                    </div>
                    <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>{stock.reason}</p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="card-static p-6 text-center">
                <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
                  겹치는 종목이 없습니다. 두 전략의 관점이 다릅니다.
                </p>
              </div>
            )}
          </section>

          {/* 나란히 비교 */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* 테마/모멘텀 */}
            <section>
              <h3 className="text-lg font-semibold mb-3 flex items-center gap-2" style={{ color: 'var(--color-text-primary)' }}>
                <span className="badge badge-success">테마/모멘텀</span>
                {themeStocks.length}개 종목
              </h3>
              {themeStocks.map((stock, i) => (
                <div key={stock.code} className="card-static p-3 mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold" style={{ color: 'var(--color-accent)' }}>{i + 1}</span>
                    <span className="font-medium text-sm" style={{ color: 'var(--color-text-primary)' }}>{stock.name}</span>
                    <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>{stock.code}</span>
                    <span className="ml-auto text-xs font-semibold" style={{ color: overlapCodes.includes(stock.code) ? 'var(--color-success)' : 'var(--color-text-muted)' }}>
                      {stock.confidence}
                      {overlapCodes.includes(stock.code) && ' ★'}
                    </span>
                  </div>
                </div>
              ))}
            </section>

            {/* 노션 원본 */}
            <section>
              <h3 className="text-lg font-semibold mb-3 flex items-center gap-2" style={{ color: 'var(--color-text-primary)' }}>
                <span className="badge badge-info">노션 원본</span>
                {originalStocks.length}개 종목
              </h3>
              {originalStocks.length > 0 ? (
                originalStocks.map((stock, i) => (
                  <div key={stock.code} className="card-static p-3 mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold" style={{ color: 'var(--color-accent)' }}>{i + 1}</span>
                      <span className="font-medium text-sm" style={{ color: 'var(--color-text-primary)' }}>{stock.name}</span>
                      <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>{stock.code}</span>
                      <span className="ml-auto text-xs font-semibold" style={{ color: overlapCodes.includes(stock.code) ? 'var(--color-success)' : 'var(--color-text-muted)' }}>
                        {stock.confidence}
                        {overlapCodes.includes(stock.code) && ' ★'}
                      </span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="card-static p-6 text-center">
                  <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>아직 실행되지 않았습니다</p>
                </div>
              )}
            </section>
          </div>
        </>
      )}
    </PageLayout>
  );
}

export default Compare;
