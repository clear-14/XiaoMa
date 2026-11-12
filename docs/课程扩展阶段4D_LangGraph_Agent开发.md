# 课程扩展阶段 4D：LangGraph Agent 开发课程建设

> 状态：已完成（2026-11-08）。`langgraph-agent` 由「12 章 32 课时的目录占位」建设为 **28 章 47 课时**的完整教材：
> 47 份正文、94 个练习、282 道测验题全部落库，内容状态 `reviewed`，等待人工终审后再逐节置 `published`。
> 本阶段只做课程内容，**没有新增运行依赖、没有新增数据库迁移、没有改动前端**。

## 一、范围

| 课程 | code | 章 | 课时 | 时长 | 知识点 | 练习 | 测验题 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| LangGraph Agent 开发 | `langgraph-agent` | 28 | 47 | 30 小时 35 分钟 | 47 | 94 | 282 |

需求给出的 28 个主题**逐一成为一章**（不像 4A—4C 需要合并主题），因此章号与主题号严格 1:1，
第 28 章「综合项目：个人 AI 学习 Agent」用 5 个课时承接需求的 6 项能力要求。

## 二、章节与课时

| # | 章节 code | 章节 | 课时数 | 时长 | 课时 |
| --- | --- | --- | --- | --- | --- |
| 1 | `langgraph-agent-01` | AI Agent 基础概念 | 2 | 60 分钟 | 什么是 AI Agent / 思考—行动—观察循环 |
| 2 | `langgraph-agent-02` | Agent 与普通大模型对话的区别 | 1 | 30 分钟 | 一次生成与多步决策 |
| 3 | `langgraph-agent-03` | LangGraph 的作用 | 1 | 30 分钟 | 从链式调用到图编排 |
| 4 | `langgraph-agent-04` | LangGraph 项目初始化 | 2 | 65 分钟 | 安装与版本确认 / 跑通第一个图 |
| 5 | `langgraph-agent-05` | Graph | 1 | 30 分钟 | 图、节点与边 |
| 6 | `langgraph-agent-06` | State | 2 | 70 分钟 | 状态结构与类型约束 / 状态的读写与生命周期 |
| 7 | `langgraph-agent-07` | Node | 1 | 30 分钟 | 节点是什么 |
| 8 | `langgraph-agent-08` | Edge | 1 | 30 分钟 | 边与入口出口 |
| 9 | `langgraph-agent-09` | StateGraph | 1 | 35 分钟 | 把三块组装起来 |
| 10 | `langgraph-agent-10` | 图创建和编译 | 2 | 70 分钟 | add_node 与 add_edge / compile 与运行 |
| 11 | `langgraph-agent-11` | 节点函数 | 1 | 35 分钟 | 函数签名与返回值 |
| 12 | `langgraph-agent-12` | 状态更新 | 2 | 70 分钟 | 部分更新与全量更新 / 并发写入冲突 |
| 13 | `langgraph-agent-13` | 条件路由 | 2 | 80 分钟 | 路由函数与条件边 / Command 与 Send |
| 14 | `langgraph-agent-14` | 循环和流程控制 | 1 | 35 分钟 | 循环、终止条件与上限 |
| 15 | `langgraph-agent-15` | Reducer | 2 | 80 分钟 | 为什么需要 reducer / 内置与自定义 reducer |
| 16 | `langgraph-agent-16` | 接入大模型 | 2 | 85 分钟 | ChatModel 抽象 / 接 OpenAI 兼容接口 |
| 17 | `langgraph-agent-17` | Tool Calling | 2 | 85 分钟 | 工具定义与 schema / tool_calls 与结果回填 |
| 18 | `langgraph-agent-18` | 工具节点 | 1 | 40 分钟 | ToolNode 与错误处理 |
| 19 | `langgraph-agent-19` | Agent 工作流 | 2 | 80 分钟 | 手写 ReAct 图 / 工作流形态与版本定位 |
| 20 | `langgraph-agent-20` | Checkpointer | 2 | 85 分钟 | 线程与检查点 / 时间旅行与人工修正 |
| 21 | `langgraph-agent-21` | Store | 1 | 40 分钟 | 跨线程长期存储 |
| 22 | `langgraph-agent-22` | Interrupt | 2 | 85 分钟 | 中断与恢复 / 审批流设计 |
| 23 | `langgraph-agent-23` | Subgraph | 2 | 85 分钟 | 子图定义与调用 / 父子状态映射 |
| 24 | `langgraph-agent-24` | Streaming | 2 | 85 分钟 | stream_mode 各模式 / 自定义事件与前端透传 |
| 25 | `langgraph-agent-25` | 错误处理与重试 | 1 | 40 分钟 | RetryPolicy 与异常分类 |
| 26 | `langgraph-agent-26` | FastAPI 集成 LangGraph | 2 | 90 分钟 | 同步接口 / SSE 流式接口 |
| 27 | `langgraph-agent-27` | LangGraph 测试 | 1 | 40 分钟 | 离线测试与断言 |
| 28 | `langgraph-agent-28` | 综合项目：个人 AI 学习 Agent | 5 | 245 分钟 | 需求拆解与图设计 / 模型配置与工具层 / 状态与条件路由 / 持久化与人工介入 / FastAPI 接口与测试 |
| — | 合计 | 28 章 | **47** | **30 小时 35 分钟** | — |

