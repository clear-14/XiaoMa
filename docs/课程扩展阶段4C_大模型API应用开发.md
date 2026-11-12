# 课程扩展阶段 4C：Python 大模型 API 应用开发课程建设

> 状态：已完成（2026-11-08）。`llm-api` 由「8 章 28 课时空目录」重建为 **16 章 32 课时**的完整教材，
> 32 份正文、64 个练习、192 道测验题全部落库，内容状态 `reviewed`，等待人工终审后再逐节置 `published`。
> 本阶段只做课程内容，没有新增依赖、没有新增数据库迁移，也没有改动前端。

## 一、范围

| 课程 | code | 章 | 课时 | 时长 | 知识点 | 练习 | 测验题 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Python 大模型 API 应用开发 | `llm-api` | 16 | 32 | 20 小时 15 分钟 | 32 | 64 | 192 |

需求列出的 20 个主题全部有落点（其中「System Prompt 和 User Prompt」并入消息结构章用 1 节讲透，
「Token 和上下文窗口」与「调用费用和限制」合并为第 13 章 1 节，「API 超时和重试」与「模型调用异常处理」
合并为第 14 章 2 节），逐条对应见第四节。

## 二、章节与课时

| # | 章节 code | 章节 | 课时数 | 时长 | 课时 |
| --- | --- | --- | --- | --- | --- |
| 1 | `llm-api-01` | 大语言模型基本概念 | 2 | 60 分钟 | 模型如何生成文本：Token、概率与采样 / 能力边界、幻觉与人工兜底 |
| 2 | `llm-api-02` | 模型服务商与 OpenAI 兼容 API | 2 | 65 分钟 | 服务商生态与兼容协议 / Base URL、模型名称与请求响应结构 |
| 3 | `llm-api-03` | API Key 管理与安全 | 2 | 60 分钟 | Key 从哪里来、怎么存 / 泄漏处置、轮换与最小权限 |
| 4 | `llm-api-04` | Python 调用大模型 | 2 | 70 分钟 | 第一次调用：httpx 打通接口 / 封装可复用的模型客户端 |
| 5 | `llm-api-05` | 消息结构、System Prompt 与 User Prompt | 1 | 35 分钟 | 三种角色与提示分工 |
| 6 | `llm-api-06` | Prompt 设计 | 2 | 75 分钟 | Prompt 结构：目标、约束与输出格式 / Few-shot、边界条件与迭代评测 |
| 7 | `llm-api-07` | 多轮对话 | 2 | 70 分钟 | 对话状态与历史拼接 / 会话隔离与角色一致性 |
| 8 | `llm-api-08` | 上下文管理 | 2 | 80 分钟 | Token 预算与上下文裁剪 / 摘要压缩与长会话策略 |
| 9 | `llm-api-09` | Streaming 流式输出 | 2 | 80 分钟 | SSE 协议与增量解析 / 流式中断、错误与后端透传 |
| 10 | `llm-api-10` | JSON 结构化输出 | 2 | 80 分钟 | JSON 模式与 Schema 约束 / 校验失败与修复重试 |
| 11 | `llm-api-11` | Function Calling | 2 | 80 分钟 | 函数声明与调用返回 / 本地执行与结果回填 |
| 12 | `llm-api-12` | Tool Calling | 2 | 80 分钟 | 多工具路由与选择 / 工具循环、上限与失败处理 |
| 13 | `llm-api-13` | Token、上下文窗口与调用费用 | 1 | 40 分钟 | 用量统计、费用估算与限流 |
| 14 | `llm-api-14` | API 超时、重试与异常处理 | 2 | 80 分钟 | 超时预算与退避重试 / 异常分类与用户可见提示 |
| 15 | `llm-api-15` | AI 应用安全 | 1 | 40 分钟 | 提示注入、越权与数据泄漏 |
| 16 | `llm-api-16` | 综合项目：Python AI 对话助手 | 5 | 220 分钟 | 模型配置与项目骨架 / 消息管理与 API 调用 / 多轮上下文与上下文裁剪 / 流式输出与前端透传 / 错误处理、测试与交付 |
| — | 合计 | 16 章 | **32** | **20 小时 15 分钟** | — |

## 三、每节课的结构

沿用阶段 3 建立的 15 个内容模块，需求里的 10 个教学环节与列的对应关系不变：

