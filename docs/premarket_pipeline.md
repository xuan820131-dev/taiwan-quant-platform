# 盤前個股指標管線（premarket pipeline）

從 TWSE / TPEx OpenAPI 官方資料，算出每檔股票的**收盤價、市場均價、法人均價**，
並輸出成早會用的模板到 `output/`。

## 模組

| 檔案 | 職責 |
|------|------|
| `config/data_sources.py` | 端點 URL、欄位對應、單位（**欄位名稱待首次連線核對**）|
| `src/tqp/twse_client.py` | HTTP 抓取：逾時、指數退避重試、節流、logging |
| `src/tqp/premarket.py` | 純運算：解析、市場均價、法人買賣超、法人均價 |
| `src/tqp/report.py` | 格式化成模板文字 |
| `scripts/gen_premarket.py` | CLI 進入點 |
| `tests/test_premarket.py` | 單元測試（正常／空／缺欄／非交易日／API 失敗／單位／重複／極端值／多空符號）|

## 用法

```bash
# 線上（需可連 TWSE OpenAPI 的環境）
python scripts/gen_premarket.py --codes 2344,2303 --date 2026-07-15

# 離線（用 fixtures 驗證流程，不需網路）
python scripts/gen_premarket.py --codes 2344,2303 --offline tests/fixtures

# 測試
python -m pytest -q
```

## 計算定義與單位

- **收盤價** = `STOCK_DAY_ALL.ClosingPrice`（元）
- **市場均價** = `TradeValue`（成交金額，元）÷ `TradeVolume`（成交股數，股）＝ 元／股
- **法人均價** = 三大法人買賣超**金額** ÷ 三大法人買賣超**股數**（元／股）
- 一張 = 1,000 股；買賣超股數正＝買超、負＝賣超

## ⚠️ 兩個必讀限制

1. **法人均價官方無個股金額**：TWSE / TPEx 的 T86 只公布個股三大法人買賣超「股數」，
   不公布個股「金額」。因此在沒有外部金額來源時，本管線以**當日市場均價近似**法人成交均價，
   並在輸出標記「〔估算〕」。若你有券商內部的法人買賣超金額，
   傳入 `build_record(..., net_amount=金額)` 即可精算（estimated=False）。

2. **欄位名稱待核對**：`config/data_sources.py` 的欄位名稱依官方文件與參考實作整理，
   `twse_client.fetch_json()` 會在 log 印出實際 keys；首次連線請核對，
   若官方調整欄位只需改設定檔，不動運算邏輯（符合 PROJECT_RULES：不猜測欄位）。

## 本環境（Claude Code on the web）限制

此開發環境的 egress 政策封鎖 `www.twse.com.tw`、`openapi.twse.com.tw`、`www.tpex.org.tw`，
**無法在此實跑線上抓取**。運算邏輯已用 `tests/fixtures`（合成資料）離線驗證；
線上模式請在你自己可連線 TWSE 的環境執行。
