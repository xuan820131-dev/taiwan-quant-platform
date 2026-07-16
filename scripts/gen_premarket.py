#!/usr/bin/env python3
"""盤前個股指標產生器。

用法：
  # 線上（需可連 TWSE OpenAPI 的環境）
  python scripts/gen_premarket.py --codes 2344,2303

  # 離線（用 tests/fixtures 驗證流程，不需網路）
  python scripts/gen_premarket.py --codes 2344,2303 --offline tests/fixtures

輸出：output/premarket_<date>.md

注意：本機（Claude Code on the web）egress 政策封鎖 TWSE/TPEx 網域，
線上模式需在你自己可連線的環境執行；離線模式可在任何環境跑。
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# 讓 `python scripts/xxx.py` 能找到 src/ 與 config/
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from config import data_sources as ds  # noqa: E402
from tqp import premarket, report  # noqa: E402
from tqp.twse_client import TWSEClient  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("gen_premarket")


def _load(offline_dir: str | None, url: str, fixture_name: str) -> list[dict]:
    """線上打 API；離線讀 fixture JSON。"""
    if offline_dir:
        path = Path(offline_dir) / fixture_name
        logger.info("離線載入 %s", path)
        return json.loads(path.read_text(encoding="utf-8"))
    return TWSEClient().fetch_json(url)


def build_records(codes: list[str], offline_dir: str | None) -> list[dict]:
    stock_rows = _load(offline_dir, ds.TWSE_STOCK_DAY_ALL, "stock_day_all.json")
    t86_rows = _load(offline_dir, ds.TWSE_T86, "t86.json")

    stock_idx = premarket.index_by_code(stock_rows, ds.STOCK_DAY_FIELDS)
    t86_idx = premarket.index_by_code(t86_rows, ds.T86_FIELDS)

    records = []
    for code in codes:
        srow = stock_idx.get(code)
        if srow is None:
            logger.warning("找不到 %s 的日成交資料（非交易日或代號錯誤？）", code)
            continue
        rec = premarket.build_record(
            code=code,
            stock_row=srow,
            stock_fields=ds.STOCK_DAY_FIELDS,
            t86_row=t86_idx.get(code),
            t86_fields=ds.T86_FIELDS,
        )
        records.append(rec)
    return records


def main() -> int:
    ap = argparse.ArgumentParser(description="產生盤前個股指標模板")
    ap.add_argument("--codes", required=True, help="股票代號，逗號分隔，例如 2344,2303")
    ap.add_argument("--offline", default=None, help="離線 fixtures 目錄（測試用）")
    ap.add_argument("--date", default="latest", help="標題用日期字串，預設 latest")
    ap.add_argument("--out", default=str(ROOT / "output"), help="輸出目錄")
    args = ap.parse_args()

    codes = [c.strip() for c in args.codes.split(",") if c.strip()]
    records = build_records(codes, args.offline)
    if not records:
        logger.error("沒有可輸出的紀錄")
        return 1

    text = report.format_report(records, title=f"盤前個股指標｜{args.date}")
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"premarket_{args.date}.md"
    out_path.write_text(text, encoding="utf-8")
    logger.info("已輸出 %s", out_path)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
