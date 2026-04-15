# 자동화 설계서: RumpTACO MVP (1단계)

## 한줄 요약
트럼프의 정책 발언과 시장 압박 지표를 매일 1회 수집·분석해, "정책 후퇴(TACO) 발생 확률"을 텔레그램으로 자동 리포트하는 일일 배치 시스템.

## 데이터 흐름

```
[트럼프 발언 RSS/뉴스] ──┐
[시장지표 API:           ├─→ [Claude 점수화] → [TACO 확률 계산]
 10Y금리/S&P/DJIA/       │                              │
 NASDAQ/VIX/WTI/         │                              ▼
 5Y기대인플/BTC/지지율]  │                  👤 사람 확인 (선택)
                         │                              │
                         │                              ▼
                         └─────────────→ [텔레그램 일일 리포트 + 근거]
```

## 입력
- **데이터**:
  - 트럼프 발언 (Truth Social RSS 미러, X RSS, 주요 뉴스 헤드라인)
  - 시장지표 9종 (Treasury 10Y, S&P500, DJIA, NASDAQ, VIX, WTI, 5Y Breakeven, BTC, 트럼프 지지율)
  - Polymarket 관련 시장 오즈 (선택)
- **형태**: JSON (API 응답), HTML (RSS), CSV (FRED)
- **위치**: 외부 API + Supabase 캐시
- **주기**: 매일 1회 (미국 시장 마감 후, KST 06:00)

## 출력
- **결과물**: 텔레그램 채널 리포트 (Markdown)
  - 오늘의 TACO 확률 (0~100%)
  - 핵심 발언 요약 + Aggression 점수
  - 시장 압박 지표 변화
  - 과거 유사 사례 비교
  - 산출 근거 (사람이 검증 가능)
- **형태**: 텔레그램 메시지 + 일별 마크다운 로그 (`reports/YYYY-MM-DD.md`)
- **대상**: 본인 + 베타 구독자 (수동 초대)

## 추천 구현 패턴

**핵심 패턴: 패턴1(Skill) + 패턴5(MCP/외부API) + 패턴4(Hook으로 일일 트리거)**

데이터 수집·분석·리포트를 매일 같은 절차로 반복하므로 Skill로 묶고, 외부 데이터/텔레그램은 MCP 또는 직접 API로 연결, cron 스케줄러가 매일 트리거합니다.

| 구성 요소 | 역할 | 상세 |
|----------|------|------|
| CLAUDE.md | 프로젝트 규칙·맥락 | TACO 정의, 점수화 기준, 면책 고지, 데이터 소스 우선순위, "투자 권유 아님" 톤 |
| Skill: `/taco-daily` | 일일 분석 워크플로 | 1) 데이터 수집 2) Aggression 점수화 3) Pain 지수 합산 4) TACO 확률 산출 5) 텔레그램 발송 |
| Skill: `/taco-backtest` | 과거 케이스 시뮬레이션 | 입력: 날짜 / 출력: 그날 모델이 예측했을 확률 vs 실제 결과 |
| Agent: `aggression-scorer.md` | 발언 점수화 전문가 | "위협 강도/구체성/시한 명시" 3축 평가, 0~100점, 근거 1줄 필수 |
| Agent: `pain-aggregator.md` | 시장 압박 합산 | 9개 지표 가중치 정규화, 이상치 플래그, Z-score 변환 |
| Python | 데이터 처리·모델 | `requests`, `pandas`, `scikit-learn` (Phase 2 모델 학습) |
| MCP/직접 API | 외부 연결 | FRED, CoinGecko, Yahoo Finance, Telegram Bot API |
| Supabase | 시계열 저장 | `statements`, `market_snapshots`, `predictions` 3개 테이블 (PRD 스키마 축약) |
| Hook (cron) | 일일 자동 트리거 | Railway/GitHub Actions cron으로 매일 KST 06:00 `/taco-daily` 실행 |

## 단계별 구현 계획