## 三、每节课的结构

沿用阶段 3 建立的 15 个内容模块，本阶段额外落两条需求硬要求：**「给出可阅读的完整示例代码」
与「解释每一个节点和状态的作用」**。

| 需求环节 | 落库列 | 本阶段写作要求 |
| --- | --- | --- |
| 本节目标 | `learning_objectives` | 3—4 条动词开头的可检验目标 |
| 为什么学 | `why_learn` | 说明「不学这节后面会卡在哪」 |
| 核心知识 | `concept_explanation` | 术语清单，每条一句定义 |
| 通俗解释 | `plain_explanation` | 生活类比，**≥80 字**（服务层要求 60 字），不与核心知识重复 |
| API 说明 | `syntax_explanation` | 关键 API 签名 + 参数含义 + 版本注意 |
| 完整代码示例 | `example_code` | 单文件可直接运行，**每个节点都带 docstring 或注释说明它在图上做什么** |
| 逐行解析 | `code_explanation` | 本节最少 6 条、平均 7.6 条，说明「为什么这么写」而不只是「这行做了什么」 |
| 运行结果 | `example_output` | **真实运行输出**，不是手写 |
| 常见错误 | `common_mistakes` | 5 条左右真实会踩的坑 |
| 错误分析 | `error_analysis` | 报错原文 + 成因 + 处理 |
| 入门 / 进阶练习 | `beginner_exercises` / `advanced_exercises` | 照着改 / 需要组合前面知识 |
| 小测验 | `quiz_note` | 说明本节 6 题的构成 |
| 学习总结 | `summary` | 3 句含记忆锚点 |
| 下一课建议 | `next_lesson` | 指向下一节的具体内容 |

**「解释每一个节点和状态的作用」**在两处落地：

1. 每节的 `code_explanation` 逐条标注节点名与它读写的 state 字段（例如第 12 章要说明
   `bump` 只返回 `{"n": ...}` 而 `add_note` 返回 `{"notes": [...]}` 的差别在哪）；
2. 综合项目第 28 章 28-1 课时用 `NODES` / `ROUTES` 两张表把 6 个节点、4 条路由逐条列出来，
   再据此编译骨架图，读者能对照表与图看。

每节课固定配 **2 个练习**（含参考答案与解析）+ **6 道测验题**：2 道基础理解 + 2 道代码阅读 + 2 道应用练习。
六种题型分布：

| 题型 | 数量 | 用在哪 |
| --- | --- | --- |
| 代码阅读（`code_analysis`） | 94 | 固定第 3、4 题：读输出、读路由结果 |
| 单选（`single_choice`） | 48 | 第 1 题：定义辨析 |
| 简答（`short_answer`） | 47 | 第 5 题：说清「为什么」 |
| 代码编写（`code_writing`） | 47 | 第 6 题：补一段实现 |
| 判断（`true_false`） | 44 | 第 2 题：认知纠偏（每题都对准一个真实误解，如「有了 `MAX_STEPS` 就不用终止条件」） |
| 多选（`multiple_choice`） | 2 | 仅在考点本身是「多项罗列」时使用（Agent 三要素、适合用图的需求） |

判断题占多是有意为之：本课程的坑大多是「以为它会 A，其实它 B」（`TypedDict` 不做运行期校验、
默认合并是整值替换、`ToolNode` 默认只兜调用错误、`invoke(None)` 恢复 `interrupt` 只会再挂一次），
用判断题一条一条纠偏比多选更直接。难度分布：`beginner` 142、`intermediate` 135、`advanced` 5，
**不允许跨两级**（入门课时里不出现 `advanced` 题）。

## 四、需求主题 → 章节对应

