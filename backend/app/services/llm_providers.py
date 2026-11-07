"""LLM 服务商预设与端点解析。

DeepSeek、通义千问（DashScope 兼容模式）、OpenAI 官方接口均实现
OpenAI Chat Completions 兼容协议，统一使用同一客户端调用；
自定义兼容接口需用户显式提供 base_url。
"""

PROVIDER_PRESETS: dict[str, dict[str, str | None]] = {
    "deepseek": {
        "label": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
    },
    "qwen": {
        "label": "通义千问",
        # DashScope 的 OpenAI 兼容模式端点
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    },
    "openai": {
        "label": "OpenAI",
        "base_url": "https://api.openai.com/v1",
    },
    "custom": {
        "label": "自定义兼容接口",
        "base_url": None,
    },
}

SUPPORTED_PROVIDERS: tuple[str, ...] = tuple(PROVIDER_PRESETS)


def resolve_base_url(provider: str, base_url: str | None) -> str:
    """解析实际请求地址：显式 base_url 优先，否则使用服务商预设端点。"""
    if base_url:
        return base_url.rstrip("/")
    preset = PROVIDER_PRESETS.get(provider)
    if preset is None:
        raise ValueError(f"不支持的服务商：{provider}")
    preset_url = preset["base_url"]
    if not preset_url:
        raise ValueError("自定义兼容接口必须提供 base_url")
    return preset_url
