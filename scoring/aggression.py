"""Aggression 점수화 — Haiku 1차 필터 → Opus 정밀.

에이전트 정의는 .claude/agents/aggression-scorer.md 를 기본 프롬프트로 삼는다.
여기서는 API 호출 구현. Claude Code 환경에서는 에이전트 dispatch로 대체 가능.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from anthropic import Anthropic


AGENT_PROMPT_PATH = Path(__file__).resolve().parent.parent / ".claude" / "agents" / "aggression-scorer.md"


def _system_prompt() -> str:
    raw = AGENT_PROMPT_PATH.read_text(encoding="utf-8")
    # frontmatter 제거
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            raw = parts[2]
    return raw.strip()


def _extract_json(text: str) -> dict[str, Any]:
    """모델 출력에서 첫 JSON 오브젝트 추출."""
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        raise ValueError(f"JSON 미발견: {text[:200]}")
    return json.loads(m.group(0))


def score_statement(content: str, *, precise: bool = False) -> dict[str, Any]:
    """단일 발언 점수화.

    precise=False: Haiku 4.5
    precise=True: Opus 4.6
    """
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    model = os.getenv("MODEL_MAIN" if precise else "MODEL_LIGHT") or (
        "claude-opus-4-6" if precise else "claude-haiku-4-5-20251001"
    )
    resp = client.messages.create(
        model=model,
        max_tokens=600,
        system=_system_prompt(),
        messages=[{"role": "user", "content": f"다음 발언의 Aggression 점수를 매겨주세요:\n\n{content}"}],
    )
    out_text = "".join(block.text for block in resp.content if hasattr(block, "text"))
    data = _extract_json(out_text)
    data["_model"] = model
    return data


def score_batch(statements: list[dict], precise_threshold: float = 50.0) -> list[dict]:
    """리스트 점수화. Haiku로 1차, 점수 >= threshold이면 Opus 재평가."""
    out = []
    for s in statements:
        try:
            light = score_statement(s["content"], precise=False)
            final = light
            if light.get("aggression_score", 0) >= precise_threshold:
                try:
                    final = score_statement(s["content"], precise=True)
                except Exception as e:  # noqa: BLE001
                    print(f"[aggression] Opus 재평가 실패, Haiku 결과 사용: {e}")
            out.append({**s, **final})
        except Exception as e:  # noqa: BLE001
            print(f"[aggression] 점수화 실패: {e}")
            out.append({**s, "aggression_score": None, "error": str(e)})
    return out


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    samples = [
        {"content": "I will impose 100% tariffs on all Chinese electric vehicles starting May 1st. No exceptions."},
        {"content": "Biden is a disaster. Our country is going down."},
    ]
    for r in score_batch(samples):
        print(json.dumps(r, ensure_ascii=False, indent=2))
