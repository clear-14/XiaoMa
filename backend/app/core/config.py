"""应用配置：统一从环境变量读取。"""

from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# 后端包根目录（本文件位于 app/core/，向上两级即 backend/）。
# 数据库默认路径锚定在此，不依赖进程执行时的工作目录。
BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_URL = f"sqlite:///{(BACKEND_DIR / 'data' / 'xiaoma.db').as_posix()}"


class Settings(BaseSettings):
    """小码后端全局配置。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 应用信息
    app_name: str = "xiaoma-backend"
    app_version: str = "1.4.1"

    # 数据库：路径通过 DATABASE_URL 环境变量覆盖；
    # 默认锚定 backend/data/xiaoma.db（与执行时工作目录无关）
    database_url: str = DEFAULT_DATABASE_URL

    # 服务监听：默认仅本机访问（见 PRD 11.1 访问控制）
    host: str = "127.0.0.1"
    port: int = 8000

    # 模型 API Key 加密密钥（PRD 11.2：加密存储）。
    # 未设置时自动生成并与数据库同目录保存（data/.secret_key），随数据卷持久化。
    # 可选改为任意口令字符串（内部经 SHA-256 派生 Fernet 密钥）。
    xiaoma_secret_key: str | None = None

    # 前端跨域来源白名单（逗号分隔，可选）。本地 localhost / 127.0.0.1
    # 任意端口默认允许；通过局域网 IP 或自定义域名访问前端时在此添加，
    # 例如 CORS_ALLOW_ORIGINS=http://192.168.1.5:3000,https://xiaoma.example
    cors_allow_origins: str = ""

    # 主 Agent 单次执行的整体超时（秒）。单个模型调用仍受模型配置中的
    # timeout 约束；整体超时用于兜底工具/模型异常，保证请求不会无限等待
    # （PRD 7.3：不得无限等待）。
    xiaoma_agent_timeout_seconds: float = 120.0

    # ---- 访问控制（PRD 11.1）----
    # 默认不设置访问密码：此时后端只应由本机反向代理/本机端口访问。
    # 开放局域网或公网访问前必须设置该密码；设置后所有 API 请求
    # （健康检查、登录与状态接口除外）都必须携带登录后签发的会话令牌。
    xiaoma_access_password: str | None = None
    # 登录会话有效期（秒），默认 24 小时。会话保存在后端内存中，
    # 后端重启后需要重新登录。
    xiaoma_access_token_ttl_seconds: int = 86400
    # 显式声明允许远程访问。为 true 时必须同时设置访问密码，
    # 否则应用拒绝启动（避免误把无密码服务暴露到局域网/公网）。
    xiaoma_allow_remote: bool = False

    # 数据库备份目录；默认与 SQLite 文件同目录的 backups/ 子目录。
    xiaoma_backup_dir: Path | None = None

    @model_validator(mode="after")
    def _validate_access_settings(self) -> "Settings":
        password = (self.xiaoma_access_password or "").strip()
        if self.xiaoma_allow_remote and not password:
            raise ValueError(
                "启用远程访问（XIAOMA_ALLOW_REMOTE=true）时必须设置 "
                "XIAOMA_ACCESS_PASSWORD，否则拒绝启动"
            )
        if self.xiaoma_access_token_ttl_seconds < 60:
            raise ValueError("XIAOMA_ACCESS_TOKEN_TTL_SECONDS 不能小于 60 秒")
        return self


@lru_cache
def get_settings() -> Settings:
    """返回全局唯一配置实例（进程内缓存）。"""
    return Settings()
