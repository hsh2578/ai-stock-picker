import { useEffect, useState } from 'react';
import PageLayout from '../components/PageLayout';
import StockCard from '../components/StockCard';
import MetaInfo from '../components/MetaInfo';
import type { Top10Result } from '../types';

function OriginalStrategy() {
  const [result, setResult] = useState<Top10Result | null>(null);

  useEffect(() => {
    fetch(import.meta.env.BASE_URL + 'data/top10_result.json')
      .then(res => res.json())
      .then(data => setResult(data))
      .catch(() => {});
  }, []);

  const stocks = result?.strategy_a_original ?? [];

  return (
    <PageLayout
      icon={
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/>
          <polyline points="16 7 22 7 22 13"/>
        </svg>
      }
      title="노션 원본 전략"
      description="MA 이동평균선 돌파 + RS 상대강도 기반 추세 추종"
      badge={{ text: '원본', type: 'info' }}
      lastUpdated={result?.meta?.run_date}
      totalCount={stocks.length}
    >
      {result?.meta && <MetaInfo meta={result.meta} />}

      {stocks.length === 0 ? (
        <div className="card-static p-8 text-center">
          <p className="text-lg mb-2" style={{ color: 'var(--color-text-primary)' }}>데이터가 없습니다</p>
          <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
            노션 원본 전략을 먼저 실행해주세요: <code>python main.py original</code>
          </p>
        </div>
      ) : (
        stocks.map((stock, i) => (
          <StockCard key={stock.code} rank={i + 1} stock={stock} />
        ))
      )}
    </PageLayout>
  );
}

export default OriginalStrategy;
