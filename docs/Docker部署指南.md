# 小码 Docker 部署指南

本文档说明如何使用 Docker Compose 部署小码 V1.4。默认配置**仅本机可访问**；开放局域网或公网前必须设置访问密码。

## 1. 前置条件

- Docker Engine 24+（Docker Desktop 或 Linux Docker Engine）
- Docker Compose v2.24+（使用 `docker compose` 命令）
- 首次构建需要能访问 PyPI 与 npm 软件源
- 建议至少 2 GB 可用内存

检查版本：

```bash
docker --version
docker compose version
```

## 2. 配置环境变量

在项目根目录复制模板：

```bash
cp .env.example .env
```

Windows PowerShell：

```powershell
Copy-Item .env.example .env
```

`.env` 包含访问密码等敏感信息，**不要提交到 Git**（已在 `.gitignore` 中忽略）。

## 3. 默认部署（仅本机访问）

保持默认配置：

```dotenv
BIND_ADDRESS=127.0.0.1
FRONTEND_PORT=3000
```

启动：

```bash
docker compose up -d --build
```

访问：<http://localhost:3000>

该模式下：

- 前端端口只绑定宿主机 `127.0.0.1`，局域网内其他设备无法访问；
- 后端容器**不映射**宿主机端口，只能由前端容器通过 Compose 内部网络访问；
- 浏览器通过 Next.js 同源 `/api/v1` 代理访问后端；
- 未设置访问密码时无需登录。

检查状态：

```bash
docker compose ps
docker compose logs -f backend
```

两个服务都应显示 `healthy`。

### 健康检查

| 服务 | 检查方式 |
| --- | --- |
| backend | 容器内请求 `http://127.0.0.1:8000/api/v1/health` |
| frontend | 容器内经同源代理请求 `http://127.0.0.1:3000/api/v1/health`（同时验证代理链路） |

`frontend` 设置了 `depends_on: backend: condition: service_healthy`，后端健康后才会启动前端。

## 4. 开放局域网访问（必须设置访问密码）

在 `.env` 中修改：

```dotenv
BIND_ADDRESS=0.0.0.0
XIAOMA_ALLOW_REMOTE=true
XIAOMA_ACCESS_PASSWORD=请替换为足够长的强密码
XIAOMA_ACCESS_TOKEN_TTL_SECONDS=86400
```

重新启动：

```bash
docker compose up -d
```

局域网设备访问：`http://<宿主机局域网IP>:3000`

访问密码规则：

- 后端启动脚本检测到 `BIND_ADDRESS` 不是回环地址时，若未设置访问密码或未设置 `XIAOMA_ALLOW_REMOTE=true`，**后端拒绝启动**；
- 浏览器首次访问需输入密码；登录成功后使用后端签发、保存在内存中的 Bearer 会话令牌；
- 除健康检查、登录、登录状态外的全部 API 均由后端中间件强制校验令牌；
- 会话默认 24 小时过期，后端重启或退出登录后失效；
- 密码只在环境变量中保存，不写入数据库、不返回前端、不记录到日志。

> 使用访问密码并不等于加密传输。局域网中密码与会话令牌仍以明文 HTTP 传输，仅建议在可信网络使用。公网部署必须配置 HTTPS。

## 5. 公网部署（必须 HTTPS）

推荐架构：

```text
公网浏览器 --HTTPS--> Caddy / Nginx --HTTP--> 127.0.0.1:3000 (xiaoma-frontend)
```

建议：

1. 保持 `BIND_ADDRESS=127.0.0.1`，只让本机反向代理访问前端端口；
2. 即使通过反向代理访问，也必须设置 `XIAOMA_ACCESS_PASSWORD` 与 `XIAOMA_ALLOW_REMOTE=true`（PRD 要求公网部署必须有访问密码；`XIAOMA_ALLOW_REMOTE=true` 时后端会校验密码非空）；
3. 在反向代理配置 TLS 证书，不要直接把 3000 端口暴露到公网；
4. 反向代理需支持 SSE（关闭响应缓冲），例如 Nginx：

