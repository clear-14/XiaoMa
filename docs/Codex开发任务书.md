# 小码 Xiaoma V1.0 Codex 分阶段开发任务书

> 文档性质：正式开发依据（与 PRD V1.3 同级）
> 接收方式：由产品负责人分阶段下发，本文档逐阶段追加归档

---

## 阶段 0：开发环境检查

**目标**：确认开发电脑具备项目开发环境。

发送给 Codex：请检查当前电脑的开发环境，不要创建业务代码。

检查：
1. Python 版本，要求 Python 3.12。
2. Node.js 和 npm 版本。
3. Git 是否正常。
4. Docker 和 Docker Compose 是否可用。
5. 当前工作目录是否为空。
6. 是否存在可能冲突的项目文件。

输出环境检查报告，指出缺少什么、应该如何安装。
不要擅自修改系统环境变量或卸载已有软件。

**验收标准**：
- Python、Node.js、Git 能正常使用。
- Docker 能正常运行。
- 确认项目工作目录。

**执行结果**：2026-11-02 完成，见会话中的环境检查报告。其中 Python 版本要求经技术决策改为 3.14（见下）。

---

## 技术决策记录

| 日期 | 决策项 | 内容 | 决策人 |
| --- | --- | --- | --- |
| 2026-11-02 | 后端 Python 版本 | 由总开发指令的 Python 3.12 改为 **3.14**（本机已装 3.14.4，主流依赖已支持 3.14；阶段 1 锁定依赖时以实际安装与测试验证兼容性） | 产品负责人 |
| 2026-11-03 | learning_profiles 表定位 | 任务书阶段 4 要求新增 learning_profiles 表，与阶段 2 已建 user_profiles（学习目标/基础/时长/偏好）存在命名重叠。经确认：**learning_profiles 为知识点掌握状态表**（user_id + knowledge_point_id + PRD 6.1 五种状态 + 开始/掌握/复习时间），学习档案接口继续读写 user_profiles | 产品负责人 |
| 2026-11-03 | 学习计划周期规则 | ①期望学习周期单位采用**天**；②排期超出期望周期时**仍创建计划并在响应中标记警告**（「按每日 N 分钟排期需要 M 天，超出期望周期 X 天」），由用户在确认前决定调整参数或直接确认 | 产品负责人 |
| 2026-11-07 | 每日任务选取规则 | 当天无任务时按**滚动追赶**选取：取当前生效计划中最早的、还有未完成项目的计划日，该日全部未完成且未掌握的知识点生成今日任务；前一天没做完的，新的一天重新生成（旧任务保留为历史记录） | 产品负责人 |
| 2026-11-07 | 每日任务完成联动 | ①任务完成时**同步标记当前生效计划版本对应项目为已完成**（记录完成时间，供调整携带与进度读取）；②开始学习 → 知识点状态 learning、任务完成 → pending_verification（PRD 6.1 联动学习档案，绝不直接 mastered） | 产品负责人 |
| 2026-11-07 | 删除默认模型行为 | 删除默认模型后**保持「无默认模型」状态**，接口明确提示用户重新设置，不自动替用户选择其他配置 | 产品负责人 |
| 2026-11-07 | 「获取模型基本信息」范围 | 指**已保存配置的信息查询**（列表/详情，含脱敏 Key、参数、是否默认），不调用服务商 /models 拉取模型列表 | 产品负责人 |
| 2026-11-07 | 模型密钥加密方案（技术决策） | Fernet（AES-128-CBC + HMAC）；密钥来源：环境变量 `XIAOMA_SECRET_KEY`（口令经 SHA-256 派生）优先，未设置则自动生成数据库同目录 `.secret_key` 并随数据卷持久化；支持密钥轮换但轮换后需重新填写 API Key；日志与错误信息中的密钥统一替换为 `***` | 技术实现（按 PRD 15 列为技术细节） |
| 2026-11-07 | 模型参数默认值（技术决策） | 新建配置默认 temperature=0.7、max_tokens=2048、timeout=60 秒；均可在配置中修改（temperature 0-2、max_tokens 1-65536、timeout 1-600） | 技术实现 |
| 2026-11-07 | learning_sessions 与对话关系 | `learning_sessions` 与 `conversations` **1:1**：每次新建聊天会话同步创建一条学习会话，记录关联的知识点/每日任务、开始时间、最后活动时间与消息数 | 产品负责人 |
| 2026-11-07 | 流式失败/中断处理 | 保存 **status=error 的助手消息**：保留已生成的部分文本并记录明确失败原因，历史中显示为失败，不伪造成功回复；失败回复不进入后续模型上下文 | 产品负责人 |
| 2026-11-07 | LangGraph 引入时点 | **阶段 8 引入 LangGraph**：以单节点 Teaching 子图承载教学流程（概念解释/分步讲解/举例/代码解释/错误分析），通过 custom 流输出增量文本；后续阶段继续扩展其他子图 | 产品负责人 |
| 2026-11-07 | 会话关联位置 | **会话级关联**：`conversations` 记录 knowledge_point_id 与 daily_task_id，会话内所有消息共享该上下文；只提供每日任务时自动关联其知识点 | 产品负责人 |
| 2026-11-07 | 会话删除方式 | **物理删除**：`DELETE /conversations/{id}` 一并删除会话、消息与学习会话记录，删除后不可恢复；前端删除前二次确认。不再使用软删除 | 产品负责人 |
| 2026-11-07 | 前端跨域配置（技术决策） | 后端启用 CORS：`localhost` / `127.0.0.1` 任意端口默认允许；其他来源（局域网 IP、自定义域名）通过环境变量 `CORS_ALLOW_ORIGINS` 逗号分隔追加白名单 | 技术实现 |
| 2026-11-07 | 前端会话创建时机（技术决策） | 工作台“新建对话”先进入空状态，**首条消息发送前才创建会话**（可携带任务/知识点上下文）；流开始前被后端拒绝（如无默认模型）时，前端删除该空会话、恢复输入与上下文，避免留下空的“新对话”记录 | 技术实现 |

