"""Fail the deployment if the generated valuation dataset is structurally unsafe."""
import json
import math
from pathlib import Path

path = Path(__file__).resolve().parent / "data" / "latest.json"
if not path.exists():
    raise SystemExit("ERROR: data/latest.json does not exist")

with path.open(encoding="utf-8") as handle:
    data = json.load(handle)

if not isinstance(data, dict) or not isinstance(data.get("markets"), dict):
    raise SystemExit("ERROR: invalid top-level JSON structure")
markets = data["markets"]
expected = {"TW": 50, "US": 100}
for market, count in expected.items():
    rows = markets.get(market)
    if not isinstance(rows, list) or len(rows) != count:
        raise SystemExit(f"ERROR: {market} expected {count} stocks; got {len(rows) if isinstance(rows, list) else 'invalid'}")
    tickers = [row.get("ticker") for row in rows]
    if any(not ticker for ticker in tickers) or len(set(tickers)) != len(tickers):
        raise SystemExit(f"ERROR: {market} has missing or duplicate tickers")
    for row in rows:
        for field in ("valuation_status", "universe_verified", "valuation_anomalies", "methods_used"):
            if field not in row:
                raise SystemExit(f"ERROR: {row.get('ticker')} missing required field {field}")
        if not isinstance(row["universe_verified"], bool):
            raise SystemExit(f"ERROR: {row['ticker']} universe_verified must be boolean")
        if not isinstance(row["valuation_anomalies"], list):
            raise SystemExit(f"ERROR: {row['ticker']} valuation_anomalies must be a list")
        for key, value in row.items():
            if isinstance(value, float) and not math.isfinite(value):
                raise SystemExit(f"ERROR: {row['ticker']} has non-finite {key}")

print("DATA VALIDATION PASSED: TW 50 + US 100 = 150 stocks")