| # | 需求主题 | 章节 | 课时数 |
| --- | --- | --- | --- |
| 1 | AI Agent 基础概念 | `langgraph-agent-01` | 2 |
| 2 | Agent 与普通大模型对话的区别 | `langgraph-agent-02` | 1 |
| 3 | LangGraph 的作用 | `langgraph-agent-03` | 1 |
| 4 | LangGraph 项目初始化 | `langgraph-agent-04` | 2 |
| 5 | Graph | `langgraph-agent-05` | 1 |
| 6 | State | `langgraph-agent-06` | 2 |
| 7 | Node | `langgraph-agent-07` | 1 |
| 8 | Edge | `langgraph-agent-08` | 1 |
| 9 | StateGraph | `langgraph-agent-09` | 1 |
| 10 | 图创建和编译 | `langgraph-agent-10` | 2 |
| 11 | 节点函数 | `langgraph-agent-11` | 1 |
| 12 | 状态更新 | `langgraph-agent-12` | 2 |
| 13 | 条件路由 | `langgraph-agent-13` | 2 |
| 14 | 循环和流程控制 | `langgraph-agent-14` | 1 |
| 15 | Reducer | `langgraph-agent-15` | 2 |
| 16 | 接入大模型 | `langgraph-agent-16` | 2 |
| 17 | Tool Calling | `langgraph-agent-17` | 2 |
| 18 | 工具节点 | `langgraph-agent-18` | 1 |
| 19 | Agent 工作流 | `langgraph-agent-19` | 2 |
| 20 | Checkpointer | `langgraph-agent-20` | 2 |
| 21 | Store | `langgraph-agent-21` | 1 |
| 22 | Interrupt | `langgraph-agent-22` | 2 |
| 23 | Subgraph | `langgraph-agent-23` | 2 |
| 24 | Streaming | `langgraph-agent-24` | 2 |
| 25 | 错误处理与重试 | `langgraph-agent-25` | 1 |
| 26 | FastAPI 集成 LangGraph | `langgraph-agent-26` | 2 |
| 27 | LangGraph 测试 | `langgraph-agent-27` | 1 |
| 28 | 综合项目：个人 AI 学习 Agent | `langgraph-agent-28` | 5 |

章号与主题号 1:1，`app/seed/langgraph/__init__.py` 的 `TOPICS` 与 `CHAPTERS` 顺序由
`test_each_topic_owns_one_chapter` 断言「逐条相等」，改一处不同步就红。

## 五、教学顺序与「不提前教学」

需求给了 12 段教学顺序，落成 5 个阶段、29 个受控术语：

| 阶段 | 章节 | 这一段只讲什么 | 第一次出现的 API |
| --- | --- | --- | --- |
| 概念 | 1—3 | Agent 是什么、与普通对话差在哪、为什么需要图。**一行框架代码都没有** | 无（纯 Python + `@dataclass`） |
| 图基础 | 4—5 | 装环境、钉版本、跑通最小的图，建立「节点 / 边 / 有向图 / 环路」词汇 | `StateGraph`、`compile(`、`TypedDict` |
| 状态三件套 | 6—12 | State 定义与合并、节点函数边界、边的连接、组装、编译、状态更新 | `Annotated`、`add_messages`、`add_node`、`add_edge` |
| 路由与控制流 | 13—15 | 条件边、`Command` / `Send`、循环与 `recursion_limit`、Reducer | `add_conditional_edges`、`Command(`、`Send(`、`operator.add`、`recursion_limit` |
| 模型与工具 | 16—19 | ChatModel 抽象、工具 schema、`ToolNode`、手写 ReAct | `BaseChatModel`、`bind_tools`、`convert_to_openai_tool`、`ToolNode`、`tools_condition`、`create_react_agent` |
| 持久化与人工 | 20—22 | 线程内检查点、跨线程 Store、中断与审批 | `checkpointer`、`thread_id`、`InMemorySaver`、`get_state_history`、`update_state`、`InMemoryStore`、`interrupt(`、`Command(resume` |
| 子图与流式 | 23—24 | 子图调用与状态映射、`stream_mode` 五种模式 | `stream_mode`、`get_stream_writer` |
| 工程化 | 25—27 | 重试策略、FastAPI 集成、离线测试 | `RetryPolicy`、`retry_on`、`StreamingResponse` |
| 综合 | 28 | 六项要求串成一个项目 | 复用上面全部 |

**两道防线**，缺一不可：