| 需求环节 | 落库列 | 本阶段写作要求 |
| --- | --- | --- |
| 本节目标 | `learning_objectives` | 3—4 条动词开头的可检验目标 |
| 核心知识 | `concept_explanation` + `plain_explanation` | 概念清单 + 一段生活类比，两列不重复 |
| API 说明 | `syntax_explanation` | 请求字段 / 协议格式 + 参数含义 + 注意事项 |
| 完整代码示例 | `example_code` | 单文件可运行，全部示例代码通过 `compile` |
| 逐行解析 | `code_explanation` | 不少于 5 条，按代码块顺序说明「为什么这么写」 |
| 请求和响应示例 | `example_output` | 真实请求体 + 响应 JSON / 运行结果（概念类课时给出可复现输出） |
| 常见错误 | `common_mistakes` + `error_analysis` | 4—6 条真实会踩的坑 + 报错原文与成因 |
| 实战练习 | `beginner_exercises` + `advanced_exercises` | 入门照着改、进阶要组合前面知识 |
| 小测验 | `quiz_note` + `question_bank` | 说明题目构成，每节固定 6 题 |
| 学习总结 | `summary` + `next_lesson` | 3 句含记忆锚点，并指向下一节具体内容 |

每节课固定配 **2 个练习**（`exercises`，含参考答案与解析）+ **6 道测验题**（`question_bank`）：
2 道基础理解 + 2 道代码阅读 + 2 道应用练习；三类各 64 道，合计 192 道。六种题型全部出现
（代码理解 64、单选 32、编程思路分析 32、多选 24、代码补全 23、判断 17），难度不超课时一级
（入门课时允许出现进阶题，但不允许跨两级）。

## 四、需求主题 → 课时对应

| # | 需求主题 | 落地课时 |
| --- | --- | --- |
| 1 | 大语言模型基本概念 | `01-lesson-01`（token、概率与采样）、`01-lesson-02`（能力边界、幻觉与人工兜底） |
| 2 | 模型服务商和 API | `02-lesson-01`（服务商生态与兼容协议）、`02-lesson-02`（Base URL / 模型名 / 请求响应结构） |
| 3 | API Key 管理 | `03-lesson-01`（环境变量、`.env`、脱敏）、`03-lesson-02`（泄漏处置、轮换与最小权限） |
| 4 | Python 调用大模型 | `04-lesson-01`（httpx 首次调用）、`04-lesson-02`（封装客户端类） |
| 5 | OpenAI 兼容 API | `02-lesson-01`、`02-lesson-02`、`04-lesson-01`（同一套 `/chat/completions` + `messages`） |
| 6 | 消息结构 | `05-lesson-01`（system / user / assistant 三种角色）、`07-lesson-01`（历史拼接） |
| 7 | System Prompt 和 User Prompt | `05-lesson-01`（规则与需求的职责划分、越权指令的处理） |
| 8 | Prompt 设计 | `06-lesson-01`（目标 / 约束 / 输出格式四段结构）、`06-lesson-02`（Few-shot、边界条件与离线评测） |
| 9 | 多轮对话 | `07-lesson-01`（历史回传）、`07-lesson-02`（会话隔离与角色一致性） |
| 10 | 上下文管理 | `08-lesson-01`（token 预算与裁剪）、`08-lesson-02`（摘要压缩与长会话策略） |
| 11 | Streaming | `09-lesson-01`（SSE 与增量解析）、`09-lesson-02`（中断、错误与后端透传） |
| 12 | JSON 结构化输出 | `10-lesson-01`（JSON 模式与字段约束）、`10-lesson-02`（校验失败与修复重试） |
| 13 | Function Calling | `11-lesson-01`（函数声明与 `tool_calls`）、`11-lesson-02`（本地执行与结果回填） |
| 14 | Tool Calling | `12-lesson-01`（多工具路由与选择）、`12-lesson-02`（循环上限与失败处理） |
| 15 | Token 和上下文窗口 | `01-lesson-01`（token 是计费与窗口的单位）、`08-lesson-01`（预算）、`13-lesson-01`（用量与成本） |
| 16 | 调用费用和限制 | `13-lesson-01`（双单价计费、配额与限流） |
| 17 | API 超时和重试 | `14-lesson-01`（分项超时、指数退避、`Retry-After`） |
| 18 | 模型调用异常处理 | `14-lesson-02`（状态码分类、用户可见提示、`finish_reason`） |
| 19 | AI 应用安全 | `15-lesson-01`（提示注入、越权、数据泄漏与代码边界） |
| 20 | 综合项目：Python AI 对话助手 | `16-lesson-01` ～ `16-lesson-05`（见第五节） |