---

## 阶段 1：初始化项目工程

**目标**：建立前后端分离的项目骨架。

任务要求（原文摘要）：
创建 frontend（Next.js + TypeScript）、backend（FastAPI + Python）、根目录 README.md、.gitignore、.env.example、docker-compose.yml 初始版本、docs 目录、backend/tests 目录。前端至少提供可正常打开的首页显示"小码 Xiaoma"；后端提供 GET /api/v1/health 返回服务状态和版本信息。前后端分别配置依赖、有独立启动命令、统一环境变量配置；本阶段不开发学习业务；依赖版本采用当前兼容稳定版本并记录具体版本。

**执行结果**（2026-11-02）：

- git 仓库已初始化（main 分支）
- frontend：Next.js 16.4.4 + React 19.3.0（App Router、TypeScript、standalone 输出），首页显示"小码 Xiaoma"，eslint 与生产构建通过
- backend：Python 3.14.4 + FastAPI 0.162.0，GET /api/v1/health 返回 status/service/version，pytest 2/2 通过
- 根目录 README.md、.gitignore、.env.example、docker-compose.yml 及前后端 Dockerfile 已创建
- 本地启动验证：前端 http://localhost:3000 返回 HTTP 200 且包含品牌文案；健康检查接口返回正常 JSON
- 版本明细见 docs/依赖版本记录.md

**验收标准对照**：浏览器可打开前端首页 ✅；健康检查接口正常响应 ✅；前后端可独立启动 ✅；项目结构清晰 ✅

---

## 阶段 2：数据库和基础架构

**目标**：建立可迁移、可测试的 SQLite 数据库。

任务要求（原文摘要）：
SQLite + SQLAlchemy 2.x + Alembic；UUID 主键；创建/更新时间；软删除字段；合理的索引和外键；统一 Session 管理。先建立基础表 users、user_profiles、system_settings、model_configs。单用户产品但保留 user_id 便于扩展；不实现多用户注册和 SaaS；数据库路径从环境变量读取；不得将数据库文件放在容器临时目录；创建第一份 Alembic migration；提供数据库初始化命令。测试：数据库可创建、数据可写入读取、Alembic upgrade 正常、重启后数据仍在。

**执行结果**（2026-11-02）：

- 依赖：SQLAlchemy 2.1.6 + Alembic 1.20.1（Python 3.14.4 下安装、运行正常）
- `app/db/`：声明式基类（统一约束命名）、TimestampMixin / UUIDPkMixin / SoftDeleteMixin、引擎与 Session 统一管理（get_db 依赖）、SQLite 目录保障工具
- `app/models/`：users（username 唯一）、user_profiles（user_id 外键 CASCADE 唯一，学习目标/基础水平/每日时长/偏好 JSON）、system_settings（key 唯一键值）、model_configs（provider/model_name/base_url/api_key_encrypted/is_default）
- 设计说明：单用户语义下 system_settings 与 model_configs 为全局表；用户维度扩展锚点保留在 users / user_profiles
- 时间约定：SQLite 不保存时区，应用侧统一使用 naive UTC（避免 aware/naive 混用比较报错）
- Alembic：`alembic/` 环境 + 首份迁移 `411f8d05cdb8_initial_tables.py`（autogenerate 生成，4 张表全部索引/外键/约束就位）
- 初始化命令：`python -m app.cli init-db`（等价 alembic upgrade head，幂等）
- 数据库文件：backend/data/xiaoma.db 已生成（路径由 DATABASE_URL 环境变量控制，已加入 .gitignore）
- 容器持久化：Dockerfile 建 /app/data，compose 命名卷 xiaoma-data 挂载，数据库不落容器临时目录
- 测试：pytest 12/12 通过（含 Alembic upgrade 建表、幂等性、重启持久性、外键级联、唯一约束、软删除）

**验收标准对照**：数据库文件正常生成 ✅；Alembic 迁移成功 ✅；测试通过 ✅；容器/服务重启后数据不丢失 ✅（引擎重启持久性测试 + 2026-11-02 容器级实证：容器内写入 → docker compose restart → 读回成功。期间修复：后端镜像补 COPY Alembic 迁移文件）

---

## 阶段 3：前端基础框架

**目标**：完成小码的整体 UI 框架。

任务要求（原文摘要）：
Next.js + TypeScript 实现 9 个页面（首页 Dashboard、学习计划、课程学习、AI 学习工作台、测验中心、错题本、学习档案、聊天历史、系统设置）。统一侧边栏导航布局；支持响应式；统一页面标题、间距、按钮、卡片和表单样式；风格简洁现代专注学习；首页可展示明确标注的空状态；不允许虚构业务数据；建立统一 API 请求封装；统一 Loading、Empty、Error 状态。

**执行结果**（2026-11-02）：

- 路由：`app/(main)/` 路由组承载 9 个页面，共享侧边栏布局壳；旧首页迁入并删除避免路由冲突
- 布局：桌面端固定侧边栏（232px）+ 内容区；<900px 切换为移动端顶栏 + 抽屉导航（含遮罩、aria 标注）
- 设计系统：globals.css 统一颜色/间距/圆角变量、卡片/按钮/表单组件样式，支持浅色/深色主题（prefers-color-scheme）
- 组件：Sidebar（内联 SVG 图标，无图标库依赖）、PageHeader、EmptyState（带"空状态"明确标注）、LoadingState、ErrorState
- API 封装：lib/api.ts 统一 fetch 封装（超时、网络错误、HTTP 错误统一为 ApiError；get/post/put/delete）
- 无虚构数据：9 个页面全部使用明确标注的空状态，文案与 PRD 8 页面内容对齐
- 零新增依赖；eslint 通过；生产构建通过（10 条路由全部静态预渲染）
- 实测 9 条路由全部 HTTP 200 且标题正确；修复遗留进程占用 3000 端口问题（旧 dev 进程未随 TaskStop 退出，taskkill 后干净重启）