1. **表驱动**：`app/core/curriculum.py` 的 `LANGGRAPH_SCOPE` 记录「术语 → 最早可出现章节」（29 条），
   审计第 8 项按章序重查示例代码与语法说明；
2. **测试兜底**：`test_no_late_terms_in_early_chapters` 用同一张表逐节课断言；
   `test_teaching_order_is_respected` 额外断言「前 3 章不出现 `langgraph` / `StateGraph`」
   与「第 4 章是项目初始化、第 16 章才接大模型、第 20 章才讲持久化」。

本阶段开发中，这条约束真的拦下过一次错误：19-1「手写 ReAct 图」的正文一度把 `checkpointer`
写进对比表格，被审计判为「第 19 章用了第 20 章的术语」，改成 `tool` 后才通过。

## 六、重点教学要求落地

需求点名 9 项必须讲清的内容，每项都有主课与代码落点（`test_key_points_covered` 逐项断言）：

| 要求 | 主课 | 讲什么 | 代码落点 |
| --- | --- | --- | --- |
| State：状态结构与状态更新 | 6-1 / 6-2 | `TypedDict` 定义、必填与可选键、节点返回增量后由框架合并、`state[...]` 读取 | `class State(TypedDict)`、`__required_keys__`、`return {"answer": ...}` |
| Node：节点函数与输入输出 | 7-1 | 入参是完整 state、返回值是增量、不能就地改传入对象、异常会中断整张图 | `def node(state: State) -> dict` |
| Edge：节点之间的连接 | 8-1 | 普通边、`START` / `END`、可达性与悬空节点 | `add_edge(START, "n")`、`add_edge("n", END)` |
| Conditional Edge：条件判断与路由 | 13-1 / 13-2 | 路由函数只读 state 返回节点名、必须覆盖兜底分支、`Command` 与 `Send` 的差别 | `def dispatch(state)`、`add_conditional_edges` |
| Checkpointer：线程范围内持久化 | 20-1 / 20-2 | `thread_id` 必须在 `configurable` 下、`StateSnapshot` 五个字段、时间旅行与人工修正 | `compile(checkpointer=InMemorySaver())`、`get_state`、`get_state_history`、`update_state` |
| Store：跨线程长期存储 | 21-1 | 命名空间是元组、`put/get/search` 前缀查询、**只能通过 `runtime.store` 取** | `runtime: Runtime` → `runtime.store.put(...)` |
| Interrupt：暂停等待人工输入 | 22-1 / 22-2 | 挂起时 `invoke` 正常返回并多出 `__interrupt__`、恢复只能用 `Command(resume=...)`、节点会从头重跑 | `interrupt({...})`、`Command(resume=...)` |
| Subgraph：模块化与子图调用 | 23-1 / 23-2 | 编译产物可直接 `add_node`、父子状态无共享键时收到 `{}`、包装节点做双向映射 | `add_node("pre", sub_graph)`、`get_graph(xray=True)` |
| Streaming：不同流式事件 | 24-1 / 24-2 | `values` / `updates` / `custom` / `messages` / `debug` 五种模式的 payload 形状、SSE 帧格式与前端切帧 | `stream(..., stream_mode=[...])`、`get_stream_writer()` |

## 七、综合项目：个人 AI 学习 Agent

需求给的 6 项能力要求，按「一次只加一层」落在第 28 章 5 个课时，前后代码可以直接串成同一个项目：

| 需求要求 | 课时 | 本步交付 |
| --- | --- | --- |
| 能识别用户问题 | 28-1 | `classify` 节点：`RULES` 顺序匹配 + `intent` 字段，四种问法分成 `concept` / `chapter` / `progress` / `note`；同时给出 `NODES` / `ROUTES` 两张表 |
| 能读取课程相关知识 | 28-3 | `retrieve`（概念题走章节检索）与 `read_chapter`（指定章号直接读）两个节点，用条件边分流 |
| 能调用允许使用的工具 | 28-2 | `ALLOWED` 白名单（`search_course` / `read_lesson` 两个只读工具）+ 参数夹紧（`limit = max(1, min(limit, 3))`）+ `convert_to_openai_tool` 导出 schema；`WRITE_TOOLS` 留空，白名单外工具直接 `KeyError` |
| 能保存对话状态 | 28-4 | `compile(checkpointer=InMemorySaver(), store=store)`：`thread_id` 隔离会话，`take_note` 把笔记写进 Store 供跨会话读取 |
| 能根据条件选择工作流 | 28-3 | `RULES` 顺序匹配（先命中先赢）+ `add_conditional_edges` 四路分流，`stream_mode="updates"` 打印真实走过的路径 |
| 能通过 FastAPI 提供接口 | 28-5 | `/ask`、`/approve`、`/ask/stream` 三个端点 + 4 个 `test_*`（`TestClient` 实测，流式用 `iter_lines()`） |