## 五、综合项目：Python AI 对话助手

需求列出的 6 个组成部分，按「一次只加一层」的顺序落在第 16 章，前后代码可以直接串成同一个项目：

| 需求组成部分 | 课时 | 本步交付 |
| --- | --- | --- |
| 模型配置 | `16-lesson-01` | `app/config.py`：从环境变量读 `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL`，启动即校验，`__repr__` 脱敏，`.env` 进 `.gitignore` |
| API 调用 | `16-lesson-02` | `app/models.py` + `app/client.py`：`Message` 模型与 `ChatClient.complete()`，超时分项设置、连接可复用 |
| 消息管理 | `16-lesson-02` | `Message.to_dict()` 只输出 `role` / `content`；`system()` / `user()` / `assistant()` 三个构造器 |
| 多轮上下文 | `16-lesson-03` | `app/session.py`：`Session.build()` 做「轮次 + token 预算」双重裁剪，整轮丢弃，预留输出预算 |
| 流式输出 | `16-lesson-04` | `app/stream.py`：SSE 逐行解析、坏帧跳过、`[DONE]` 结束；配合 `StreamingResponse` 与 `X-Accel-Buffering: no` 透传 |
| 错误处理 | `16-lesson-05` | `app/errors.py` + `complete_with_retry()`：状态码分类、可重试标记、有限重试；`tests/test_client.py` 4 项测试 |

**API Key 从环境变量读取**这条硬要求，落在三个地方，不靠口头约定：

1. `app/config.py` 里唯一入口是 `os.environ.get(...)`，缺变量抛 `ConfigError`；
2. 全部 32 节示例代码与语法说明里**没有**任何密钥字面量（`test_key_never_appears_in_course_code` 用
   `sk-[A-Za-z0-9]{16,}` 与 `api_key="..."` 两条正则扫描）；
3. `.gitignore` 屏蔽 `.env`、只提交 `.env.example`，并把「误提交后先轮换再清历史」写进正文与练习。

综合项目的示例代码按「第 1 步给出骨架、后续每步只贴增量」组织，每节课的 `example_output` 都是本机真实运行结果
（第 16 章的 5 段代码在本阶段开发机上逐一跑过：配置模块的两条路径、MockTransport 客户端、12 条历史裁到 6 条、
三段 SSE 增量、`pytest -q` 4 passed）；**课程不执行用户提交的 Python 代码**，只做文本与静态检查。

## 六、教材适用版本与技术规范

教材以「稳定的 OpenAI 兼容调用方式」为基础，服务商差异只作为独立示例出现：

| 项目 | 教材口径 | 落地方式 |
| --- | --- | --- |
| HTTP 客户端 | `httpx` **0.28** | 全部示例直接 `client.post("/chat/completions", json=payload)`，不依赖任何厂商 SDK |
| 认证 | `Authorization: Bearer <key>` | `04-lesson-01` 起统一写法，`key` 只来自环境变量 |
| 请求体 | `model` / `messages` / `temperature` / `max_tokens` | `02-lesson-02` 逐字段讲透；`stream`、`response_format`、`tools` 在对应章节增量引入 |
| 响应体 | `choices[0].message.content`、`finish_reason`、`usage` | `02-lesson-02` 讲结构，`13-lesson-01` 用 `usage` 算成本 |
| 流式 | `text/event-stream`、`data:` 帧、`[DONE]`、`delta.content` | `09-lesson-01` / `16-lesson-04` |
| 函数调用 | `tools` 声明 + `tool_calls` 返回 + `tool` 角色回填 | `11-lesson-01` ～ `12-lesson-02` |

**「不把某个服务商的临时参数写成所有模型都支持的统一规范」**落到三处：

1. `02-lesson-01` 用能力开关表（`PROVIDERS`）描述「哪些参数是该厂商可选能力」，示例里用 `supports_top_p`
   之类的布尔开关决定是否发送，而不是默认全发；
2. `14-lesson-01` 明确 `max_retries`、`backoff` **不是**协议字段，属于客户端实现，本课程用显式常量
   `MAX_RETRIES` + 自己的指数退避函数；只有 `Retry-After` 是服务端给的，优先采信；
3. 各厂商独有的能力（长文档、特定 JSON 模式变体）在正文里声明为「可选增强 + 必须有降级路径」，
   并配启动校验：配置了不支持该能力的服务商时，启动阶段就报错。

