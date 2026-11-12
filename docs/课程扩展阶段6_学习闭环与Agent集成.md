# 课程扩展阶段 6：课程体系接入学习闭环与 LangGraph Agent 集成

> 完成日期：2026-11-08
> 前置阶段：阶段 5（知识点掌握度与学习诊断升级，迁移 `d8cfe871faa5`）
> 本阶段迁移：`7e6ec48dafbe`
> 状态：**停在阶段 6**，等待阶段 7 指令

---

## 一、目标与边界

把已建成的 7 门课程目录、6 门正式教材与知识点级掌握度模型接入 V1.3 学习闭环：

**学习目标 → 入学诊断 → 学习计划 → 每日任务 → AI 教学 → 练习和测验 → 学习档案更新 → 动态计划调整 → 复习任务**

本阶段不改变技术栈、不删除既有功能、不让 Agent 直接访问数据库。所有业务读写继续走 `API → Service → Repository`，所有数据库结构变化继续由 Alembic 管理。

### 正式课程发布口径（阶段 6 起生效）

| 课程 | 发布状态 | 能否进入正式学习计划 |
| --- | --- | --- |
| `python-basics` | `published` | 是（阶段 3 教材） |
| `python-advanced` / `python-database` | `published` | 是（阶段 4A 教材） |
| `fastapi-backend` | `published` | 是（阶段 4B 教材） |
| `llm-api` | `published` | 是（阶段 4C 教材） |
| `langgraph-agent` | `published` | 是（阶段 4D 教材） |
| `software-engineering-deploy` | `draft` | 否（仍为 8 章 28 课时空目录） |

判定集中在 `CoursePublicationService.require_published()`：

- 课程 `publish_status != "published"` → `409`，草稿课程不能进入正式计划；
- 知识点没有归属的、未软删除的真实课时，或课时/章节/课程归属不一致 → `422`；
- 课时内容的 `status` 若为 `draft` → `422`；内容为 `reviewed` / `published` 视为正式教材；
- 课时尚无正文时允许排期，但在 `notes` 中明确标注「内容待补充」，**不伪造教材**。

开发库已执行 `python -m app.cli seed-catalog` 同步发布状态；该命令在副本上试运行比对过：只改 `publish_status`，107 个章节标题、190 个课时标题/时长与全部业务表行数零变化。

---

## 二、完整调用流程

### 2.1 主链路（前端 → API → Service → 数据）

