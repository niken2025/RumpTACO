"""시장지표 수집기.

소스:
  - FRED: 10Y Treasury (DGS10), 5Y Breakeven Inflation (T5YIE)
  - Yahoo Finance (yfinance): ^GSPC, ^DJI, ^IXIC, ^VIX, CL=F
  - CoinGecko: BTC/USD
  - 538 / RCP 트럼프 지지율 (수동 주입 또는 별도 스크레이퍼)
"""
from __future__ import annotations

import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx
import yfinance as yf


FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"
COINGECKO_BASE = "https://api.coingecko.com/api/v3"


@dataclass
class MarketSnapshot:
    ts: str
    treasury_10y: Optional[float] = None
    sp500: Optional[float] = None
    vix: Optional[float] = None
    djia: Optional[float] = None
    nasdaq: Optional[float] = None
    wti_usd: Optional[float] = None
    breakeven_5y: Optional[float] = None
    btc_usd: Optional[float] = None
    trump_approval: Optional[float] = None


def _fred_latest(series_id: str, api_key: str) -> Optional[float]:
    """FRED에서 해당 시리즈의 가장 최신 관측치를 가져옴."""
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 5,
    }
    with httpx.Client(timeout=15.0) as c:
        r = c.get(FRED_BASE, params=params)
        r.raise_for_status()
        for obs in r.json().get("observations", []):
            v = obs.get("value")
            if v not in (None, "", "."):
                return float(v)
    return None


def _yahoo_latest(ticker: str) -> Optional[float]:
    """yfinance로 최근 5일 중 마지막 종가."""
    t = yf.Ticker(ticker)
    hist = t.history(period="5d")
    if hist.empty:
        return None
    return float(hist["Close"].iloc[-1])


def _coingecko_btc() -> Optional[float]:
    with httpx.Client(timeout=15.0) as c:
        r = c.get(f"{COINGECKO_BASE}/simple/price", params={"ids": "bitcoin", "vs_currencies": "usd"})
        r.raise_for_status()
        return float(r.json()["bitcoin"]["usd"])


def collect_snapshot(trump_approval: Optional[float] = None) -> MarketSnapshot:
    """모든 지표를 수집해 스냅샷을 반환. 실패한 지표는 None."""
    fred_key = os.getenv("FRED_API_KEY")
    snap = MarketSnapshot(ts=datetime.now(timezone.utc).isoformat())

    def _safe(fn, *a, **kw):
        try:
            return fn(*a, **kw)
        except Exception as e:  # noqa: BLE001
            print(f"[market] {fn.__name__} 실패: {e}")
            return None

    if fred_key:
        snap.treasury_10y = _safe(_fred_latest, "DGS10", fred_key)
        snap.breakeven_5y = _safe(_fred_latest, "T5YIE", fred_key)
    else:
        print("[market] FRED_API_KEY 없음 — 국채/BEI 건너뜀")

    snap.sp500 = _safe(_yahoo_latest, "^GSPC")
    snap.djia = _safe(_yahoo_latest, "^DJI")
    snap.nasdaq = _safe(_yahoo_latest, "^IXIC")
    snap.vix = _safe(_yahoo_latest, "^VIX")
    snap.wti_usd = _safe(_yahoo_latest, "CL=F")
    snap.btc_usd = _safe(_coingecko_btc)
    snap.trump_approval = trump_approval
    return snap


def snapshot_dict(snap: MarketSnapshot) -> dict:
    return asdict(snap)


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    s = collect_snapshot()
    for k, v in snapshot_dict(s).items():
        print(f"{k:20s} {v}")
