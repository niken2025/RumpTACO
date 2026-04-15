"""Pain Index 계산 — 9개 시장·정치 지표 Z-score 가중합.

30일 평균/표준편차는 market_snapshots 히스토리에서 읽어 계산.
히스토리 부족(< 10일) 시 정적 기준선(fallback) 사용.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


# 방향: True면 상승이 고통, False면 하락이 고통(부호 반전)
INDICATORS: dict[str, tuple[float, bool]] = {
    "treasury_10y": (0.15, True),
    "sp500":        (0.10, False),
    "djia":         (0.08, False),
    "nasdaq":       (0.08, False),
    "vix":          (0.15, True),
    "wti_usd":      (0.07, True),
    "breakeven_5y": (0.10, True),
    "btc_usd":      (0.07, False),
    "trump_approval": (0.20, False),
}

# 히스토리 부족 시 쓰는 정적 fallback: (대략적 수준, 대략적 1σ)
FALLBACK_BASELINE: dict[str, tuple[float, float]] = {
    "treasury_10y": (4.2, 0.3),
    "sp500":        (5200.0, 150.0),
    "djia":         (39000.0, 1000.0),
    "nasdaq":       (16500.0, 500.0),
    "vix":          (15.0, 4.0),
    "wti_usd":      (80.0, 5.0),
    "breakeven_5y": (2.4, 0.2),
    "btc_usd":      (65000.0, 5000.0),
    "trump_approval": (45.0, 2.0),
}


@dataclass
class PainResult:
    pain_index: float
    weighted_z: float
    contributions: dict
    missing: list


def _zscore(x: float, mean: float, std: float) -> float:
    if std <= 0:
        return 0.0
    return (x - mean) / std


def compute_pain(
    current: dict,
    history: Optional[list[dict]] = None,
    min_history: int = 10,
) -> PainResult:
    """current: 오늘의 스냅샷 dict. history: 과거 스냅샷 리스트(오래된→최신)."""
    contributions: dict = {}
    missing: list = []
    weight_sum_used = 0.0
    weighted = 0.0

    for key, (weight, up_is_pain) in INDICATORS.items():
        val = current.get(key)
        if val is None:
            missing.append(key)
            continue

        series = [h.get(key) for h in (history or []) if h.get(key) is not None]
        if len(series) >= min_history:
            mean = sum(series) / len(series)
            var = sum((x - mean) ** 2 for x in series) / len(series)
            std = math.sqrt(var)
        else:
            mean, std = FALLBACK_BASELINE[key]

        z = _zscore(val, mean, std)
        if not up_is_pain:
            z = -z
        contrib = weight * z
        contributions[key] = round(contrib, 4)
        weighted += contrib
        weight_sum_used += weight

    if weight_sum_used > 0:
        weighted = weighted / weight_sum_used  # 결측 가중치 재정규화

    pain = 100.0 / (1.0 + math.exp(-weighted * 2.0))  # 민감도 2배
    return PainResult(
        pain_index=round(pain, 2),
        weighted_z=round(weighted, 4),
        contributions=contributions,
        missing=missing,
    )


if __name__ == "__main__":
    sample = {
        "treasury_10y": 4.7,
        "sp500": 5050.0,
        "djia": 38500.0,
        "nasdaq": 16000.0,
        "vix": 22.0,
        "wti_usd": 87.0,
        "breakeven_5y": 2.6,
        "btc_usd": 62000.0,
        "trump_approval": 43.5,
    }
    r = compute_pain(sample)
    print(f"Pain Index: {r.pain_index}")
    print(f"Weighted Z: {r.weighted_z}")
    print("Contributions:")
    for k, v in sorted(r.contributions.items(), key=lambda x: -abs(x[1])):
        print(f"  {k:18s} {v:+.4f}")
