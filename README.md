# 小码 Xiaoma

[中文](README.md) | [English](README.en.md)

开源、免费、个人独立部署的 **AI 编程学习教练**，帮助编程初学者通过结构化课程与持续验证真正掌握编程知识。首发课程为 **Python 零基础入门**，课程体系覆盖 Python 基础、工程与数据库、后端、大模型应用与 Agent 五个方向。

## 项目状态

| 阶段 | 内容 | 状态 |
| --- | --- | --- |
| 阶段 0 | 开发环境检查 | ✅ 完成（Python 3.14 决策已记录） |
| 阶段 1 | 项目工程初始化 | ✅ 完成 |
| 阶段 2 | 数据库和基础架构 | ✅ 完成（SQLite + SQLAlchemy + Alembic，4 张基础表） |
| 阶段 3 | 前端基础框架 | ✅ 完成（9 页面 + 侧边栏布局 + 设计系统） |
| 阶段 4 | 学习档案与课程体系 | ✅ 完成（课程/章节/知识点 + Python 零基础入门种子课程 + 学习档案接口） |
| 阶段 5 | 学习计划 | ✅ 完成（诊断→排期→草稿→确认；版本化调整；历史保留） |
| 阶段 6 | 每日学习任务 | ✅ 完成（首页查询/生成当天任务；防重复；开始/完成标记；进度联动） |
| 阶段 7 | 模型接入和系统设置 | ✅ 完成（统一 LLM Provider、密钥加密、连接测试、默认模型切换、流式输出；已用 DeepSeek 真实模型验收） |
| 阶段 8 | AI 教学与聊天历史 | ✅ 完成（会话/消息/学习会话持久化、LangGraph Teaching 子图、流式教学、失败不伪造回复；前端工作台/聊天历史/任务与知识点入口已接入；已用 DeepSeek 真实模型验收） |
| 阶段 9 | 测验、评分与错题本 | ✅ 完成（5 张测验相关表、7 种题型、知识点/章节/阶段组卷、自动评分、掌握验证、错题与间隔复习、AI 变式题双重验证；前端测验中心与错题本已接入；已用 DeepSeek 真实验收 AI 变式题） |
| 阶段 10 | LangGraph Agent | ✅ 完成（主 Agent + Planning/Teaching/Quiz/Review/Resource 五个子图、确定性意图识别、结构化状态、Service 工具层、整体超时与失败处理、执行日志脱敏；已用真实 DeepSeek 与 7 个验收场景实测） |
| 阶段 11 | 测试、安全与部署 | ✅ 完成（后端 217 项测试、前端 Vitest 核心流程测试、Docker Compose 实际启动与核心流程验收、访问控制、备份恢复、中英文 README 与开源交付文档） |
| V1.4 | 桌面软件窗口 + 对话工作台 | ✅ 批次 0–9 验收闭环（Electron 窗口壳、三栏工作台、9 类消息卡片全部可达、卡片按钮接真实接口、消息级操作、真实 LLM 产卡 7/7、超范围回复不发讲解卡、聊天查看测验成绩、启动探活复用、安装/卸载实测；安装包 `Xiaoma-Setup-1.4.1.exe` 已产出并完成包内校验） |

## 技术栈

| 层次 | 选型 |
| --- | --- |
| 前端 | Next.js（App Router）+ TypeScript + React |
| 后端 | Python 3.14 + FastAPI + Pydantic |
| AI | LangGraph（主 Agent + 五个子图）+ 统一 LLM Provider |
| 数据库 | SQLite + SQLAlchemy + Alembic |
| 部署 | Docker Compose |

## 目录结构

```
.
├── frontend/              # Next.js 前端（App Router）
├── backend/               # FastAPI 后端
│   ├── app/               # 应用代码（api / core / services / agent / repositories）
│   └── tests/             # 自动化测试
├── desktop/               # Electron 桌面窗口壳（启动服务、健康检查、打包）
├── docs/                  # PRD、任务书、部署指南、模型配置、FAQ、验收记录
├── docker-compose.yml     # 容器编排（默认仅本机访问）
├── .env.example           # 统一环境变量模板
├── CHANGELOG.md
├── LICENSE                # Apache License 2.0
├── README.md              # 中文说明
└── README.en.md           # English README
```

## 本地启动

### 后端（默认 http://127.0.0.1:8000）

