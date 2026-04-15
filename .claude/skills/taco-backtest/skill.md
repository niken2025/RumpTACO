---
name: taco-backtest
description: 과거 특정 날짜를 입력하면 그날의 데이터로 현재 모델이 어떤 TACO 확률을 예측했을지 시뮬레이션. 실제 결과(TACO 발생 여부)와 비교해 정확도를 기록.
---

# /taco-backtest — 과거 시뮬레이션

## 언제 사용
- 모델 튜닝 시 과거 사례로 정확도 검증
- "2019-05-10 미중 관세 위협 때 우리 모델이 뭐라고 했을까?" 조사

## 입력
- `--date YYYY-MM-DD` : 기준일
- `--statement-id <uuid>` : (선택) 특정 발언 기준
- `--was-taco true/false` : (선택) 실제 결과 — 기록용

## 절차
1. `market_snapshots` 테이블에서 해당 날짜의 스냅샷 조회
2. `statements` 테이블에서 해당 날짜의 발언 및 점수 조회 (없으면 점수화)
3. `models/rule_based.py`로 예측
4. `taco_cases` 테이블에 저장 (`was_taco` 필드)
5. 현재 누적 백테스트 정확도 출력

## 출력 예시
```
=== Backtest: 2025-03-14 ===
Aggression (max): 72.0
Pain Index: 58.3
Predicted TACO probability: 68.4%
Actual outcome: TACO (reverted 36h later) ✓
Cumulative accuracy: 18/27 = 66.7%
```

## 향후 확장 (Phase 2)
- 이 커맨드로 30건 이상 라벨 축적 후 로지스틱 회귀 학습
- `models/learned.py` 생성 → 룰베이스 대체