**验收标准对照**：每个页面都能正常访问 ✅；导航切换正常 ✅（active 高亮 + 移动端抽屉）；页面无明显布局错乱 ✅；移动端和桌面端都能使用 ✅（响应式断点 899px）

---

## 阶段 4：学习档案与课程体系

**目标**：建立结构化课程体系与学习档案数据层及查询接口。

任务要求（原文摘要）：
数据库增加 courses、chapters、knowledge_points、learning_profiles；首发课程为 Python 通用基础；结构化数据包含课程名称、章节、知识点、学习目标、难度、预计学习时间、前置知识点、掌握标准、学习资源；接口包括获取课程列表、课程详情、章节列表、知识点详情、获取学习档案、更新学习档案；提供初始 Python 课程种子数据；知识点拥有稳定 ID；支持前置依赖关系；不允许 AI 自由生成课程目录并直接写入；种子数据重复执行不能产生重复课程。验收：能查看 Python 课程、查看章节与知识点、知识点关联关系正确、学习档案能保存与读取。

**执行结果**（2026-11-03）：

- 新增表（迁移 `3ac5723b47d6`）：courses / chapters / knowledge_points / knowledge_point_prerequisites（知识点多对多自关联，前置关系）/ learning_profiles（知识点掌握状态：user_id + knowledge_point_id 唯一，PRD 6.1 五种状态 + 开始/掌握/复习时间，数据库级 CHECK 约束）
- 稳定标识：课程/章节/知识点均以业务 code（如 python-basics-01-01）作为跨环境稳定 ID，接口与前置关系均以 code 引用；不依赖数据库自增 ID
- 分层实现：API（app/api/v1/courses、knowledge_points、profile）→ Service（course_service、profile_service）→ Repository（course_repository、profile_repository）；统一 404/500 错误响应结构
- 种子数据：Python 通用基础 6 章 31 个知识点（学习目标/难度/预计时长/掌握标准/资源齐全），38 条前置依赖关系；`python -m app.cli seed-courses` 幂等写入（按 code upsert，前置关系按集合差集同步，实测重复执行 0 新增）
- 学习档案接口：GET/PUT /api/v1/profile 读写 user_profiles（PUT 部分更新语义，字段校验：level L0-L2、每日时长 1-1440 分钟、目标 ≤500 字）；单用户产品默认账号 local 懒创建（正式首次初始化流程由后续阶段实现）
- 课程内容为人工编写与审核的初始版本；种子只 upsert 不删除，扩展内容须经产品确认
- 测试：pytest 36/36 通过（新增 24：模型关系/级联/唯一约束/状态 CHECK、种子幂等与前置关系同步、6 个接口含 404 与参数校验）；真实服务接口逐一 curl 验证通过
- 零新增依赖

**验收标准对照**：能查看 Python 课程 ✅（GET /courses、GET /courses/python-basics）；能查看章节与知识点 ✅（/chapters、/knowledge-points/{code}，按 order_index 排序）；知识点关联关系正确 ✅（前置关系按稳定 code 关联，实测 06-05 前置 = 06-01/06-03/06-04）；学习档案能保存与读取 ✅（PUT 保存 → GET 读回一致，服务重启前已实测）

---

## 阶段 5：学习计划

**目标**：让系统根据用户目标建立学习计划（诊断 → 排期 → 草稿 → 用户确认 → 生效）。

任务要求（原文摘要）：
数据库增加 learning_plans、learning_plan_items、learning_plan_versions。实现创建学习计划、查看当前计划、查看计划详情、调整学习目标、调整每日学习时长、查看历史计划版本、更新计划时保留旧版本。初始诊断信息包括当前编程基础、学习目标、每天可学习时间、期望学习周期、已掌握的知识点。AI 可以辅助分析学习计划，但后端必须校验课程知识点、前置依赖和计划结构。用户确认后才正式创建或调整计划。验收：能创建学习计划、能查看计划项目、能调整计划、历史版本保留、已完成任务不会因为调整计划而丢失。

**执行结果**（2026-11-03）：

- 新增表（迁移 `a7577ec16a23`）：learning_plans（user_id/course_id/状态 draft|active/开始日/当前版本号/待确认版本号）、learning_plan_versions（版本号 plan 内唯一，参数快照：目标/每日时长/期望周期/实际排期天数/基础水平/已掌握知识点，状态 draft|active|superseded）、learning_plan_items（版本内知识点唯一，day_index/状态 pending|completed/完成时间）
- 接口 6 个：POST /plans（创建，201）、POST /plans/{id}/confirm、POST /plans/{id}/adjust、GET /plans/current、GET /plans/{id}（含版本列表）、GET /plans/{id}/versions/{n}
- 流程：创建/调整 → 草稿版本（不改变当前生效计划）→ 用户确认 → 生效；调整产生新版本，旧版本转 superseded 保留，历史不覆盖（PRD 9）
- 排期：确定性贪心算法按每日时长把知识点装入「天」（课程顺序、不拆分知识点、超长知识点独占一天）；期望周期单位「天」；排期超出期望周期时仍创建并在响应 warning 字段标记（产品决策见技术决策记录）
- 校验（任务书硬性要求）：课程归属、知识点不重复、前置依赖（前置必须在已知集合〔已掌握∪已完成〕或更早的天，同天须课程顺序更靠前）；已掌握知识点不在课程范围 → 422；排期算法自产结构也过校验器兜底
- 已完成任务保护：调整时已完成项目携带到新版本（保留 day_index 与完成时间），未完成项目重新排期；历史版本项目原样保留（验收实测：3 个项目完成后调整+确认，新版本 3 个已完成项目在、旧版本完整）
- 诊断「已掌握知识点」仅作排期范围，不写入 learning_profiles 掌握状态（PRD：未经测验验证不得标记为已掌握）；项目完成入口（pending→completed 写入）由每日任务阶段实现
- AI 辅助分析：本阶段为基础确定性算法（任务书表述为「AI 可以辅助」非必须），LLM 接入后可在排期建议环节增强，后端校验规则不变
- 测试：pytest 65/65 通过（新增 29：模型关系/唯一约束/级联、排期 6 例、结构校验 8 例含手工构造违规结构、API 13 例覆盖创建/确认/调整/历史/409/422/404 与已完成任务保留）；真实服务全流程 curl 验证通过（创建→警告→确认→调整→再确认→版本 1 保留）
- 零新增依赖

