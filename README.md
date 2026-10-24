# 台美大型股超級估值雷達 v1

## 這一版已加入
1. 台股 50 + 美股 50 的候選股票池。
2. 真實行情抓取介面（yfinance，可能延遲／缺漏）。
3. DCF、Forward P/E、P/B、EV/EBITDA 四種估值方法。
4. 依產業使用不同的中性假設。
5. Bear / Base / Bull 三情境。
6. 品質分數與估值信心。
7. `/api/stock/<ticker>` 任意股票查詢入口（目前只查股票池）。
8. 手機友善網頁。
9. 未取得足夠資料時，fair value 保持 null，不產生假估值。

## 重要：目前是 v1 工程原型
`universe.py` 目前的 50+50 是候選大型股清單，不是已驗證的「當日市值 Top 50」。
正式版需要接可合法使用的市值排名資料源，並保存排名日期。
同樣地，yfinance 只作免費原型資料接入；正式使用前要確認資料條款。

## 本機
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python refresh_data.py
python app.py

## 雲端
GitHub repository → Render Web Service
Build: pip install -r requirements.txt
Start: gunicorn app:app

## API Key
本版本不要求 API key。
若未來接需 key 的免費額度 API，放雲端 Environment Variables，絕不寫入前端。

## 下一階段
- 驗證每日市值 Top 50
- SEC / TWSE 財報標準化
- Forward EPS / FCF 的一致口徑
- 同業估值分布
- WACC 自動估計
- 產業專屬模型
- 估值歷史分位數
- 估值變動原因解釋
- 任意 ticker 擴充到全市場
