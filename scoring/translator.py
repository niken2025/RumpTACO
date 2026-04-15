"""영어 발언/뉴스 한 줄을 한국어로 번역. Gemini Flash 사용, rate limit 재시도 포함."""
from __future__ import annotations

import os
import time

import google.generativeai as genai


SYSTEM = (
    "다음 영어 뉴스 헤드라인/발언 요약을 자연스러운 한국어로 1~2문장 이내 번역하라. "
    "고유명사는 원어 병기 없이 한국어로(예: Donald Trump → 트럼프). "
    "번역 결과 텍스트만 출력. 설명/따옴표/라벨 금지."
)


_configured = False


def _ensure():
    global _configured
    if _configured:
        return
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY 없음")
    genai.configure(api_key=api_key)
    _configured = True


def translate_ko(text: str, max_len: int = 400) -> str:
    if not text:
        return ""
    try:
        _ensure()
    except Exception as e:  # noqa: BLE001
        return f"(번역 불가: {e})"

    model = genai.GenerativeModel(
        model_name=os.getenv("MODEL_LIGHT", "gemini-2.5-flash"),
        system_instruction=SYSTEM,
        generation_config={"temperature": 0.2, "max_output_tokens": 2048},
    )
    snippet = text[:max_len]
    import re as _re
    for attempt in range(3):
        try:
            resp = model.generate_content(snippet)
            out = (resp.text or "").strip().strip('"').strip("'")
            return out or text
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            if "429" in msg or "quota" in msg.lower():
                m = _re.search(r"retry in (\d+(?:\.\d+)?)s", msg)
                wait = float(m.group(1)) + 1 if m else 20
                time.sleep(min(wait, 60))
                continue
            return text
    return text


def translate_batch(statements: list[dict]) -> list[dict]:
    """각 발언에 translated 필드 추가."""
    out = []
    for s in statements:
        tr = translate_ko(s.get("content", ""))
        out.append({**s, "translated": tr})
    return out
