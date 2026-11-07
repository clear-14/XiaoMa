"""API Key 加密与脱敏测试（PRD 11.2：加密存储、脱敏展示、不记录完整密钥）。"""

import pytest

from app.core import config, crypto
from app.core.crypto import SecretDecryptionError


def _reset(monkeypatch, secret: str | None) -> None:
    if secret is None:
        monkeypatch.delenv("XIAOMA_SECRET_KEY", raising=False)
    else:
        monkeypatch.setenv("XIAOMA_SECRET_KEY", secret)
    config.get_settings.cache_clear()
    crypto.reset_crypto_cache()


def test_encrypt_roundtrip_and_ciphertext_hides_plaintext():
    plaintext = "sk-abcdef1234567890"
    token = crypto.encrypt_secret(plaintext)

    assert token != plaintext
    assert plaintext not in token
    assert crypto.decrypt_secret(token) == plaintext


def test_mask_secret_keeps_prefix_and_suffix():
    assert crypto.mask_secret("sk-abcdef1234567890") == "sk-****7890"
    assert crypto.mask_secret("short") == "*****"
    assert crypto.mask_secret(None) is None


def test_decrypt_with_changed_key_raises_clear_error(monkeypatch):
    token = crypto.encrypt_secret("sk-secret")

    _reset(monkeypatch, "another-passphrase")
    with pytest.raises(SecretDecryptionError) as excinfo:
        crypto.decrypt_secret(token)
    assert "重新填写" in str(excinfo.value)


def test_key_file_generated_when_env_absent(monkeypatch, tmp_path):
    _reset(monkeypatch, None)
    key_file = tmp_path / ".secret_key"
    monkeypatch.setattr(crypto, "secret_key_file", lambda: key_file)

    token = crypto.encrypt_secret("sk-file-key")
    assert key_file.exists()
    first_content = key_file.read_text(encoding="utf-8")

    # 重新加载（模拟进程重启）后仍能解密，且不重复生成密钥
    crypto.reset_crypto_cache()
    assert crypto.decrypt_secret(token) == "sk-file-key"
    assert key_file.read_text(encoding="utf-8") == first_content


def test_env_accepts_arbitrary_passphrase():
    # autouse 夹具提供了普通口令字符串，应可派生密钥并正常加解密
    token = crypto.encrypt_secret("sk-passphrase")
    assert crypto.decrypt_secret(token) == "sk-passphrase"
