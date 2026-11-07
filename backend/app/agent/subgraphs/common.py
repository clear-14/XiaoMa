"""子图共用的工具结果校验与文本格式化。"""

from __future__ import annotations

from datetime import date, datetime

from app.agent.contracts import AgentRunError, ToolResult


def require_ok(result: ToolResult, action: str) -> ToolResult:
    """工具服务异常必须中止并明确报错，不能继续组装成功回答。"""
    if result.status == "failed":
        raise AgentRunError(result.message or f"{action}失败，请稍后重试")
    return result


def unavailable_message(result: ToolResult, action: str) -> str:
    """业务不可用时的统一说明（明确说明未完成，不伪装成功）。"""
    reason = result.message or "当前条件不满足"
    return f"{action}未完成：{reason}"


def format_date(value: date | datetime | None) -> str:
    if value is None:
        return "未设置"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    return value.isoformat()


def truncate(text: str, limit: int = 60) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[:limit] + "…"