```
① 学习目标
   PUT /api/v1/profile                     → ProfileService.update_profile
   （写入 learning_goal / current_level / daily_study_minutes）

② 入学诊断与跳级验证
   POST /api/v1/diagnosis                  → DiagnosisService（6 维 / 31 锚点）
   POST /api/v1/diagnosis/placement/plan  → 生成诊断测验计划
   POST /api/v1/diagnosis/placement       → QuizService.create_quiz(purpose=placement)
   POST /api/v1/quizzes/{id}/submit       → MasteryService（写 placement 证据 → MASTERED）

③ 学习计划（八类输入）
   POST /api/v1/plans                     → PlanService.create_plan
        ├─ CoursePublicationService.require_published(course_code)
        │    └─ CourseRepository.get_course_knowledge_points_with_lessons()
        ├─ MasteryService.mastered_kp_codes()       （只采信掌握证据）
        ├─ plan_scheduler.build_schedule / validate_schedule
        ├─ PlanContextService.collect(...)          （八类输入快照）
        │    ├─ CourseCatalogService.get_learning_path() → 补学提示
        │    ├─ MasteryService.review_suggestions()      → 复习清单
        │    ├─ QuizRepository.list_attempts()           → 最近测验表现
        │    └─ MasteryRepository.count_evidence_by_source("placement")
        └─ LearningPlanVersion(plan_context=...)          （写入快照，可审计）
   POST /api/v1/plans/{id}/confirm        → 版本生效（未确认不改变当前安排）

④ 今日任务（首页显式两步走）
   GET  /api/v1/daily-tasks/today?generate=false   → DailyTaskService.read_today_tasks
        │  存在任务 → 直接返回（generated=false，不写任何数据）
        └─ 无任务 → 前端才调用 ↓
   POST /api/v1/daily-tasks/today/generate         → DailyTaskService.generate_today_tasks
        ├─ 先查后生成（幂等）
        ├─ CoursePublicationService.resolve_task_refs(kp)
        │    校验并固化 course_id / module_id(chapter_id) / lesson_id / knowledge_point_id
        └─ DailyTaskRepository.add_tasks()（唯一约束 user_date_kp + IntegrityError 回滚兜底）
   GET  /api/v1/daily-tasks/{id}          → 任务详情（含四 ID 引用）
   POST /api/v1/daily-tasks/{id}/start    → MasteryService.start_learning
   POST /api/v1/daily-tasks/{id}/complete→ MasteryService.report_self_completed（只写自述证据）

⑤ AI 教学
   POST /api/v1/conversations             → ConversationService（绑定知识点/每日任务）
   POST /api/v1/conversations/{id}/messages/stream
        → 主 Agent 意图识别 → Teaching Subgraph
             ├─ load_course_material 节点：
             │    AgentToolbox.get_knowledge_point() → CourseService.get_knowledge_point()
             │    AgentToolbox.get_lesson()          → CourseService.get_lesson()
             │    build_course_material_section()    → 注入 system prompt
             └─ teach 节点：build_teaching_graph(system_prompt + 课程库内容) → SSE delta

⑥ 练习和测验 / ⑦ 学习档案更新
   POST /api/v1/quizzes                   → QuizService.create_quiz（内置已验证题库）
   POST /api/v1/quizzes/{id}/submit       → QuizService.submit_attempt
        ├─ 评分 → MasteryService（写掌握证据 / 7 态状态机）
        ├─ 答错 → 错题本 + 间隔复习任务（ReviewService）
        └─ 完成时同步计划项目 completed
   GET  /api/v1/mastery                   → MasteryService.get_overview（7 态）
   GET  /api/v1/overview                  → LearningOverviewService.get_overview（旧档案视图）

⑧ 动态计划调整（提案 → 用户确认 → 生效）
   GET  /api/v1/plan-adjustments/signals → PlanAdjustmentService.get_signals
        └─ PlanSignalService.collect()（六类信号，全部基于真实数据）
   POST /api/v1/plan-adjustments/proposals → PlanAdjustmentService.propose
        └─ 只写 plan_adjustment_proposals(status=proposed)，**不产生任何计划版本**
   前端「学习计划」页展示 preview（当前值 → 建议值 + 影响清单 + 补学/复习清单）
   POST /api/v1/plan-adjustments/proposals/{id}/confirm
        └─ PlanService.adjust_plan() + PlanService.confirm_plan() → 新版本生效
   POST /api/v1/plan-adjustments/proposals/{id}/reject → 只改提案状态，计划保持原样

⑨ 复习任务
   GET  /api/v1/reviews/tasks             → ReviewService.list_tasks（真实错题任务）
   GET  /api/v1/mastery/review-suggestions → MasteryService.review_suggestions
   POST /api/v1/review-requests           → ReviewRequestService.request
        （按 user + kp + date 幂等；只记录申请，返回真实复习任务，不改掌握状态）
```

### 2.2 学习计划生成的八类输入（`learning_plan_versions.plan_context`）

| # | 输入 | 取自 | 在排期中的作用 |
| --- | --- | --- | --- |
| 1 | 用户学习目标 | `PlanCreate.learning_goal` | 写入版本，确认后用于目标变化检测 |
| 2 | 每日学习时间 | `PlanCreate.daily_study_minutes` | `build_schedule` 按分钟装填每一天 |
| 3 | 当前能力等级 | `PlanCreate.current_level` | 写入版本与快照，供前端展示 |
| 4 | 已掌握知识点 | `MasteryService.mastered_kp_codes()` | 有掌握证据才跳过基础教学 |
| 5 | 未掌握知识点 | 课程知识点 − 已掌握 | 排期范围 |
| 6 | 课程前置关系 | `CourseCatalogService.get_learning_path` + `kp.prerequisites` | `validate_schedule` 校验；未掌握只提示补学、不自动跳过 |
| 7 | 课程预计时间 | `Course.estimated_minutes` vs 知识点时长合计 | 偏差 >10% 时写入提示，排期按实际时长 |
| 8 | 用户测验表现 | `QuizRepository.list_attempts()` 最近 5 次 | 平均分 <60 时提示先复习；连续不通过触发调整信号 |

