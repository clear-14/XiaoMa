"""健康检查接口。"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """健康检查响应结构。"""

    status: str
    service: str
    version: str


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """返回服务状态与版本信息。"""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
    )
