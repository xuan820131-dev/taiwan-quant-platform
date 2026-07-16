"""把盤前紀錄格式化成早會用的模板文字。"""

from __future__ import annotations

from typing import Any

SHARES_PER_LOT = 1000


def _fmt_price(v: float | None) -> str:
    return f"{v:,.2f} 元" if v is not None else "無資料"


def _fmt_lots(shares: float | None) -> str:
    """股數轉張數顯示（正=買超、負=賣超）。"""
    if shares is None:
        return "無資料"
    lots = shares / SHARES_PER_LOT
    sign = "＋" if lots > 0 else ("－" if lots < 0 else "")
    return f"{sign}{abs(lots):,.0f} 張"


def format_record(record: dict[str, Any]) -> str:
    """輸出使用者指定的模板；基本面/技術面留白待人工補充。"""
    inst = record.get("institutional") or {}
    est = record.get("institutional_avg_estimated")
    if record.get("institutional_avg") is None:
        inst_avg_line = "法人均價（法人買賣超金額/股數）：無資料"
    elif est:
        inst_avg_line = (
            f"法人均價（法人買賣超金額/股數）：{_fmt_price(record['institutional_avg'])}"
            "〔估算：官方個股無法人金額，以市場均價近似〕"
        )
    else:
        inst_avg_line = f"法人均價（法人買賣超金額/股數）：{_fmt_price(record['institutional_avg'])}"

    chip_line = (
        f"外資 {_fmt_lots(inst.get('foreign'))}、"
        f"投信 {_fmt_lots(inst.get('trust'))}、"
        f"自營 {_fmt_lots(inst.get('dealer'))}、"
        f"三大法人合計 {_fmt_lots(inst.get('total'))}"
    ) if inst else "無三大法人資料"

    return "\n".join([
        "產業：（待補）",
        f"標的：{record['code']}／{record['name']}",
        "基本面：（待補）",
        f"籌碼面：{chip_line}",
        "技術面：（待補）",
        "結論：",
        f"　收盤價：{_fmt_price(record.get('close'))}",
        f"　市場均價（成交值/成交股數）：{_fmt_price(record.get('market_avg'))}",
        f"　{inst_avg_line}",
    ])


def format_report(records: list[dict[str, Any]], title: str) -> str:
    blocks = [format_record(r) for r in records]
    return f"# {title}\n\n" + "\n\n---\n\n".join(blocks) + "\n"
