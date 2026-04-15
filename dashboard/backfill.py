"""60일 시장 데이터 백필 — docs/data/history.json 초기화.

- FRED: DGS10(10Y), T5YIE(5Y BEI) — 일별 시계열 최근 90일에서 가장 최신 60영업일
- yfinance: SPX/DJI/IXIC/VIX/CL=F — history(period='90d')
- CoinGecko: BTC daily 90일
- trump_approval: 데이터 없음 → None

기존 history.json이 있어도 덮어씀 (--preserve 플래그로 보존 가능).
"""
from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import yfinance as yf


KST = timezone(timedelta(hours=9))
DOCS_DATA = Path(__file__).resolve().parent.parent / "docs" / "data"
DAYS = 60


def _fred_series(series_id: str, api_key: str, days: int = 90) -> dict[str, float]:
    """{date_str: value} 반환."""
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=days)
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": start.isoformat(),
        "observation_end": end.isoformat(),
    }
    with httpx.Client(timeout=20.0) as c:
        r = c.get("https://api.stlouisfed.org/fred/series/observations", params=params)
        r.raise_for_status()
        data = r.json().get("observations", [])
    out = {}
    for o in data:
        v = o.get("value")
        if v not in (None, "", "."):
            out[o["date"]] = float(v)
    return out


def _yahoo_series(ticker: str, days: int = 90) -> dict[str, float]:
    t = yf.Ticker(ticker)
    hist = t.history(period=f"{days}d")
    return {idx.strftime("%Y-%m-%d"): float(row["Close"]) for idx, row in hist.iterrows() if row["Close"] == row["Close"]}


def _coingecko_btc_series(days: int = 90) -> dict[str, float]:
    url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
    with httpx.Client(timeout=20.0) as c:
        r = c.get(url, params={"vs_currency": "usd", "days": days, "interval": "daily"})
        r.raise_for_status()
        data = r.json().get("prices", [])
    # [[ms, price], ...]
    out: dict[str, float] = {}
    for ms, price in data:
        d = datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        out[d] = float(price)
    return out


def build_history(days: int = DAYS) -> list[dict]:
    from dotenv import load_dotenv
    load_dotenv()

    fred_key = os.getenv("FRED_API_KEY")
    series = {
        "treasury_10y": _fred_series("DGS10", fred_key) if fred_key else {},
        "breakeven_5y": _fred_series("T5YIE", fred_key) if fred_key else {},
        "sp500": _yahoo_series("^GSPC"),
        "djia": _yahoo_series("^DJI"),
        "nasdaq": _yahoo_series("^IXIC"),
        "vix": _yahoo_series("^VIX"),
        "wti_usd": _yahoo_series("CL=F"),
        "btc_usd": _coingecko_btc_series(),
    }

    # 전체 날짜 집합
    all_dates = set()
    for s in series.values():
        all_dates.update(s.keys())
    sorted_dates = sorted(all_dates)[-days:]

    out = []
    for d in sorted_dates:
        market = {k: series[k].get(d) for k in series}
        market["trump_approval"] = None
        out.append({
            "date": d,
            "generated_at": d + "T00:00:00+09:00",
            "taco_probability": None,
            "aggression_score": None,
            "pain_index": None,
            "market": market,
        })
    return out


def main(preserve_today: bool = True) -> Path:
    DOCS_DATA.mkdir(parents=True, exist_ok=True)
    new_hist = build_history()
    hist_path = DOCS_DATA / "history.json"

    today_entry = None
    if preserve_today and hist_path.exists():
        try:
            old = json.loads(hist_path.read_text(encoding="utf-8"))
            today = datetime.now(KST).strftime("%Y-%m-%d")
            today_entry = next((e for e in old if e.get("date") == today and e.get("taco_probability") is not None), None)
        except Exception:  # noqa: BLE001
            pass

    if today_entry:
        existing = next((e for e in new_hist if e["date"] == today_entry["date"]), None)
        merged_market = dict(existing.get("market", {})) if existing else {}
        merged_market.update({k: v for k, v in (today_entry.get("market") or {}).items() if v is not None})
        today_entry["market"] = merged_market
        new_hist = [e for e in new_hist if e["date"] != today_entry["date"]]
        new_hist.append(today_entry)
        new_hist.sort(key=lambda x: x["date"])

    hist_path.write_text(json.dumps(new_hist, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[backfill] {len(new_hist)}일 데이터 저장 → {hist_path}")
    return hist_path


if __name__ == "__main__":
    main()
