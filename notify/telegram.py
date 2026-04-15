"""텔레그램 리포트 발송."""
from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta

import httpx


KST = timezone(timedelta(hours=9))


def send_message(text: str, *, parse_mode: str = "Markdown") -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("[telegram] 토큰/채팅ID 없음 — 콘솔로만 출력")
        print(text)
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    # Telegram 메시지 길이 제한 4096
    payload = {
        "chat_id": chat_id,
        "text": text[:4000],
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    try:
        with httpx.Client(timeout=15.0) as c:
            r = c.post(url, json=payload)
            r.raise_for_status()
        return True
    except Exception as e:  # noqa: BLE001
        print(f"[telegram] 발송 실패: {e}")
        return False


def format_daily_report(
    *,
    prediction,
    top_statements: list[dict],
    market_snapshot: dict,
    pain_result,
) -> str:
    """일일 리포트 마크다운 생성."""
    now_kst = datetime.now(KST)
    prob = prediction.taco_probability
    if prob >= 80:
        emoji = "🚨"
        label = "매우 높음"
    elif prob >= 60:
        emoji = "⚠️"
        label = "높음"
    elif prob >= 40:
        emoji = "🟡"
        label = "중간"
    else:
        emoji = "⚪"
        label = "낮음"

    lines = [
        f"*{emoji} RumpTACO 일일 리포트* — {now_kst.strftime('%Y-%m-%d %H:%M KST')}",
        "",
        f"*TACO 확률*: `{prob:.1f}%` ({label})",
        f"*Aggression*: `{prediction.aggression_score:.1f}` / *Pain Index*: `{prediction.pain_index:.1f}`",
    ]
    if prediction.expected_window_hours:
        lo, hi = prediction.expected_window_hours
        lines.append(f"*예상 윈도우*: {lo:.0f}~{hi:.0f}시간")
    lines.append("")

    lines.append("*📊 시장 지표*")
    label_map = {
        "treasury_10y": "10Y T", "sp500": "S&P", "djia": "DJIA", "nasdaq": "NASDAQ",
        "vix": "VIX", "wti_usd": "WTI", "breakeven_5y": "5Y BEI", "btc_usd": "BTC",
        "trump_approval": "지지율",
    }
    for k, lbl in label_map.items():
        v = market_snapshot.get(k)
        if v is None:
            continue
        lines.append(f"  • {lbl}: `{v}`")
    lines.append("")

    lines.append("*🗣 주요 발언 Top 3*")
    for s in top_statements[:3]:
        score = s.get("aggression_score")
        snippet = s.get("content", "")[:140].replace("\n", " ")
        score_str = f"{score:.0f}" if isinstance(score, (int, float)) else "?"
        lines.append(f"  • [{score_str}] {snippet}")
    lines.append("")

    if pain_result.missing:
        lines.append(f"_결측 지표_: {', '.join(pain_result.missing)}")
        lines.append("")

    lines.append(f"_모델: {prediction.model_version} (실험적 룰베이스)_")
    lines.append("_⚠️ 투자 권유 아님. 정보 제공 목적._")
    return "\n".join(lines)


def save_report(text: str, date_str: str | None = None) -> str:
    from pathlib import Path
    date_str = date_str or datetime.now(KST).strftime("%Y-%m-%d")
    path = Path(__file__).resolve().parent.parent / "reports" / f"{date_str}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return str(path)
