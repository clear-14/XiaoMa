"""跨域（CORS）配置测试：前端浏览器直接调用后端 API / SSE 所需。"""


def test_local_origin_allowed(api_env):
    client, _ = api_env
    resp = client.get(
        "/api/v1/health", headers={"Origin": "http://localhost:3000"}
    )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_loopback_origin_any_port_allowed(api_env):
    client, _ = api_env
    resp = client.get(
        "/api/v1/health", headers={"Origin": "http://127.0.0.1:3001"}
    )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "http://127.0.0.1:3001"


def test_preflight_allows_streaming_post(api_env):
    client, _ = api_env
    resp = client.options(
        "/api/v1/conversations/00000000-0000-0000-0000-000000000000/messages/stream",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "POST" in resp.headers["access-control-allow-methods"]


def test_unknown_origin_not_allowed(api_env):
    client, _ = api_env
    resp = client.get(
        "/api/v1/health", headers={"Origin": "https://evil.example"}
    )
    assert resp.status_code == 200
    # 未授权来源不返回跨域许可头，浏览器会阻止页面读取响应
    assert "access-control-allow-origin" not in resp.headers
