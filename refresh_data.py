
import json, math
from pathlib import Path
from datetime import datetime, timezone
import yfinance as yf
from universe import get_universe
from valuation_engine import run_valuation, assumptions_for

ROOT=Path(__file__).parent; DATA=ROOT/"data"; DATA.mkdir(exist_ok=True)
U=get_universe(); markets={"TW":[],"US":[]}
for market, rows in U.items():
    for r in rows:
        x={**r,"name":r["ticker"],"price":None,"currency":"TWD" if market=="TW" else "USD",
           "price_as_of":None,"market_cap":None,"sector":None,"forward_eps":None,"forward_ebitda":None,
           "forward_fcf":None,"bvps":None,"net_debt":None,"diluted_shares":None,"roe":None,
           "fcf_margin":None,"net_debt_to_ebitda":None,"fair_value":None,"bear_value":None,"bull_value":None,
           "upside_pct":None,"quality_score":None,"confidence":0,"valuation_status":"資料不足",
           "universe_verified":False,"source":"Yahoo Finance via yfinance","notes":""}
        try:
            t=yf.Ticker(r["ticker"]); info=t.get_info() or {}; h=t.history(period="5d",auto_adjust=False)
            if h is not None and not h.empty:
                x["price"]=float(h["Close"].dropna().iloc[-1]); x["price_as_of"]=str(h.index[-1].date())
            x["name"]=info.get("longName") or info.get("shortName") or x["name"]
            x["sector"]=info.get("sector")
            x["market_cap"]=info.get("marketCap")
            x["currency"]=info.get("currency") or x["currency"]
            x["forward_eps"]=info.get("forwardEps")
            x["diluted_shares"]=info.get("sharesOutstanding")
            x["bvps"]=info.get("bookValue")
            x["roe"]=info.get("returnOnEquity")
            x["forward_ebitda"]=info.get("ebitda")
            x["forward_fcf"]=info.get("freeCashflow")
            cash=info.get("totalCash") or 0; debt=info.get("totalDebt") or 0
            x["net_debt"]=debt-cash
            if x["forward_ebitda"]: x["net_debt_to_ebitda"]=x["net_debt"]/x["forward_ebitda"]
            if x["price"] and x["forward_eps"] and x["price"]>0:
                pass
            v=run_valuation(x,assumptions_for(x["sector"]))
            if v["fair_value"] is not None:
                x.update(v); x["valuation_status"]="模型計算（需人工/資料源驗證假設）"
                if x["price"]: x["upside_pct"]=(x["fair_value"]/x["price"]-1)*100
            else:
                x["notes"]="財務資料不足，未輸出合理價。"
        except Exception as e:
            x["notes"]="資料取得失敗："+str(e)[:180]
        markets[market].append(x)
payload={"updated_at":datetime.now(timezone.utc).isoformat(),
         "warning":"行情可能延遲/缺漏；市值 Top 50 名單仍需可靠來源每日驗證；估值為透明模型計算，不能視為保證價格。",
         "markets":markets}
tmp=DATA/"latest.json.tmp";tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8");tmp.replace(DATA/"latest.json")
print("updated", {k:len(v) for k,v in markets.items()})
