import { useState } from 'react';
import type { StockItem } from '../types';

interface StockCardProps {
  rank: number;
  stock: StockItem;
}

function parseConfidence(val: string | number): number {
  if (typeof val === 'number') return val;
  const n = parseInt(String(val).replace('%', '').replace(/[^0-9]/g, ''), 10);
  return isNaN(n) ? 50 : n;
}

function confColor(v: number) {
  if (v >= 70) return { color: '#10b981', bg: 'rgba(16,185,129,0.1)', label: '강력' };
  if (v >= 55) return { color: '#f59e0b', bg: 'rgba(245,158,11,0.1)', label: '양호' };
  return { color: '#ef4444', bg: 'rgba(239,68,68,0.08)', label: '주의' };
}

function StockCard({ rank, stock }: StockCardProps) {
  const [open, setOpen] = useState(false);
  const cv = parseConfidence(stock.confidence);
  const cc = confColor(cv);
  const summary = stock.reason.split(/[.。]/)[0];

  return (
    <div className="card-flat overflow-hidden mb-3 cursor-pointer" onClick={() => setOpen(!open)}
      style={{ borderLeft: `3px solid ${cc.color}` }}>

      {/* ─── 메인 행 ─── */}
      <div className="flex items-center gap-4 px-5 py-4">
        {/* 순위 */}
        <div className="flex-shrink-0 text-center" style={{ width: 36 }}>
          <div className="text-2xl font-black" style={{ color: cc.color }}>{rank}</div>
        </div>

        {/* 종목 정보 */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="font-bold text-base" style={{ color: 'var(--text-strong)' }}>{stock.name}</span>
            <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>{stock.code}</span>
            {stock.change_pct !== undefined && (
              <span className="text-xs font-bold px-1.5 py-0.5 rounded"
                style={{
                  color: stock.change_pct > 0 ? '#ef4444' : stock.change_pct < 0 ? '#3b82f6' : 'var(--text-muted)',
                  background: stock.change_pct > 0 ? 'rgba(239,68,68,0.08)' : stock.change_pct < 0 ? 'rgba(59,130,246,0.08)' : 'transparent',
                }}>
                {stock.change_pct > 0 ? '+' : ''}{stock.change_pct}%
              </span>
            )}
            {stock.close !== undefined && (
              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                {stock.close.toLocaleString()}원
              </span>
            )}
            {stock.marcap_eok !== undefined && (
              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                {stock.marcap_eok >= 10000
                  ? `${(stock.marcap_eok / 10000).toFixed(1)}조`
                  : `${stock.marcap_eok.toLocaleString()}억`}
              </span>
            )}
          </div>
          <p className="text-sm truncate" style={{ color: 'var(--text-light)' }}>{summary}</p>
        </div>

        {/* 확신도 */}
        <div className="flex-shrink-0 text-center px-3 py-1.5 rounded-lg"
          style={{ background: cc.bg, minWidth: 56 }}>
          <div className="text-xl font-extrabold leading-none" style={{ color: cc.color }}>{cv}</div>
          <div className="text-[10px] font-semibold mt-0.5" style={{ color: cc.color }}>{cc.label}</div>
        </div>

        {/* 화살표 */}
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
          stroke="var(--text-muted)" strokeWidth="2" strokeLinecap="round"
          style={{ transition: 'transform 0.2s', transform: open ? 'rotate(180deg)' : '' }}>
          <path d="M6 9l6 6 6-6"/>
        </svg>
      </div>

      {/* ─── 상세 (펼침) ─── */}
      {open && (
        <div className="px-5 pb-5 pt-0" style={{ borderTop: '1px solid var(--border)' }}>
          {/* 선정 이유 */}
          <div className="mt-4 mb-3">
            <div className="flex items-center gap-1.5 mb-2">
              <div className="w-1.5 h-1.5 rounded-full" style={{ background: 'var(--success)' }}/>
              <span className="text-xs font-bold tracking-wide" style={{ color: 'var(--success)' }}>선정 이유</span>
            </div>
            <p className="text-sm leading-relaxed pl-3" style={{ color: 'var(--text)' }}>{stock.reason}</p>
          </div>

          {/* 리스크 */}
          <div className="mb-3 p-3 rounded-lg" style={{ background: 'var(--danger-bg)' }}>
            <div className="flex items-center gap-1.5 mb-1.5">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--danger)" strokeWidth="2.5">
                <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>
                <path d="M12 9v4"/><path d="M12 17h.01"/>
              </svg>
              <span className="text-xs font-bold" style={{ color: 'var(--danger)' }}>리스크</span>
            </div>
            <p className="text-sm leading-relaxed" style={{ color: 'var(--text)' }}>{stock.risk}</p>
          </div>

          {/* 분석 경로 */}
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-[11px] font-medium" style={{ color: 'var(--text-muted)' }}>분석 경로</span>
            {stock.path.split(/[→;+]/).map(s => s.trim()).filter(Boolean).map((step, i) => (
              <span key={i}>
                {i > 0 && <span className="text-[10px] mx-0.5" style={{ color: 'var(--text-muted)' }}>→</span>}
                <span className="text-[11px] px-1.5 py-0.5 rounded"
                  style={{ background: 'var(--accent-bg)', color: 'var(--accent)', fontWeight: 500 }}>
                  {step}
                </span>
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default StockCard;