两个**未安装**的依赖按「原理用标准库 / 原生 HTTP 演示 + 注明生产建议」处理，不为教学引入新的运行依赖：

| 依赖 | 处理方式 |
| --- | --- |
| `openai` SDK | 全部示例改用 `httpx` 直接发 HTTP，既讲清协议本身，也避免「换个服务商就换一套 SDK」。正文注明「生产若用官方 SDK，字段语义与此一致」 |
| `tiktoken` | 用 `estimate_tokens()` 粗估（中文 1 字 1 token、其它 3 字符 1 token，向上取整），并明确「估算必须保守，`usage` 才是真值」；`13-lesson-01` 讲用真实 `usage` 校准系数 |

### 「不提前教学」怎么落地

两道防线，缺一不可：

1. **章节顺序**：`Bearer` / `choices` 最早第 2 章，`os.environ` 第 3 章，`httpx` 第 4 章，`json.loads` 第 5 章，
   `stream` / `event:` 第 9 章，`response_format` 第 10 章，`tools` / `tool_calls` 第 11 章，
   `max_retries` / `backoff` / `Retry-After` 第 14 章。
2. **自动检查**：`app/core/curriculum.py` 的 `LLM_SCOPE` 记录「术语 → 最早可出现章节」，审计第 8 项按章顺序重查；
   `test_no_late_terms_in_early_chapters` 用同一份表断言早期章节不出现后续术语（含代码与说明文字）。
   当前 13 个术语全部在引入章或之后出现，无一处提前。

## 七、先修关系

- 课程级：`llm-api` ← `python-advanced`（沿用阶段 2 的目录定义，未改动）。
- 入学知识点：全部指向 `python-basics-*`（`python-basics-02-06`、`python-basics-05-02`、`python-basics-06-03`），
  由 `test_entry_knowledge_points_from_basics` 校验。
- 知识点级：32 个新知识点串成一条先修链（`llm-api-01-01` → … → `llm-api-16-05`），
  由 `test_knowledge_point_prerequisites_follow_course_order` 与 `test_lesson_knowledge_point_links` 守住；
  审计第 10 项（学习计划可引用课时知识点）每次验收重查。

## 八、验收结果

需求没有给出编号验收项，本阶段按「章节 / 重点内容 / 综合项目 / 教材口径」四部分拆成 21 项自动化测试
（`backend/tests/test_phase4c.py`）：

| # | 验收点 | 验证方式 | 结果 |
| --- | --- | --- | --- |
| 1 | 章节完整 | 断言 16 章 / 32 课时、章序连续、课时难度合法 | 通过 |
| 2 | 20 个主题全覆盖 | `REQUIRED_TOPICS` 里 20 个主题必须出现在章或课时标题里 | 通过 |
| 3 | 综合项目 6 个组成部分 | 6 个关键字必须对应到第 16 章的 5 节课 | 通过 |
| 4 | 每节课有实质内容 | 15 个模块逐个非空且 ≥10 字；逐行解释 ≥5 条；示例输出 ≥10 字 | 通过 |
| 5 | 教材可经既有 API 读取 | `GET /api/v1/lessons/{code}/textbook` 的 10 个字段全部非空 | 通过 |
| 6 | 示例代码可运行 | 32 段代码全部 `compile` 通过 | 通过 |
| 7 | Key 不写进课程代码 | 全文扫描 `sk-[A-Za-z0-9]{16,}` 与 `api_key="..."` 字面量，均无命中；Key 课时必须出现 `os.environ` + `LLM_API_KEY` | 通过 |
| 8 | Key 课覆盖脱敏与仓库防护 | 出现 `.env`、`.gitignore`、`mask` | 通过 |
| 9 | 重点内容有代码落点 | 9 组关键课时分别断言 `Bearer` / `os.environ` / `data:` / `delta` / `response_format` / `tool_calls` / `Retry-After` 等 | 通过 |
| 10 | 以兼容协议为基础 | 全课程出现 `/chat/completions`、`Bearer`、`messages`、`choices`、`usage`、`finish_reason`、`delta`、`response_format`、`tool_calls` | 通过 |
| 11 | 服务商差异只作示例 | 服务商课时必须出现「不同 / 差异 / 各有」类表述，不做统一化断言 | 通过 |
| 12 | 不提前使用后续术语 | `LLM_SCOPE` 13 个术语按章序检查，无一提前 | 通过 |
| 13 | 练习挂知识点 | 64 个练习全部挂本科时知识点，每节 ≥2 个，均有参考答案与解析 | 通过 |
| 14 | 测验不超纲 | 192 题：每节 ≥6、三类各 ≥2、六种题型齐备 | 通过 |
| 15 | 知识点可排期 | 32 个知识点先修边方向正确、无倒挂 | 通过 |
| 16 | 课程可经 API 查询 | `/courses/llm-api/textbook` 返回 16 章 32 课时 32 份内容 | 通过 |
| 17 | 内容审计通过 | `/courses/llm-api/textbook/audit` 返回 `passed = true`，10 项检查全 PASS | 通过 |
| 18 | 课程详情正确 | 等级 `L1`、方向 `ai-llm`、16 章 | 通过 |
| 19 | 先修关系正确 | 课程先修 = `{python-advanced}`；入学知识点全部 `python-basics-*` | 通过 |
| 20 | 写入幂等 | 二次执行 `seed-phase4c`：`新增内容 0`、`新增练习 0`、`新增题目 0` | 通过 |
| 21 | 其它课程不受影响 | 6 门课「跑前跑后章数 / 课时数快照一致」 | 通过 |