**「不执行用户提交的代码」**在两处落实：

1. 工具层只有 `ALLOWED` 白名单里的 2 个只读工具（`search_course` 按关键词找章节、`read_lesson` 读指定章），
   `WRITE_TOOLS` 留空表示暂不开放写操作；「记笔记」这类写动作走**节点 + 人工审批**：
   28-4 的 `take_note` 先 `interrupt({"action": "保存笔记", ...})`，`Command(resume={"approved": True})`
   之后才 `runtime.store.put(...)`，拒绝则返回「已取消保存」。
2. 全部工具用 `@tool` + `args_schema` 声明，参数做夹紧（`limit = max(1, min(limit, 3))`），
   不接收代码字符串、不 `eval`、不起子进程；`test_project_does_not_execute_user_code` 断言项目正文里
   不出现 `eval(` / `exec(` / `subprocess` / `os.system` / `__import__`，且必须出现 `ALLOWED`。

## 八、教材适用版本与技术规范

教材以 `backend/.venv` 的实测环境为准，**所有示例都在该环境跑过**：

| 包 | 版本 | 在教材里承担什么 |
| --- | --- | --- |
| `langgraph` | **1.2.20** | `StateGraph`、`compile`、`interrupt`、`Command`、`stream_mode` |
| `langchain-core` | **1.7.6** | `BaseChatModel`、消息类型、`@tool`、`convert_to_openai_tool` |
| `langgraph-checkpoint` | **4.3.1** | `InMemorySaver`、`StateSnapshot`、`get_state_history` |
| `langgraph-prebuilt` | **1.1.1** | `ToolNode`、`tools_condition`、`create_react_agent`（仅作历史形态） |
| `pydantic` | **2.14** | 工具 `args_schema` |
| Python | **3.14.4** | 类型写法（`list[str]`、`X | None`） |

三条**版本事实**写进正文，不靠读者自己猜：

1. `create_react_agent` 在 LangGraph V1.0 起迁往 `langchain.agents`，调用会发
   `LangGraphDeprecatedSinceV10`（V2.0 移除）。第 19-2 用 `warnings.catch_warnings(record=True)`
   把这个告警**真实抓出来**贴在教材里，并说明「本机没装 `langchain` 全量包，所以字符串指定模型会 `ImportError`」。
2. `Store` 的取法变了：节点参数写 `runtime: Runtime` → `runtime.store`。写成 `store=...` 关键字参数会
   `TypeError: missing 1 required keyword-only argument: 'store'`，老教程的 `config["store"]` 也取不到。
   第 21-1 把两种失效写法与报错原文一并写进「常见错误」。
3. `BaseChatModel.bind_tools` 默认抛 `NotImplementedError`（消息体为空字符串），自定义模型必须自己实现；
   第 17-2 给了 `self.bind(tools=[convert_to_openai_tool(t)["function"] ...])` 的最小实现。

**示例输出不是手写的**。新增测试 `test_example_output_matches_real_execution` 逐节课执行
`example_code`（`redirect_stdout` 捕获，UUID 归一化为 `<uuid>`），与教材 `output` 字段逐行比对：
47 节课全部一致，任何一侧改动都会立刻报错。开发期用它抓到 6 处不一致（见第十一节）。

## 九、先修关系

- 课程级：`langgraph-agent` ← `python-advanced` + `llm-api`（沿用阶段 2 目录定义，未改动）。
  先修 `llm-api` 是本阶段新增的实质约束：教材假定读者已会「消息结构 / 工具调用协议 / Key 管理」，
  这三块不重复讲，只在第 16—17 章引用。
- 入学知识点：`python-basics-05-02`、`python-basics-06-03`（由 `test_entry_knowledge_points_from_basics` 校验）。
- 知识点级：47 个新知识点串成一条链（`langgraph-agent-01-01` → … → `langgraph-agent-28-05`），
  由 `test_knowledge_point_prerequisites_follow_course_order` 与审计第 10 项守住，无倒挂。

## 十、验收结果

`backend/tests/test_phase4d.py` 共 **24 项**自动化测试：

