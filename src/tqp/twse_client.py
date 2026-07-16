"""TWSE / TPEx OpenAPI HTTP 用戶端。

負責：送出 GET、逾時控制、失敗重試（指數退避）、速率節流與 logging。
不做任何金融運算，運算邏輯放在 premarket.py，方便分離測試。
"""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

# 預設參數（可由呼叫端覆寫）
DEFAULT_TIMEOUT: float = 15.0        # 單次請求逾時（秒）
DEFAULT_RETRIES: int = 4             # 最多重試次數
DEFAULT_BACKOFF: float = 2.0         # 退避基數（2s, 4s, 8s, 16s）
DEFAULT_INTERVAL: float = 0.5        # 相鄰請求最小間隔（秒），避免被限流
USER_AGENT: str = (
    "Mozilla/5.0 (compatible; TQP/0.1; +https://github.com/xuan820131-dev/"
    "taiwan-quant-platform)"
)


class TWSEClientError(RuntimeError):
    """對外統一的資料抓取錯誤。"""


class TWSEClient:
    """簡單、可重試的 OpenAPI 用戶端。"""

    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
        backoff: float = DEFAULT_BACKOFF,
        interval: float = DEFAULT_INTERVAL,
        session: requests.Session | None = None,
    ) -> None:
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff
        self.interval = interval
        self._session = session or requests.Session()
        self._last_request_at = 0.0

    def _throttle(self) -> None:
        """確保相鄰請求間隔至少 self.interval 秒。"""
        elapsed = time.time() - self._last_request_at
        if elapsed < self.interval:
            time.sleep(self.interval - elapsed)

    def fetch_json(self, url: str) -> list[dict[str, Any]]:
        """抓取單一 OpenAPI 端點並回傳 list[dict]。

        失敗時以指數退避重試；重試用盡才丟出 TWSEClientError。
        會在 log 印出實際欄位 keys，方便核對官方欄位是否變動。
        """
        last_err: Exception | None = None
        for attempt in range(1, self.retries + 1):
            self._throttle()
            try:
                logger.info("GET %s (第 %d 次)", url, attempt)
                resp = self._session.get(
                    url,
                    headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                    timeout=self.timeout,
                )
                self._last_request_at = time.time()
                resp.raise_for_status()
                data = resp.json()
                if not isinstance(data, list):
                    raise TWSEClientError(f"預期回傳 list，實得 {type(data).__name__}")
                if data:
                    logger.info("實際欄位 keys：%s", sorted(data[0].keys()))
                else:
                    logger.warning("端點回傳空資料（可能為非交易日或尚未更新）：%s", url)
                return data
            except (requests.RequestException, ValueError) as err:
                last_err = err
                self._last_request_at = time.time()
                if attempt < self.retries:
                    wait = self.backoff ** attempt
                    logger.warning("抓取失敗（%s），%.0f 秒後重試：%s", err, wait, url)
                    time.sleep(wait)
        raise TWSEClientError(f"抓取失敗，已重試 {self.retries} 次：{url}") from last_err
