"""트럼프 지지율 수집 — Wikipedia "Opinion polling on the second Trump presidency" 집계.

RCP 단일 소스는 Cloudflare 차단(2026-04 기준 403). Wikipedia는 10개 집계기관
(Ballotpedia / CNN / Decision Desk HQ / FiftyPlusOne / Race to the WH / RCP /
Silver Bulletin / The Economist / NYT / VoteHub)의 최신 평균을 'Average' 행에
유지 중이며, Wikimedia API는 키 없이 합법적으로 접근 가능.

전략:
    1) action=parse로 wikitext 획득 (UA 명시 필수)
    2) '==== Approval ====' 섹션에서 '| '''Average''' |' 행 탐색
    3) 접근(approve) 퍼센트만 추출해 float 반환
    4) 실패 시 None (Pain Index는 결측 시 가중치 재정규화)
"""
from __future__ import annotations

import re
from typing import Optional

import httpx


WIKI_PAGE = "Opinion_polling_on_the_second_Trump_presidency"
WIKI_API = "https://en.wikipedia.org/w/api.php"
UA = "RumpTACO/0.1 (https://github.com/niken2025/RumpTACO; badada01@gmail.com)"


def fetch_trump_approval(timeout: float = 20.0) -> Optional[float]:
    """최신 집계 평균 승인율(%)을 float로 반환. 실패 시 None."""
    try:
        with httpx.Client(timeout=timeout, headers={"User-Agent": UA}) as c:
            r = c.get(WIKI_API, params={
                "action": "parse",
                "page": WIKI_PAGE,
                "format": "json",
                "prop": "wikitext",
            })
            r.raise_for_status()
            txt = r.json().get("parse", {}).get("wikitext", {}).get("*", "")
    except Exception as e:  # noqa: BLE001
        print(f"[polls] Wikipedia fetch 실패: {e}")
        return None

    if not txt:
        return None

    # '==== Approval ====' 섹션만 잘라 Favorability 표와 혼선 방지
    start = txt.find("==== Approval ====")
    if start < 0:
        start = txt.find("Approval ====")
    end = txt.find("==== Favorability ====", start + 1) if start >= 0 else -1
    chunk = txt[start:end] if start >= 0 and end > start else txt[:15000]

    # "| '''Average'''" 다음 줄부터 첫 번째 퍼센트가 approve 값
    m = re.search(r"\|\s*'''Average'''\s*\n\|[^\n]*\n\|\s*(\d{1,2}(?:\.\d)?)\s*%", chunk)
    if not m:
        print("[polls] Average 행 파싱 실패")
        return None

    try:
        return float(m.group(1))
    except ValueError:
        return None


if __name__ == "__main__":
    v = fetch_trump_approval()
    print(f"Trump approval (aggregate avg): {v}")