| # | 验收点 | 验证方式 | 结果 |
| --- | --- | --- | --- |
| 1 | 章节完整 | 28 章 / 47 课时、章序连续、课时难度合法 | 通过 |
| 2 | 28 个主题 1:1 成章 | `TOPICS` 与章节标题列表逐条相等 | 通过 |
| 3 | 教学顺序正确 | 前 3 章无 `langgraph` / `StateGraph`；术语按章序出现；第 4/6/16/19/20/28 章标题固定 | 通过 |
| 4 | 9 项重点教学要求 | 每项断言主课存在 + 该章代码/语法含指定关键片段 | 通过 |
| 5 | 综合项目 6 项要求 | 6 组关键片段分别落到第 28 章 5 节课 | 通过 |
| 6 | 不执行用户代码 | 项目正文无 `eval(` / `exec(` / `subprocess` / `os.system` / `__import__`，且必须有 `ALLOWED` | 通过 |
| 7 | 每节课有实质内容 | 15 模块非空且 ≥10 字；通俗解释 ≥80 字；逐行解释 ≥5 条；输出 ≥80 字 | 通过 |
| 8 | 教材可经既有 API 读取 | `GET /lessons/{code}/textbook` 15 个字段全部非空 | 通过 |
| 9 | 示例代码可编译 | 47 段代码全部 `compile` 通过 | 通过 |
| 10 | 版本事实写明 | 断言 `1.2.20` / `1.7.6` / `4.3.1` / `LangGraphDeprecatedSinceV10` / `langchain.agents` / `runtime.store` 都出现 | 通过 |
| 11 | 不混用版本接口 | 无 `StateGraphV2` / `config["store"]` / `ToolExecutor`；`create_react_agent` 只出现在第 19 章 | 通过 |
| 12 | 示例输出真实 | 47 节课真实执行，与 `output` 字段逐行一致 | 通过 |
| 13 | 不提前使用术语 | `LANGGRAPH_SCOPE` 29 条按章序检查，无一提前 | 通过 |
| 14 | 练习挂知识点 | 94 个练习全部挂在本科时知识点，每节 2 个，均有答案与解析 | 通过 |
| 15 | 测验题量与分类 | 282 题：每节 6 道、三类各 ≥2、六种题型齐备 | 通过 |
| 16 | 难度不超纲 | 每题难度不高于课时难度 +1 级 | 通过 |
| 17 | 知识点可排期 | 47 个知识点先修边方向正确 | 通过 |
| 18 | API 大纲 | `/courses/langgraph-agent/textbook` 返回 28 章 / 47 课时 / 47 份 `reviewed` | 通过 |
| 19 | 内容审计 | `/courses/langgraph-agent/textbook/audit` → `passed = true`，10 项全 PASS | 通过 |
| 20 | 课程详情 | 等级 `L2`、方向 `ai-llm`、28 章 | 通过 |
| 21 | 先修关系 | 课程先修 = `{python-advanced, llm-api}`；入学知识点全部 `python-basics-*` | 通过 |
| 22 | 写入幂等 | 二次执行：新增内容 0 / 练习 0 / 题目 0 | 通过 |
| 23 | 其它课程不受影响 | 5 门课「跑前跑后章数课时快照一致」 | 通过 |
| 24 | 课时挂知识点 | 47 节课都有 `LessonKnowledgePoint` 关联 | 通过 |

10 项内容审计（真实开发库）：

| 检查项 | 结果 |
| --- | --- |
| 28 个章节存在且顺序连续 | PASS |
| 每个章节都有完整课时 | PASS（47 课时） |
| 教材内容 15 个模块齐全 | PASS |
| 代码示例、输出与逐行解释完整 | PASS |
| 通俗解释适合初学者 | PASS |
| 练习已关联对应知识点 | PASS（94 个） |
| 测验题题量、分类、题型、关联与解析合规 | PASS（282 题，覆盖 6 种题型） |
| 不提前使用未学习的语法 | PASS |
| 课时与题目没有大量重复 | PASS |
| 学习计划可以引用课时知识点 | PASS（47 个知识点） |

后端全量测试：**394 passed**（阶段 4C 基线 370 + 本阶段新增 24）。

## 十一、缺陷与修正

本阶段同样用测试反过来修内容。真实抓到并修掉的问题：

