# 小码 Xiaoma

开源、免费、个人独立部署的 **AI 编程学习教练**，帮助编程初学者通过结构化课程与持续验证真正掌握编程知识。

> English: Xiaoma is an open-source, self-hosted AI learning coach that helps beginners master programming through structured courses and continuous verification. First course: Python Basics.

## 项目状态

| 阶段 | 内容 | 状态 |
| --- | --- | --- |
| 阶段 0 | 开发环境检查 | ✅ 完成（Python 3.14 决策已记录） |
| 阶段 1 | 项目工程初始化 | ✅ 完成 |
| 阶段 2 | 数据库和基础架构 | ✅ 完成（SQLite + SQLAlchemy + Alembic，4 张基础表） |
| 阶段 3 | 前端基础框架 | ✅ 完成（9 页面 + 侧边栏布局 + 设计系统） |
| 阶段 4 | 学习档案与课程体系 | ✅ 完成（课程/章节/知识点 + Python 通用基础种子课程 + 学习档案接口） |
| 阶段 5 | 学习计划 | ✅ 完成（诊断→排期→草稿→确认；版本化调整；历史保留） |
| 阶段 6 | 每日学习任务 | ✅ 完成（首页查询/生成当天任务；防重复；开始/完成标记；进度联动） |
| 阶段 7 | 模型接入和系统设置 | ✅ 完成（统一 LLM Provider、密钥加密、连接测试、默认模型切换、流式输出；已用 DeepSeek 真实模型验收） |
| 阶段 8 | AI 教学与聊天历史 | ✅ 完成（会话/消息/学习会话持久化、LangGraph Teaching 子图、流式教学、失败不伪造回复；前端工作台/聊天历史/任务与知识点入口已接入；已用 DeepSeek 真实模型验收） |
| 阶段 9 | 测验、评分与错题本 | ✅ 完成（5 张测验相关表、7 种题型、知识点/章节/阶段组卷、自动评分、掌握验证、错题与间隔复习、AI 变式题双重验证；前端测验中心与错题本已接入；已用 DeepSeek 真实验收 AI 变式题） |
| 阶段 10 | LangGraph Agent | ✅ 完成（主 Agent + Planning/Teaching/Quiz/Review/Resource 五个子图、确定性意图识别、结构化状态、Service 工具层、整体超时与失败处理、执行日志脱敏；已用真实 DeepSeek 与 7 个验收场景实测） |
| 后续阶段 | 按 docs/Codex开发任务书.md 逐阶段推进 | ⏳ |

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
├── docs/                  # 正式开发依据文档（PRD、任务书、验收记录）
├── docker-compose.yml     # 容器编排（初始版本）
├── .env.example           # 统一环境变量模板
└── README.md
```

## 本地启动

### 后端（默认 http://127.0.0.1:8000）

```bash
cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt    # Windows；macOS/Linux 用 .venv/bin/
.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

- 健康检查：http://127.0.0.1:8000/api/v1/health
- 接口文档：http://127.0.0.1:8000/docs

主要接口（前缀 `/api/v1`）：

| 接口 | 说明 |
| --- | --- |
| GET /courses | 课程列表 |
| GET /courses/{code} | 课程详情（含章节与知识点） |
| GET /courses/{code}/chapters | 章节列表 |
| GET /knowledge-points/{code} | 知识点详情（含前置知识点） |
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
| GET /profile / PUT /profile | 获取 / 更新学习档案 |
| GET /quizzes/eligibility | 可测验范围（仅已学习知识点/章节/当前阶段） |
| GET /quizzes | 测验历史记录 |
| POST /quizzes | 按知识点/章节/阶段组卷（可请求 AI 变式题） |
| GET /quizzes/{id} | 测验详情与题目（未提交不返回答案与解析） |
| POST /quizzes/{id}/submit | 提交全部答案并自动评分 |
| GET /mistakes | 错题本（可按 pending/resolved 筛选） |
| GET /reviews/tasks | 待复习任务（按到期时间升序） |
| POST /reviews/tasks/{id}/submit | 提交错题复习答案并推进/重置复习间隔 |

