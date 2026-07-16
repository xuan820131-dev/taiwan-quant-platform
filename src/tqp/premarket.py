"""盤前個股指標運算。

輸入為 OpenAPI 已解析的 list[dict]（見 twse_client），輸出每檔股票的：
- 收盤價（元）
- 市場均價 = 成交金額 / 成交股數（元／股）
- 法人均價 = 三大法人買賣超金額 / 三大法人買賣超股數（元／股）

⚠️ 法人均價的資料限制（務必知道）
--------------------------------------------------------
TWSE / TPEx 官方個股 T86 只提供三大法人買賣超「股數」，
**不提供個股層級的法人買賣超金額**。因此：
- 若呼叫端能提供外部「法人買賣超金額」（例如券商內部資料），
  就用官方公式精算，estimated=False。
- 若沒有金額來源，本模組以「當日市場均價」近似法人成交均價，
  並標記 estimated=True，避免把估計值當成官方數字。

本模組為純函式、不碰網路，便於單元測試。
"""

from __future__ import annotations

import logging
from typing import Any, Iterable

logger = logging.getLogger(__name__)

SHARES_PER_LOT = 1000  # 一張 = 1,000 股


class MissingFieldError(KeyError):
    """來源資料缺少必要欄位。"""


def parse_number(raw: Any) -> float | None:
    """把 TWSE 字串數字（可能含千分位逗號或 '--'）轉為 float。

    無法解析或表示「無資料」時回傳 None，不丟例外，
    交由上層決定如何處理（符合『空資料／缺欄位』需可測試）。
    """
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    text = str(raw).strip().replace(",", "")
    if text in ("", "--", "---", "N/A", "NA"):
        return None
    try:
        return float(text)
    except ValueError:
        logger.debug("無法解析數字：%r", raw)
        return None


def _require(row: dict, field_map: dict, key: str) -> Any:
    """依對應表取值，缺欄位時丟 MissingFieldError。"""
    src = field_map.get(key)
    if src is None or src not in row:
        raise MissingFieldError(f"缺少欄位 {key!r}（來源鍵 {src!r}）")
    return row[src]


def index_by_code(rows: Iterable[dict], field_map: dict) -> dict[str, dict]:
    """以股票代號建索引；遇重複代號保留最後一筆並記錄警告。"""
    indexed: dict[str, dict] = {}
    code_key = field_map["code"]
    for row in rows:
        code = str(row.get(code_key, "")).strip()
        if not code:
            continue
        if code in indexed:
            logger.warning("重複代號 %s，以最後一筆為準", code)
        indexed[code] = row
    return indexed


def market_average_price(trade_value: float | None, trade_volume: float | None) -> float | None:
    """市場均價（元／股）= 成交金額(元) / 成交股數(股)。

    成交量為 0、None 或負值時回傳 None（避免除以零／極端值）。
    """
    if trade_value is None or trade_volume is None:
        return None
    if trade_volume <= 0:
        return None
    return trade_value / trade_volume


def institutional_net_shares(t86_row: dict, field_map: dict) -> dict[str, float | None]:
    """回傳外資／投信／自營／合計買賣超『股數』（正=買超，負=賣超）。"""
    return {
        "foreign": parse_number(t86_row.get(field_map.get("foreign_net", ""))),
        "trust": parse_number(t86_row.get(field_map.get("trust_net", ""))),
        "dealer": parse_number(t86_row.get(field_map.get("dealer_net", ""))),
        "total": parse_number(t86_row.get(field_map.get("total_net", ""))),
    }


def institutional_average_price(
    net_amount: float | None,
    net_shares: float | None,
    fallback_vwap: float | None = None,
) -> tuple[float | None, bool]:
    """法人均價（元／股）。

    回傳 (價格, estimated)。
    - 有官方/外部法人金額時：price = 金額 / 股數，estimated=False。
    - 否則以 fallback_vwap（當日市場均價）近似，estimated=True。
    - 股數為 0 時無意義，回傳 (None, False)。
    """
    if net_shares is not None and net_shares != 0 and net_amount is not None:
        # 金額與股數同為淨額，相除得法人平均成交價；取絕對值使買/賣超皆為正價格
        return abs(net_amount) / abs(net_shares), False
    if fallback_vwap is not None:
        return fallback_vwap, True
    return None, False


def build_record(
    code: str,
    stock_row: dict,
    stock_fields: dict,
    t86_row: dict | None = None,
    t86_fields: dict | None = None,
    net_amount: float | None = None,
) -> dict:
    """組出單一個股的盤前紀錄。

    Args:
        stock_row/stock_fields: STOCK_DAY_ALL 該股資料與欄位對應。
        t86_row/t86_fields: 三大法人資料與欄位對應（可為 None）。
        net_amount: 外部提供之三大法人買賣超金額（元）；None 表示無官方金額。
    """
    name = stock_row.get(stock_fields.get("name", ""), "")
    close = parse_number(_require(stock_row, stock_fields, "close"))
    volume = parse_number(_require(stock_row, stock_fields, "volume"))
    value = parse_number(_require(stock_row, stock_fields, "value"))
    vwap = market_average_price(value, volume)

    record: dict[str, Any] = {
        "code": code,
        "name": name,
        "close": close,
        "market_avg": vwap,
        "trade_volume_shares": volume,
        "trade_value": value,
        "institutional": None,
        "institutional_avg": None,
        "institutional_avg_estimated": None,
    }

    if t86_row is not None and t86_fields is not None:
        nets = institutional_net_shares(t86_row, t86_fields)
        inst_price, estimated = institutional_average_price(
            net_amount=net_amount,
            net_shares=nets.get("total"),
            fallback_vwap=vwap,
        )
        record["institutional"] = nets
        record["institutional_avg"] = inst_price
        record["institutional_avg_estimated"] = estimated

    return record