**验收标准对照**：能创建学习计划 ✅（POST /plans 返回草稿+排期）；能查看计划项目 ✅（GET /plans/current 与版本详情含全部项目）；能调整计划 ✅（目标/每日时长/期望周期，草稿→确认）；历史版本保留 ✅（版本列表与版本详情，旧版本 superseded 不覆盖）；已完成任务不因调整丢失 ✅（实测携带与保留）

---

## 阶段 6：每日学习任务

**目标**：实现首页自动查询或生成每日任务。

任务要求（原文摘要）：
数据库增加 daily_tasks。实现查询当天任务、生成当天任务、查看任务详情、标记开始学习、标记用户已完成、记录任务完成时间。核心规则：打开首页先查询当天是否已有任务（有则直接返回，没有才生成）；根据学习计划和当前进度选择知识点；不得重复安排已掌握知识点；不得跳过未满足的前置知识点；同一用户同一天不能重复生成任务。注意：用户点击完成只代表任务完成，不代表知识点已经掌握。验收：首页能够自动获取当天任务、同一天重复打开不会重复生成、用户完成任务后状态正确、学习进度没有被错误标记为 mastered。

**执行结果**（2026-11-07）：

- 新增表（迁移 `6497e0ceef46`）：daily_tasks（user_id/plan_id/knowledge_point_id 级联外键、task_date、生成时计划日快照 day_index、状态 pending|learning|completed 带 CHECK 约束、started_at/completed_at；**user_id + task_date + knowledge_point_id 唯一约束**为防重复机制的数据库层兜底）
- 接口 4 个：GET /daily-tasks/today（首页：先查询当天任务，已有直接返回；无则按计划与进度生成）、GET /daily-tasks/{id}（详情，含知识点学习目标/难度/预计时长/掌握标准/资源/章节/前置）、POST /daily-tasks/{id}/start、POST /daily-tasks/{id}/complete
- 任务选取（产品决策 2026-11-07「滚动追赶」）：取当前生效计划最早的未完成计划日整批生成；已掌握（learning_profiles.status=mastered）与已完成项目排除；更早计划日已全部完成/已掌握 + 计划结构经后端校验 → 前置依赖不会被跳过；同批内按课程顺序学习
- 防重复：先查后生成 + 唯一约束兜底（并发下 IntegrityError 回滚并返回已有任务）
- 完成联动（产品决策 2026-11-07）：①当前生效计划版本对应项目标记 completed + 完成时间（计划调整后完成旧任务会同步到新生效版本）；②学习档案：开始 → learning（记 started_at），完成 → pending_verification——**绝不直接 mastered**（PRD 6.1/12.4，掌握须经测验验证）；已 mastered/review_due 不降级；重复完成 409、完成后不可再开始
- 无计划 → 404「暂无学习计划，请先创建」；有计划未确认 → 409「请先确认计划」；计划全部完成/掌握 → 空任务列表 + 说明 note
- 基础设施修复：SQLite 默认不启用外键约束，此前各表声明的 ON DELETE CASCADE 实际未生效；在统一引擎与测试引擎连接时开启 PRAGMA foreign_keys=ON，使迁移声明的外键行为真正生效（数据完整性加固，不改变业务语义）
- 测试：pytest 89/89 通过（新增 24：模型 6 例——关系/唯一约束/状态 CHECK/级联删除；接口 18 例——生成/防重复/滚动追赶/同天排除已完成/排除已掌握/全部完成 note/开始学习/幂等开始/完成/重复完成 409/完成后不可开始/未开始直接完成/调整计划后旧任务同步新版本/详情/404/409）；真实服务全流程 curl 验证后演示数据已清理
- 零新增依赖

**验收标准对照**：首页能够自动获取当天任务 ✅（GET /daily-tasks/today 实测生成 3 个任务，含知识点与章节信息）；同一天重复打开不会重复生成 ✅（第二次请求 generated=false，任务 id 一致）；用户完成任务后状态正确 ✅（任务 completed + 完成时间、计划项目同步 completed、知识点 pending_verification）；学习进度没有被错误标记为 mastered ✅（实测 01-03 → pending_verification、01-04 → learning，mastered 字段均为空）

---

## 阶段 7：模型接入和系统设置

**目标**：实现多模型兼容（统一 LLM Provider）。

任务要求（原文摘要）：
支持 DeepSeek、通义千问、OpenAI 兼容接口、自定义兼容接口。实现添加/编辑/删除模型配置、设置默认模型、测试连接、获取模型基本信息、流式输出、超时处理、统一错误处理。配置字段：provider、base_url、api_key、model_name、temperature、max_tokens、timeout。安全要求：API Key 不得明文展示、日志不得记录完整密钥、密钥加密保存、未配置模型时明确提示、不允许假模型响应冒充真实模型。验收：至少成功接入一种真实模型、能够测试连接、能够切换默认模型、能够正常进行一次流式对话、模型异常时能够明确提示。

**执行结果**（2026-11-07）：

