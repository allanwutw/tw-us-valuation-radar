"""Fetch market data and produce data/latest.json for the static dashboard."""
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import yfinance as yf

from universe import get_universe
from valuation_engine import run_valuation, assumptions_for

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
OUTPUT = DATA_DIR / "latest.json"


def number_or_none(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def is_verified(ticker, info, market):
    """Verify identity conservatively; no successful lookup means unverified."""
    returned_symbol = str(info.get("symbol") or "").upper().strip()
    quote_type = str(info.get("quoteType") or "").upper().strip()
    expected = ticker.upper().strip()
    market_suffix_ok = (market == "TW" and expected.endswith(".TW")) or (
        market == "US" and not expected.endswith((".TW", ".TWO"))
    )
    return bool(returned_symbol == expected and quote_type == "EQUITY" and market_suffix_ok)


def clean_value(value):
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {str(k): clean_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean_value(v) for v in value]
    try:
        return clean_value(value.item())
    except (AttributeError, ValueError, TypeError):
        return str(value)


def fetch_one(row, market):
    ticker = row["ticker"]
    curated_name = row.get("display_name") or row.get("name") or ticker
    stock = {
        **row,
        "name": curated_name,
        "price": None,
        "currency": "TWD" if market == "TW" else "USD",
        "price_as_of": None,
        "market_cap": None,
        "sector": None,
        "forward_eps": None,
        "forward_ebitda": None,
        "forward_fcf": None,
        "bvps": None,
        "net_debt": None,
        "diluted_shares": None,
        "roe": None,
        "fcf_margin": None,
        "net_debt_to_ebitda": None,
        "fair_value": None,
        "bear_value": None,
        "bull_value": None,
        "upside_pct": None,
        "quality_score": None,
        "confidence": 0,
        "methods_used": 0,
        "valuation_status": "資料不足，尚未完成計算",
        "valuation_anomalies": [],
        "outlier_adjusted": False,
        "universe_verified": False,
        "verification_detail": "尚未取得可核對的 Yahoo Finance 股票識別資料",
        "source": "Yahoo Finance via yfinance",
        "notes": "",
    }

    try:
        instrument = yf.Ticker(ticker)
        try:
            info = instrument.get_info() or {}
        except Exception as exc:
            info = {}
            stock["notes"] = f"基本資料取得失敗：{str(exc)[:120]}"

        try:
            history = instrument.history(period="5d", auto_adjust=False)
            if history is not None and not history.empty:
                closes = history["Close"].dropna()
                if not closes.empty:
                    stock["price"] = number_or_none(closes.iloc[-1])
                    stock["price_as_of"] = str(closes.index[-1].date())
        except Exception as exc:
            stock["notes"] = (stock["notes"] + "；" if stock["notes"] else "") + f"行情取得失敗：{str(exc)[:120]}"

        yahoo_name = info.get("longName") or info.get("shortName")
        stock["name"] = (yahoo_name or curated_name or ticker) if market == "US" else curated_name
        stock["sector"] = info.get("sector") or info.get("industry")
        stock["market_cap"] = number_or_none(info.get("marketCap"))
        stock["currency"] = info.get("currency") or stock["currency"]
        stock["forward_eps"] = number_or_none(info.get("forwardEps"))
        stock["bvps"] = number_or_none(info.get("bookValue"))
        stock["roe"] = number_or_none(info.get("returnOnEquity"))

        # Yahoo's generic EBITDA and freeCashflow fields are trailing/current
        # reported values, not necessarily analyst forward estimates. Keep the
        # legacy field names for compatibility, but disclose the data definition.
        stock["forward_ebitda"] = number_or_none(info.get("ebitda"))
        stock["forward_fcf"] = number_or_none(info.get("freeCashflow"))
        shares = info.get("impliedSharesOutstanding") or info.get("sharesOutstanding")
        stock["diluted_shares"] = number_or_none(shares)

        cash_raw, debt_raw = info.get("totalCash"), info.get("totalDebt")
        cash, debt = number_or_none(cash_raw), number_or_none(debt_raw)
        # Do not silently turn a missing balance-sheet value into zero.
        if cash is not None and debt is not None:
            stock["net_debt"] = debt - cash
        elif cash is not None and debt_raw is None:
            stock["notes"] = (stock["notes"] + "；" if stock["notes"] else "") + "總負債資料缺失，未計算淨負債"
        elif debt is not None and cash_raw is None:
            stock["notes"] = (stock["notes"] + "；" if stock["notes"] else "") + "現金資料缺失，未計算淨負債"

        revenue = number_or_none(info.get("totalRevenue"))
        if stock["forward_fcf"] is not None and revenue is not None and revenue > 0:
            stock["fcf_margin"] = stock["forward_fcf"] / revenue
        ebitda = stock["forward_ebitda"]
        if ebitda is not None and ebitda != 0 and stock["net_debt"] is not None:
            stock["net_debt_to_ebitda"] = stock["net_debt"] / ebitda

        stock["universe_verified"] = is_verified(ticker, info, market)
        stock["verification_detail"] = (
            "Yahoo Finance 回傳代號及股票類型相符"
            if stock["universe_verified"] else
            "未能確認回傳代號／股票類型；不代表股票代號必然錯誤"
        )

        valuation = run_valuation(stock, assumptions_for(stock["sector"]))
        # Always preserve the engine's status and diagnostics, including when
        # fair_value is intentionally suppressed.
        stock.update(valuation)
        if stock["fair_value"] is not None and stock["price"] not in (None, 0):
            stock["upside_pct"] = (stock["fair_value"] / stock["price"] - 1) * 100
        elif stock["fair_value"] is None:
            stock["upside_pct"] = None

        stock["notes"] = (stock["notes"] + "；" if stock["notes"] else "") + (
            "EBITDA／自由現金流採 Yahoo Finance 回傳欄位，可能為近四季資料，非保證為預估值。"
        )
        if shares is not None and info.get("impliedSharesOutstanding") is None:
            stock["notes"] += "股數採 sharesOutstanding 作為估值分母近似值，非明確稀釋後股數。"
    except Exception as exc:
        stock["valuation_status"] = "資料取得失敗，暫不提供合理價"
        stock["notes"] = (stock["notes"] + "；" if stock["notes"] else "") + "資料取得失敗：" + str(exc)[:180]
        stock["valuation_anomalies"] = ["資料取得程序發生例外"]

    return clean_value(stock)


def main():
    universe = get_universe()
    markets = {"TW": [], "US": []}
    for market, rows in universe.items():
        for row in rows:
            stock = fetch_one(row, market)
            markets[market].append(stock)
            print(f"{market} {stock['ticker']}: {stock['valuation_status']}")

    payload = {
        "schema_version": 2,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "warning": (
            "股票池為候選觀察清單，非每日即時市值排名；行情可能延遲或缺漏。"
            "估值為模型推算，財務欄位可能含近四季資料，需自行核對，不構成投資建議。"
        ),
        "markets": markets,
    }
    temporary = OUTPUT.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(OUTPUT)
    print("updated", {market: len(rows) for market, rows in markets.items()})


if __name__ == "__main__":
    main()
