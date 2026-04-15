"""Aggression 점수화 — Google Gemini Flash (1차) / Pro (정밀).

에이전트 정의는 .claude/agents/aggression-scorer.md 를 시스템 프롬프트로 사용.
무료 티어: Gemini 1.5 Flash 15 req/min, 1500 req/day — 일일 배치에 충분.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import google.generativeai as genai


AGENT_PROMPT_PATH = Path(__file__).resolve().parent.parent / ".claude" / "agents" / "aggression-scorer.md"


def _system_prompt() -> str:
    raw = AGENT_PROMPT_PATH.read_text(encoding="utf-8")
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            raw = parts[2]
    return raw.strip()


def _extract_json(text: str) -> dict[str, Any]:
    """모델 출력에서 첫 JSON 오브젝트 추출 (코드펜스 제거 포함)."""
    # ```json ... ``` 제거
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```\s*$", "", text)
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        raise ValueError(f"JSON 미발견: {text[:200]}")
    return json.loads(m.group(0))


_configured = False


def _ensure_configured() -> None:
    global _configured
    if _configured:
        return
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY (또는 GEMINI_API_KEY) 환경변수 없음")
    genai.configure(api_key=api_key)
    _configured = True


def score_statement(content: str, *, precise: bool = False) -> dict[str, Any]:
    """단일 발언 점수화.

    precise=False: Gemini 1.5 Flash (무료·빠름)
    precise=True: Gemini 1.5 Pro (정밀·느림·유료 많음)
    """
    _ensure_configured()
    default_light = "gemini-1.5-flash"
    default_main = "gemini-1.5-pro"
    model_name = os.getenv("MODEL_MAIN" if precise else "MODEL_LIGHT") or (
        default_main if precise else default_light
    )

    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=_system_prompt(),
        generation_config={
            "temperature": 0.2,
            "max_output_tokens": 600,
            "response_mime_type": "application/json",
        },
    )
    resp = model.generate_content(
        f"다음 발언의 Aggression 점수를 매겨주세요:\n\n{content}"
    )
    out_text = resp.text or ""
    data = _extract_json(out_text)
    data["_model"] = model_name
    return data


def score_batch(statements: list[dict], precise_threshold: float = 50.0) -> list[dict]:
    """Flash 1차 → 점수 >= threshold이면 Pro 재평가."""
    out = []
    for s in statements:
        try:
            light = score_statement(s["content"], precise=False)
            final = light
            if light.get("aggression_score", 0) >= precise_threshold:
                try:
                    final = score_statement(s["content"], precise=True)
                except Exception as e:  # noqa: BLE001
                    print(f"[aggression] Pro 재평가 실패, Flash 결과 사용: {e}")
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