诊断影响计划的具体路径：`placement` 证据 → `MASTERED` → 进入 `mastered` 集合 → `build_schedule` 跳过；**仅自述完成不跳过**，仍安排基础教学。

### 2.3 今日任务的四 ID 与证据联动

`module_id` 对应需求里的 `CourseModule`，本项目复用既有 `chapters` 表（不新建同义表）。生成任务时由 `CoursePublicationService.resolve_task_refs()` 一次性校验并写入：

```
course_id → courses.id            （必须 published）
module_id → chapters.id           （必须属于该课程）
lesson_id → lessons.id            （必须与知识点同章节、未软删除）
knowledge_point_id → knowledge_points.id
```

任务输出新增 `course_refs`、`mastery_status`、`mastery_evidence_count`、`completion_note`。完成只写「用户自述完成」证据，**绝不写 `mastered`**；掌握状态只由测验 / 练习 / 诊断验证的证据推进。

---

## 三、AI 教学集成

### 3.1 教学前必须先取课程库内容

Teaching Subgraph 现在有两个节点：`load_course_material → teach`。前者经 `AgentToolbox` → `CourseService` 读取知识点详情与课时正文，用 `build_course_material_section()` 结构化转写后注入系统提示词；取不到内容时明确标注「该课时尚未录入正式教材内容；不要编造教材原文」，工具 `failed` 直接抛 `AgentRunError`，不把失败包装成成功回答。

系统提示词中的课程库段落带 `【课程库内容】（以下全部来自课程库 Service，是本次讲解的事实依据）`，并按 15 个内容模块中的实际字段渲染（学习目标、核心概念、示例代码、逐行解释、常见错误、学习总结等）。

### 3.2 Agent 可以做 / 不可以做

| 可以做 | 不可以做（工具层与提示词双重拦截） |
| --- | --- |
| 解释课程内容、讲解代码、换不同例子 | 自己创建 / 发布正式课程 |
| 帮助用户理解报错与错误原因 | 修改课程依赖关系 |
| 按用户情况提供练习 | 自动跳过先修条件（未掌握先修只提示补学） |
| 给出学习总结 | 随意更新用户掌握状态（只如实转述系统查询结果） |
| 引导用户确认待确认的调整方案 | 未经用户确认保存或声称已保存学习计划修改 |

工具层用 `FORBIDDEN_TOOL_NAMES` 明确列出 12 个禁止入口（`create_course`、`create_lesson`、`create_knowledge_point`、`update_publish_status`、`add_prerequisite`、`remove_prerequisite`、`skip_prerequisite`、`grant_mastery`、`set_mastery_status`、`confirm_plan`、`confirm_proposal`、`adjust_plan`），测试逐个断言它们既不在工具清单里、也不是 `AgentToolbox` 的方法。

---

## 四、Agent 工具列表

工具清单由 `app/agent/tools.py` 的 `AGENT_TOOL_SPECS` / `LEGACY_TOOL_SPECS` 声明，`tool_specs()` 输出可序列化清单（文档与测试共用）。共 **16 个**：需求要求的 9 个 + 原有闭环的 7 个兼容工具。

### 4.1 阶段 6 必备 9 个工具

| 工具名 | 方法 | 调用的 Service | 写操作 | 说明 |
| --- | --- | --- | --- | --- |
| `get_course` | `get_course` | `CourseService.get_course_detail` | 否 | 读取已发布课程结构与前置关系 |
| `get_lesson` | `get_lesson` | `CourseService.get_lesson` | 否 | 读取课时教学内容和所属章节 |
| `get_knowledge_point` | `get_knowledge_point` | `CourseService.get_knowledge_point` | 否 | 读取目标、前置、练习与所属课时 |
| `get_user_learning_progress` | `get_user_learning_progress` | `LearningOverviewService` + `MasteryService` | 否 | 学习进度、7 态掌握度、复习建议 |
| `get_today_tasks` | `get_today_tasks` | `DailyTaskService.get_today_tasks` | 否 | 当日任务（含真实课程引用） |
| `submit_exercise` | `submit_exercise` | `MasteryService.submit_exercise` | **是** | 练习答案 → 练习记录与掌握证据 |
| `submit_quiz_result` | `submit_quiz_result` | `QuizService.submit_attempt` | **是** | 评分 → 掌握证据 / 错题复习任务 |
| `request_review_task` | `request_review_task` | `ReviewRequestService.request` | **是** | 幂等写复习申请，不伪造复习任务 |
| `propose_learning_plan_adjustment` | `propose_learning_plan_adjustment` | `PlanAdjustmentService.propose` | **是** | 只生成待确认提案，不写任何计划版本 |

