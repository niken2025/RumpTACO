# RumpTACO

트럼프의 정책 발언과 시장 압박 지표로 **TACO (Trump Always Chickens Out)** 확률을 매일 산출하는 배치 시스템.

> ⚠️ 투자 권유 아님. 정보 제공 목적. 실험적 룰베이스 v0.1.

## 문서
- [PRD.md](PRD.md) — 전체 제품 사양
- [AUTOMATION_DESIGN.md](AUTOMATION_DESIGN.md) — 1단계 MVP 설계서
- [CLAUDE.md](CLAUDE.md) — Claude Code 작업 규칙

## 빠른 시작

```bash
# 1. 의존성
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. 환경변수
cp .env.example .env        # Windows: copy .env.example .env
# .env 편집 — ANTHROPIC_API_KEY, FRED_API_KEY, TELEGRAM_* 채우기

# 3. 스모크 테스트
python cli.py smoke-pain    # Pain Index 공식 확인 (API 불필요)
python cli.py smoke-agg     # Aggression 점수화 (ANTHROPIC_API_KEY 필요)

# 4. 수동 전체 실행
python cli.py daily --no-send   # 미리보기
python cli.py daily             # 텔레그램 발송

# 5. Supabase 스키마
# supabase/migrations/0001_init.sql 을 Supabase SQL Editor에 붙여넣기
```

## 자동 실행
`.github/workflows/daily.yml` 이 매일 KST 06:00 (UTC 21:00) 트리거.
GitHub repo Secrets에 `.env` 항목들을 등록하면 자동 발송.

## 커맨드
| 커맨드 | 용도 |
|--------|------|
| `python cli.py collect` | 지표·발언 수집만 (stdout) |
| `python cli.py score` | 발언 Aggression 점수화 |
| `python cli.py predict` | 예측까지 (발송 X) |
| `python cli.py daily` | 전체 파이프라인 + 텔레그램 발송 |
| `python cli.py smoke-agg` | Aggression 샘플 3건 테스트 |
| `python cli.py smoke-pain` | Pain Index 샘플 테스트 |

## 1단계 MVP 범위
- ✅ 9개 시장지표 수집 (FRED/Yahoo/CoinGecko)
- ✅ Tavily 뉴스 페일오버 발언 수집
- ✅ Claude Haiku 1차 → Opus 정밀 점수화
- ✅ 룰베이스 TACO 확률 (공식: composite + interaction sigmoid)
- ✅ 텔레그램 리포트 + 일별 마크다운 로그
- ✅ GitHub Actions 일일 cron
- ❌ 실시간 폴링 / Next.js 대시보드 / 자동 매매 (3단계)