- 新增 3 列（迁移 `d0b5a8fe0785`）：model_configs 增加 temperature / max_tokens / timeout（带服务端默认值，兼容已有行）
- 统一 Provider：`app/services/llm_providers.py` 预设 DeepSeek（api.deepseek.com/v1）、通义千问（DashScope 兼容模式）、OpenAI（api.openai.com/v1），自定义接口必须提供 base_url；四者统一走 OpenAI Chat Completions 协议
- 统一客户端（`app/services/llm_client.py`）：非流式（连接测试）+ 流式（SSE 解析增量文本）；超时→504 明确提示、网络不可达→502、401/403→「API Key 无效或无权限」、404→端点/模型错误、429→频率/额度、400→带服务商原因、5xx→服务异常、空回复→明确提示；错误信息中的密钥统一替换为 `***`
- 安全：API Key 以 Fernet 加密落库（`app/core/crypto.py`），接口只返回脱敏值（如 `sk-****abcd`）；加密密钥支持环境变量 `XIAOMA_SECRET_KEY` 或自动生成 `data/.secret_key`；解密失败返回明确提示要求重新填写；日志不记录完整密钥（实测日志无密钥）
- 接口 7 个：GET/POST /model-configs、GET/PUT/DELETE /model-configs/{id}、POST /model-configs/{id}/default、POST /model-configs/{id}/test；另有 POST /llm/chat/stream（SSE：start/delta/done/error 事件）
- 产品决策落地：删除默认模型后保持无默认并提示；「获取模型基本信息」= 已保存配置信息查询；未配置默认模型流式对话返回 409「尚未配置默认模型，请先在系统设置中添加模型配置并设为默认」
- 测试：pytest 118/118 通过（新增 29：加密/脱敏/密钥轮换/密钥文件 5 例；配置 CRUD/默认切换/删除默认/校验/脱敏 14 例；连接测试成功/401/超时/不可达/空回复/错误脱敏/自定义端点 7 例；流式成功/无默认/指定配置/服务商错误/空回复/超时/参数校验 7 例）
- 真实服务验证：已配置验证配置 → 响应脱敏、数据库密文、日志无密钥、删除默认后无默认；**真实请求 DeepSeek 已连通**，无效 Key 返回明确 401 提示（连接测试与流式 error 事件均正确）
- 真实模型验收（2026-11-07 补验）：用户提供 DeepSeek Key 后，连接测试 ok=true（实测 902ms，回复 OK）；流式对话返回 25 个 delta 事件并正常 done，输出真实内容（「Python 是一种简洁易读、用途广泛的通用高级编程语言…」）；响应与日志均不含密钥原文
- 零新增业务依赖（新增 cryptography 用于加密，httpx 由测试依赖转为运行时依赖）

**验收标准对照**：至少成功接入一种真实模型 ✅（DeepSeek 真实调用，连接测试与流式对话均成功）；能够测试连接 ✅（真实成功 + 401/超时/不可达/空回复自动化测试）；能够切换默认模型 ✅（同一时刻仅一个默认，真实配置实测来回切换）；能够正常进行一次流式对话 ✅（真实 DeepSeek 流式输出 25 个增量事件并正常结束）；模型异常时能够明确提示 ✅（超时/不可达/密钥无效/空回复均有明确中文提示，真实 401 实测）

---

## 阶段 8：AI 教学与聊天历史

**目标**：实现可以持续学习的 AI 教学工作台。

任务要求（原文摘要）：
数据库增加 conversations、messages、learning_sessions。实现新建聊天会话、查询聊天历史、继续已有会话、删除会话、保存用户消息、保存 AI 回复、关联学习任务、关联知识点。AI 教学能力：概念解释、分步骤讲解、举例、根据用户基础调整难度、解释代码、分析代码错误并提出修改建议。V1.0 不执行用户代码。要求：每次对话读取必要的学习档案和当前知识点；对话历史必须持久化；新建会话不能覆盖旧会话；模型失败时不能伪造回复；支持流式输出。验收：对话正常、刷新页面后历史仍存在、可以继续历史会话、AI 能够结合当前学习知识点回答。

**执行结果**（2026-11-07）：

- 新增 3 表（迁移 `e8b1c4d7a902`）：conversations（用户、标题、会话级知识点/每日任务关联、软删除字段）、messages（角色/内容/completed|error 状态/失败原因/模型名，CHECK 约束）、learning_sessions（与对话 1:1 唯一约束、用户、知识点/任务、开始/最后活动时间、消息数）
- 会话级关联（产品决策）：创建会话时可传 knowledge_point_code / daily_task_id；只传每日任务时自动关联该任务的知识点；两者不匹配返回 422；关联在会话内所有消息间共享
- 5 个接口：POST /conversations（新建）、GET /conversations（历史列表）、GET /conversations/{id}（详情 + 全量消息）、DELETE /conversations/{id}（**物理删除**）、POST /conversations/{id}/messages/stream（SSE 流式教学）
- LangGraph 1.2.20（产品决策本阶段引入）：单节点 Teaching 子图（`app/services/teaching_graph.py`），节点内调用统一 LLM Provider，经 `get_stream_writer()` / `stream_mode="custom"` 输出增量文本
- 教学提示词（`app/services/teaching_prompt.py`）：每轮从数据库读取 user_profiles（目标/基础/每日时长/偏好）、当前知识点（名称/章节/难度/目标/时长/掌握标准/前置）、每日任务与 learning_profiles 掌握状态；明确要求概念解释、分步骤讲解、举例、代码解释、错误分析，并按 L0/L1/L2 调整难度；明确 V1.0 不执行代码、不得声称运行结果、不得仅凭聊天判定掌握
- 持久化与失败处理（产品决策）：每轮用户消息立即保存；流式成功保存 status=completed 的助手消息；模型错误/空回复/中断保存 status=error 的助手消息（保留已生成部分文本 + 明确原因），失败回复不进入后续模型上下文；未配置默认模型在开始流式响应前返回 409，且不保存本轮用户消息
- 上下文：每轮携带最近 20 条有效消息（失败回复与空消息排除），继续会话时按时间顺序带入历史；会话标题未提供时由首条用户消息生成（24 字截断）
- 测试：pytest 145/145 通过（新增 27：模型关系/约束/1:1/级联 6 例；会话创建/关联/校验/不覆盖 7 例；流式成功与持久化/继续上下文/知识点与档案提示词/任务上下文 4 例；失败部分内容/空回复/HTTP 错误/无默认模型 4 例；删除/隔离/404/空消息/标题 6 例）
- 真实服务验收（DeepSeek）：两轮真实对话（第一轮概念讲解 + 举例，回复明确围绕当前知识点「什么是编程与 Python」；第二轮逐行解释 `age = 18 / print(age)` 并分析大写变量名问题）；刷新后 4 条消息完整；learning_sessions 消息数=4；新建第二个会话后旧会话历史未变；删除临时会话后旧会话可正常访问；响应无密钥；验收后清理会话数据