```nginx
server {
    listen 443 ssl;
    server_name xiaoma.example.com;

    ssl_certificate     /etc/letsencrypt/live/xiaoma.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/xiaoma.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_read_timeout 300s;
    }
}
```

5. 不要将后端 8000 端口映射到公网；本项目 Compose 默认不暴露后端。

## 6. 数据持久化

SQLite 数据库、模型密钥与备份都保存在命名卷 `xiaoma_xiaoma-data` 中，挂载到后端容器 `/app/data`：

| 路径 | 内容 |
| --- | --- |
| `/app/data/xiaoma.db` | 学习档案、计划、任务、聊天、测验、模型配置等全部业务数据 |
| `/app/data/.secret_key` | 模型 API Key 加密密钥（未配置 `XIAOMA_SECRET_KEY` 时自动生成） |
| `/app/data/backups/` | 数据库备份文件 |

容器重启、升级、重建都不会删除命名卷。**不要执行 `docker compose down -v`**，`-v` 会删除数据卷。

查看卷位置：

```bash
docker volume inspect xiaoma_xiaoma-data
```

## 7. 备份数据

方式一：设置页 → 数据备份 → 立即备份（推荐日常使用），可下载备份文件。

方式二：命令行：

```bash
# 创建备份（生成在数据卷 /app/data/backups/）
docker compose exec backend python -m app.cli backup-db

# 列出备份
docker compose exec backend python -m app.cli list-backups

# 复制备份到宿主机（可选）
docker compose cp backend:/app/data/backups/<文件名>.db ./xiaoma-backup.db
```

备份使用 SQLite 在线备份 API 生成一致性快照，服务运行中执行也是安全的。

## 8. 恢复数据

恢复会**替换当前数据库文件**。必须先停止后端，且恢复前系统会自动备份当前数据（生成 `pre-restore-*.db`）。

```bash
# 1. 停止后端（前端可保持运行，但恢复期间无法访问数据）
docker compose stop backend

# 2. 恢复指定备份（只写备份文件名，默认在 /app/data/backups/ 中查找）
docker compose run --rm --no-deps backend python -m app.cli restore-db <备份文件名> --yes

# 3. 重新启动
docker compose start backend
```

恢复前后端会对备份执行 `PRAGMA integrity_check` 与必需表校验；校验失败不会替换当前数据库。恢复成功后如需回退，可使用自动生成的 `pre-restore-*.db` 再执行一次恢复。

## 9. 更新升级

```bash
git pull
docker compose up -d --build
```

- 后端启动脚本会自动执行 Alembic 迁移（`init-db`）与幂等种子数据；
- 数据卷保持不变；
- 升级前建议先备份数据。

## 10. 常用运维命令

```bash
docker compose ps                 # 查看状态与健康检查
docker compose logs -f backend    # 后端日志
docker compose logs -f frontend   # 前端日志
docker compose restart            # 重启
docker compose down               # 停止并删除容器（保留数据卷）
docker compose up -d              # 重新启动
```

日志不会记录完整 API Key、访问密码或用户聊天内容。

## 11. 故障排查

| 现象 | 排查 |
| --- | --- |
| `backend` 一直不健康 | `docker compose logs backend`，确认迁移/种子数据是否失败、数据卷是否可写 |
| 端口被占用 | 修改 `.env` 中 `FRONTEND_PORT` |
| 局域网无法访问 | 检查 `BIND_ADDRESS`、防火墙是否放行端口；确认后端日志提示已启用访问密码 |
| 忘记访问密码 | 修改 `.env` 中 `XIAOMA_ACCESS_PASSWORD` 后 `docker compose up -d`；旧会话全部失效 |
| 页面提示无法连接服务器 | `docker compose ps` 确认两个容器 healthy；查看前端日志中的代理错误 |
| 模型连接失败 | 查看设置页测试连接结果；确认宿主机可访问模型服务商网络 |
| 更换 `XIAOMA_SECRET_KEY` 后模型密钥失效 | 这是预期行为，需在设置页重新填写 API Key |
