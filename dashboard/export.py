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

    # --- 히스토리: Supabase 있으면 DB에서 재빌드, 없으면 JSON에 append ---
    history_path = DOCS_DATA / "history.json"
    history = _rebuild_history_from_db(payload, market_snapshot)
    if history is None:
        history = _append_history_local(history_path, payload, market_snapshot)

    history_path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    return latest_path


def _rebuild_history_from_db(payload: dict, market_snapshot: dict) -> list | None:
    """Supabase가 설정돼 있으면 DB를 진실의 원천으로 삼아 history.json 재빌드."""
    try:
        from db import supabase_client as sb
    except Exception:  # noqa: BLE001
        return None
    if not sb.is_enabled():
        return None

    daily = sb.fetch_history(limit=HISTORY_MAX)
    market_by_date = sb.fetch_market_history(limit_days=HISTORY_MAX)

    out: list = []
    for d in daily:
        date = d["date"]
        out.append({
            "date": date,
            "generated_at": d.get("generated_at"),
            "taco_probability": d.get("taco_probability"),
            "aggression_score": d.get("aggression_score"),
            "pain_index": d.get("pain_index"),
            "market": market_by_date.get(date, {}),
        })
    # 오늘 값이 DB에 아직 없다면(또는 커밋 지연) payload 기반으로 병합
    today = payload["date"]
    today_entry = next((h for h in out if h["date"] == today), None)
    if today_entry is None:
        out.append({
            "date": today,
            "generated_at": payload["generated_at"],
            "taco_probability": payload["taco_probability"],
            "aggression_score": payload["aggression_score"],
            "pain_index": payload["pain_index"],
            "market": _market_subset(market_snapshot),
        })
        out.sort(key=lambda x: x["date"])
    return out[-HISTORY_MAX:]


def _append_history_local(history_path: Path, payload: dict, market_snapshot: dict) -> list:
    """Supabase 미설정 시 로컬 JSON 기반 이력 관리."""
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
        "market": _market_subset(market_snapshot),
    })
    history.sort(key=lambda x: x["date"])
    return history[-HISTORY_MAX:]


def _market_subset(snapshot: dict) -> dict:
    keys = ("treasury_10y", "sp500", "djia", "nasdaq", "vix", "wti_usd",
            "breakeven_5y", "btc_usd", "trump_approval")
    return {k: snapshot.get(k) for k in keys}
