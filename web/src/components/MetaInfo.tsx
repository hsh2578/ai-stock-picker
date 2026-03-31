import type { ResultMeta } from '../types';

function MetaInfo({ meta }: { meta: ResultMeta }) {
  const items = [
    { icon: '🤖', label: '모델', value: meta.model },
    { icon: '🧠', label: '추론', value: meta.reasoning_effort },
    { icon: '📊', label: '유니버스', value: `${meta.universe_count.toLocaleString()}개` },
    { icon: '💰', label: '시총 기준', value: `${(meta.min_market_cap / 1_0000_0000).toLocaleString()}억+` },
  ];

  return (
    <div className="flex flex-wrap gap-3 mb-5">
      {items.map(item => (
        <div key={item.label} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm"
          style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}>
          <span>{item.icon}</span>
          <span style={{ color: 'var(--text-muted)' }}>{item.label}</span>
          <span className="font-semibold" style={{ color: 'var(--text-strong)' }}>{item.value}</span>
        </div>
      ))}
    </div>
  );
}

export default MetaInfo;