### 4.2 原有闭环兼容 7 个工具

| 工具名 | 方法 | 调用的 Service | 写操作 |
| --- | --- | --- | --- |
| `get_current_plan` | `get_current_plan` | `PlanService.get_current_plan` | 否 |
| `get_progress` | `get_progress` | `LearningOverviewService.get_overview` | 否 |
| `search_learning_resources` | `search_resources` | `CourseService.search_learning_resources` | 否 |
| `generate_quiz` | `generate_quiz` | `QuizService.create_quiz` | **是**（写测验记录） |
| `get_quiz_attempts` | `get_quiz_attempts` | `QuizService.list_attempts` | 否 |
| `get_mistakes` | `get_mistakes` | `ReviewService.list_mistakes` | 否 |
| `get_review_tasks` | `get_review_tasks` | `ReviewService.list_tasks` | 否 |

### 4.3 写操作的 Service 约束

`AgentToolbox` 不导入任何 Repository、不执行 SQL；4 个必备写工具各自只构造 Pydantic 入参并调用对应 Service。测试用 `monkeypatch` 替换 Service 方法，逐个断言工具确实委托到 Service 层、没有绕过。`propose_learning_plan_adjustment` 还带参数白名单，只接受 `learning_goal` / `daily_study_minutes` / `expected_duration_days`，其余键一律丢弃。

---

## 五、动态计划调整：六类触发信号

`PlanSignalService.collect()` 优先按真实数据判定，数值规则放在纯函数里（`consecutive_failures` / `is_downstream_mastery_signal`），不交给模型推断。

> **2026-11-08 独立验收修订**：调用方可通过 `declared_triggers` 补充调整线索。此前实现会把「仅声明、后端未实测达标」的条件混进 `signals`，措辞却宣称「全部基于真实数据」，且会凭声明自动追加 7 天缓冲。现已改为：声明类信号在 `detail` 统一标注「调用方声明，后端未实测到对应数据」并写出后端实测值；`summary` 分别统计「后端实测达标 N 项 / 调用方声明 M 项」；`suggest_changes()` 只接收实测达标信号，声明线索保留在 `preview.signals` 与 `triggers` 供用户判断，不会凭空改动计划参数。新增 `test_declared_only_signals_never_pretend_to_be_measured` 固化该约束。

| 触发条件 code | 判定依据 | 阈值 |
| --- | --- | --- |
| `consecutive_quiz_failures` | 最近连续已提交的非诊断测验得分低于 60 | ≥2 次 |
| `mastered_downstream_points` | 有掌握证据且仍排在后续计划日的知识点 | ≥2 个 |
| `weak_foundation` | `needs_review` 数量 >0 或存在薄弱项复习建议 | >0 |
| `learning_goal_changed` | 请求目标与当前生效版本不同 | 字符串不等 |
| `daily_minutes_increased` | 请求每日分钟数 > 当前版本 | 严格大于 |
| `review_requested` | 存在 `pending` 复习申请或调用方显式声明 | >0 |

建议参数由纯函数 `suggest_changes()` 生成：连续不通过 / 基础不足 / 请求复习时，在现有期望周期上预留 `REVIEW_BUFFER_DAYS = 7` 天缓冲（上限 3650 天）；调用方显式给出的参数优先。

**确认闸**：`propose()` 只写 `plan_adjustment_proposals(status=proposed)`，返回的 `requires_confirmation` 恒为 `True`，`resulting_version_number` 为 `None`，`note` 明确「尚未保存为学习计划」。只有 `POST /api/v1/plan-adjustments/proposals/{id}/confirm` 才会调用 `PlanService.adjust_plan()` + `confirm_plan()` 生成并生效新版本；`reject()` 只改提案状态。前端「学习计划」页新增提案区，展示触发信号、当前值 → 建议值、影响清单与确认/拒绝按钮；Agent 回复也只展示方案并引导用户确认。

