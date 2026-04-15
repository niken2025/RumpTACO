"""Gemini로 현재 상황을 2-4문장 분석 (대시보드 상단 인사이트)."""
from __future__ import annotations

import os
import google.generativeai as genai


SYSTEM = """당신은 매크로·정치 리스크 애널리스트다.
주어진 TACO 시뮬레이션 수치로 현재 상황을 3~4문장 한국어 브리핑으로 정리한다.

규칙:
- "과거 어느 사례와 유사한지" 한 줄 비교 포함
- 구체 숫자 1~2개 인용 (Aggression, Pain, 확률)
- 시장/정치 함의 한 줄
- 투자 권유 금지
- 단정 금지, "가능성", "시사" 같은 표현 사용
- 4문장 초과 금지
"""


def generate_insight(
    *,
    taco_probability: float,
    aggression: float,
    pain: float,
    pain_contributions: dict,
    top_statements: list[dict],
) -> str:
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "(GOOGLE_API_KEY 없음 — 인사이트 생략)"
    genai.configure(api_key=api_key)

    top3 = sorted(pain_contributions.items(), key=lambda x: -abs(x[1]))[:3]
    top_stmt = top_statements[0] if top_statements else None
    stmt_str = (top_stmt.get("content", "")[:200] if top_stmt else "(발언 없음)")
    stmt_score = top_stmt.get("aggression_score") if top_stmt else None

    prompt = f"""현재 수치:
- TACO 확률: {taco_probability:.1f}%
- Aggression(최고 발언 점수): {aggression:.1f}
- Pain Index: {pain:.1f}
- Pain 기여도 Top 3: {top3}
- 최고 Aggression 발언({stmt_score}): {stmt_str}

위 수치로 3~4문장 한국어 브리핑을 작성하라."""

    model = genai.GenerativeModel(
        model_name=os.getenv("MODEL_LIGHT", "gemini-2.5-flash"),
        system_instruction=SYSTEM,
        generation_config={"temperature": 0.4, "max_output_tokens": 4096},
    )
    import time
    last_err = None
    for attempt in range(3):
        try:
            resp = model.generate_content(prompt)
            return (resp.text or "").strip()
        except Exception as e:  # noqa: BLE001
            last_err = e
            msg = str(e)
            if "429" in msg or "quota" in msg.lower():
                import re as _re
                m = _re.search(r"retry in (\d+(?:\.\d+)?)s", msg)
                wait = float(m.group(1)) + 1 if m else 30
                time.sleep(min(wait, 60))
                continue
            break
    return f"(인사이트 생성 실패: {last_err})"


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    print(generate_insight(
        taco_probability=65.0, aggression=78, pain=55,
        pain_contributions={"vix": 0.25, "treasury_10y": 0.18, "trump_approval": -0.15},
        top_statements=[{"content": "I will impose 100% tariffs on Chinese EVs on May 1.",
                         "aggression_score": 85}],
    ))