**前端接入补全**（2026-11-07，产品负责人要求“优先接入前端 AI 教学工作台，删除会话需要物理删除”）：

- 工作台 `/workspace`：会话列表、新建对话、切换会话、SSE 流式渲染（start/delta/done/error）、失败消息明确标识（保留已生成部分与失败原因）、上下文卡片、自动滚动；删除会话二次确认
- 入口：首页每日任务“让 AI 讲解”（`?daily_task_id=`）与课程学习页知识点“向 AI 提问”（`?knowledge_point_code=`）直接进入工作台并携带上下文；未指定上下文时为“通用问答”
- 聊天历史 `/chat-history`：查看、继续、永久删除历史会话
- 删除方式由软删除改为**物理删除**：会话、消息、学习会话一并移除，其他会话不受影响；自动化测试断言删除后数据库无残留
- 后端启用 CORS：localhost/127.0.0.1 任意端口默认允许，其他来源用 `CORS_ALLOW_ORIGINS` 配置；覆盖流式 POST 预检
- 首条消息前懒创建会话；流开始前被拒绝（如未配置默认模型，HTTP 409）时回滚乐观消息、恢复草稿与上下文，并删除刚创建的空会话
- 测试：后端 pytest 149/149 通过（新增 CORS 4 例，删除测试改为断言物理删除）；前端 `npm run lint`、`npm run build` 通过；无头 Edge + CDP 实测真实 DeepSeek 流式对话/刷新历史/继续会话/失败模型标识/物理删除/任务与知识点入口/409 处理
- 零新增前端依赖（原生 fetch + ReadableStream 解析 SSE）

**验收标准对照**：对话正常 ✅（真实 DeepSeek 两轮流式对话，start/delta/done 事件完整；前端工作台实时渲染）；刷新页面后历史仍存在 ✅（重新查询详情返回持久化消息，前端刷新后完整展示）；可以继续历史会话 ✅（工作台/聊天历史均可继续，后端携带历史上下文）；AI 能够结合当前学习知识点回答 ✅（系统提示词注入当前知识点/学习档案/掌握状态，真实回复围绕当前知识点）；删除会话 ✅（物理删除，数据库无残留）

---

## 阶段 9：测验、评分与错题本

**目标**：建立可信的学习掌握验证机制。

任务要求（原文摘要）：
数据库增加 question_bank、quiz_attempts、quiz_answers、mistakes、review_tasks。支持单选、多选、判断、填空、简答、代码分析、代码编写题（仅文本分析，不执行代码）。实现按章节、知识点、学习阶段生成测验、提交答案、自动评分、保存答题记录、错题记录与错题复习。题目来源为人工审核的内置题库与 AI 生成变式题；AI 题必须验证题目格式、正确答案、解析内容、知识点归属与学习范围，无法验证的题目不得进入正式测验。掌握状态规则：用户完成任务不等于掌握；只有满足后端规定的测验条件才允许标记为 mastered；主观题必须保留评分依据；不得只根据一次简单对话判断掌握。验收：题目与已学知识点匹配；答案可提交评分；错题可保存；复习任务可生成；未学习知识点不会进入正式测验。

**技术决策与产品口径**（2026-11-07）：

- 题量目标按 PRD 6.2：知识点测验 5 题、章节测验 10 题、阶段综合测验 30 题；实际题量受当前题库可用题数限制，不重复出题。
- 掌握判定（PRD 6.4 由后端明确规则）：**仅知识点测验**可更新掌握状态，且必须同时满足「有效题量 ≥ 3」「全部题目通过」「百分制得分 ≥ 90」；章节/阶段测验只记录成绩，不改变掌握状态。90 分不单独构成掌握依据，完成任务与普通对话永不写入 mastered。
- 评分规则：每题满分 10 分；客观题全对得满分、否则 0 分；主观题按参考答案关键词覆盖率评分，覆盖率 ≥ 80% 视为通过，评分依据（参考答案、命中/缺失关键词、比例）持久化到 quiz_answers。
- 复习调度（PRD 6.5）：首次答错 stage=0，1 天后复习；连续答对按 1→3→7→14 天推进，stage=4 标记错题 resolved；答错重置 stage=0、间隔回到 1 天；允许未到期提前复习，提前答对同样推进间隔；每次复习保存为 scope_type=review 的独立 QuizAttempt/QuizAnswer，保留历史。
- AI 变式题：仅以客观题作为源题，生成后依次做确定性结构校验、独立复核调用（使用默认模型二次作答，不额外引入模型）、正确答案比对；仅当格式/答案/解析/知识点归属/学习范围全部通过才以 `ai_validated` 落库并进入组卷；任何一步失败都不落库。未配置默认模型、调用失败或全部未通过时降级内置题库，并在测验 `ai_note` 中明确说明。
- 内置题库：本阶段开发期整理 31 个知识点 × 3 题 = 93 题，逐题程序校验（知识点归属、标准答案结构、解析长度、主观题关键词均须出现在参考答案中）；**未声称已完成产品负责人人工审核**，题库说明明确标记建议抽检复核后再作为正式发布内容。

**执行结果**（2026-11-07）：

