# PRD: RumpTACO — Trump Always Chickens Out 통합 예측 시뮬레이터

- **문서 버전:** v0.1 (Draft)
- **작성일:** 2026-04-15
- **작성자:** Nerd Master (with Claude)
- **상태:** Draft — 검토 대기

---

## 1. 개요 (Overview)

### 1.1 제품 정의
**RumpTACO**는 트럼프 대통령의 정책 발언과 시장/정치 압박 지표를 실시간으로 통합 분석하여, **"Trump Always Chickens Out (TACO)" — 정책 후퇴(번복) 발생 확률과 예상 시점**을 정량적으로 예측하는 AI 기반 시뮬레이터다.

### 1.2 문제 정의 (Problem Statement)
- 트럼프의 정책 발언은 시장 변동성을 즉각적으로 유발하지만, **번복(chicken out) 패턴이 반복적**이다.
- 개인 투자자/트레이더는 발언의 "실행 강도"와 "회항 가능성"을 직관에만 의존하고 있다.
- 과거 패턴(2019 미중 무역전쟁, 2024~2025 관세 위협 등)을 체계적으로 학습한 모델이 부재하다.

### 1.3 타깃 사용자
1. **암호화폐/주식 단기 트레이더** — TACO 발생 시점에 저점 매수 타이밍 포착
2. **매크로 리서처/뉴스레터 운영자** — 정책 리스크 정량화 자료
3. **일반 정치/경제 관심층** — "이번엔 진짜일까?" 판단 보조

### 1.4 성공 지표 (Success Metrics)
| 지표 | 목표 (MVP) | 목표 (v1.0) |
|---|---|---|
| TACO 예측 정확도 (백테스팅 기준) | ≥ 65% | ≥ 80% |
| 평균 알림 선행 시간 (TACO 발생 전) | 6시간 | 24시간 |
| 일일 활성 사용자 (DAU) | 50 | 1,000 |
| 데이터 파이프라인 가동률 | 95% | 99.5% |

---

## 2. 핵심 기능 (Core Features)

### 2.1 모듈 구조

#### Module A — Sentiment Aggression Engine (공격 지수)
- **입력:** Truth Social, X(Twitter), 백악관 공식 발표, 주요 연설 트랜스크립트
- **처리:** Claude Opus 4.6으로 발언의 (1) 위협 강도 (2) 구체성 (3) 시한 명시 여부를 0~100점으로 스코어링
- **출력:** `aggression_score` (0~100), `topic_tags` (관세/이민/외교 등)

#### Module B — Pain Point Tracker (고통 지수)
- **추적 지표:**
  - US 10Y Treasury Yield
  - S&P 500 / VIX
  - Dow Jones Industrial Average (DJIA)
  - NASDAQ Composite
  - WTI 원유 선물 가격
  - 기대인플레이션 (5Y Breakeven Inflation Rate, FRED: T5YIE)
  - BTC 가격 및 24h 변동률
  - 트럼프 지지율 (538, RealClearPolitics 평균)
  - Polymarket 관련 시장 오즈
- **출력:** `pain_index` (0~100, 가중 합산)

#### Module C — Chicken Out Threshold Engine (회항 임계점)
- **로직:** 과거 사례 데이터셋(N≥30 케이스)으로부터 `aggression_score × pain_index` 조합별 TACO 발생 확률 분포 학습
- **모델:** 초기는 로지스틱 회귀 + Gradient Boosting, v1.0에서 시계열 LSTM 검토
- **출력:** `taco_probability` (0~100%), `expected_window` (예상 번복 시간 윈도우)

#### Module D — Simulation Dashboard
- **UI 요소:**
  - 실시간 TACO 확률 게이지 (대형)
  - 공격 지수 vs 고통 지수 2D 산점도 (현재 위치 + 과거 케이스 오버레이)
  - 타임라인: 최근 발언 → 시장 반응 → 예상 번복 시점
  - 관련 자산(BTC/SOL) 미니 차트

#### Module E — Killer Features
1. **Trump-to-Crypto 상관계수** — 발언별 BTC 즉각 반응 및 TACO 후 회복 탄력성 지수
2. **실시간 알림** — TACO 확률 ≥ 80% 시 Telegram/Slack 푸시 ("저점 매수 시그널")
3. **백테스팅 모드** — 과거 사건 입력 시 모델이 어떻게 예측했을지 시뮬레이션

---

