"""台股官方資料來源設定（TWSE / TPEx OpenAPI）。

集中管理 API 端點、欄位對應與單位，方便日後核對與維護。

⚠️ 重要（符合 PROJECT_RULES：不猜測 API 欄位／單位）
--------------------------------------------------------
下列「欄位名稱」依 TWSE / TPEx OpenAPI 官方文件與參考實作整理，
但**必須在你可連線的環境用實際回傳核對一次**再視為定案。
`twse_client.fetch_json()` 會在 log 印出實際 keys，
若官方調整欄位，只需修改本檔的對應表，不必動運算邏輯。

單位說明（TWSE OpenAPI STOCK_DAY_ALL）
- TradeVolume  成交股數，單位：股
- TradeValue   成交金額，單位：元
- ClosingPrice 收盤價，單位：元／股
- 一張 = 1,000 股
"""

from typing import Final

# --- 端點 -------------------------------------------------------------------
# 上市個股「當日」全部日成交資訊（回傳最近一個交易日）
TWSE_STOCK_DAY_ALL: Final[str] = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"

# 上市個股「當日」三大法人買賣超（單位：股）
TWSE_T86: Final[str] = "https://openapi.twse.com.tw/v1/fund/T86"

# 上櫃個股當日收盤行情（TPEx OpenAPI）
TPEX_DAILY_CLOSE: Final[str] = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes"

# 上櫃個股當日三大法人買賣超
TPEX_T86: Final[str] = "https://www.tpex.org.tw/openapi/v1/tpex_3insti_trading_stock"

# --- 欄位對應（待實際回傳核對）---------------------------------------------
# STOCK_DAY_ALL：一檔股票一筆 dict
STOCK_DAY_FIELDS: Final[dict] = {
    "code": "Code",             # 股票代號
    "name": "Name",             # 股票名稱
    "close": "ClosingPrice",    # 收盤價（元）
    "volume": "TradeVolume",    # 成交股數（股）
    "value": "TradeValue",      # 成交金額（元）
}

# T86：一檔股票一筆 dict。TWSE OpenAPI 的 T86 只提供三大法人買賣超「股數」，
# 官方**不揭露個股層級的法人買賣超金額**，因此「法人均價」在無外部金額來源時
# 只能以市場均價近似（premarket.py 會標記 estimated=True）。
T86_FIELDS: Final[dict] = {
    "code": "Code",
    "name": "Name",
    # 外資及陸資（不含外資自營商）買賣超股數
    "foreign_net": "ForeignInvestorsExcludingForeignDealersNetBuySell",
    # 投信買賣超股數
    "trust_net": "InvestmentTrustNetBuySell",
    # 自營商買賣超股數（自行買賣＋避險合計）
    "dealer_net": "DealerNetBuySell",
    # 三大法人買賣超股數合計
    "total_net": "TotalNetBuySell",
}

# 一張股票的股數
SHARES_PER_LOT: Final[int] = 1000
