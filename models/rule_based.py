"""룰베이스 TACO 확률 모델.

학습 데이터 부족(< 30건) 단계에서 쓰는 임시 공식.
가설: Aggression이 높고 Pain이 동반 상승할수록 정책 번복 가능성 증가.
    - Aggression 단독으로는 약한 시그널 (트럼프는 위협 자주 함)
    - Pain이 같이 높아야 "회항 유인"이 생김

공식:
    composite = 0.55 * (aggression/100) + 0.45 * (pain/100)
    interaction = 0.6 * (aggression/100) * (pain/100)
    raw = composite + interaction
    taco_prob = 100 * sigmoid(4 * (raw - 0.55))

예상 윈도우:
    - prob >= 80: 24~48시간
    - 60 <= prob < 80: 48~96시간
    - 40 <= prob < 60: 96~168시간
    - < 40: "임계점 미도달"
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


MODEL_VERSION = "rule-based-v0.1"


@dataclass
class TacoPrediction:
    taco_probability: float
    expected_window_hours: Optional[tuple[float, float]]
    aggression_score: float
    pain_index: float
    explanation: str
    model_version: str = MODEL_VERSION


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def predict(aggression: float, pain: float) -> TacoPrediction:
    a = max(0.0, min(100.0, aggression)) / 100.0
    p = max(0.0, min(100.0, pain)) / 100.0

    composite = 0.55 * a + 0.45 * p
    interaction = 0.6 * a * p
    raw = composite + interaction

    prob = 100.0 * _sigmoid(4.0 * (raw - 0.55))
    prob = round(prob, 2)

    if prob >= 80:
        window = (24.0, 48.0)
        label = "매우 높음"
    elif prob >= 60:
        window = (48.0, 96.0)
        label = "높음"
    elif prob >= 40:
        window = (96.0, 168.0)
        label = "중간"
    else:
        window = None
        label = "낮음"

    expl = (
        f"[{label}] Aggression {aggression:.1f} × Pain {pain:.1f} → "
        f"composite={composite:.3f}, interaction={interaction:.3f}, raw={raw:.3f}. "
        f"룰베이스 공식 {MODEL_VERSION} 적용."
    )
    return TacoPrediction(
        taco_probability=prob,
        expected_window_hours=window,
        aggression_score=aggression,
        pain_index=pain,
        explanation=expl,
    )


if __name__ == "__main__":
    cases = [(85, 70), (85, 30), (40, 70), (20, 20), (95, 90)]
    for a, p in cases:
        r = predict(a, p)
        window = f"{r.expected_window_hours[0]:.0f}~{r.expected_window_hours[1]:.0f}h" if r.expected_window_hours else "N/A"
        print(f"A={a:3d} P={p:3d} → TACO {r.taco_probability:5.2f}% ({window})")
