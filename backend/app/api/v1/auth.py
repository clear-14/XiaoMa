"""访问密码登录与会话状态接口（PRD 11.1）。

密码只从服务端环境变量读取；请求中的密码仅用于常量时间比较，
不会写入日志、数据库或任何响应。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.core.access import (
    access_required,
    extract_bearer_token,
    issue_token,
    revoke_token,
    validate_token,
    verify_password,
)

logger = logging.getLogger("xiaoma.access")

router = APIRouter(prefix="/auth", tags=["auth"])

# 登录失败时的人为延迟，降低在线暴力尝试速度。
_FAILED_LOGIN_DELAY_SECONDS = 0.4


class LoginRequest(BaseModel):
    """访问密码登录请求。"""

    password: str = Field(min_length=1, max_length=256)


class LoginResponse(BaseModel):
    """登录成功后的会话令牌。令牌仅保存在前端本地，不写入日志。"""

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class AuthStatusResponse(BaseModel):
    """前端用于判断是否需要展示登录页。"""

    required: bool
    authenticated: bool


def _request_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.get("/status", response_model=AuthStatusResponse)
def auth_status(request: Request, response: Response) -> AuthStatusResponse:
    """返回是否启用访问密码，以及当前请求是否已登录。"""
    response.headers["Cache-Control"] = "no-store"
    required = access_required()
    token = extract_bearer_token(request.headers.get("authorization"))
    return AuthStatusResponse(
        required=required,
        authenticated=(not required) or validate_token(token),
    )


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, request: Request, response: Response) -> LoginResponse:
    """校验访问密码并签发内存会话令牌。"""
    response.headers["Cache-Control"] = "no-store"
    if not access_required():
        raise HTTPException(status_code=409, detail="当前部署未启用访问密码")

    if not verify_password(payload.password):
        logger.warning("访问密码验证失败 ip=%s", _request_ip(request))
        await asyncio.sleep(_FAILED_LOGIN_DELAY_SECONDS)
        raise HTTPException(status_code=401, detail="访问密码错误")

    token, expires_in = issue_token()
    logger.info("访问密码登录成功 ip=%s", _request_ip(request))
    return LoginResponse(access_token=token, expires_in=expires_in)


@router.post("/logout", status_code=204)
def logout(request: Request) -> Response:
    """退出登录：立即吊销当前会话令牌。"""
    revoke_token(extract_bearer_token(request.headers.get("authorization")))
    return Response(status_code=204)