```bash
cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt    # Windows；macOS/Linux 用 .venv/bin/
.venv/Scripts/python -m app.cli init-db          # 执行 Alembic 迁移
.venv/Scripts/python -m app.cli seed-courses     # 课程种子数据（幂等）
.venv/Scripts/python -m app.cli seed-questions   # 内置题库（幂等）
.venv/Scripts/python -m app.cli seed-textbook    # 零基础入门教材 20 章（幂等）
.venv/Scripts/python -m app.cli seed-phase4a     # 进阶与数据库两门课教材（幂等）
.venv/Scripts/python -m app.cli seed-phase4b     # FastAPI 后端开发教材（幂等）
.venv/Scripts/python -m app.cli seed-phase4c     # 大模型 API 应用开发教材（幂等）
.venv/Scripts/python -m app.cli seed-phase4d     # LangGraph Agent 开发教材（幂等）
.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

- 健康检查：http://127.0.0.1:8000/api/v1/health
- 接口文档：http://127.0.0.1:8000/docs

主要接口（前缀 `/api/v1`）：

| 接口 | 说明 |
| --- | --- |
| GET /health | 健康检查（公开，无需登录） |
| GET /auth/status | 是否启用访问密码 / 当前是否已登录（公开） |
| POST /auth/login | 访问密码登录，签发 Bearer 会话令牌（公开） |
| POST /auth/logout | 退出登录并吊销当前令牌 |
| GET /profile / PUT /profile | 获取 / 更新学习档案 |
| GET /overview | 学习概览（计划、掌握、测验、错题统计） |
| GET /courses | 课程列表（支持 direction / difficulty / recommended_level / publish_status 筛选） |
| GET /courses/{code} | 课程详情（课程元数据 + 章节、课时与知识点 + 方向与先修课程） |
| GET /courses/{code}/chapters | 章节列表（含课时与知识点概要） |
| GET /courses/{code}/chapters/{chapter_code}/lessons | 章节下的课时列表 |
| GET /lessons/{code} | 课时详情（教学内容 + 知识点） |
| GET /knowledge-points/{code} | 知识点详情（含所属课时、前置知识点、练习与题目数量） |
| GET /knowledge-points/{code}/exercises | 知识点练习（含参考答案与解析） |
| GET /knowledge-points/{code}/questions | 知识点测验题（默认不返回答案与解析） |
| GET /courses/{code}/versions | 课程版本列表 |
| GET /courses/{code}/versions/{version} | 课程版本快照 |
| POST /courses/{code}/versions | 保存当前课程结构快照为指定版本 |
| PATCH /courses/{code}/status | 切换课程发布状态（draft 草稿 / published 已发布 / archived 已归档） |
| GET /course-directions | 课程方向列表（课程分类，含各方向课程数） |
| GET /course-catalog | 课程目录总览（按方向分组，含章节/课时规模与先修） |
| GET /course-catalog/dependency-graph | 课程先修依赖图（边、环检测、引用完整性、拓扑顺序） |
| GET /courses/{code}/prerequisites | 前置课程（直接关系 + 传递闭包） |
| GET /courses/{code}/next-courses | 后续课程（直接关系 + 传递闭包） |
| POST /courses/{code}/prerequisites | 新增先修课程（拒绝自引用与循环依赖，重复添加幂等） |
| DELETE /courses/{code}/prerequisites/{prerequisite_code} | 删除先修课程 |
| GET /courses/{code}/learning-path | 学习路径（缺前置课程、缺基础知识点、可跳过课程、是否可开始） |
| POST /courses/{code}/required-knowledge-points | 登记课程入学知识点 |
| DELETE /courses/{code}/required-knowledge-points/{knowledge_point_code} | 移除课程入学知识点 |
| POST /plans | 创建学习计划（提交诊断 → 生成草稿） |
| POST /plans/{id}/confirm | 确认计划（草稿生效） |
| POST /plans/{id}/adjust | 调整计划（生成新草稿版本） |
| GET /plans/current | 查看当前计划（含计划项目） |
| GET /plans/{id} | 计划详情 + 历史版本列表 |
| GET /plans/{id}/versions/{n} | 历史版本详情 |
| GET /daily-tasks/today | 首页今日任务（查询已有，无则按计划与进度生成） |
| GET /daily-tasks/{id} | 任务详情（含知识点信息） |
| POST /daily-tasks/{id}/start | 标记开始学习 |
| POST /daily-tasks/{id}/complete | 标记用户已完成（记录完成时间） |
| GET /model-configs | 模型配置列表（API Key 脱敏） |
| POST /model-configs | 添加模型配置（Key 加密保存） |
| GET /model-configs/{id} | 模型配置基本信息（脱敏） |
| PUT /model-configs/{id} | 编辑模型配置（不传 api_key 则保持原密钥） |
| DELETE /model-configs/{id} | 删除模型配置 |
| POST /model-configs/{id}/default | 设为默认模型 |
| POST /model-configs/{id}/test | 测试连接（返回耗时与回复） |
| POST /llm/chat/stream | 流式对话（SSE，默认模型或指定 config_id） |
| POST /conversations | 新建聊天会话（可关联知识点/每日任务） |
| GET /conversations | 聊天历史列表（最近活动在前） |
| GET /conversations/{id} | 会话详情与完整消息历史 |
| DELETE /conversations/{id} | 物理删除会话及其全部消息（不可恢复，不影响其他会话） |
| POST /conversations/{id}/messages/stream | 发送消息，由主 Agent 识别意图并路由子图，SSE 流式返回（消息自动持久化） |
| GET /quizzes/eligibility | 可测验范围（仅已学习知识点/章节/当前阶段） |
| GET /quizzes | 测验历史记录 |
| POST /quizzes | 按知识点/章节/阶段组卷（可请求 AI 变式题） |
| GET /quizzes/{id} | 测验详情与题目（未提交不返回答案与解析） |
| POST /quizzes/{id}/submit | 提交全部答案并自动评分 |
| GET /mistakes | 错题本（可按 pending/resolved 筛选） |
| GET /reviews/tasks | 待复习任务（按到期时间升序） |
| POST /reviews/tasks/{id}/submit | 提交错题复习答案并推进/重置复习间隔 |
| GET /data/backups | 备份列表 |
| POST /data/backups | 创建数据库备份 |
| GET /data/backups/{name} | 下载备份文件 |
| DELETE /data/backups/{name} | 删除备份文件 |

### 数据库初始化（迁移与种子数据）

```bash
cd backend
.venv/Scripts/python -m app.cli init-db         # 等价于 alembic upgrade head
.venv/Scripts/python -m app.cli seed-courses    # 写入课程种子数据（幂等，可重复执行）
.venv/Scripts/python -m app.cli seed-questions  # 写入内置题库（幂等；需先执行 seed-courses）
.venv/Scripts/python -m app.cli seed-textbook    # 写入零基础入门教材正文（20 章 / 29 课时，幂等）
.venv/Scripts/python -m app.cli seed-phase4a     # 写入 Python 进阶与数据库两门课正文（19 章 / 23 课时，幂等）
.venv/Scripts/python -m app.cli seed-phase4b     # 写入 FastAPI 后端开发课程正文（16 章 / 31 课时，幂等）
.venv/Scripts/python -m app.cli seed-phase4c     # 写入大模型 API 应用开发课程正文（16 章 / 32 课时，幂等）
.venv/Scripts/python -m app.cli seed-phase4d     # 写入 LangGraph Agent 开发课程正文（28 章 / 47 课时，幂等）
```

- `seed-phase4a` 会先把这两门课的章节/课时目录对齐到当前版本，再写入正文；目录外且从未写过正文的空壳课时会被清理，已有正文的课时一律保留。
- `seed-phase4b` 同样先 `seed_course_catalog` 对齐 FastAPI 课目录（8 章 28 课时 → 16 章 31 课时），再写 31 份正文与配套练习题目。
- `seed-phase4c` 先 `seed_course_catalog` 对齐大模型 API 课目录（8 章 28 课时 → 16 章 32 课时），再写 32 份正文、64 个练习与 192 道题。课程示例代码统一用 `httpx` 直连 OpenAI 兼容端点，**API Key 一律从环境变量读取**，代码与仓库里不出现任何密钥。
- `seed-phase4d` 先 `seed_course_catalog` 对齐 LangGraph 课目录（12 章 32 课时 → 28 章 47 课时），再写 47 份正文、94 个练习与 282 道题。示例代码按 `langgraph 1.2 / langchain-core 1.7` 的口径写，前 3 章不出现任何框架代码，写操作一律经 `interrupt` 人工审批。

- 内置题库当前为 31 个知识点 × 3 题，共 93 题；题目经结构校验，并已生成 [抽检表](docs/内置题库抽检表.md) 与 [审核报告](docs/内置题库审核报告.md)。2026-11-07 产品负责人已完成抽检确认，题库随 V1.0 正式发布。
- AI 变式题生成的题目经结构校验、独立复核调用（默认模型二次作答）与答案比对后才会落库并进入测验；未配置模型或验证失败时自动改用内置题库。

- 数据库文件默认生成于 `backend/data/xiaoma.db`（可用环境变量 `DATABASE_URL` 修改）
- 新增模型后生成迁移：`.venv/Scripts/python -m alembic revision --autogenerate -m "描述"`
- 容器部署时数据库位于命名卷 `xiaoma-data`（/app/data），容器重启数据不丢失

### 前端（默认 http://localhost:3000）

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 http://localhost:3000

### Docker Compose（推荐部署方式）

前置条件：Docker Engine 24+、Docker Compose v2.24+。

```bash
cp .env.example .env
docker compose up -d --build
```

浏览器打开 <http://localhost:3000>。

默认配置**仅本机可访问**：前端端口绑定 `127.0.0.1`，后端不映射宿主机端口，由前端 Next.js 同源代理访问。容器会等待后端健康检查通过后启动前端，并在后端启动时自动执行数据库迁移与幂等种子数据。

**开放局域网访问（必须设置密码）**：修改 `.env`：

```dotenv
BIND_ADDRESS=0.0.0.0
XIAOMA_ALLOW_REMOTE=true
XIAOMA_ACCESS_PASSWORD=你的强密码
```

然后 `docker compose up -d`，访问 `http://<宿主机IP>:3000`。若绑定非回环地址但未设置密码或未显式允许远程访问，后端会拒绝启动。

