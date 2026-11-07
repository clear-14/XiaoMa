"""应用时间工具：统一 naive UTC 约定（SQLite 不保存时区，避免 aware/naive 混用）。"""

from datetime import date, datetime, timezone


def utc_now_naive() -> datetime:
    """当前 UTC 时间（naive）。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def utc_today_naive() -> date:
    """当前 UTC 日期。"""
    return utc_now_naive().date()
