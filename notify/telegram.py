"""텔레그램 리포트 발송 — HTML parse_mode 사용 (Markdown보다 견고)."""
from __future__ import annotations

import html
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

import httpx


KST = timezone(timedelta(hours=9))


def _esc(s) -> str:
    """텔레그램 HTML 모드용 이스케이프."""
    return html.escape(str(s), quote=False)


def send_message(text: str, *, parse_mode: str = "HTML") -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("[telegram] 토큰/채팅ID 없음 — 콘솔로만 출력")
        print(text)
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    truncated = text[:4000]

    def _post(body: dict) -> tuple[bool, str]:
        try:
            with httpx.Client(timeout=15.0) as c:
                r = c.post(url, json=body)
                if r.status_code >= 400:
                    return False, f"{r.status_code} {r.text[:200]}"
            return True, ""
        except Exception as e:  # noqa: BLE001
            return False, str(e)

    ok, err = _post({
        "chat_id": chat_id,
        "text": truncated,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    })
    if ok:
        return True

    print(f"[telegram] HTML 발송 실패 ({err}) → 플레인 텍스트로 재시도")
    import re
    plain = re.sub(r"<[^>]+>", "", truncated)
    plain = html.unescape(plain)
    ok, err = _post({
        "chat_id": chat_id,
        "text": plain,
        "disable_web_page_preview": True,
    })
    if not ok:
        print(f"[telegram] 플레인 발송도 실패: {err}")
    return ok


def format_daily_report(
    *,
    prediction,
    top_statements: list[dict],
    market_snapshot: dict,
    pain_result,
) -> str:
    """일일 리포트 HTML 생성."""
    now_kst = datetime.now(KST)
    prob = prediction.taco_probability
    if prob >= 80:
        emoji, label = "🚨", "매우 높음"
    elif prob >= 60:
        emoji, label = "⚠️", "높음"
    elif prob >= 40:
        emoji, label = "🟡", "중간"
    else:
        emoji, label = "⚪", "낮음"

    lines = [
        f"<b>{emoji} RumpTACO 일일 리포트</b> — {_esc(now_kst.strftime('%Y-%m-%d %H:%M KST'))}",
        "",
        f"<b>TACO 확률</b>: <code>{prob:.1f}%</code> ({_esc(label)})",
        f"<b>Aggression</b>: <code>{prediction.aggression_score:.1f}</code> / "
        f"<b>Pain Index</b>: <code>{prediction.pain_index:.1f}</code>",
    ]
    if prediction.expected_window_hours:
        lo, hi = prediction.expected_window_hours
        lines.append(f"<b>예상 윈도우</b>: {lo:.0f}~{hi:.0f}시간")
    lines.append("")

    lines.append("<b>📊 시장 지표</b>")
    label_map = {
        "treasury_10y": "10Y T", "sp500": "S&amp;P", "djia": "DJIA", "nasdaq": "NASDAQ",
        "vix": "VIX", "wti_usd": "WTI", "breakeven_5y": "5Y BEI", "btc_usd": "BTC",
        "trump_approval": "지지율",
    }
    for k, lbl in label_map.items():
        v = market_snapshot.get(k)
        if v is None:
            continue
        v_fmt = f"{v:,.2f}" if isinstance(v, float) else str(v)
        lines.append(f"  • {lbl}: <code>{_esc(v_fmt)}</code>")
    lines.append("")

    lines.append("<b>🗣 주요 발언 Top 3</b>")
    if not top_statements:
        lines.append("  <i>(수집된 발언 없음)</i>")
    else:
        for s in top_statements[:3]:
            score = s.get("aggression_score")
            snippet = s.get("content", "")[:140].replace("\n", " ")
            score_str = f"{score:.0f}" if isinstance(score, (int, float)) else "?"
            lines.append(f"  • [{score_str}] {_esc(snippet)}")
    lines.append("")

    if pain_result.missing:
        lines.append(f"<i>결측 지표</i>: {_esc(', '.join(pain_result.missing))}")
        lines.append("")

    lines.append(f"<i>모델: {_esc(prediction.model_version)} (실험적 룰베이스)</i>")
    lines.append("<i>⚠️ 투자 권유 아님. 정보 제공 목적.</i>")
    return "\n".join(lines)


def save_report(text: str, date_str: str | None = None) -> str:
    date_str = date_str or datetime.now(KST).strftime("%Y-%m-%d")
    path = Path(__file__).resolve().parent.parent / "reports" / f"{date_str}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return str(path)