---

## 六、数据模型与迁移

迁移 `7e6ec48dafbe`（`down_revision = d8cfe871faa5`）：

- 新增 `plan_adjustment_proposals`（提案状态 CHECK、触发条件 JSON、变更 JSON、预览 JSON、来源、确认/拒绝时间、生效版本号）；
- 新增 `review_requests`（`uq_review_requests_user_kp_date` 唯一约束、状态 CHECK、触发条件）；
- `learning_plan_versions.plan_context`（JSON，八类输入快照）；
- `daily_tasks` 新增 `course_id` / `chapter_id` / `lesson_id` 三个可空 FK 列与索引，SQLite 用 `batch_alter_table` 一次重建（首次直接 `create_foreign_key` 会抛 `NotImplementedError`）；
- `_backfill_daily_task_refs()` 按 `lesson_knowledge_points` 回填历史任务，老数据确无归属课时则保持 NULL，不猜测；
- `downgrade()` 用 batch 删除列，再按逆序删索引与两张表。

开发库处理：先在副本上试跑目录种子比对 → 发现 `alembic check` 检测到 `plan_context` 列漂移（版本号已 head 但列缺失，属阶段 6 迁移曾被部分执行的历史状态）→ 恢复 `data/backups/phase6-before.db`（`d8cfe871faa5`）后完整重放 `alembic upgrade head` → `alembic check` 输出 `No new upgrade operations detected.` → 再执行 `seed-catalog` 同步发布状态。最终 `integrity_check = ok`、`foreign_key_check = []`，7 课程 / 107 章 / 190 课时 / 194 知识点 / 162 内容 / 324 练习 / 1085 题全部保留。

---

## 七、测试结果

### 7.1 需求「七、测试」十项必测（`backend/tests/test_phase6.py`）

| # | 必测项 | 测试函数 | 结果 |
| --- | --- | --- | --- |
| 1 | 今日任务引用真实课程 | `test_today_tasks_reference_real_course_data` | ✅ |
| 2 | 不重复生成每日任务 | `test_today_tasks_are_not_generated_twice_in_one_day` | ✅ |
| 3 | 未掌握的先修知识可以提示补学 | `test_unmastered_prerequisites_prompt_remedial_not_skip` | ✅ |
| 4 | 已掌握的知识点不重复安排基础教学 | `test_mastered_points_not_scheduled_again` | ✅ |
| 5 | 诊断结果能够影响计划 | `test_placement_diagnosis_result_affects_plan` | ✅ |
| 6 | 测验结果可以影响后续复习任务 | `test_quiz_failure_affects_followup_review_tasks` | ✅ |
| 7 | Agent 能从课程库读取内容 | `test_agent_teaching_reads_course_library_via_service` | ✅ |
| 8 | Agent 写操作经过 Service | `test_agent_write_tools_delegate_to_service_layer` | ✅ |
| 9 | 学习计划调整需要确认 | `test_plan_adjustment_requires_explicit_confirmation` | ✅ |
| 10 | 原有学习闭环正常 | `test_original_learning_loop_remains_intact` | ✅ |

另加 6 项：课程库内容缺失时不编造、9 个工具清单完整且禁止入口不存在、草稿课程与无归属课时被拒绝、八因素快照完整、六类信号与纯函数规则、复习申请按用户+知识点+日期幂等。

```
$ cd backend && .venv/Scripts/python -m pytest tests/test_phase6.py --basetemp=.pytest-tmp-p6b -p no:cacheprovider -q
16 passed, 13 warnings in 17.42s
```

### 7.2 全量回归

| 范围 | 命令 | 结果 |
| --- | --- | --- |
| 后端全量 | `pytest tests --basetemp=.pytest-tmp-p6-full2 -p no:cacheprovider -q` | ✅ 442 passed |
| 前端 lint | `npm run lint` | ✅ 通过 |
| 前端类型 | `npx tsc --noEmit` | ✅ 通过 |
| 前端单元测试 | `npm test`（Vitest，5 个文件，含新增 `DashboardClient.test.tsx` 4 项） | ✅ 18 passed |
| 前端生产构建 | `npm run build` | ✅ 通过 |
| 迁移版本 | `alembic current` → `7e6ec48dafbe (head)` | ✅ |
| 模型漂移 | `alembic check` → `No new upgrade operations detected.` | ✅ |
| 数据库完整性 | `integrity_check = ok`、`foreign_key_check = []` | ✅ |