| 缺陷 | 现象 | 修正 |
| --- | --- | --- |
| 目录里 4 个课时难度写错 | `seed_course_catalog` 抛 `ValueError: langgraph-agent-04 课时难度不合法：basic`，整套目录种子连带 34 个测试全红 | `langgraph-agent-04/05/07/08` 的 4 个 `basic` 改为 `beginner`（枚举只有 `beginner`/`intermediate`/`advanced`） |
| 10-2 少一个内容模块 | `write_textbook` 抛 `KeyError: 'mistakes'` | 补齐 10-2 的「常见错误」5 条（构建器忘了 `compile`、每次重新编译、按注册名判断节点是否生效、误以为有跨调用记忆、把返回值当增量） |
| 课时标题与目录不一致 | 16—19 章早期用自拟标题（如「模型在节点里是什么角色」），与目录对不上 | 按目录统一为「ChatModel 抽象」「接 OpenAI 兼容接口」「工具定义与 schema」「ToolNode 与错误处理」「手写 ReAct 图」「工作流形态与版本定位」，`minutes` 同步对齐 40/45/35 等 |
| 19-1 提前用 `checkpointer` | 审计第 8 项报「第 19 章使用了第 20 章才讲的术语」 | 对比表里的 `checkpointer` 换成第 18 章的 `tool` |
| 16-1 对 `messages` 条数解释错 | 正文说「`add_messages` 会追加 `prepare` 的两条」，实际 `AskState.messages` 是普通 `list`，后写覆盖 | 改正逐行解释第 5—7 条，对应选择题答案改为 A |
| 示例输出与代码不一致（6 处） | `04-02` 缺 Mermaid 与边列表、`10-02` `{'n': 99}` 写成 `100`、`13-02` 缺边打印、`14-01` 异常消息被截断、`23-01`、`24-01` | 全部按真实运行输出重写；同类问题已由新增的 `test_example_output_matches_real_execution` 长期看住 |
| 修正脚本把 `\3a` 写成 `\x03` | 重写 23-01 输出时三引号字符串把 `\3` 当八进制转义，Mermaid 里的 `pre\3aclean` 变成控制字符 | 写入前统一 `replace("\\", "\\\\")`，并在比对时跳过 `#` 注释行 |
| 28-1 四个问题走同一条路 | 用 `graph.invoke({"intent": "progress"})` 传参，被 `classify` 节点覆盖，四种问法都判成 `concept` | 改为不传 `intent`，由 `classify` 从问题文本推断 |
| 28-3 路由被前一条规则截胡 | `我学到哪了` 命中 `("态", "concept")` | 重排 `RULES`（`学到哪` / `进度` / `笔记` / `章` 优先），并把 `retrieve` 与 `read_chapter` 拆成两个节点 |
| 26-1 第二轮回到第 0 条响应 | `FakeMessagesListChatModel` 循环回 `i=0`，`add_messages` 按 id 去重，`messages` 停在 3 条 | 改用自定义 `EchoModel` 每次新建 `AIMessage`，输出变成 `2 → 4`；顺手把「别复用同一个消息对象」写成本节知识点 |
| SSE 测试用 `iter_text()` 报错 | 当前 httpx 版本 `TestClient.iter_text()` 不可用 | 全部改用 `iter_lines()`，并把这条写进 26-2 的「常见错误」 |
| 单元测试断言的对象写错 | `KEY_POINTS` 第一版按课时标题断言，`Annotated` 实际在第 15 章才讲；`def route` 实际叫 `dispatch` | 断言口径改为「章级聚合」——9 项要求各对应一章，检查该章全部课时的代码与语法说明 |

## 十二、数据影响与兼容

- 课程目录：`langgraph-agent` 由 **12 章 32 课时**（18 小时 55 分钟）重建为 **28 章 47 课时**（30 小时 35 分钟）。
  7 门课目录合计由 **77 章 160 课时** 变为 **93 章 175 课时**
  （`tests/test_course_catalog.py` 的 `EXPECTED_CHAPTERS` / `EXPECTED_LESSONS` 同步改为 93 / 175）。
  `test_phase4c.py` 里「其它课程不受影响」的 `langgraph-agent` 章数断言由 12 改为 28。
- 新增数据：47 份教学内容、47 个知识点、94 个练习、282 道题，全部为**新增行**；
  二次执行 `seed-phase4d` 时 `新增内容 0 / 新增练习 0 / 新增题目 0`。
- 旧课时处理：目录对齐会清理「已移出目录且从未写入正文」的空壳课时；**有正文的课时一律保留**。
  本阶段被替换的 12 章 32 课时都没有正文，因此全部被新目录覆盖。
- 当前开发库状态：**7 门课 / 107 章 / 190 课时 / 194 知识点 / 162 份教学内容 / 324 个练习 / 1085 道题**；
  `langgraph-agent` 的 47 份内容状态均为 `reviewed`，课程 `publish_status` 为 `draft`。
