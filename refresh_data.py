import json
from pathlib import Path
from datetime import datetime, timezone

import yfinance as yf

from universe import get_universe
from valuation_engine import run_valuation, assumptions_for

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

UNIVERSE = get_universe()
markets = {"TW": [], "US": []}

for market, rows in UNIVERSE.items():
    for row in rows:
        ticker = row["ticker"]

        # Keep the curated universe display name separate from Yahoo Finance's name.
        # For Taiwan stocks, display_name/name from universe.py should remain Chinese.
        curated_name = row.get("display_name") or row.get("name")
        initial_name = curated_name or ticker

        stock = {
            **row,
            "name": initial_name,
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
            "valuation_status": "資料不足",
            "universe_verified": False,
            "source": "Yahoo Finance via yfinance",
            "notes": "",
        }

        try:
            yahoo_ticker = yf.Ticker(ticker)
            info = yahoo_ticker.get_info() or {}
            history = yahoo_ticker.history(period="5d", auto_adjust=False)

            if history is not None and not history.empty:
                closes = history["Close"].dropna()
                if not closes.empty:
                    stock["price"] = float(closes.iloc[-1])
                    stock["price_as_of"] = str(history.index[-1].date())

            # Taiwan display names are controlled by universe.py; avoid replacing
            # them with Yahoo's English longName/shortName.
            yahoo_name = info.get("longName") or info.get("shortName")
            if market == "US":
                stock["name"] = yahoo_name or curated_name or ticker
            else:
                stock["name"] = curated_name or yahoo_name or ticker

            stock["sector"] = info.get("sector")
            stock["market_cap"] = info.get("marketCap")
            stock["currency"] = info.get("currency") or stock["currency"]
            stock["forward_eps"] = info.get("forwardEps")
            stock["diluted_shares"] = info.get("sharesOutstanding")
            stock["bvps"] = info.get("bookValue")
            stock["roe"] = info.get("returnOnEquity")
            stock["forward_ebitda"] = info.get("ebitda")
            stock["forward_fcf"] = info.get("freeCashflow")

            cash = info.get("totalCash") or 0
            debt = info.get("totalDebt") or 0
            stock["net_debt"] = debt - cash

            if stock["forward_ebitda"]:
                stock["net_debt_to_ebitda"] = (
                    stock["net_debt"] / stock["forward_ebitda"]
                )

            valuation = run_valuation(stock, assumptions_for(stock["sector"]))
            if valuation.get("fair_value") is not None:
                stock.update(valuation)
                stock["valuation_status"] = "模型計算（需人工/資料源驗證假設）"
                if stock["price"]:
                    stock["upside_pct"] = (
                        stock["fair_value"] / stock["price"] - 1
                    ) * 100
            else:
                stock["notes"] = "財務資料不足，未輸出合理價。"

        except Exception as exc:
            stock["notes"] = "資料取得失敗：" + str(exc)[:180]

        markets[market].append(stock)

payload = {
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "warning": (
        "行情可能延遲/缺漏；市值 Top 名單仍需可靠來源定期驗證；"
        "估值為透明模型計算，不能視為保證價格。"
    ),
    "markets": markets,
}

temporary_file = DATA / "latest.json.tmp"
temporary_file.write_text(
    json.dumps(payload, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
temporary_file.replace(DATA / "latest.json")

print("updated", {market: len(rows) for market, rows in markets.items()})