既有用例同步：`tests/test_course_catalog.py` 的发布状态断言改为 6 门已验收课程 `published`、`software-engineering-deploy` 保持 `draft`；`tests/test_agent_api.py` 的「调整计划」用例改为断言只生成 `proposed` 提案、确认接口调用后版本 2 才生效；「无参数调整」用例按阶段 6 新措辞同步。

### 7.3 本阶段修掉的真实缺陷

1. `AgentToolbox.propose_learning_plan_adjustment()` 算出参数白名单 `clean` 后没有传入 `ProposalCreate`，导致用户请求的每日时长 / 周期 / 目标被静默丢弃 → 已补 `**clean`，并加测试断言参数确实到达 Service。
2. 开发库 `learning_plan_versions.plan_context` 列缺失但版本号已 head 的迁移漂移 → 恢复迁移前备份并用 Alembic 完整重放，`alembic check` 零漂移。
3. `planning.py` 仍写「调整生成待确认草案」，与新语义（只生成提案、不写计划版本）不符 → 文档字符串与回复文案同步。
4. 前端首页仍用单次 `GET /today`（默认生成）→ 改为显式「`GET ?generate=false` → 无任务才 `POST /today/generate`」，并补 4 项组件测试。

---

## 八、手动验收方式

```bash
cd backend
.venv/Scripts/python -m app.cli init-db
.venv/Scripts/python -m app.cli seed-catalog      # 同步 6 门课程 published
uvicorn app.main:app --reload --port 8000
cd ../frontend && npm run dev
```

1. 首页打开两次：网络面板应只见一次 `GET /api/v1/daily-tasks/today?generate=false`（无任务时再跟一次 `POST /today/generate`）；第二次打开不重复生成，任务 ID 不变。
2. 任务卡片显示「教材课时」、`course_refs` 四个 ID 与「掌握状态 / 证据条数」；完成一个任务后状态为「用户自述完成」，不是「真正掌握」。
3. 「学习计划」页查看 `plan_context`：目标、每日时间、能力等级、已/未掌握、前置、预计时长、最近测验、诊断证据八类字段齐全；未掌握的入学知识点出现在 `remedial_kp_codes`，但课程知识点照常排期。
4. 在测验中心对一个知识点连续两次全错提交 → `GET /api/v1/plan-adjustments/signals` 出现「连续测验不通过」「基础能力不足」「请求复习」；`POST /api/v1/review-requests` 返回真实错题复习任务且重复调用 `created=false`。
5. 在「学习计划」页生成待确认方案 → 确认前 `GET /api/v1/plans/current` 的 `pending_version_number` 仍为 `null`、版本 1 参数不变；点「确认并生效」后版本 2 才出现。
6. 工作台对某知识点提问，检查模型请求的系统提示词包含「【课程库内容】」与该课时的真实「核心概念」；对话里要求「帮我创建一门课程 / 把先修跳掉 / 直接把计划改了」，Agent 应拒绝并引导确认。

---

## 九、边界与留给阶段 7 的接口

- `software-engineering-deploy` 仍是 `draft` 且无教材正文，按硬门槛不进入任何正式计划或每日任务。
- 课时未录入正文时允许排期，但明确标注「内容待补充」，系统不生成教材、不把空课时伪装成已发布内容。
- 复习申请只记录申请；没有真实错题时明确说明「暂无待复习错题任务」，不伪造任务、不改动掌握状态。
- Agent 永远拿不到 `confirm_plan` / `confirm_proposal` / `adjust_plan` 入口，确认动作只由用户通过 API 或前端按钮触发。
- 阶段 7 可直接复用：`GET /api/v1/plan-adjustments/signals`、`POST /api/v1/plan-adjustments/proposals`、`POST /api/v1/review-requests`、`GET /api/v1/daily-tasks/today?generate=false` 与 `plan_context` 快照。

详见 [README.md](../README.md) 与 [docs/开发进度与验收记录.md](开发进度与验收记录.md)。