- 本阶段**没有新增数据库迁移**，也**没有新增运行依赖**：教材用到的 `langgraph` / `langchain-core` /
  `langgraph-checkpoint` / `langgraph-prebuilt` 在阶段 4D 之前就已在 `backend/.venv` 中；
  `langchain` 全量包与 `langgraph-checkpoint-sqlite` **仍未安装**，教材明确写出这一点并给出替代写法。
- 操作顺序：备份 `data/backups/phase4d-before.db` → `python -m app.cli seed-phase4d`
  （内部先 `seed_course_catalog` 对齐目录，再写正文）。

## 十三、代码组织

| 文件 | 职责 |
| --- | --- |
| `app/seed/langgraph/ch01_04.py` | 第 1—4 章：Agent 概念、与对话的区别、LangGraph 定位、安装与第一个图（6 课时） |
| `app/seed/langgraph/ch05_09.py` | 第 5—9 章：图的语言、State、Node、Edge、StateGraph 组装（6 课时） |
| `app/seed/langgraph/ch10_12.py` | 第 10—12 章：注册与编译、节点函数、状态更新与并发冲突（5 课时） |
| `app/seed/langgraph/ch13_15.py` | 第 13—15 章：条件路由、`Command`/`Send`、循环与上限、Reducer（5 课时） |
| `app/seed/langgraph/ch16_17.py` | 第 16—17 章：`BaseChatModel`、OpenAI 兼容接入、工具 schema、`tool_calls` 回填（4 课时） |
| `app/seed/langgraph/ch18_19.py` | 第 18—19 章：`ToolNode` 与错误处理、手写 ReAct、工作流形态与版本定位（3 课时） |
| `app/seed/langgraph/ch20_21.py` | 第 20—21 章：检查点与时间旅行、跨线程 Store（3 课时） |
| `app/seed/langgraph/ch22_23.py` | 第 22—23 章：中断与审批流、子图与父子状态映射（4 课时） |
| `app/seed/langgraph/ch24_25.py` | 第 24—25 章：`stream_mode` 五模式、SSE 透传、`RetryPolicy`（3 课时） |
| `app/seed/langgraph/ch26_27.py` | 第 26—27 章：FastAPI 同步与 SSE 接口、离线测试（3 课时） |
| `app/seed/langgraph/ch28.py` | 第 28 章：综合项目 5 步（5 课时） |
| `app/seed/langgraph/__init__.py` | 汇总 `CHAPTERS`、`META`、`TOPICS`、版本常量与规模统计 |
| `app/seed/phase4d_seed.py` | 写入入口：调通用 `write_textbook(..., content_status="reviewed")` |
| `app/seed/course_catalog_seed.py` | 重建 `langgraph-agent` 的 28 章 47 课时目录（并修掉 4 个非法难度值） |
| `app/core/curriculum.py` | `LANGGRAPH_SCOPE`（29 条术语最早章节）+ `COURSE_PROFILES["langgraph-agent"]`（28 章） |
| `app/cli.py` | 新增 `seed-phase4d` 子命令 |
| `tests/test_phase4d.py` | 24 项验收测试（对应第十节 24 个验收点） |

## 十四、未完成内容

- 47 份内容停在 `reviewed`：按状态机需人工终审后才能逐节置 `published`，本阶段没有代劳；
  课程 `publish_status` 同步保持 `draft`。
- 示例代码全部是「可编译、可离线跑」的最小实现，**没有接真实大模型服务商联调**：
  第 16 章用 `EchoModel`、第 28 章用 `StudyModel`（脚本化 `BaseChatModel`）代替真实调用，
  正文给出 `httpx.MockTransport` 的接法。若要换成真实模型，需要按 `llm-api` 第 11—12 章的
  `tools` 字段补齐请求体。
- `langchain` 全量包未安装：`create_react_agent` 只在第 19-2 作为「历史形态」讲解，
  正文明确写出「字符串指定模型会 `ImportError: Please install langchain`」。
- `langgraph-checkpoint-sqlite` 未安装：持久化只用 `InMemorySaver` / `InMemoryStore`，
  正文注明「进程重启即丢失，生产要换持久化实现」，未给 SQLite 版本示例。
- 软件工程与部署（`software-engineering-deploy`，8 章 28 课时）仍是目录状态，无正文；
  它是 7 门课里最后一门没有教材的课程。
- 本阶段未改动前端：综合项目的流式接口只给后端 SSE 端点与前端 `fetch` 解析示例，
  没有为 Agent 课新增专属页面。
