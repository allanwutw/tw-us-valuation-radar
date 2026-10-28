# 台美大型股估值雷達股票池
# 台股 50 檔 + 美股 100 檔候選池
#
# 注意：
# 這裡的清單是候選股票池，不代表每日即時市值排名。
# universe_verified 應由資料更新程序依可靠來源進一步驗證。

TW = [
    "2330.TW","2454.TW","2317.TW","2382.TW","2308.TW",
    "2881.TW","2882.TW","2891.TW","2412.TW","3711.TW",
    "2303.TW","1301.TW","1303.TW","2002.TW","2886.TW",
    "2884.TW","2892.TW","2885.TW","2880.TW","1216.TW",
    "2207.TW","3045.TW","4904.TW","3008.TW","2395.TW",
    "2357.TW","2353.TW","2379.TW","3034.TW","6669.TW",
    "3231.TW","4938.TW","2327.TW","2603.TW","2609.TW",
    "2615.TW","2618.TW","2912.TW","5871.TW","5876.TW",
    "2890.TW","2887.TW","2883.TW","3037.TW","2345.TW",
    "3661.TW","5269.TW","8299.TW","2408.TW","6770.TW"
]

US = [
    "NVDA","MSFT","AAPL","AMZN","GOOGL","GOOG","META","AVGO","BRK-B","TSLA",
    "LLY","WMT","JPM","V","XOM","UNH","ORCL","MA","COST","JNJ",
    "HD","PG","ABBV","BAC","NFLX","CVX","KO","CRM","MRK","AMD",
    "PEP","ADBE","TMO","LIN","ACN","CSCO","MCD","WFC","IBM","GE",
    "ABT","CAT","DHR","QCOM","INTU","TXN","AMGN","NOW","PM","AXP",
    "ISRG","VZ","GS","RTX","SPGI","BLK","DIS","LOW","PLTR","SYK",
    "UBER","PFE","BKNG","TJX","ADP","BSX","C","AMAT","GILD","DE",
    "MDT","LRCX","ADI","MMC","VRTX","MU","PANW","HON","ETN","COP",
    "CB","REGN","KLAC","CMCSA","SO","BMY","NKE","SBUX","PGR","CI",
    "LMT","MO","ICE","DUK","UPS","CME","SNPS","CDNS","CRWD","MAR"
]

TW_NAMES = {
    "2330.TW": "台積電",
    "2454.TW": "聯發科",
    "2317.TW": "鴻海",
    "2382.TW": "廣達",
    "2308.TW": "台達電",
    "2881.TW": "富邦金",
    "2882.TW": "國泰金",
    "2891.TW": "中信金",
    "2412.TW": "中華電",
    "3711.TW": "日月光投控",
    "2303.TW": "聯電",
    "1301.TW": "台塑",
    "1303.TW": "南亞",
    "2002.TW": "中鋼",
    "2886.TW": "兆豐金",
    "2884.TW": "玉山金",
    "2892.TW": "第一金",
    "2885.TW": "元大金",
    "2880.TW": "華南金",
    "1216.TW": "統一",
    "2207.TW": "和泰車",
    "3045.TW": "台灣大",
    "4904.TW": "遠傳",
    "3008.TW": "大立光",
    "2395.TW": "研華",
    "2357.TW": "華碩",
    "2353.TW": "宏碁",
    "2379.TW": "瑞昱",
    "3034.TW": "聯詠",
    "6669.TW": "緯穎",
    "3231.TW": "緯創",
    "4938.TW": "和碩",
    "2327.TW": "國巨",
    "2603.TW": "長榮",
    "2609.TW": "陽明",
    "2615.TW": "萬海",
    "2618.TW": "長榮航",
    "2912.TW": "統一超",
    "5871.TW": "中租-KY",
    "5876.TW": "上海商銀",
    "2890.TW": "永豐金",
    "2887.TW": "台新新光金",
    "2883.TW": "凱基金",
    "3037.TW": "欣興",
    "2345.TW": "智邦",
    "3661.TW": "世芯-KY",
    "5269.TW": "祥碩",
    "8299.TW": "群聯",
    "2408.TW": "南亞科技",
    "6770.TW": "力積電",
}


def get_universe():
    return {
        "TW": [
            {
                "ticker": ticker,
                "market": "TW",
                "display_name": TW_NAMES.get(ticker, ticker),
            }
            for ticker in TW
        ],
        "US": [
            {
                "ticker": ticker,
                "market": "US",
                "display_name": ticker,
            }
            for ticker in US
        ],
    }
