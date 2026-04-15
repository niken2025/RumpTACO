"""대시보드용 JSON export — docs/data/ 에 latest.json + history.json 저장."""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path


KST = timezone(timedelta(hours=9))
DOCS_DATA = Path(__file__).resolve().parent.parent / "docs" / "data"
HISTORY_MAX = 60  # 최근 60일 유지


def _to_jsonable(obj):
    if hasattr(obj, "__dataclass_fields__"):
        return asdict(obj)
    return obj


def write_snapshot(
    *,
    prediction,
    pain_result,
    market_snapshot: dict,
    top_statements: list[dict],
    insight: str = "",
) -> Path:
    DOCS_DATA.mkdir(parents=True, exist_ok=True)
    now = datetime.now(KST)
    payload = {
        "generated_at": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "taco_probability": prediction.taco_probability,
        "aggression_score": prediction.aggression_score,
        "pain_index": prediction.pain_index,
        "expected_window_hours": list(prediction.expected_window_hours) if prediction.expected_window_hours else None,
        "model_version": prediction.model_version,
        "threshold": {
            "very_high": 80,
            "high": 60,
            "medium": 40,
        },
        "market_snapshot": market_snapshot,
        "pain": {
            "index": pain_result.pain_index,
            "weighted_z": pain_result.weighted_z,
            "contributions": pain_result.contributions,
            "missing": pain_result.missing,
        },
        "top_statements": [
            {
                "source": s.get("source"),
                "url": s.get("url"),
                "content": s.get("content", "")[:500],
                "translated": s.get("translated"),
                "aggression_score": s.get("aggression_score"),
                "threat_intensity": s.get("threat_intensity"),
                "specificity": s.get("specificity"),
                "deadline_specified": s.get("deadline_specified"),
                "topic_tags": s.get("topic_tags"),
                "rationale": s.get("rationale"),
            }
            for s in top_statements[:5]
        ],
        "explanation": prediction.explanation,
    }

    latest_path = DOCS_DATA / "latest.json"
    latest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # 히스토리 업데이트
    history_path = DOCS_DATA / "history.json"
    history: list = []
    if history_path.exists():
        try:
            history = json.loads(history_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            history = []

    history = [h for h in history if h.get("date") != payload["date"]]
    history.append({
        "date": payload["date"],
        "generated_at": payload["generated_at"],
        "taco_probability": payload["taco_probability"],
        "aggression_score": payload["aggression_score"],
        "pain_index": payload["pain_index"],
        "market": {
            k: market_snapshot.get(k) for k in (
                "treasury_10y", "sp500", "djia", "nasdaq",
                "vix", "wti_usd", "breakeven_5y", "btc_usd", "trump_approval",
            )
        },
    })
    history.sort(key=lambda x: x["date"])
    history = history[-HISTORY_MAX:]
    history_path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")

    return latest_path