`GET /api/v1/courses/llm-api/textbook/audit` 的 10 项内容审计：

| 检查项 | 结果 |
| --- | --- |
| 16 个章节存在且顺序连续 | PASS |
| 每个章节都有完整课时 | PASS（32 课时） |
| 教材内容 15 个模块齐全 | PASS |
| 代码示例、输出与逐行解释完整 | PASS |
| 通俗解释适合初学者 | PASS |
| 练习已关联对应知识点 | PASS（64 个） |
| 测验题题量、分类、题型、关联与解析合规 | PASS（192 题） |
| 不提前使用未学习的语法 | PASS |
| 课时与题目没有大量重复 | PASS |
| 学习计划可以引用课时知识点 | PASS（32 个知识点） |

后端全量测试：**370 passed**（阶段 4B 基线 349 + 本阶段新增 21）。

## 九、缺陷与修正

本阶段同样用测试反过来修内容，实际抓到并修掉的问题：

| 缺陷 | 现象 | 修正 |
| --- | --- | --- |
| 4 道进阶题放在入门课时 | 审计第 7 项报 `q-llm-01-01-4`、`q-llm-02-01-6`、`q-llm-05-01-4`、`q-llm-05-01-6` 难度 `advanced` 高于课时一级 | 这 4 题降为 `intermediate`；考点不变，只是把表述从「架构权衡」收回到「识别与选择」 |
| 脱敏正则顺序错误 | 证件号 `110101199003071234` 被手机号规则先命中，输出成 `110101138****00004` | 证件号规则移到手机号之前，并补 `(?<!\d)` / `(?!\d)` 数字边界断言，重跑后输出为 `****` |
| 协议术语未真正出现 | `tools=` 与 `max_retries` / `backoff` 三处术语在正文里没有落点，`LLM_SCOPE` 形同虚设 | 第 11 章补「封装成 `chat(messages, tools=TOOLS)`」一句；第 14 章补「重试参数不是协议字段」小节，讲清 `max_retries` / `backoff` 属于客户端、只有 `Retry-After` 来自服务端 |
| Key 课时缺仓库防护 | 断言 `.gitignore` 只在概念列出现，示例与语法说明里没有 | 语法说明补 `.gitignore` 代码块与「误提交后先轮换再清历史」两句 |
| 示例输出断言过严 | 概念类课时（第 1 章采样、第 3 章 Key、第 6 章 Prompt）没有请求响应，被「每节必须含请求与响应」判定失败 | 改为「示例输出 ≥10 字 + 至少 5 节给出请求与响应完整对照」，与实际教学形态一致 |
| 测试用错模型字段 | `Exercise` 没有 `lesson_id` / `answer` 字段，`KnowledgePointPrerequisite` 的外键叫 `prerequisite_kp_id` | 改为按知识点查练习、断言 `reference_answer`、用正确的外键名 |
| 方向断言写成字符串 | 课程详情接口返回的 `directions` 是 `[{code, name}]` 而非字符串列表 | 断言改为 `any(item["code"] == "ai-llm" ...)` |

## 十、数据影响与兼容

