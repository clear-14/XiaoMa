"""模型 API Key 加密存储（PRD 11.2：加密存储、页面脱敏展示、日志不记录完整密钥）。

加密方案：Fernet（AES-128-CBC + HMAC-SHA256，cryptography 库）。
密钥来源优先级：
1. 环境变量 XIAOMA_SECRET_KEY：可为 Fernet 密钥（44 位 urlsafe base64），
   也可为任意口令字符串（内部经 SHA-256 派生 Fernet 密钥）；
2. 与数据库同目录的 .secret_key 文件：首次使用时自动生成并持久化
   （Docker 部署时位于数据卷 /app/data，随备份恢复一起保留）。

密钥更换或密钥文件丢失后，已保存的 API Key 将无法解密——此时接口返回
明确提示，由用户重新填写 Key（本产品不做自动密钥轮换，轮换即重新填写）。
"""

import base64
import hashlib
import os
from functools import lru_cache
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import BACKEND_DIR, get_settings

SECRET_KEY_FILE_NAME = ".secret_key"


class SecretDecryptionError(RuntimeError):
    """已保存的密钥无法解密（加密密钥变更或数据损坏）。"""


def _database_dir() -> Path:
    """数据库文件所在目录（密钥文件与数据库同目录，便于备份与容器持久化）。"""
    url = get_settings().database_url
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        return BACKEND_DIR / "data"
    raw = url[len(prefix):]
    path = Path(raw)
    if not path.is_absolute():
        path = BACKEND_DIR / path
    return path.parent


def secret_key_file() -> Path:
    """密钥文件路径（可通过 XIAOMA_SECRET_KEY 环境变量完全绕过该文件）。"""
    return _database_dir() / SECRET_KEY_FILE_NAME


def _derive_fernet_key(raw: str) -> bytes:
    """把任意口令字符串派生为合法 Fernet 密钥。"""
    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _key_from_env_or_file() -> bytes:
    configured = get_settings().xiaoma_secret_key
    if configured:
        raw = configured.strip()
        # 已是合法 Fernet 密钥则直接使用，否则按口令派生
        try:
            Fernet(raw.encode("ascii"))
            return raw.encode("ascii")
        except (ValueError, UnicodeEncodeError):
            return _derive_fernet_key(raw)

    path = secret_key_file()
    if path.exists():
        return path.read_text(encoding="utf-8").strip().encode("ascii")

    # 首次使用：生成并持久化密钥文件
    path.parent.mkdir(parents=True, exist_ok=True)
    key = Fernet.generate_key()
    path.write_text(key.decode("ascii"), encoding="utf-8")
    try:
        os.chmod(path, 0o600)  # Windows 上为尽力而为，不阻断启动
    except OSError:
        pass
    return key


@lru_cache
def get_fernet() -> Fernet:
    """进程内缓存的 Fernet 实例。"""
    return Fernet(_key_from_env_or_file())


def reset_crypto_cache() -> None:
    """清空缓存（密钥变更或测试使用）。"""
    get_fernet.cache_clear()


def encrypt_secret(plaintext: str) -> str:
    """加密 API Key，返回可存库的 Fernet token（密文）。"""
    return get_fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_secret(token: str) -> str:
    """解密 API Key；密钥变更或数据损坏时抛出明确的业务异常。"""
    try:
        return get_fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, UnicodeEncodeError) as exc:
        raise SecretDecryptionError(
            "无法解密已保存的 API Key：服务端加密密钥已变更或数据损坏，"
            "请重新填写该模型的 API Key"
        ) from exc


def mask_secret(plaintext: str | None) -> str | None:
    """页面脱敏展示：保留前 3 位与后 4 位，其余以 * 代替。"""
    if not plaintext:
        return None
    if len(plaintext) <= 8:
        return "*" * len(plaintext)
    return f"{plaintext[:3]}****{plaintext[-4:]}"
