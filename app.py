from flask import Flask, jsonify, request, send_from_directory
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data" / "latest.json"

app = Flask(__name__, static_folder="static")


def read_data():
    """Read the latest valuation payload; return a safe fallback if unavailable."""
    if not DATA_FILE.exists():
        return {
            "markets": {"TW": [], "US": []},
            "warning": "尚未更新資料。",
            "updated_at": None,
        }

    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("latest.json 根目錄格式錯誤")
        markets = data.get("markets")
        if not isinstance(markets, dict):
            data["markets"] = {"TW": [], "US": []}
        else:
            data["markets"].setdefault("TW", [])
            data["markets"].setdefault("US", [])
        return data
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        app.logger.exception("讀取 latest.json 失敗")
        return {
            "markets": {"TW": [], "US": []},
            "warning": f"資料檔讀取失敗，請稍後重新整理。({type(exc).__name__})",
            "updated_at": None,
        }


@app.get("/")
def home():
    return send_from_directory(ROOT / "static", "index.html")


@app.get("/api/stocks")
def stocks():
    market = request.args.get("market", "TW").upper()
    if market not in ("TW", "US"):
        return jsonify(error="invalid market", message="market 必須是 TW 或 US"), 400

    data = read_data()
    stocks_list = data.get("markets", {}).get(market, [])
    if not isinstance(stocks_list, list):
        stocks_list = []

    return jsonify(
        market=market,
        updated_at=data.get("updated_at"),
        warning=data.get("warning"),
        stocks=stocks_list,
    )


@app.get("/api/stock/<ticker>")
def stock(ticker):
    data = read_data()
    requested = ticker.strip().upper()

    for market in ("TW", "US"):
        for item in data.get("markets", {}).get(market, []):
            item_ticker = str(item.get("ticker", "")).upper()
            normalized_ticker = item_ticker.replace(".TW", "")
            if requested in (item_ticker, normalized_ticker):
                return jsonify(item)

    return jsonify(
        error="ticker not found in current universe",
        message="找不到此股票，請確認代號是否正確。",
    ), 404


@app.get("/health")
def health():
    return jsonify(ok=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