### 数据库初始化（迁移与种子数据）

```bash
cd backend
.venv/Scripts/python -m app.cli init-db         # 等价于 alembic upgrade head
.venv/Scripts/python -m app.cli seed-courses    # 写入课程种子数据（幂等，可重复执行）
.venv/Scripts/python -m app.cli seed-questions  # 写入内置题库（幂等；需先执行 seed-courses）
```

- 内置题库当前为 31 个知识点 × 3 题，共 93 题；题目经结构校验，并已生成 [抽检表](docs/内置题库抽检表.md) 与 [审核报告](docs/内置题库审核报告.md)。产品负责人抽检确认前，仍建议按开发期整理内容对待。
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

### Docker Compose（需先启动 Docker Desktop）

```bash
cp .env.example .env
docker compose up -d
```

## 模型配置与密钥安全

- 通过 `POST /api/v1/model-configs`（或设置页）添加模型：支持 DeepSeek、通义千问、OpenAI 及任意 OpenAI 兼容端点（自定义需填 `base_url`）。
- API Key 使用 Fernet 加密后存入 SQLite，接口与页面只展示脱敏值（如 `sk-****abcd`）。
- 加密密钥默认自动生成于数据库同目录 `data/.secret_key`（Docker 下位于数据卷）；也可通过环境变量 `XIAOMA_SECRET_KEY` 指定。**更换密钥后已保存的 Key 无法解密，需要重新填写。**
- 未配置默认模型时，教学类流式对话返回 409 并提示先配置模型；计划/进度/测验/错题/资源查询不依赖模型。模型超时/不可用/空回复均返回明确中文提示。
- 日志不记录完整 API Key。

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
- 掌握状态：只有知识点测验满足「有效题量 ≥3、全部题目通过、百分制 ≥90」时才标记为 mastered；章节/阶段测验、完成任务和普通聊天都不会直接改变掌握状态。
- 错题自动收录并生成复习任务，间隔按 1、3、7、14 天推进；答错重置为 1 天，允许提前复习；每次复习保留独立答题记录。
- AI 变式题仅在通过题目格式、正确答案、解析、知识点归属与学习范围验证后进入正式测验；验证失败自动使用内置题库，并在本次测验中明确说明。

## 环境变量

所有环境变量集中说明于根目录 `.env.example`。复制为 `.env` 后按需修改（Docker 部署使用；本地开发使用代码内默认值即可）。`.env` 不会被提交到版本库。

- 浏览器直接调用后端 API/SSE 需要跨域许可：本机 `localhost` / `127.0.0.1` 任意端口默认允许；通过局域网 IP 或自定义域名访问前端时，在 `CORS_ALLOW_ORIGINS` 中追加来源（逗号分隔，如 `http://192.168.1.5:3000`）。
- 主 Agent 整体超时：`XIAOMA_AGENT_TIMEOUT_SECONDS`（默认 120 秒）。

## 测试

```bash
cd backend
.venv/Scripts/python -m pytest tests/ -v
```

## 文档

- 产品需求文档：[docs/Xiaoma_PRD_V1.3.docx](docs/Xiaoma_PRD_V1.3.docx)（[docs/Xiaoma_PRD_V1.3.md](docs/Xiaoma_PRD_V1.3.md) 为阅读镜像）
- 项目总开发指令：[docs/项目总开发指令.md](docs/项目总开发指令.md)
- 分阶段开发任务书：[docs/Codex开发任务书.md](docs/Codex开发任务书.md)
- 开发进度与验收记录：[docs/开发进度与验收记录.md](docs/开发进度与验收记录.md)
- 内置题库抽检表：[docs/内置题库抽检表.md](docs/内置题库抽检表.md)
- 内置题库审核报告：[docs/内置题库审核报告.md](docs/内置题库审核报告.md)
- 依赖版本记录：[docs/依赖版本记录.md](docs/依赖版本记录.md)

## 许可证

Apache License 2.0（LICENSE 文件将在交付阶段提供）
