# RumpTACO — Project Context

## 프로젝트 정체성
트럼프 대통령의 정책 발언과 시장/정치 압박 지표를 매일 1회 분석해, "Trump Always Chickens Out(TACO)" 확률을 정량화하고 텔레그램으로 리포트하는 일일 배치 시스템.

상세 사양은 [PRD.md](PRD.md), 1단계 MVP 설계는 [AUTOMATION_DESIGN.md](AUTOMATION_DESIGN.md) 참조.

## 핵심 원칙

### TACO 정의
- **TACO 발생**: 트럼프가 공개적으로 표명한 정책/위협을 48시간 이내에 철회·유예·완화하는 경우
- **판단 기준**: 공식 발언(Truth Social / 백악관 / 주요 연설)을 소스로, 이후 공식 발언이나 정책 문서로 번복된 경우

### 점수화 기준
- **Aggression Score (0~100)**: 위협 강도(40%) + 구체성(30%) + 시한 명시(30%)
- **Pain Index (0~100)**: 9개 지표 Z-score 가중 합산
  - 지표: 10Y Treasury, S&P500, DJIA, NASDAQ, VIX, WTI, 5Y Breakeven Inflation, BTC, 트럼프 지지율
- **TACO Probability**: `sigmoid(w₁·aggression + w₂·pain + b)` — 1단계는 룰베이스, 2단계부터 로지스틱 회귀로 학습

### 데이터 소스 우선순위
1. **시장지표**: FRED (Treasury/BEI), Yahoo Finance (SPX/DJIA/IXIC/VIX/WTI), CoinGecko (BTC), 538/RCP 스크랩 (지지율)
2. **발언**: Truth Social RSS 미러 → X RSS → 뉴스 API (Perplexity/Tavily) 페일오버
3. **Polymarket**: 1단계는 수동, 3단계에서 Playwright

## 코드 규칙
- **언어**: Python 3.11+, 한국어 주석 허용, 리포트는 한국어
- **LLM 비용**: Gemini 1.5 Flash 1차 필터(무료 티어) → 시그널 강하면 Gemini 1.5 Pro 정밀 분석
- **비밀값**: `.env`만 사용, 절대 커밋 금지 (`.gitignore` 필수)
- **데이터 저장**: Supabase (Postgres), 개인정보 X, 공개 정보만
- **리포트 면책**: 모든 출력 하단에 "투자 권유 아님, 정보 제공 목적" 명시
- **실험적 라벨**: 백테스팅 전까지 리포트에 "실험적 룰베이스" 표기

## 디렉터리 구조
```
RumpTACO/
├── CLAUDE.md, PRD.md, AUTOMATION_DESIGN.md
├── .env.example, .gitignore, requirements.txt
├── cli.py                    # Typer CLI 엔트리
├── collectors/
│   ├── market.py             # 시장지표 수집
│   └── statements.py         # 발언 수집 (RSS/뉴스 API)
├── scoring/
│   ├── aggression.py         # Claude API로 발언 점수화
│   └── pain.py               # 지표 Z-score + 가중합
├── models/
│   └── rule_based.py         # 1단계 TACO 확률 산출
├── notify/
│   └── telegram.py           # 텔레그램 리포트 발송
├── reports/                  # YYYY-MM-DD.md 일별 로그
├── supabase/migrations/      # SQL 마이그레이션
├── .claude/
│   ├── agents/               # aggression-scorer.md, pain-aggregator.md
│   └── skills/               # taco-daily, taco-backtest
└── .github/workflows/daily.yml
```

## 커밋 규칙 (사용자 전역 규칙 반영)
- 의미 있는 변경마다 자동 커밋, 메시지는 구체적으로
- 되돌릴 때는 revert 우선

## 1단계 범위 외 (3단계에서)
- 실시간 5분 폴링
- Truth Social 직접 크롤링
- Next.js 대시보드 + Vercel 배포
- 자동 매매 연동
