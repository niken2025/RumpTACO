-- 2차 마이그레이션: statements 테이블에 번역·태그·저자 필드 추가
alter table statements
  add column if not exists translated text,
  add column if not exists author text default 'trump';

-- 일일 집계 뷰 (대시보드 history 용도)
create or replace view daily_taco_summary as
select
  to_char(ts at time zone 'Asia/Seoul', 'YYYY-MM-DD') as date,
  (array_agg(taco_probability order by ts desc))[1] as taco_probability,
  (array_agg(aggression_score order by ts desc))[1] as aggression_score,
  (array_agg(pain_index order by ts desc))[1] as pain_index,
  (array_agg(model_version order by ts desc))[1] as model_version,
  max(ts) as generated_at
from predictions
group by 1
order by 1 desc;

-- Row Level Security: 공개 읽기 허용 (anon key로 대시보드에서 접근)
alter table predictions enable row level security;
alter table market_snapshots enable row level security;
alter table statements enable row level security;

drop policy if exists "public read predictions" on predictions;
create policy "public read predictions" on predictions for select using (true);

drop policy if exists "public read snapshots" on market_snapshots;
create policy "public read snapshots" on market_snapshots for select using (true);

drop policy if exists "public read statements" on statements;
create policy "public read statements" on statements for select using (true);
