from flask import Flask,jsonify,request,send_from_directory
from pathlib import Path
import json
app=Flask(__name__,static_folder="static"); F=Path(__file__).parent/"data/latest.json"
def read(): return json.loads(F.read_text(encoding="utf-8")) if F.exists() else {"markets":{"TW":[],"US":[]},"warning":"尚未更新資料。"}
@app.get("/")
def home(): return send_from_directory("static","index.html")
@app.get("/api/stocks")
def stocks():
 m=request.args.get("market","TW").upper()
 if m not in ("TW","US"): return jsonify(error="invalid market"),400
 d=read();return jsonify(market=m,updated_at=d.get("updated_at"),warning=d.get("warning"),stocks=d["markets"].get(m,[]))
@app.get("/api/stock/<ticker>")
def stock(ticker):
 d=read()
 for m in ("TW","US"):
  for x in d["markets"].get(m,[]):
   if x["ticker"].upper()==ticker.upper() or x["ticker"].replace(".TW","").upper()==ticker.upper(): return jsonify(x)
 return jsonify(error="ticker not found in current 100-stock universe"),404
@app.get("/health")
def health(): return {"ok":True}
if __name__=="__main__": app.run(host="0.0.0.0",port=5000)
