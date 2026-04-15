-- RumpTACO 초기 스키마
-- 실행: Supabase SQL Editor에 붙여넣기 또는 `supabase db push`

create extension if not exists "uuid-ossp";

-- 트럼프 발언 이벤트
create table if not exists statements (
  id uuid primary key default uuid_generate_v4(),
  source text not null check (source in ('truth_social','x','whitehouse','news','manual')),
  url text,
  content text not null,
  posted_at timestamptz not null,
  aggression_score numeric,
  threat_intensity numeric,
  specificity numeric,
  deadline_specified boolean,
  topic_tags text[] default '{}',
  scoring_model text,
  scoring_rationale text,
  processed_at timestamptz,
  created_at timestamptz default now()
);
create index if not exists idx_statements_posted_at on statements(posted_at desc);
create index if not exists idx_statements_topic_tags on statements using gin(topic_tags);

-- 시장 스냅샷 (일 단위; 실시간 확장 시 1분 단위로 변경)
create table if not exists market_snapshots (
  ts timestamptz primary key,
  treasury_10y numeric,
  sp500 numeric,
  vix numeric,
  djia numeric,
  nasdaq numeric,
  wti_usd numeric,
  breakeven_5y numeric,
  btc_usd numeric,
  trump_approval numeric,
  polymarket_odds jsonb,
  raw jsonb,
  created_at timestamptz default now()
);

-- TACO 과거 케이스 (학습/검증용)
create table if not exists taco_cases (
  id uuid primary key default uuid_generate_v4(),
  statement_id uuid references statements(id),
  declared_at timestamptz not null,
  reverted_at timestamptz,
  reversion_lag_hours numeric,
  aggression_at_decl numeric,
  pain_at_decl numeric,
  pain_at_revert numeric,
  was_taco boolean not null,
  notes text,
  created_at timestamptz default now()
);
create index if not exists idx_taco_cases_declared_at on taco_cases(declared_at desc);

-- 예측 로그
create table if not exists predictions (
  id uuid primary key default uuid_generate_v4(),
  ts timestamptz not null default now(),
  taco_probability numeric not null,
  expected_window_hours numeric,
  trigger_statement_id uuid references statements(id),
  aggression_score numeric,
  pain_index numeric,
  model_version text not null,
  explanation text,
  created_at timestamptz default now()
);
create index if not exists idx_predictions_ts on predictions(ts desc);
