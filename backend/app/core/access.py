"""访问密码与会话令牌（PRD 11.1 访问控制）。

设计要点（2026-11-07 技术设计记录）：

- 未设置 ``XIAOMA_ACCESS_PASSWORD`` 时，后端不要求登录；部署层（Docker
  Compose 默认仅绑定 127.0.0.1）保证服务只在本机可访问。
- 设置密码后，除健康检查、登录和登录状态接口外，所有请求都必须携带
  ``Authorization: Bearer <token>``。访问保护在 FastAPI 中间件中强制执行，
  不依赖前端隐藏页面。
- 会话保存在后端进程内存中，使用 ``secrets`` 生成不可预测的随机令牌，
  默认 24 小时过期；进程重启、用户退出登录都会使令牌失效。V1.0 单用户、
  单进程部署，不引入 Redis 等额外基础设施。
- 密码只从环境变量读取，不写入数据库、不返回给前端、不记录到日志；
  比较使用 ``hmac.compare_digest`` 防止时序侧信道。
"""

from __future__ import annotations

import hmac
import secrets
import threading
import time

from app.core.config import get_settings

# token -> 过期时间（time.monotonic() 秒）
_sessions: dict[str, float] = {}
_sessions_lock = threading.Lock()


def access_password() -> str | None:
    """返回配置的访问密码（去除首尾空白）；未配置时返回 None。"""
    raw = get_settings().xiaoma_access_password
    if raw is None:
        return None
    password = raw.strip()
    return password or None


def access_required() -> bool:
    """当前部署是否要求访问密码。"""
    return access_password() is not None


def verify_password(candidate: str) -> bool:
    """常量时间比较访问密码。"""
    configured = access_password()
    if configured is None:
        return False
    return hmac.compare_digest(
        candidate.encode("utf-8"), configured.encode("utf-8")
    )


def issue_token() -> tuple[str, int]:
    """创建登录会话，返回 (token, 有效期秒数)。"""
    ttl = get_settings().xiaoma_access_token_ttl_seconds
    token = secrets.token_urlsafe(32)
    now = time.monotonic()
    with _sessions_lock:
        _purge_expired_locked(now)
        _sessions[token] = now + ttl
    return token, ttl


def validate_token(token: str | None) -> bool:
    """校验会话令牌是否有效；过期令牌会被清理。"""
    if not token:
        return False
    now = time.monotonic()
    with _sessions_lock:
        _purge_expired_locked(now)
        expires_at = _sessions.get(token)
        if expires_at is None:
            return False
        if expires_at <= now:
            _sessions.pop(token, None)
            return False
        return True


def revoke_token(token: str | None) -> None:
    """退出登录：立即删除会话令牌。"""
    if not token:
        return
    with _sessions_lock:
        _sessions.pop(token, None)


def reset_access_sessions() -> None:
    """清空全部会话（测试或密钥变更时使用）。"""
    with _sessions_lock:
        _sessions.clear()


def extract_bearer_token(authorization: str | None) -> str | None:
    """从 Authorization 头中解析 Bearer 令牌。"""
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        return None
    token = token.strip()
    return token or None


def _purge_expired_locked(now: float) -> None:
    """调用方必须持有锁。删除已过期会话，避免内存无限增长。"""
    expired = [token for token, expires_at in _sessions.items() if expires_at <= now]
    for token in expired:
        _sessions.pop(token, None)
