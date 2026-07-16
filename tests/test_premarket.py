"""盤前運算單元測試。

涵蓋 PROJECT_RULES 要求：正常、空資料、缺欄位、非交易日、API 失敗、
單位轉換、重複資料、極端值、多空方向符號。

注意：tests/fixtures 內的數字為**合成測試資料**，非真實行情。
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from config import data_sources as ds  # noqa: E402
from tqp import premarket  # noqa: E402
from tqp.twse_client import TWSEClient, TWSEClientError  # noqa: E402

SF = ds.STOCK_DAY_FIELDS
TF = ds.T86_FIELDS
FIX = ROOT / "tests" / "fixtures"


def _load(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


# --- parse_number：單位／格式 --------------------------------------------
@pytest.mark.parametrize("raw,expected", [
    ("1,234.5", 1234.5),
    ("1000", 1000.0),
    (2330, 2330.0),
    ("--", None),
    ("", None),
    (None, None),
    ("-3,000,000", -3000000.0),
])
def test_parse_number(raw, expected):
    assert premarket.parse_number(raw) == expected


# --- 市場均價：正常 / 極端值（除零）--------------------------------------
def test_market_average_normal():
    assert premarket.market_average_price(990_000_000, 10_000_000) == pytest.approx(99.0)


def test_market_average_zero_volume():
    assert premarket.market_average_price(1000, 0) is None
    assert premarket.market_average_price(1000, -5) is None
    assert premarket.market_average_price(None, 10) is None


# --- 缺欄位 ---------------------------------------------------------------
def test_missing_field_raises():
    bad = {"Code": "2344", "Name": "華邦電"}  # 無收盤/量/值
    with pytest.raises(premarket.MissingFieldError):
        premarket.build_record("2344", bad, SF)


# --- 空資料 / 非交易日 ----------------------------------------------------
def test_empty_dataset():
    assert premarket.index_by_code([], SF) == {}


def test_non_trading_day_like_empty():
    # 非交易日時 API 回空 list，索引為空，查無該股
    idx = premarket.index_by_code([], SF)
    assert idx.get("2344") is None


# --- 重複資料 -------------------------------------------------------------
def test_duplicate_code_keeps_last():
    rows = [
        {"Code": "2344", "Name": "舊", "ClosingPrice": "10", "TradeVolume": "1", "TradeValue": "10"},
        {"Code": "2344", "Name": "新", "ClosingPrice": "20", "TradeVolume": "1", "TradeValue": "20"},
    ]
    idx = premarket.index_by_code(rows, SF)
    assert idx["2344"]["Name"] == "新"


# --- 多空方向符號 ---------------------------------------------------------
def test_institutional_sign():
    rows = _load("t86.json")
    idx = premarket.index_by_code(rows, TF)
    buy = premarket.institutional_net_shares(idx["2344"], TF)
    sell = premarket.institutional_net_shares(idx["2303"], TF)
    assert buy["foreign"] > 0 and buy["total"] > 0     # 買超為正
    assert sell["foreign"] < 0 and sell["total"] < 0   # 賣超為負


# --- 法人均價：估算 vs 官方精算 ------------------------------------------
def test_institutional_avg_estimated_uses_vwap():
    price, estimated = premarket.institutional_average_price(
        net_amount=None, net_shares=5_500_000, fallback_vwap=99.0
    )
    assert estimated is True
    assert price == pytest.approx(99.0)


def test_institutional_avg_official_when_amount_given():
    # 有外部金額：均價 = 金額 / 股數，買賣超皆取正價格
    price, estimated = premarket.institutional_average_price(
        net_amount=-155_000_000, net_shares=-3_100_000, fallback_vwap=50.5
    )
    assert estimated is False
    assert price == pytest.approx(50.0)


def test_institutional_avg_zero_shares():
    price, estimated = premarket.institutional_average_price(0, 0, fallback_vwap=None)
    assert price is None and estimated is False


# --- 整合：build_record 正常路徑 -----------------------------------------
def test_build_record_full():
    srow = premarket.index_by_code(_load("stock_day_all.json"), SF)["2344"]
    trow = premarket.index_by_code(_load("t86.json"), TF)["2344"]
    rec = premarket.build_record("2344", srow, SF, trow, TF)
    assert rec["close"] == pytest.approx(100.0)
    assert rec["market_avg"] == pytest.approx(99.0)
    assert rec["institutional_avg_estimated"] is True          # 無金額→估算
    assert rec["institutional"]["total"] == pytest.approx(5_500_000)


# --- API 失敗 / 重試（用假 session，不碰網路）---------------------------
class _FakeResp:
    def __init__(self, payload=None, exc=None):
        self._payload, self._exc = payload, exc

    def raise_for_status(self):
        if self._exc:
            raise self._exc

    def json(self):
        return self._payload


class _FakeSession:
    """前 fail_times 次丟例外，之後回傳 payload。"""
    def __init__(self, fail_times, payload):
        self.fail_times, self.payload, self.calls = fail_times, payload, 0

    def get(self, *a, **k):
        self.calls += 1
        if self.calls <= self.fail_times:
            import requests
            raise requests.RequestException("boom")
        return _FakeResp(payload=self.payload)


def test_client_retry_then_success():
    # backoff=0.0 → 退避等待為 0，測試不被拖慢；前 2 次失敗、第 3 次成功
    sess = _FakeSession(fail_times=2, payload=[{"Code": "2344"}])
    client = TWSEClient(retries=4, backoff=0.0, interval=0.0, session=sess)
    data = client.fetch_json("http://x")
    assert data == [{"Code": "2344"}]
    assert sess.calls == 3


def test_client_all_fail_raises():
    sess = _FakeSession(fail_times=99, payload=[])
    client = TWSEClient(retries=3, backoff=0.0, interval=0.0, session=sess)
    with pytest.raises(TWSEClientError):
        client.fetch_json("http://x")
    assert sess.calls == 3
