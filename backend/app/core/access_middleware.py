"""后端访问保护中间件（PRD 11.1：访问保护必须在后端执行）。

未配置访问密码时直接放行；默认部署通过 Docker Compose 只绑定
127.0.0.1 保证仅本机可访问。配置访问密码后，除公开接口外一律要求
有效的 Bearer 会话令牌。
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.access import access_required, extract_bearer_token, validate_token

# 公开路径：健康检查供容器探活；登录与状态接口用于建立会话。
PUBLIC_PATHS = frozenset(
    {
        "/api/v1/health",
        "/api/v1/auth/status",
        "/api/v1/auth/login",
    }
)


class AccessControlMiddleware(BaseHTTPMiddleware):
    """在路由前强制校验访问会话。"""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # CORS 预检不携带 Authorization，必须放行。
        if request.method == "OPTIONS":
            return await call_next(request)

        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        if not access_required():
            return await call_next(request)

        token = extract_bearer_token(request.headers.get("authorization"))
        if not validate_token(token):
            return JSONResponse(
                status_code=401,
                content={"detail": "需要访问密码登录"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        return await call_next(request)
