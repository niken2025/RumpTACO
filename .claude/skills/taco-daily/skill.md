---
name: taco-daily
description: 오늘의 TACO 확률을 산출해 텔레그램으로 리포트 발송. 시장지표 9종 수집 → 발언 수집 → Aggression 점수화 → Pain Index 합산 → 룰베이스 확률 산출 → 텔레그램 발송.
---

# /taco-daily — 일일 TACO 리포트

## 언제 사용
- 매일 KST 06:00 cron 트리거
- 수동 점검 시: `/taco-daily` 또는 `/taco-daily hours=12`

## 실행 절차

1. **환경 확인**
   - `.env` 로드 (ANTHROPIC_API_KEY, FRED_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
   - 키 누락 시 경고 로그 + 가능한 범위에서 진행

2. **시장 스냅샷 수집** — `collectors/market.py`
   - FRED: `DGS10`, `T5YIE`
   - Yahoo Finance: `^GSPC`, `^DJI`, `^IXIC`, `^VIX`, `CL=F`
   - CoinGecko: `bitcoin` USD
   - 지지율: 수동 (현재값 argument 전달)

3. **발언 수집** — `collectors/statements.py`
   - 우선순위: Truth Social RSS → X RSS → Tavily 뉴스 페일오버
   - 지난 24시간 기준, URL 기준 중복 제거

4. **Aggression 점수화** — `scoring/aggression.py`
   - Haiku 4.5로 1차 점수화
   - 점수 ≥ 50인 발언만 Opus 4.6 재평가
   - 실패 시 해당 발언 건너뛰고 진행

5. **Pain Index 계산** — `scoring/pain.py`
   - 9개 지표 Z-score 가중합, 결측은 가중치 재정규화

6. **TACO 확률 산출** — `models/rule_based.py`
   - Aggression(max) × Pain 조합 룰베이스 공식
   - 결과에 `model_version = "rule-based-v0.1"` 기록

7. **리포트 생성 및 발송** — `notify/telegram.py`
   - Markdown 리포트 생성
   - `reports/YYYY-MM-DD.md` 저장
   - `TELEGRAM_BOT_TOKEN` 있으면 채널 발송, 없으면 콘솔 출력
   - 하단에 "투자 권유 아님" 면책 고지 필수

## 실행 명령

```bash
python cli.py daily            # 기본 24시간 윈도우
python cli.py daily --hours 12 # 짧은 윈도우
python cli.py daily --no-send  # 발송 없이 미리보기
```

## 체크리스트
- [ ] 리포트 하단 "실험적 룰베이스" 표기 유지
- [ ] 결측 지표가 3개 이상이면 리포트에 경고 섹션 추가
- [ ] Aggression 점수화 실패율 > 50% 시 Telegram에 "데이터 품질 경고" 병기

## 관련 파일
- `cli.py` (daily 커맨드)
- `collectors/`, `scoring/`, `models/`, `notify/`
- `.claude/agents/aggression-scorer.md`, `.claude/agents/pain-aggregator.md`