- 课程目录：`llm-api` 由 **8 章 28 课时**（16 小时）重建为 **16 章 32 课时**（20 小时 15 分钟）。
  7 门课目录合计由 **69 章 156 课时** 变为 **77 章 160 课时**（`tests/test_course_catalog.py` 的
  `EXPECTED_CHAPTERS` / `EXPECTED_LESSONS` 同步改为此值）。
- 新增数据：32 份教学内容、32 个知识点、64 个练习、192 道题，全部为**新增行**；
  二次执行 `seed-phase4c` 时 `新增内容 0 / 新增练习 0 / 新增题目 0`，只做更新，可反复运行。
- 旧课时处理：目录对齐会清理「已移出目录且从未写入正文」的空壳课时；**有正文的课时一律保留**。
- 其它课程未受影响：`python-basics` 仍为 20 章 29 课时，进阶 10 章 12 课时，数据库 9 章 11 课时，
  `fastapi-backend` 16 章 31 课时，由 `test_other_courses_untouched` 用「跑前跑后快照一致」守住。
- 当前开发库状态：**7 门课 / 91 章 / 175 课时 / 147 知识点 / 115 份教学内容 / 230 个练习 / 803 道题**；
  `llm-api` 的 32 份内容状态均为 `reviewed`，课程 `publish_status` 为 `draft`。
- 本阶段**没有新增数据库迁移**，也**没有新增运行依赖**（`openai` / `tiktoken` 均未引入）。
- 操作顺序：备份 `data/backups/xiaoma-20261108-181659-110969.db` → `python -m app.cli seed-phase4c`
  （内部先 `seed_course_catalog` 对齐目录，再写正文）。

## 十一、代码组织

| 文件 | 职责 |
| --- | --- |
| `app/seed/llm/ch01_03.py` | 第 1—3 章：Token 与采样、能力边界、兼容协议与 Base URL、Key 管理与泄漏处置（6 课时） |
| `app/seed/llm/ch04_06.py` | 第 4—6 章：httpx 首次调用、客户端封装、三种角色、Prompt 结构与评测（5 课时） |
| `app/seed/llm/ch07_09.py` | 第 7—9 章：多轮历史、会话隔离、预算与裁剪、摘要、SSE 解析与透传（6 课时） |
| `app/seed/llm/ch10_12.py` | 第 10—12 章：JSON 模式与修复循环、函数声明与执行、多工具路由与上限（6 课时） |
| `app/seed/llm/ch13_15.py` | 第 13—15 章：用量与费用、超时与退避重试、异常分类、注入与越权防护（4 课时） |
| `app/seed/llm/ch16.py` | 第 16 章：综合项目 5 步（5 课时） |
| `app/seed/llm/__init__.py` | 汇总 `CHAPTERS`、`META`、教材口径常量与规模统计 |
| `app/seed/phase4c_seed.py` | 写入入口：调通用 `write_textbook(..., content_status="reviewed")` |
| `app/seed/course_catalog_seed.py` | 重建 `llm-api` 的 16 章 32 课时目录与课程描述 |
| `app/core/curriculum.py` | 新增 `LLM_SCOPE`（13 个术语的最早章节）+ `COURSE_PROFILES["llm-api"]`（16 章） |
| `app/cli.py` | 新增 `seed-phase4c` 子命令 |
| `tests/test_phase4c.py` | 21 项验收测试（对应第八节 21 个验收点） |

## 十二、未完成内容

- 32 份内容停在 `reviewed`：按状态机需人工终审后才能逐节置 `published`，本阶段没有代劳；
  课程 `publish_status` 同步保持 `draft`。
- 所有示例代码都是「可编译、可离线跑」的最小实现，**没有接真实服务商**做过线上联调：
  正文里的请求体字段以兼容协议为准，若某家服务商有额外必填项，需要按该厂商文档补充（教材已把
  「服务商差异」单列一节并给出适配层写法）。
- `openai` / `tiktoken` 未引入：若后续要让「官方 SDK 用法」与「精确 token 计数」进课堂，
  需先补依赖并同步 `requirements.txt`，同时评估第 4 章、第 13 章的示例改写成本。
- LangGraph Agent（`langgraph-agent`，12 章 32 课时）与软件工程与部署（`software-engineering-deploy`，8 章 28 课时）
  两门课仍是目录状态，合计 60 课时无正文。
- 本阶段未改动前端：课程详情页仍按现有接口渲染章节与课时，没有为 LLM 课新增专属页面
  （流式对话的演示界面在综合项目里只给出后端 SSE 端点与前端 `fetch` 解析示例）。