### Step 1: 프로젝트 골격 (Day 1~2)
- 할 일: 레포 초기화, CLAUDE.md 작성, Supabase 프로젝트 + 3개 테이블 마이그레이션, `.env` 템플릿
- 산출물: `CLAUDE.md`, `supabase/migrations/0001_init.sql`, `.env.example`
- 예상 소요: 4시간

### Step 2: 데이터 수집기 (Day 3~5)
- 할 일: 9개 지표 수집 Python 스크립트 + RSS 발언 수집기, Supabase에 저장
- 산출물: `collectors/market.py`, `collectors/statements.py`, `cli.py collect`
- 예상 소요: 8시간

### Step 3: Aggression Agent + 점수화 (Day 6~7)
- 할 일: `.claude/agents/aggression-scorer.md` 작성, 5개 발언으로 smoke test, 캐시 적용
- 산출물: 에이전트 파일 + `cli.py score-statements`
- 예상 소요: 6시간

### Step 4: TACO 확률 산출 룰베이스 (Day 8~9)
- 할 일: Aggression × Pain 가중합 룰 + 임계점 (학습 전 임시 룰)
- 산출물: `models/rule_based.py`, `cli.py predict`
- 예상 소요: 4시간

### Step 5: 텔레그램 리포트 + Skill 통합 (Day 10~12)
- 할 일: 텔레그램 봇 발송, 마크다운 리포트 템플릿, `/taco-daily` Skill 작성
- 산출물: `.claude/skills/taco-daily/skill.md`, `notify/telegram.py`
- 예상 소요: 6시간

### Step 6: 자동 트리거 + 운영 (Day 13~14)
- 할 일: GitHub Actions cron 또는 Railway scheduler 설정, 1주일 시범 운영
- 산출물: `.github/workflows/daily.yml`, 운영 로그
- 예상 소요: 4시간

**1단계 합계: 약 32시간 / 2주**

## 실현 가능성

✅ **바로 가능**: CLAUDE.md, Skills, Agents, Python 데이터 처리, FRED/CoinGecko/Yahoo API, 룰베이스 점수화

🔶 **도전 가능 (Claude Code 도움으로)**:
- Supabase 스키마 + RLS 설정 — "공유 엑셀 같은 클라우드 DB. CC가 마이그레이션 SQL 짜줌"
- Telegram Bot API — "초기 토큰 발급만 하면 메시지 발송은 한 줄"
- GitHub Actions cron — "매일 정해진 시간에 자동 실행되는 알람시계"

❌ **이번 1단계에서는 제외**:
- Truth Social 직접 크롤링 → **대안: RSS 미러 + 뉴스 API 페일오버**
- 실시간 5분 폴링 → **대안: 일일 배치부터, 3단계에서 확장**
- Polymarket 동적 크롤링 → **대안: 1단계는 수동 입력, 안정화 후 Playwright**

## 주의사항
- **면책 고지 필수**: 모든 리포트 하단에 "투자 권유 아님, 정보 제공 목적" 명시
- **데이터 소스 투명 공개**: 어떤 발언/지표를 썼는지 리포트에 기재 (편향 논란 대응)
- **Claude API 비용 관리**: Aggression 점수화는 Haiku 4.5 1차 필터 → 강한 시그널만 Opus 4.6 정밀 분석
- **백테스팅 전 모델 신뢰 금지**: 1단계는 "실험적 룰베이스" 라벨 명시
- **개인정보 X**: 수집 데이터는 모두 공개 정보. `.env`에 API 키만 보관, 절대 커밋 금지

## 사람이 확인할 포인트 (Human in the Loop)
- **첫 2주 시범 운영**: 매일 리포트를 사람이 직접 검토 → "이 점수가 직관과 맞는가" 평가 → 가중치 튜닝
- **TACO 발생 시점 라벨링**: 자동 감지 어려움 → 사람이 "이건 TACO다/아니다" 마킹 → 학습 데이터 축적
- **알림 임계값 발송 전 확인**: 1단계는 "확률 산출만 발송", 자동 알림은 백테스팅 후 활성화
