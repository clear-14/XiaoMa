"""小码（Xiaoma）后端 FastAPI 入口。"""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.conversations import router as conversations_router
from app.api.v1.courses import router as courses_router
from app.api.v1.daily_tasks import router as daily_tasks_router
from app.api.v1.health import router as health_router
from app.api.v1.knowledge_points import router as knowledge_points_router
from app.api.v1.llm import router as llm_router
from app.api.v1.mistakes import router as mistakes_router
from app.api.v1.model_configs import router as model_configs_router
from app.api.v1.plans import router as plans_router
from app.api.v1.profile import router as profile_router
from app.api.v1.quizzes import router as quizzes_router
from app.api.v1.reviews import router as reviews_router
from app.core.config import get_settings

# uvicorn 只配置自身的 logger；显式配置根日志级别，确保 Agent 执行日志
# （开始/结束/工具状态/耗时）真正写入日志，便于审计且不包含密钥。
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

logger = logging.getLogger("xiaoma")

settings = get_settings()

app = FastAPI(
    title="小码 Xiaoma API",
    description="小码（Xiaoma）——开源、免费、个人独立部署的 AI 编程学习教练后端服务",
    version=settings.app_version,
)

# 前端（浏览器）直接调用后端 API 与 SSE 流，需要跨域许可。
# 默认仅允许本机任意端口的前端来源，避免任意网站读取本地学习数据；
# 局域网/自定义域名部署时通过 CORS_ALLOW_ORIGINS 显式追加。
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in settings.cors_allow_origins.split(",")
        if origin.strip()
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (
    health_router,
    courses_router,
    knowledge_points_router,
    plans_router,
    daily_tasks_router,
    conversations_router,
    model_configs_router,
    llm_router,
    profile_router,
    quizzes_router,
    mistakes_router,
    reviews_router,
):
    app.include_router(router, prefix="/api/v1")


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """统一 HTTP 错误响应结构：{"detail": 错误信息}。"""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """未处理异常：记录完整堆栈并返回统一 500 响应（不吞掉异常细节，日志可追溯）。"""
    logger.exception("未处理异常: %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "服务器内部错误，请稍后重试"})
