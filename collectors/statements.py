"""트럼프 발언 수집기.

전략:
  1. Truth Social RSS 미러 (공개된 서드파티 미러가 있을 때)
  2. X/Twitter RSS (Nitter 등 미러, 불안정)
  3. Tavily News API 페일오버 — "Donald Trump" 최신 발언 검색

1단계 MVP는 (3) Tavily 페일오버만 안정 경로로 사용.
RSS는 설정되면 시도, 실패해도 파이프라인은 계속.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx
import feedparser


@dataclass
class Statement:
    source: str
    url: Optional[str]
    content: str
    posted_at: str  # ISO8601


def _parse_rss(url: str, source: str, since: datetime) -> list[Statement]:
    out: list[Statement] = []
    feed = feedparser.parse(url)
    for entry in feed.entries:
        published = entry.get("published_parsed") or entry.get("updated_parsed")
        if not published:
            continue
        dt = datetime(*published[:6], tzinfo=timezone.utc)
        if dt < since:
            continue
        text = entry.get("summary") or entry.get("title") or ""
        out.append(
            Statement(
                source=source,
                url=entry.get("link"),
                content=text,
                posted_at=dt.isoformat(),
            )
        )
    return out


def _tavily_search(query: str, since_days: int = 1) -> list[Statement]:
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        print("[statements] TAVILY_API_KEY 없음 — 뉴스 페일오버 건너뜀")
        return []
    body = {
        "api_key": api_key,
        "query": query,
        "topic": "news",
        "days": since_days,
        "max_results": 10,
        "include_answer": False,
    }
    try:
        with httpx.Client(timeout=20.0) as c:
            r = c.post("https://api.tavily.com/search", json=body)
            r.raise_for_status()
            data = r.json()
    except Exception as e:  # noqa: BLE001
        print(f"[statements] Tavily 실패: {e}")
        return []

    out: list[Statement] = []
    for item in data.get("results", []):
        out.append(
            Statement(
                source="news",
                url=item.get("url"),
                content=(item.get("title", "") + "\n\n" + item.get("content", "")).strip(),
                posted_at=datetime.now(timezone.utc).isoformat(),
            )
        )
    return out


def collect_recent(hours: int = 24) -> list[Statement]:
    """최근 N시간 내 발언 후보 수집."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    items: list[Statement] = []

    truth_rss = os.getenv("TRUTH_SOCIAL_RSS")  # 사용 가능한 미러 URL을 .env에 주입
    if truth_rss:
        try:
            items.extend(_parse_rss(truth_rss, "truth_social", since))
        except Exception as e:  # noqa: BLE001
            print(f"[statements] Truth RSS 실패: {e}")

    x_rss = os.getenv("X_RSS")
    if x_rss:
        try:
            items.extend(_parse_rss(x_rss, "x", since))
        except Exception as e:  # noqa: BLE001
            print(f"[statements] X RSS 실패: {e}")

    if not items:
        items = _tavily_search(
            'Trump said OR announced OR threatened OR "Truth Social" '
            '(tariff OR sanction OR deal OR policy OR "will impose" OR "executive order")',
            since_days=max(1, hours // 24),
        )
        # Trump이 주어로 등장하는 기사만 통과 (휴리스틱)
        items = [
            s for s in items
            if any(kw in s.content.lower() for kw in ["trump said", "trump announced",
                                                        "trump threatened", "trump will",
                                                        "trump's", "president trump",
                                                        "trump signed", "trump's plan"])
        ]

    # 중복 제거 (URL 기준)
    seen = set()
    deduped = []
    for s in items:
        key = s.url or s.content[:80]
        if key in seen:
            continue
        seen.add(key)
        deduped.append(s)
    return deduped


def to_dicts(items: list[Statement]) -> list[dict]:
    return [asdict(s) for s in items]


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    items = collect_recent(24)
    print(f"수집 {len(items)}건")
    for s in items[:5]:
        print(f"- [{s.source}] {s.posted_at} {s.content[:100]}...")
