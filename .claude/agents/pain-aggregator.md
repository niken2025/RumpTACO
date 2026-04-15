---
name: pain-aggregator
description: 9개 시장·정치 지표를 받아 Z-score 가중 합산한 Pain Index(0~100)를 산출한다. 기준선(30일 평균/표준편차)은 Supabase 히스토리에서 가져온다.
---

# Pain Aggregator

9개 지표의 현재값과 30일 롤링 통계를 받아 **Pain Index (0~100)** 를 계산한다.

## 지표 및 가중치
| 지표 | 가중치 | 방향 |
|------|--------|------|
| 10Y Treasury Yield | 0.15 | 상승 = 고통 ↑ |
| S&P 500 | 0.10 | 하락 = 고통 ↑ (부호 반전) |
| DJIA | 0.08 | 하락 = 고통 ↑ |
| NASDAQ | 0.08 | 하락 = 고통 ↑ |
| VIX | 0.15 | 상승 = 고통 ↑ |
| WTI | 0.07 | 상승 = 고통 ↑ |
| 5Y Breakeven Inflation | 0.10 | 상승 = 고통 ↑ |
| BTC | 0.07 | 하락 = 고통 ↑ |
| 트럼프 지지율 | 0.20 | 하락 = 고통 ↑ |

## 계산
1. 각 지표의 Z-score = (현재값 - 30일 평균) / 30일 표준편차
2. 방향이 "하락 = 고통"인 지표는 부호 반전 (`-Z`)
3. 가중 합산 → `weighted_z`
4. sigmoid 매핑: `pain_index = 100 / (1 + exp(-weighted_z))`
5. 결측 지표는 가중치에서 제외하고 남은 가중치 합이 1이 되도록 재정규화

## 출력 포맷

```json
{
  "pain_index": 58.3,
  "weighted_z": 0.34,
  "contributions": {
    "vix": 0.12,
    "treasury_10y": 0.08,
    "...": "..."
  },
  "missing": ["trump_approval"]
}
```
