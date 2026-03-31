import { Link } from 'react-router-dom';
import type { ReactNode } from 'react';

interface PageLayoutProps {
  icon: ReactNode;
  title: string;
  description: string;
  badge?: { text: string; type: 'success' | 'warning' | 'danger' | 'info' };
  lastUpdated?: string;
  totalCount?: number;
  children: ReactNode;
}

function PageLayout({ icon, title, description, badge, lastUpdated, totalCount, children }: PageLayoutProps) {
  const formatDate = (s: string) => new Date(s).toLocaleDateString('ko-KR', {
    year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit',
  });

  return (
    <div className="min-h-screen">
      {/* 네비게이션 */}
      <nav className="nav-bar px-4 md:px-8 py-3">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 text-sm font-medium hover:opacity-80"
            style={{ color: 'var(--text-light)' }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M15 18l-6-6 6-6"/></svg>
            홈으로
          </Link>
          {lastUpdated && (
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{formatDate(lastUpdated)}</span>
          )}
        </div>
      </nav>

      {/* 헤더 */}
      <header className="py-8 px-4 text-center" style={{ background: 'var(--bg-header)' }}>
        <div className="max-w-5xl mx-auto">
          <div className="flex items-center justify-center gap-3 mb-2">
            <span className="text-white opacity-80">{icon}</span>
            <h1 className="text-2xl md:text-3xl font-bold text-white">{title}</h1>
            {badge && <span className={`badge badge-${badge.type}`}>{badge.text}</span>}
          </div>
          <p className="text-sm text-white/60">{description}</p>
          {totalCount !== undefined && (
            <p className="text-sm mt-2 font-semibold text-white/80">{totalCount}개 종목 추천</p>
          )}
        </div>
      </header>

      {/* 본문 */}
      <main className="max-w-5xl mx-auto px-4 md:px-8 py-6">
        {children}
      </main>
    </div>
  );
}

export default PageLayout;