## 3. 기술 스택 (Tech Stack)

| 계층 | 선택 | 이유 |
|---|---|---|
| IDE | Cursor | Vibe coding 최적화 |
| Language | Python 3.11+ | 데이터 분석 생태계 |
| Backend | FastAPI | 비동기 API, 가벼움 |
| Frontend | Next.js + Tailwind | Vercel 배포 친화 |
| LLM | Claude Opus 4.6 (메인), Haiku 4.5 (경량 분류) | 컨텍스트/추론 품질 |
| Research Agent | Perplexity API, Tavily API | 실시간 뉴스 |
| Scraping | Playwright | 동적 페이지 (Polymarket 등) |
| Data | CoinGecko API, FRED API, Solana RPC | 가격/매크로/온체인 |
| Storage | Supabase (Postgres) | 시계열 + 인증 무료 티어 |
| Deploy | Vercel (FE) + Railway (BE/Worker) | 속도 |
| Notification | Telegram Bot API, Slack Webhook | 무료, 빠름 |

---

## 4. 데이터 모델 (핵심 스키마)

```sql
-- 발언 이벤트
statements (
  id, source, url, content, posted_at,
  aggression_score, topic_tags[], processed_at
)

-- 시장 스냅샷 (1분 단위)
market_snapshots (
  ts, treasury_10y, sp500, vix, djia, nasdaq,
  wti_usd, breakeven_5y, btc_usd,
  trump_approval, polymarket_odds_json
)

-- TACO 사례 (학습/검증용)
taco_cases (
  id, statement_id, declared_at, reverted_at,
  reversion_lag_hours, aggression_at_decl, pain_at_decl,
  pain_at_revert, was_taco BOOL
)

-- 예측 로그
predictions (
  ts, taco_probability, expected_window_hours,
  trigger_statement_id, model_version
)
```

---

## 5. 개발 로드맵 (Phased Plan)

### Phase 0 — Foundation (1주)
- 레포 셋업, Supabase 스키마, 환경변수, CI
- Playwright + API 클라이언트 PoC

### Phase 1 — Data Pipeline (2주) — **MVP 핵심**
- Truth Social / X 스크레이퍼 (Playwright)
- 시장 데이터 1분 단위 수집 워커
- 과거 TACO 케이스 30건 수동 라벨링

### Phase 2 — Scoring Engines (2주)
- Module A (Aggression) — Claude 프롬프트 엔지니어링 + 캐시
- Module B (Pain) — 가중치 튜닝
- Module C (Threshold) — 로지스틱 + GBM 베이스라인

### Phase 3 — Dashboard MVP (2주)
- Next.js 대시보드, 게이지 + 타임라인
- 백테스팅 UI

### Phase 4 — Alerts & Killer Features (1주)
- Telegram 봇
- BTC/SOL 상관계수 카드

### Phase 5 — Beta 공개 & 튜닝 (지속)
- 트위터/디스코드 베타 모집
- 모델 정확도 모니터링 + 주간 리트레인

**총 MVP 기간 추정:** 약 8주 (개인 개발자 기준, vibe coding 가속)

---

## 6. 리스크 및 대응

| 리스크 | 영향 | 완화 방안 |
|---|---|---|
| Truth Social 스크레이핑 차단 | High | 다중 소스 (X, 뉴스 API) 페일오버 |
| TACO 케이스 데이터 부족 (N<30) | High | 초기엔 룰베이스 + LLM judge 병행 |
| LLM 비용 폭증 | Med | Haiku 1차 필터 → Opus 정밀 분석 2단계 |
| 정치적 편향 논란 | Med | 면책 고지 + 데이터 소스 투명 공개 |
| 시장 데이터 API rate limit | Low | 로컬 캐시 + 1분 폴링 상한 |

---

## 7. 비범위 (Out of Scope, MVP)
- 트럼프 외 타국 정상 (시진핑/푸틴) 발언 분석
- 자동 매매 봇 연동
- 모바일 네이티브 앱
- 다국어 (영어/한국어 외)

---

## 8. 다음 단계 (Next Actions)
1. **본 PRD 검토 및 승인** ← 현재 단계
2. Phase 0 착수 — 레포 초기화 + Supabase 프로젝트 생성
3. 과거 TACO 케이스 후보 리스트업 (별도 리서치 세션)
4. Aggression Engine 프롬프트 v0 작성 및 5개 발언으로 smoke test
