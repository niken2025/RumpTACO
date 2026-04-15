"""Supabase 연동 — predictions / market_snapshots / statements 저장 & 조회.

설계 원칙:
- Supabase가 "진실의 원천" (source of truth). JSON은 대시보드 캐시.
- SUPABASE_URL / SUPABASE_SERVICE_KEY 미설정 시 모든 함수는 no-op (그라데이션 다운그레이드).
- 삽입 실패도 파이프라인 중단 안 시킴 (로그만 출력).
- 중복 키(같은 date/ts) 방지 위해 upsert 사용.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

try:
    from supabase import Client, create_client  # type: ignore
except Exception:  # noqa: BLE001
    Client = None  # type: ignore
    create_client = None  # type: ignore


KST = timezone(timedelta(hours=9))


def _client() -> Optional["Client"]:
    if create_client is None:
        return None
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        return None
    try:
        return create_client(url, key)
    except Exception as e:  # noqa: BLE001
        print(f"[supabase] 클라이언트 생성 실패: {e}")
        return None


def is_enabled() -> bool:
    return _client() is not None


def insert_prediction(
    *,
    taco_probability: float,
    expected_window_hours: Optional[tuple[float, float]],
    aggression_score: float,
    pain_index: float,
    model_version: str,
    explanation: str,
    trigger_statement_id: Optional[str] = None,
    ts: Optional[datetime] = None,
) -> Optional[str]:
    c = _client()
    if c is None:
        return None
    row = {
        "ts": (ts or datetime.now(timezone.utc)).isoformat(),
        "taco_probability": taco_probability,
        "expected_window_hours": (expected_window_hours[1] if expected_window_hours else None),
        "aggression_score": aggression_score,
        "pain_index": pain_index,
        "model_version": model_version,
        "explanation": explanation,
        "trigger_statement_id": trigger_statement_id,
    }
    try:
        res = c.table("predictions").insert(row).execute()
        data = res.data or []
        return data[0]["id"] if data else None
    except Exception as e:  # noqa: BLE001
        print(f"[supabase] predictions insert 실패: {e}")
        return None


def upsert_market_snapshot(snapshot: dict, ts: Optional[datetime] = None) -> bool:
    c = _client()
    if c is None:
        return False
    row = dict(snapshot)
    row["ts"] = (ts or datetime.now(timezone.utc)).isoformat()
    try:
        c.table("market_snapshots").upsert(row, on_conflict="ts").execute()
        return True
    except Exception as e:  # noqa: BLE001
        print(f"[supabase] market_snapshots upsert 실패: {e}")
        return False


def insert_statements(statements: list[dict]) -> list[str]:
    """각 발언을 statements에 삽입. 반환: 삽입된 ID 목록."""
    c = _client()
    if c is None or not statements:
        return []
    rows = []
    for s in statements:
        rows.append({
            "source": s.get("source") or "news",
            "url": s.get("url"),
            "content": (s.get("content") or "")[:4000],
            "translated": s.get("translated"),
            "posted_at": s.get("posted_at") or datetime.now(timezone.utc).isoformat(),
            "aggression_score": s.get("aggression_score"),
            "threat_intensity": s.get("threat_intensity"),
            "specificity": s.get("specificity"),
            "deadline_specified": (
                100.0 if s.get("deadline_specified") is True
                else 0.0 if s.get("deadline_specified") is False
                else s.get("deadline_specified")
            ),
            "topic_tags": s.get("topic_tags") or [],
            "scoring_model": s.get("_model"),
            "scoring_rationale": s.get("rationale"),
            "processed_at": datetime.now(timezone.utc).isoformat(),
        })
    try:
        res = c.table("statements").insert(rows).execute()
        return [r.get("id") for r in (res.data or []) if r.get("id")]
    except Exception as e:  # noqa: BLE001
        print(f"[supabase] statements insert 실패: {e}")
        return []


def fetch_history(limit: int = 60) -> list[dict]:
    """daily_taco_summary 뷰에서 최근 N일 이력 조회."""
    c = _client()
    if c is None:
        return []
    try:
        res = (
            c.table("daily_taco_summary")
            .select("*")
            .order("date", desc=True)
            .limit(limit)
            .execute()
        )
        rows = list(reversed(res.data or []))
        return rows
    except Exception as e:  # noqa: BLE001
        print(f"[supabase] history 조회 실패: {e}")
        return []


def fetch_market_history(limit_days: int = 60) -> dict[str, dict[str, float]]:
    """market_snapshots에서 최근 N일 시장 데이터. {date: {indicator: value}}."""
    c = _client()
    if c is None:
        return {}
    try:
        res = (
            c.table("market_snapshots")
            .select("*")
            .order("ts", desc=True)
            .limit(limit_days)
            .execute()
        )
        out: dict[str, dict[str, float]] = {}
        for row in (res.data or []):
            ts = row.get("ts")
            if not ts:
                continue
            date = ts[:10]
            out[date] = {k: v for k, v in row.items() if k not in ("ts", "polymarket_odds", "raw", "created_at")}
        return out
    except Exception as e:  # noqa: BLE001
        print(f"[supabase] market_snapshots 조회 실패: {e}")
        return {}