- 新增 5 表（迁移 `5a9439936da5`）：question_bank、quiz_attempts、quiz_answers、mistakes、review_tasks；包含题型/来源/状态/范围类型 CHECK、用户+题目错题唯一约束、复习任务与错题/用户外键、常用查询索引
- 后端分层：QuestionRepository / QuizRepository / MistakeRepository / ReviewTaskRepository；QuizService / ReviewService / AiQuestionService；API 路由 quizzes / mistakes / reviews；组卷、评分、错题、复习均不经过 Agent，Agent 后续只能调用 Service
- 8 个接口：GET /quizzes/eligibility、GET/POST /quizzes、GET /quizzes/{id}、POST /quizzes/{id}/submit、GET /mistakes、GET /reviews/tasks、POST /reviews/tasks/{id}/submit；测验详情在提交前不返回答案/解析
- 可测范围：eligibility 与组卷均只读取 `learning / pending_verification / mastered / review_due` 状态知识点；未学习知识点返回 400「该知识点尚未学习，不能进行正式测验」，章节/阶段范围自动排除未学习知识点；阶段范围要求已确认的当前学习计划
- 组卷：知识点轮转选题保证覆盖面，同组内随机、最终随机排序；目标题量 5/10/30；提交时要求题目集合完全匹配，逐题评分、写入答题记录、错题收录与复习任务生成在同一事务提交
- 内置题库：`python -m app.cli seed-questions` 幂等写入 `q-{知识点code}-{序号}`；题型覆盖单选 25、多选 13、判断 12、填空 12、简答 12、代码分析 6、代码编写 13；只允许更新内置题，不覆盖 AI 题
- 前端：`/quiz` 测验中心（范围切换、AI 变式题数量 0–5、7 题型答题、提交评分、掌握判定、AI 说明、历史记录与详情）；`/mistakes` 错题本（待复习任务、到期/未到期、筛选待复习/已解决/全部、上次答案与正确答案、解析、复习面板、复习结果与下次复习时间）；复用 AnswerInput / QuestionResult 组件；零新增前端依赖
- 测试：后端 pytest 183/183 通过（新增 34：评分规则 7、题库种子 6、AI 生成验证 7、测验 API 9、复习 API 5）；前端 `npm run lint`、`npm run build` 通过
- 真实服务验收：创建并确认临时学习计划 → 开始每日任务（learning）→ 组卷 3 题 → 全错提交 score=0、mastery=false、生成 3 条错题与 3 个 1 天后复习任务 → 复习答对推进到 3 天、提前复习再答对推进到 7 天、另一题答错重置为 1 天 → 全对重测 score=100、mastery=true、学习档案状态变为 mastered → 未学习知识点 400、章节/阶段测验 201 → DeepSeek 实测 AI 变式题请求 1 道、通过验证 1 道、耗时约 4.6s → 验收后清理临时计划/任务/学习档案/测验/错题/复习记录与 AI 题，题库恢复 93 道内置题
- 前端实测（2026-11-07 补验）：无头 Edge + CDP 从空状态开始，完整走通 `/quiz` 开始测验 → 3 题作答 → 提交（得分 33.3，掌握判定正确展示）→ `/mistakes` 显示 2 个复习任务与 2 张错题卡 → 进入复习 → 提交 → 复习结果、解析与下次复习时间正常显示；两页控制台无运行时错误；验收后再次清理测试数据
- 未新增后端或前端业务依赖（AI 复核复用已有统一 LLM Provider 与 httpx）

**验收标准对照**：测验题目与已学知识点匹配 ✅（范围只读已学习状态，未学习知识点 400；章节/阶段排除未学）；答案可以提交和评分 ✅（7 题型逐题评分，测试与真实提交通过）；错题能够保存 ✅（答错自动写入 mistakes，保留答案/正确答案/解析/评分依据）；复习任务能够生成 ✅（首次答错生成 1 天后任务，1/3/7/14 天推进、答错重置、复习历史保留）；未学习知识点不会进入正式测验 ✅（eligibility 不返回，直接组卷返回 400）

---

## 阶段 10：LangGraph Agent

**目标**：把已有业务功能组织成可靠的 AI 学习工作流。

任务要求（原文摘要）：
先检查之前完成的 API 与 Service，不重复开发已有业务。采用一个主 Agent，内部包含 Planning / Teaching / Quiz / Review / Resource 五个子图。主流程：用户输入 → 意图识别 → 读取学习上下文 → 路由子图 → 调用工具 → 整理回答 → 保存聊天记录 → 返回结果。要求：Agent 不直接访问数据库；所有数据修改通过 Service；使用结构化状态；每个子图有明确输入和输出；支持超时和异常处理；工具调用失败不能返回虚假成功；重要业务操作需要后端验证；记录 Agent 执行日志但不泄漏密钥。测试场景：今天应该学什么、解释 Python 变量、查看学习进度、为当前章节生成测验、分析错题、调整学习计划、模型不可用时如何提示。验收：主 Agent 正确识别常见意图；子图调用正确业务服务；不会无响应或无限等待；不会把错误数据当成真实数据；历史聊天正常保存。

**技术决策与实现口径**（2026-11-07）：

- 复用现有 API/Service：阶段 5~9 的计划、任务、课程、测验、错题、复习、档案业务不重复实现；Agent 新增 `app/agent/`，只作为编排层。
- 主 Agent 为 LangGraph `StateGraph`：`recognize_intent → load_context → route → 五个子图之一 → finalize`。状态为结构化 `AgentState`（用户消息、历史消息、ChatContext、LearningContext、IntentResult、子图名、工具结果、回复、是否流式、结果状态）。
- 五个子图均为独立编译的 LangGraph，输入/输出为 `AgentState` 子集：
  - Planning：today_tasks / progress / plan_overview / adjust_plan；
  - Teaching：复用阶段 8 教学子图（`build_teaching_graph`），转发模型增量；
  - Quiz：generate_quiz / quiz_history；
  - Review：analyze_mistakes；
  - Resource：search_resources。
