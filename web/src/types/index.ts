export interface StockItem {
  code: string;
  name: string;
  reason: string;
  risk: string;
  confidence: string | number;
  path: string;
  close?: number;
  change_pct?: number;
  marcap_eok?: number;
}

export interface ResultMeta {
  run_date: string;
  model: string;
  reasoning_effort: string;
  universe_count: number;
  ohlcv_cached_count: number;
  min_market_cap: number;
  strategy: string;
}

export interface Top10Result {
  meta: ResultMeta;
  strategy_a_original?: StockItem[];
  strategy_b_theme?: StockItem[];
}