**公网部署必须配置 HTTPS 反向代理**，详见 [Docker 部署指南](docs/Docker部署指南.md)。

### 桌面版（Windows 安装包）

安装包 `Xiaoma-Setup-1.4.1.exe`（约 117 MB）是自带 Compose 工程的桌面窗口壳。**仓库里不包含这个文件**（`desktop/dist/` 属于构建产物，已被忽略）：请从 [Releases](https://github.com/clear-14/XiaoMa/releases) 下载，或由发布者直接提供；若 Releases 尚无资产，按下方「自行打包」从源码生成。

双击安装完成后启动，窗口会自动拉起本地服务并进入工作台。若本机已有同一套服务在运行（例如开发栈），窗口会先探活并直接复用，约 2 秒进入工作台；否则在包内工程上执行 `docker compose up -d --build`，本机实测首次启动 **87 秒**（含镜像构建）。

前置条件：Windows 10/11 64 位，且已安装并运行 Docker Desktop —— 窗口只是加载器，前后端服务都在容器里。零基础分步教程见 [零基础桌面应用部署教程](docs/零基础桌面应用部署教程.md)。

自行打包（需要 Node.js 22+ 与 Docker Desktop）：

```bash
git clone https://github.com/clear-14/XiaoMa.git
cd XiaoMa/desktop
npm install
npm run check && npm test
npm run dist:win      # 产物：desktop/dist/Xiaoma-Setup-1.4.1.exe
```


- 安装位置：默认 `%LOCALAPPDATA%\Programs\Xiaoma`（安装器会记住上次选择的路径）。
- 静默安装：`Xiaoma-Setup-1.4.1.exe /S`（Git Bash 中写 `//S`）。
- 静默卸载：**推荐用 PowerShell** `Start-Process "C:\Users\<你>\AppData\Local\Programs\Xiaoma\Uninstall Xiaoma.exe" -ArgumentList "/S" -Wait`。在 Git Bash 里执行 `"Uninstall Xiaoma.exe" //S` 可能出现「退出码 0 但一个文件都没删」的假成功，实测必须换 PowerShell 才真正卸载。
- 安装包未做代码签名，SmartScreen 会提示「未知发布者」，需点「更多信息 → 仍要运行」。
- **卸载不会清理用户数据与容器**：`%APPDATA%\xiaoma-desktop`（窗口状态、缓存）与 Docker 容器/数据卷会保留，方便重装续用。要彻底清除：删除该目录后执行 `docker compose down -v`（会一并删除数据库，请先备份）。

## 模型配置与密钥安全

- 通过 `POST /api/v1/model-configs`（或设置页）添加模型：支持 DeepSeek、通义千问、OpenAI 及任意 OpenAI 兼容端点（自定义需填 `base_url`）。
- API Key 使用 Fernet 加密后存入 SQLite，接口与页面只展示脱敏值（如 `sk-****abcd`）。
- 加密密钥默认自动生成于数据库同目录 `data/.secret_key`（Docker 下位于数据卷）；也可通过环境变量 `XIAOMA_SECRET_KEY` 指定。**更换密钥后已保存的 Key 无法解密，需要重新填写。**
- 未配置默认模型时，教学类流式对话返回 409 并提示先配置模型；计划/进度/测验/错题/资源查询不依赖模型。模型超时/不可用/空回复均返回明确中文提示。
- 日志不记录完整 API Key。

## 访问安全

- **默认仅本机访问**：Docker Compose 默认将前端绑定到 `127.0.0.1`，后端不暴露宿主机端口；浏览器通过同源 `/api/v1` 代理访问后端。
- **远程访问必须设置密码**：设置 `XIAOMA_ACCESS_PASSWORD` 后，除健康检查、登录与登录状态外，所有 API 都由后端中间件强制校验 `Authorization: Bearer` 会话令牌，不能只靠前端隐藏页面。
- **启动保护**：绑定地址不是回环地址时，后端启动脚本要求同时设置访问密码与 `XIAOMA_ALLOW_REMOTE=true`，否则拒绝启动。
- **会话安全**：令牌由 `secrets` 随机生成，默认 24 小时过期；保存在后端内存中，重启或退出登录即失效。密码使用常量时间比较，不写入数据库、不返回前端、不记录日志。
- **公网部署**：必须使用 HTTPS 反向代理；详见 [Docker 部署指南](docs/Docker部署指南.md)。

## 数据备份与恢复

- 数据备份：设置页 → 数据备份 → 立即备份，可创建、下载、删除备份；也可执行 `python -m app.cli backup-db`（Docker：`docker compose exec backend python -m app.cli backup-db`）。
- 备份使用 SQLite 在线备份 API 生成一致性快照，服务运行中执行也安全；默认保存在数据库同目录 `backups/`（Docker 数据卷内，随卷持久化）。
- 恢复：必须先停止后端，再执行 `python -m app.cli restore-db <备份文件名> --yes`。恢复前系统会自动备份当前数据库（`pre-restore-*.db`），并校验备份完整性与必需表；校验失败不会替换现有数据。
- Docker 下的完整备份/恢复命令见 [Docker 部署指南](docs/Docker部署指南.md#7-备份数据)。

## AI 教学与聊天历史

- 前端页面：`/workspace` 为 AI 学习工作台（会话列表、新建对话、SSE 流式渲染、失败消息标识、永久删除会话）；首页每日任务“让 AI 讲解”与课程学习页知识点“向 AI 提问”可直接带着上下文进入工作台；`/chat-history` 可查看、继续或永久删除历史会话。
- 每个会话可关联一个知识点和/或当天学习任务（会话级上下文，会话内所有消息共享）。
- 每轮对话都会从数据库读取学习档案、当前知识点、任务状态和知识点掌握状态，构建教学提示词；AI 支持概念解释、分步骤讲解、举例、代码解释、错误分析与修改建议，并按 L0/L1/L2 基础调整难度。
- 消息全部持久化：刷新页面后可查看完整历史并继续对话；新建会话不会覆盖旧会话。
- 会话删除为物理删除：会话、消息与学习会话记录一并移除，删除后不可恢复；界面会二次确认。
- 模型失败、超时、空回复或生成中断时，保存 `status=error` 的助手消息（保留已生成部分并记录原因），不会伪造成功回复；失败回复不会进入后续上下文。
- **V1.0 不执行用户代码**，AI 也不会声称运行过代码。
- 流式接口使用 SSE：`start` / `delta` / `done` / `error` 事件；未配置默认模型时返回 409 并提示先配置。
- 隐私说明：使用 AI 教学时，教学提示词及必要的学习上下文（学习目标/基础、当前知识点、任务与掌握状态等）会发送给**你自己配置的模型服务商**；数据保存在本地部署环境中，不会上传到开发者服务器。

## 主 Agent 与子图（阶段 10）

- 主流程：用户输入 → 确定性意图识别 → 读取学习上下文（档案/当前知识点/任务/计划）→ 路由子图 → 调用业务工具 → 整理回答 → 保存聊天记录 → SSE 返回。主 Agent 与子图使用结构化 `AgentState`，每个子图有明确输入/输出。
- 五个子图：
  - **Planning**：今日任务、学习进度、计划查看与计划调整草案（调整只生成待确认版本，绝不自动确认）。
  - **Teaching**：复用阶段 8 教学子图，调用用户配置的模型流式讲解。
  - **Quiz**：为当前知识点/章节或已学习阶段组卷，只使用后端可测验范围与已验证题库。
  - **Review**：分析错题分布、复习阶段与到期任务，不剧透答案与解析。
  - **Resource**：按相关度检索课程库中已登记的学习资源（整句/主题词优先，通用词降权），不联网、不编造链接。
- Agent 不直接访问数据库：工具层 `app/agent/tools.py` 只调用既有 Service；数据修改（如计划调整草案、组卷）同样经过 Service 校验。
- 只有 Teaching 子图需要模型；未配置模型时，计划/进度/测验/错题/资源查询仍可使用，教学请求返回明确的 409 提示。
- 工具业务不可用（如暂无计划、章节尚无已学知识点）会明确说明「未完成 + 原因」，不会伪造成功；工具服务异常、模型失败、空回复或整体超时都会保存 `status=error` 的助手消息并通过 SSE `error` 事件提示。
- 整体超时由 `XIAOMA_AGENT_TIMEOUT_SECONDS` 控制（默认 120 秒）；单个模型调用仍受模型配置的 timeout 约束。
- SSE 事件名保持 `start` / `delta` / `done` / `error`，`start` / `done` 额外携带 `intent` / `sub_intent` / `subgraph` / `result_status`；非教学子图不调用模型，`model` 为 `null`。
- Agent 执行日志记录会话 ID、意图、子图、工具名、状态与耗时，不记录用户消息、系统提示词或 API Key。

## 测验、错题与复习

- 前端页面：`/quiz` 为测验中心（按知识点/章节/阶段选择范围、请求 0–5 道 AI 变式题、7 种题型答题、提交评分、查看掌握判定与历史记录）；`/mistakes` 为错题本（待复习任务、到期/未到期、错题解析、复习作答与下次复习时间）。
- 可测验范围只包含已学习知识点；未学习知识点不会出现在正式测验中，直接请求会被后端拒绝。章节测验只取本章已学习知识点，阶段测验取当前已确认学习计划所属课程内的已学习知识点。
- 题量目标按 PRD：知识点 5 题、章节 10 题、阶段综合 30 题，实际题量受题库可用题数限制。
- 每种题 10 分；客观题全对得分，主观题按参考答案关键词覆盖率 ≥80% 视为通过，并保存参考答案、命中/缺失关键词等评分依据。V1.0 代码题只做文本分析，不执行代码。
- 掌握状态（阶段 5 起）：知识点层新增 7 态掌握度（见「知识点掌握度与学习诊断（阶段 5）」），原有 `learning_profiles` 仍作为进度状态被投影同步。知识点测验满足「有效题量 ≥3、全部题目通过、百分制 ≥90」判为 `MASTERED`；诊断（跳级）测验 ≥2 题全对可验证未学知识点；未通过进入 `NEEDS_REVIEW`（旧状态投影 `review_due`）。章节/阶段/复习测验、完成任务和普通聊天都不改变掌握度。
- 用户自述完成只写 `SELF_REPORTED_COMPLETED`（旧状态 `pending_verification`），**不会变成 `MASTERED`，也不能据此跳级**。
- 错题自动收录并生成复习任务，间隔按 1、3、7、14 天推进；答错重置为 1 天，允许提前复习；每次复习保留独立答题记录。
- AI 变式题仅在通过题目格式、正确答案、解析、知识点归属与学习范围验证后进入正式测验；验证失败自动使用内置题库，并在本次测验中明确说明。

## 课程结构与课程管理（阶段 1）

- 课程层级：课程方向 → 课程 → 章节 → 课时 → 知识点 → 教学内容 → 练习 → 测验题。
- 章节复用原 `chapters` 表（即 CourseModule）；课时为新增层，一个章节可含多个课时；一个知识点只归属一个课时（`lesson_knowledge_points.knowledge_point_id` 唯一）。
- 知识点仍保留 `chapter_id` 直属章节关系，既有学习计划、每日任务、测验与前端课程页无需改动即可继续工作；课时归属与章节归属由种子与 Service 保证一致。
- 教学内容按课时保存（学习目标、概念讲解、语法/API 讲解、示例代码、代码解释、常见错误、学习总结），一个课时一份。
- 练习挂在知识点下，与测验题库（`question_bank`）分离：练习用于日常动手并返回参考答案，测验用于组卷评分。
- 课程发布状态为 `draft` 草稿 / `published` 已发布 / `archived` 已归档，课程列表默认只返回已发布课程。
- 课程版本以 JSON 快照保存在 `course_versions`，同版本号不覆盖；快照包含课程元数据、章节、课时、教学内容、知识点与练习。
- 课程唯一 slug 复用既有 `code`（如 `python-basics`），接口同时返回 `code` 与 `slug`，不额外维护重复唯一键。
- 课程内容仍由种子或受控 Service 写入，Agent 不直接访问数据库；本阶段不改动前端。

## 课程目录与学习路线（阶段 2）

- 课程方向是**课程分类**，能力等级（L0 零基础 / L1 有基础 / L2 进阶）是独立维度，两者不放在同一字段，也不互相替代。
- 5 个方向：Python 编程基础、Python 工程与数据库、Python 后端开发、AI 大模型应用开发、AI Agent 与综合项目；一门课可关联多个方向（如 LangGraph 同时属大模型与 Agent），主方向冗余在 `courses.direction` 便于单值筛选。
- 7 门课程目录共 93 章、175 课时：Python 零基础入门、Python 进阶与工程实践、数据库与 Python 数据库开发、FastAPI 后端开发、Python 大模型 API 应用开发、LangGraph Agent 开发、软件工程与项目部署。（章节课时随教材写入而调整：阶段 3 把 `python-basics` 扩为 20 章 29 课时，阶段 4A 把进阶课定为 10 章 12 课时、数据库课定为 9 章 11 课时，阶段 4B 把 FastAPI 课定为 16 章 31 课时，阶段 4C 把大模型 API 课定为 16 章 32 课时，阶段 4D 把 LangGraph 课定为 28 章 47 课时；当前库内合计 107 章 190 课时。）
- 先修关系为有向无环图（9 条边）：基础 → 进阶 → 数据库 / 大模型 → FastAPI / LangGraph → 项目部署；写入时拒绝自引用与循环依赖，并返回拓扑顺序。
- 每门课可登记跨课程的「入学知识点」，学习路径据此给出补学清单；前置课程已掌握或其入学知识点已全部掌握时自动跳过（支持诊断后跳级）。
- 新课目录以 `draft` 初始化，学习入口默认只返回已发布课程；`python-basics` 因已有完整知识点与内置题库保持已发布。
- 完整目录见 [docs/课程扩展阶段2_课程目录与学习路线.md](docs/课程扩展阶段2_课程目录与学习路线.md)。

## 零基础入门教材（课程扩展阶段 3）

- `python-basics` 扩为 **20 章 / 29 课时**，每节课固定 15 个内容模块：学习目标、为什么学、核心概念、通俗解释、语法介绍、示例代码、逐行解释、示例输出、常见错误、错误分析、入门练习、进阶练习、本节测验、学习总结、下一课建议。
- 教材正文共 194 道测验题 + 58 个练习：每节课 ≥2 道基础理解 + ≥2 道代码阅读 + ≥2 道应用练习，课程整体覆盖单选、多选、判断、代码理解、代码补全、编程思路分析 6 种题型；每题都带参考答案与解析，并挂在本科时的知识点上。
- 内容状态 `draft → reviewed → published`：跳到发布前会重新检查 15 个模块，模块不全直接拒绝；默认读取不返回草稿内容。当前全部内容为 `reviewed`，等待人工终审。
- 内容验收提供 10 项确定性检查（章节与课时结构、模块齐全、代码与输出、初学者友好度、练习与题目关联、分类与题型、是否提前使用未学语法、重复度、能否被学习计划排期）：`GET /api/v1/courses/python-basics/textbook/audit`。
- 31 个旧知识点与 93 道内置题按 id 原样保留（知识点 code 未改名，题库题目 code 与课程先修关系继续有效）；重排章节后与新顺序冲突的 5 条前置边已清理，学习计划的排期与版本历史不受影响。
- 教材只做文本评分，不执行用户代码。
- 详见 [docs/课程扩展阶段3_零基础入门教材.md](docs/课程扩展阶段3_零基础入门教材.md)。

## Python 进阶与数据库教材（课程扩展阶段 4A）

- 两门课写入完整正文：`python-advanced` **10 章 / 12 课时**、`python-database` **9 章 / 11 课时**，合计 19 章 23 课时、24 个知识点、23 份教学内容、46 个练习、138 道测验题。
- 需求列出的 12 个进阶主题（面向对象、类和对象、封装/继承/多态、推导式、迭代器与生成器、装饰器、上下文管理器、类型注解、虚拟环境、pip 与依赖管理、项目目录结构、日志与配置）与 11 个数据库主题（数据库基础、SQL、SQLite、主键与外键、JOIN、索引与事务、SQLAlchemy 2.x、ORM 模型、Session、CRUD、Alembic）全部落到独立课时。
- 每节课沿用阶段 3 的 15 个内容模块，示例输出与**真实运行结果**对齐：`test_example_code_runs_and_matches_declared_output` 会真实执行示例代码并逐行比对，本阶段据此修掉 6 处内容错误。
- 版本规范由测试固化：SQLAlchemy 必须用 2.0 写法（`DeclarativeBase` / `Mapped[]` / `mapped_column` / `select()`，禁 `declarative_base()` 与 `session.query()`）、Alembic 迁移必须用 `batch_alter_table` 并保留 `down_revision` 版本链、SQLite 相关课时必须提到 `PRAGMA foreign_keys = ON`。
- 先修关系：进阶课 ← 零基础课，数据库课 ← 进阶课；两门课都登记了来自 `python-basics` 的入学知识点，24 个新知识点之间 22 条先修边全部「靠前课时 → 靠后课时」，无倒挂。
- 内容验收按课程 profile 取配置（`app/core/curriculum.py`）：章数与「是否提前使用未学语法」的语法表按课程区分，不再是一套零基础标准套所有课。
- 两门课内容状态为 `reviewed`，等待人工终审后置 `published`；验收结果见 `GET /api/v1/courses/python-advanced/textbook/audit` 与 `/courses/python-database/textbook/audit`。
- 详见 [docs/课程扩展阶段4A_进阶与数据库.md](docs/课程扩展阶段4A_进阶与数据库.md)。

## FastAPI 后端开发教材（课程扩展阶段 4B）

- `fastapi-backend` 由目录状态重建为 **16 章 / 31 课时**，共 31 个知识点、31 份教学内容、62 个练习、186 道测验题；课程描述与学习目标同步重写，预计时长 21 小时 5 分钟。
- 需求列出的 24 个主题全部落到独立课时：API 基础（2）、安装启动（1）、路由与路径参数（2）、查询参数（1）、五种 HTTP 方法与请求响应体（2）、Pydantic 与数据校验（2）、Depends（1）、路由模块化（1）、异常处理与中间件（2）、CORS 与同步异步（2）、SQLAlchemy 集成（2）、认证与 JWT（2）、权限与文件上传（2）、文档与接口测试（2）、日志配置与部署（2）、综合项目（5）。
- 综合项目「任务管理 API」的 9 个步骤（创建项目 → 拆分路由 → 数据模型 → 连接 SQLite → CRUD → 认证 → 接口校验 → 测试 → 项目配置）由第 16 章 5 节课逐步推进，每步都给出可串起来的增量代码与真实请求响应。
- 教材标注适用版本并以实测为准：FastAPI **0.162.0** / Starlette 1.10 / Pydantic **2.14.2** / pydantic-settings 2.16 / uvicorn 0.54 / SQLAlchemy **2.1.6** / pytest 9.2；写法统一为 `Annotated[T, Depends(...)]`、`lifespan`、`DeclarativeBase` + `Mapped[]`，禁用 `@app.on_event`、`declarative_base()`、`session.query()`、`typing.List`、`pydantic.v1`。
- 「不把 JWT、数据库、异步提前」由两道防线保障：章节顺序（`async` 最早第 9 章、`create_engine` 第 11 章、JWT 第 12 章、上传第 13 章、测试第 14 章）+ `app/core/curriculum.py` 的 `FASTAPI_SCOPE` 术语表（审计第 8 项与本阶段测试同时检查）。
- `python-multipart` 与 `PyJWT` 未引入运行依赖：上传课照现代写法给 `Annotated[UploadFile, File()]`（分块读取、413/415、路径清洗）并注明「解析表单需装 `python-multipart`」；JWT 课用 `hmac`+`hashlib`+`base64url` 手工实现 HS256（配 `OAuth2PasswordBearer`），正文注明生产环境应直接装这两个库。
- 内容验收：`GET /api/v1/courses/fastapi-backend/textbook/audit` 的 10 项检查全部 PASS；`backend/tests/test_phase4b.py` 20 项测试覆盖本阶段 8 个验收项，全量后端测试 349 passed。
- 31 份内容状态为 `reviewed`、课程 `publish_status` 为 `draft`（与进阶、数据库两门课一致；只有内容已验收的零基础课保持 `published`），人工终审后再置 `published`。
- 详见 [docs/课程扩展阶段4B_FastAPI后端开发.md](docs/课程扩展阶段4B_FastAPI后端开发.md)。

## Python 大模型 API 应用开发教材（课程扩展阶段 4C）

- `llm-api` 由目录状态重建为 **16 章 / 32 课时**，共 32 个知识点、32 份教学内容、64 个练习、192 道测验题，预计时长 20 小时 15 分钟。
- 需求列出的 20 个主题全部有落点：大模型基本概念（2）、服务商与兼容 API（2）、API Key 管理（2）、Python 调用（2）、消息结构与 system/user 提示（1）、Prompt 设计（2）、多轮对话（2）、上下文管理（2）、Streaming（2）、JSON 结构化输出（2）、Function Calling（2）、Tool Calling（2）、Token 与费用（1）、超时重试与异常（2）、AI 应用安全（1）、综合项目（5）。
- 教材以**稳定的 OpenAI 兼容调用方式**为基础：全部示例用 `httpx` 直连 `/chat/completions`，只靠 Base URL 与模型名切换服务商；厂商专属参数作为「可选能力」单列一节，`max_retries` / `backoff` 明确声明为客户端实现而非协议字段。
- **API Key 只从环境变量读取**：`LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL` 由 `os.environ` 读取，启动即校验，`__repr__` 与日志只留后四位指纹，`.env` 进 `.gitignore`；32 段示例代码经正则扫描无任何密钥字面量。
- 综合项目「Python AI 对话助手」覆盖需求列出的 6 个组成部分（模型配置 / API 调用 / 消息管理 / 多轮上下文 / 流式输出 / 错误处理），5 节课逐步推进，代码可直接串成 `config` / `models` / `client` / `session` / `stream` / `errors` 六层结构，并附 `pytest` + `MockTransport` 的 4 项离线测试。
- `openai` 与 `tiktoken` 未引入运行依赖：前者用 `httpx` 直连替代（协议字段一一对应），后者用 `estimate_tokens()` 粗估并强调「`usage` 才是真值」。
- 内容验收：`GET /api/v1/courses/llm-api/textbook/audit` 的 10 项检查全部 PASS；`backend/tests/test_phase4c.py` 21 项测试覆盖四部分要求，全量后端测试 370 passed。
- 32 份内容状态为 `reviewed`、课程 `publish_status` 为 `draft`，人工终审后再置 `published`。
- 详见 [docs/课程扩展阶段4C_大模型API应用开发.md](docs/课程扩展阶段4C_大模型API应用开发.md)。

## LangGraph Agent 开发教材（课程扩展阶段 4D）

- `langgraph-agent` 由目录占位重建为 **28 章 / 47 课时**，共 47 个知识点、47 份教学内容、94 个练习、282 道测验题，预计时长 30 小时 35 分钟。需求给出的 28 个主题**逐一独立成章**，章号与主题号 1:1。
- 教学顺序按需求分五段推进：概念（1—3 章，一行框架代码都没有）→ 图基础（4—5 章）→ State/Node/Edge（6—12 章）→ 条件路由与流程控制（13—15 章）→ 大模型接入与工具调用（16—19 章）→ 持久化与人工审批（20—22 章）→ 子图与流式事件（23—24 章）→ 工程化（25—27 章）→ 综合项目（28 章）。
- 9 项重点内容各有主课与代码落点：State（结构 + 更新）、Node（签名与返回值）、Edge（普通边与出入点）、Conditional Edge（路由函数 + 兜底分支）、Checkpointer（`thread_id` + `get_state_history` + `update_state`）、Store（`runtime.store` + 命名空间前缀查询）、Interrupt（`interrupt` + `Command(resume)`）、Subgraph（`add_node(子图)` + 父子状态映射）、Streaming（`stream_mode` 五种模式 + SSE 帧）。
- 版本口径按实测环境钉死并写进正文：`langgraph 1.2.20` / `langchain-core 1.7.6` / `langgraph-checkpoint 4.3.1` / `langgraph-prebuilt 1.1.1` / `pydantic 2.14`。三条易混事实单列：`create_react_agent` 已发 `LangGraphDeprecatedSinceV10`（迁往 `langchain.agents`）、`Store` 只能经 `runtime.store` 取（`config["store"]` 已失效）、`bind_tools` 默认抛 `NotImplementedError` 需自行实现。
- 综合项目「个人 AI 学习 Agent」覆盖需求 6 项能力：识别问题（`classify` + `intent`）、读取课程知识（`retrieve` / `read_chapter`）、调用白名单工具（`ALLOWED` + 参数夹紧）、保存对话状态（`checkpointer` + `store`）、按条件选工作流（`RULES` + `add_conditional_edges`）、FastAPI 接口（`/ask`、`/approve`、`/ask/stream`）。
- **不执行用户提交的代码**：工具层只有 `ALLOWED` 白名单里的 2 个只读工具（`search_course` / `read_lesson`），`WRITE_TOOLS` 留空；记笔记这类写动作走「节点 + `interrupt` 人工审批」，批准后才写 Store；示例里不出现 `eval` / `exec` / `subprocess`，由测试断言确保。
- 示例输出全部是真实运行结果：新增测试逐节课执行 `example_code` 并与教材 `output` 逐行比对（UUID 归一化），47 节课零差异。
- 内容验收：`GET /api/v1/courses/langgraph-agent/textbook/audit` 的 10 项检查全部 PASS；`backend/tests/test_phase4d.py` 24 项测试覆盖六部分要求，全量后端测试 394 passed。
- 47 份内容状态为 `reviewed`；课程 `publish_status` 在阶段 4D 时为 `draft`，**阶段 6 完成教材验收后已置为 `published`**，可进入正式学习计划。
- 详见 [docs/课程扩展阶段4D_LangGraph_Agent开发.md](docs/课程扩展阶段4D_LangGraph_Agent开发.md)。

## 知识点掌握度与学习诊断（阶段 5）

- 学习进度从「课程完成状态」升级为**知识点级掌握度**：新增 `knowledge_mastery`（7 态当前态）、`mastery_evidence`（只追加的证据流水）、`exercise_attempts`（练习记录）三张表，`learning_plan_versions` 增加 `self_reported_kp_codes` 快照，`quiz_attempts` 增加 `purpose`（`practice` / `placement`）。
- 7 个状态：`NOT_STARTED` / `LEARNING` / `SELF_REPORTED_COMPLETED` / `UNDERSTOOD` / `APPLIED` / `MASTERED` / `NEEDS_REVIEW`，分别投影回原有的 5 态 `learning_profiles`（不改其取值集合与 CHECK 约束），历史档案在迁移时一次性补建，老数据不丢。
- **自述不等于掌握**：`on_self_report` 代码路径上不存在「自述 → MASTERED」的分支；计划排期、学习路径、跳级检查三处统一只采信 `mastered`（有测验/练习证据），整门课自述也不能跳过全部前置。
- 掌握证据关联用户标识、知识点 ID、练习记录、测验记录、正确率、测验难度、状态与验证时间；自述时间、验证时间、进入复习时间分开存。
- 诊断升级为 **6 个维度**（Python 基础 / Python 工程能力 / 数据库能力 / Web 后端能力 / 大模型 API 能力 / LangGraph Agent 能力），映射到 31 个具体锚点知识点，输出个性化学习路线（跳过 / 验证 / 复习 / 补学 / 学习）、薄弱点复习建议与跳级检查。
- 诊断（跳级）测验允许对**未学知识点**出题，通过后写 `placement` 证据并进入 `MASTERED`；练习判定用参考答案文本覆盖率比对，**不执行用户提交的代码**。
- 前端新增「能力诊断」页（掌握度总览、六维画像、路线筛选、自述登记、诊断测验、复习建议、证据详情），测验中心支持从诊断页跳转自动打开测验并标注「诊断测验」。
- 验收：`backend/tests/test_phase5.py` 32 项覆盖需求六 7 项必测；后端全量 **426 passed**，前端 lint / tsc / 14 项测试 / `next build` 全通过；`alembic check` 无漂移。
- 详见 [docs/课程扩展阶段5_知识点掌握度与学习诊断.md](docs/课程扩展阶段5_知识点掌握度与学习诊断.md)。

## 学习闭环与 LangGraph Agent 集成（课程扩展阶段 6）

- **正式发布门槛**：6 门已完成教材的课程（含 `langgraph-agent`）目录种子 `publish_status` 统一为 `published`，`software-engineering-deploy` 仍为 `draft`。`CoursePublicationService.require_published()` 是唯一判定入口：草稿课程返回 409、知识点没有真实归属课时或内容为草稿返回 422，课时尚无正文时只标注「内容待补充」，不伪造教材。
- **学习计划八类输入**：生成计划时把学习目标、每日学习时间、当前能力等级、已/未掌握知识点、课程前置关系、课程预计时间、最近测验表现与诊断证据写入 `learning_plan_versions.plan_context`（可审计快照）。排期仍由确定性算法执行；`placement` 诊断证据才跳过基础教学，仅自述完成不跳过，未掌握先修只提示补学。
- **今日任务两步走**：首页先 `GET /api/v1/daily-tasks/today?generate=false` 只读查询，有任务直接读取；无任务才 `POST /api/v1/daily-tasks/today/generate` 幂等生成（唯一约束 + `IntegrityError` 回滚兜底）。每条任务固化 `course_id` / `module_id`(章节) / `lesson_id` / `knowledge_point_id` 四个真实标识；任务完成只写「用户自述完成」证据，输出附带 7 态掌握状态与证据条数。
- **AI 教学**：Teaching 子图新增 `load_course_material` 节点，先经 `AgentToolbox → CourseService` 读取知识点与课时正文，再注入系统提示词；Agent 可解释/举例/讲代码/分析错误/给练习与总结，但工具层与提示词双重禁止「创建课程、改依赖、跳先修、随意改掌握状态、未经确认保存计划修改」。
- **Agent 工具**：9 个阶段 6 必备工具（`get_course`、`get_lesson`、`get_knowledge_point`、`get_user_learning_progress`、`get_today_tasks`、`submit_exercise`、`submit_quiz_result`、`request_review_task`、`propose_learning_plan_adjustment`）+ 7 个原闭环兼容工具，共 16 个；所有写操作都经 Service 层，禁止入口在 `FORBIDDEN_TOOL_NAMES` 中逐项列出。
- **动态计划调整**：六类触发信号（连续测验不通过 / 已掌握多个后续知识点 / 基础能力不足 / 目标改变 / 每日时间增加 / 请求复习）全部按真实数据判定；`propose()` 只写 `proposed` 提案，用户确认后才由 `PlanService` 生成并生效新版本。前端「学习计划」页新增提案展示与确认/拒绝。
- **验收**：`backend/tests/test_phase6.py` 16 项覆盖需求十项必测；后端全量 **442 passed**，前端 lint / `tsc --noEmit` / 18 项 Vitest / `next build` 全通过；迁移 `7e6ec48dafbe`，`alembic current` 为 head、`alembic check` 零漂移、`integrity_check = ok`、外键 0 违规。
- 详见 [docs/课程扩展阶段6_学习闭环与Agent集成.md](docs/课程扩展阶段6_学习闭环与Agent集成.md)（含完整调用流程、工具列表、测试结果与手动验收方式）。

## 环境变量

所有环境变量集中说明于根目录 `.env.example`。复制为 `.env` 后按需修改（Docker 部署使用；本地开发使用代码内默认值即可）。`.env` 不会被提交到版本库。

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `BIND_ADDRESS` | `127.0.0.1` | 宿主机端口绑定地址；`0.0.0.0` 表示开放局域网/公网 |
| `FRONTEND_PORT` | `3000` | 宿主机前端端口 |
| `XIAOMA_ACCESS_PASSWORD` | 空 | 访问密码；设置后后端强制登录 |
| `XIAOMA_ALLOW_REMOTE` | `false` | 显式允许远程访问；为 true 时必须有访问密码 |
| `XIAOMA_ACCESS_TOKEN_TTL_SECONDS` | `86400` | 登录会话有效期（秒） |
| `XIAOMA_SECRET_KEY` | 自动生成 | 模型 API Key 加密密钥 |
| `XIAOMA_AGENT_TIMEOUT_SECONDS` | `120` | 主 Agent 整体超时（秒） |
| `XIAOMA_BACKUP_DIR` | 数据库同目录 `backups/` | 备份目录 |
| `CORS_ALLOW_ORIGINS` | 空 | 浏览器直连后端时的跨域来源白名单 |

## 测试

```bash
# 后端：单元测试、API 集成测试、数据库迁移测试、Agent 工作流测试
cd backend
.venv/Scripts/python -m pytest tests/ -v

# 前端：核心流程测试（Vitest）
cd frontend
npm test
```

## 安全说明

- 不硬编码 API Key、密码等秘密信息；`.env` 不提交到版本库。
- 模型 API Key 加密存储，接口与页面只展示脱敏值，日志不记录完整密钥。
- 访问保护由后端强制实施；默认部署仅本机可访问。
- 用户数据不上传开发者服务器；启用 AI 功能时，提示词与必要上下文会发送给用户自己配置的模型服务商。
- V1.0 不执行用户提交的 Python 代码。

## 文档

- 产品需求文档：[docs/Xiaoma_PRD_V1.3.md](docs/Xiaoma_PRD_V1.3.md)（V1.3 阅读镜像；`.docx` 原件已从版本库移除）
- V1.4 产品需求（软件端对话工作台）：[docs/小码_Xiaoma_软件端_对话工作台版.md](docs/小码_Xiaoma_软件端_对话工作台版.md)
- V1.4 开发任务书：[docs/小码_Xiaoma_软件端开发任务书.md](docs/小码_Xiaoma_软件端开发任务书.md)
- V1.4 技术设计与契约：[docs/V1.4技术设计与契约.md](docs/V1.4技术设计与契约.md)
- 项目总开发指令：[docs/项目总开发指令.md](docs/项目总开发指令.md)
- 分阶段开发任务书：[docs/Codex开发任务书.md](docs/Codex开发任务书.md)
- Docker 部署指南：[docs/Docker部署指南.md](docs/Docker部署指南.md)
- V1.0 部署操作方案（可直接照做的分步清单）：[docs/V1.0部署操作方案.md](docs/V1.0部署操作方案.md)
- 课程扩展阶段 0 项目检查报告：[docs/课程扩展阶段0项目检查报告.md](docs/课程扩展阶段0项目检查报告.md)
- 课程扩展阶段 2 课程目录与学习路线：[docs/课程扩展阶段2_课程目录与学习路线.md](docs/课程扩展阶段2_课程目录与学习路线.md)
- 课程扩展阶段 3 零基础入门教材：[docs/课程扩展阶段3_零基础入门教材.md](docs/课程扩展阶段3_零基础入门教材.md)
- 课程扩展阶段 4A Python 进阶与数据库教材：[docs/课程扩展阶段4A_进阶与数据库.md](docs/课程扩展阶段4A_进阶与数据库.md)
- 课程扩展阶段 4B FastAPI 后端开发教材：[docs/课程扩展阶段4B_FastAPI后端开发.md](docs/课程扩展阶段4B_FastAPI后端开发.md)
- 课程扩展阶段 4C 大模型 API 应用开发教材：[docs/课程扩展阶段4C_大模型API应用开发.md](docs/课程扩展阶段4C_大模型API应用开发.md)
- 课程扩展阶段 4D LangGraph Agent 开发教材：[docs/课程扩展阶段4D_LangGraph_Agent开发.md](docs/课程扩展阶段4D_LangGraph_Agent开发.md)
- 课程扩展阶段 5 知识点掌握度与学习诊断：[docs/课程扩展阶段5_知识点掌握度与学习诊断.md](docs/课程扩展阶段5_知识点掌握度与学习诊断.md)
- 课程扩展阶段 6 学习闭环与 Agent 集成：[docs/课程扩展阶段6_学习闭环与Agent集成.md](docs/课程扩展阶段6_学习闭环与Agent集成.md)
- 最终开发报告与独立验收（15 项报告 + 10 项验收 + 实测结果）：[docs/最终开发报告与独立验收.md](docs/最终开发报告与独立验收.md)
- 模型配置说明：[docs/模型配置说明.md](docs/模型配置说明.md)
- 常见问题：[docs/常见问题.md](docs/常见问题.md)
- 开发进度与验收记录：[docs/开发进度与验收记录.md](docs/开发进度与验收记录.md)
- 内置题库抽检表：[docs/内置题库抽检表.md](docs/内置题库抽检表.md)
- 内置题库审核报告：[docs/内置题库审核报告.md](docs/内置题库审核报告.md)
- 依赖版本记录：[docs/依赖版本记录.md](docs/依赖版本记录.md)
- 更新日志：[CHANGELOG.md](CHANGELOG.md)
- English README：[README.en.md](README.en.md)

## 许可证

[Apache License 2.0](LICENSE)