- 意图识别为确定性规则（不额外调用模型），顺序覆盖计划调整、错题、测验、进度、资源、今日任务、计划查看；未命中时按教学问题处理。教学兜底置信度 0.35，返回值包含匹配关键词与原因。
- 工具层 `AgentToolbox` 只调用 Service：DailyTaskService、PlanService、LearningOverviewService、CourseService、QuizService、ReviewService；不导入 Repository、不执行 SQL。
- 工具结果显式区分 `ok` / `unavailable` / `failed`：业务上可预期的不满足（暂无计划、未学习、未确认、题库不足）返回 unavailable 并给出明确说明；Service 异常返回 failed，子图抛出 `AgentRunError`，不组装成功回答。
- 数据修改全部经过 Service：计划调整调用 `PlanService.adjust_plan` 生成待确认草案，绝不自动确认；组卷调用 `QuizService.create_quiz`，只使用后端可测验范围；AI 变式题不在 Agent 中自动生成（仍由测验中心按需请求），避免聊天请求不可控耗时。
- 学习上下文通过 `AgentContextService` 使用 ProfileService / PlanService 读取；读取失败记录 notes 并明确说明，不伪造数据。
- 模型依赖调整：只有 Teaching 意图要求默认模型；计划/进度/测验/错题/资源查询在未配置模型时仍可正常工作。教学未配置模型仍在保存用户消息前返回 409。
- 嵌套子图的 LangGraph custom 事件不会自动冒泡；Teaching 节点显式取得父图 `get_stream_writer()` 并作为 emit 传给子图，逐个转发模型增量。
- SSE 保持 `start` / `delta` / `done` / `error` 事件名，仅增加元数据：start 增加 `intent` / `sub_intent`，done 增加 `intent` / `sub_intent` / `subgraph` / `result_status`；非教学子图 `model` 为 null。非教学回复的 `model_name` 保存为 null。
- 超时：新增 `XIAOMA_AGENT_TIMEOUT_SECONDS`（默认 120 秒），用 `asyncio.timeout` 包住整个图执行；超时、空回复、Agent 异常均保存 `status=error` 助手消息并发送 `error` 事件；客户端断开保留已生成部分并标记中断。
- 日志：`xiaoma.agent` 记录会话 ID、意图、子图、工具名、状态、耗时；不记录用户消息、系统提示词或密钥。启动时配置根日志级别，确保 INFO 执行日志实际落盘。
- 无数据库迁移、无新增依赖。阶段 8 的 `test_task_context_included_in_prompt` 消息由「今天学什么？」改为教学类问题，避免与新意图路由冲突，任务上下文断言保留。

**执行结果**（2026-11-07）：

- 新增 `backend/app/agent/`：`contracts.py`（结构化状态/工具结果/上下文快照）、`intent.py`（确定性意图识别）、`context.py`（Service 读取学习上下文）、`tools.py`（Service 工具层 + 状态与耗时日志）、`graph.py`（主 Agent 图）、`runner.py`（AgentService/AgentRun、超时、事件、持久化入口）、`subgraphs/`（planning / teaching / quiz / review / resource）。
- 新增 `LearningOverviewService` 与 `LearningOverviewOut`：只读聚合档案、当前计划、掌握统计、测验记录、错题与到期复习，供 Agent 进度查询使用；不新增数据库表。
- 新增 `CourseService.search_learning_resources` 与 `KnowledgePointResourcesOut`：只检索数据库已登记资源，支持关键词与当前知识点回退，不联网、不生成链接。
- 修改 `ConversationService`：`ChatContext` 增加 `learning_status`；`llm_request` / `model_name` 允许为空（非教学意图）；`prepare_chat` 增加 `require_llm`；`complete_assistant_message` / `fail_assistant_message` 支持显式 model_name 覆盖。
- 修改对话流式接口：改用 AgentService/AgentRun；保留原有 SSE 契约、LlmError 处理、客户端断开与保存失败处理，新增意图/子图元数据；非教学回答不显示模型名。
- 修改 `teaching_graph.py`：`_teach_node` / `build_teaching_graph` 支持显式 emit；新增 `app/agent/subgraphs/teaching.py` 作为 Teaching 子图包装。
- 前端仅更新 `lib/types.ts` 的 SSE 元数据类型（`model` 允许 null，新增 intent/subgraph/result_status）；无需新增页面或依赖。
- 测试：后端 pytest **196/196** 通过（新增 13：意图识别 1、验收场景 8、异常 3、资源 1）；前端 `npm run lint`、`npm run build` 通过。
- 真实服务验收（DeepSeek 默认模型）：
  - 「今天应该学什么？」→ planning/today_tasks，返回真实今日任务，model=null；
  - 「查看我的学习进度。」→ planning/progress，统计随任务完成/测验/错题实时变化；
  - 「推荐 Python 变量的学习资料」→ resource，返回课程库已登记文档链接；
  - 未学习时「为当前章节生成测验。」→ result_status=unavailable，明确说明原因；完成学习后重新请求 → quiz/chapter，生成 3 题、30 分真实测验记录；
  - 全错提交后「分析我的错题。」→ review，显示 3 道待复习、知识点分布、题型分布与复习任务；
  - 「调整我的学习计划，每天学习 30 分钟，期望 20 天完成。」→ 生成版本 2 待确认草案，当前生效版本仍为版本 1；
  - 「解释 Python 变量。」→ teaching，真实 DeepSeek 流式 300+ delta，结合当前知识点与掌握状态作答；start/done 携带模型名；
  - 历史消息全部持久化，非教学回答 model_name=null；运行日志包含 agent run start/done 与工具状态，`sk-` 出现次数为 0；
  - 验收后清理临时档案/计划/任务/学习档案/测验/错题/复习/会话，数据库恢复至验收前状态（题库 93 题、模型配置保留）。

**验收标准对照**：主 Agent 能够正确识别常见意图 ✅（7 个验收场景 + 计划查看/资源检索的单测与真实请求均路由正确）；子图能够调用正确的业务服务 ✅（Planning→DailyTask/Plan/Overview，Quiz→QuizService，Review→ReviewService，Resource→CourseService，Teaching→LLM）；不会出现无响应或无限等待 ✅（整体超时 + 模型超时 + 空回复错误 + 流式兜底，测试覆盖慢模型）；不会将错误数据当成真实数据 ✅（工具 unavailable/failed 明确区分、失败保存 error、进度/计划/测验均来自真实 Service，资源不编造）；历史聊天能够正常保存 ✅（用户与助手消息持久化、失败保留部分内容与原因、非教学 model_name=null、真实请求后 GET 历史完整）。
