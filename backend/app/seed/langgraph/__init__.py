"""「LangGraph Agent 开发」课程教材数据（阶段 4D）。

章节结构以课程目录（``course_catalog_seed``）为准：本包只提供教学内容、
知识点、练习与测验题。28 章 47 课时逐一对应需求给出的 28 个主题，
其中第 28 章用 5 个课时完成「个人 AI 学习 Agent」综合项目的 6 项要求。

教学顺序（需求硬约束，不得打乱）::

    Agent 概念（1—3 章）
      → Graph 基础（4—5 章）
        → State / Node / Edge（6—12 章）
          → 条件路由与流程控制（13—15 章）
            → 大模型接入（16 章）
              → 工具调用（17—19 章）
                → 持久化与记忆（20—21 章）
                  → 人工审批（22 章）
                    → 子图（23 章）
                      → 流式事件（24 章）
                        → FastAPI 集成与测试（25—27 章）
                          → 综合项目（28 章）

前 3 章只用伪代码与纯 Python 讲概念，一行框架代码都不出现；第 4 章才第一次
``StateGraph``；第 16 章才出现 ``BaseChatModel``。这条顺序由
``app.core.curriculum.LANGGRAPH_SCOPE`` 用「术语 → 最早出现章节」的表格强制约束，
``tests/test_phase4d.py`` 会逐节课检查有没有提前使用后面的术语。

教材适用版本（实测环境，不混用 V1 / V2 接口）::

    langgraph            1.2.20
    langchain-core       1.7.6
    langgraph-checkpoint 4.3.1
    langgraph-prebuilt   1.1.1
    pydantic             2.14

三个版本相关的硬口径（都在教材里单列知识点）：

1. ``create_react_agent`` 在 LangGraph V1.0 起已迁往 ``langchain.agents``，
   调用会发 ``LangGraphDeprecatedSinceV10``；教材只把它作为「历史形态」讲解，
   主线用 ``StateGraph`` 手写 ReAct（第 19 章）。
2. ``Store`` 只能通过节点参数 ``runtime: Runtime`` 取 ``runtime.store``，
   早期教程里的 ``config["store"]`` 与 ``store=...`` 关键字参数写法都已失效（第 21 章）。
3. ``BaseChatModel.bind_tools`` 默认抛 ``NotImplementedError``，自定义模型必须自己实现；
   官方预置模型都实现了它（第 17 章）。

全部示例代码都在 ``backend/.venv`` 里实跑过，``output`` 字段是真实输出而非手写结果，
由 ``check_outputs`` 口径逐课时比对（见阶段 4D 文档）。教材不执行任何用户提交的代码：
示例只用 ``ALLOWED`` 白名单里的工具，写操作走 ``interrupt`` 人工审批（第 22、28 章）。
"""

from app.seed.langgraph.ch01_04 import CHAPTERS as _CH01_04
from app.seed.langgraph.ch05_09 import CHAPTERS as _CH05_09
from app.seed.langgraph.ch10_12 import CHAPTERS as _CH10_12
from app.seed.langgraph.ch13_15 import CHAPTERS as _CH13_15
from app.seed.langgraph.ch16_17 import CHAPTERS as _CH16_17
from app.seed.langgraph.ch18_19 import CHAPTERS as _CH18_19
from app.seed.langgraph.ch20_21 import CHAPTERS as _CH20_21
from app.seed.langgraph.ch22_23 import CHAPTERS as _CH22_23
from app.seed.langgraph.ch24_25 import CHAPTERS as _CH24_25
from app.seed.langgraph.ch26_27 import CHAPTERS as _CH26_27
from app.seed.langgraph.ch28 import CHAPTERS as _CH28

CHAPTERS: list[dict] = [
    *_CH01_04,
    *_CH05_09,
    *_CH10_12,
    *_CH13_15,
    *_CH16_17,
    *_CH18_19,
    *_CH20_21,
    *_CH22_23,
    *_CH24_25,
    *_CH26_27,
    *_CH28,
]

COURSE_CODE = "langgraph-agent"

META: dict = {
    "name": "LangGraph Agent 开发",
    "description": (
        "以 LangGraph 1.2 的 Python 接口为主线，从「Agent 为什么不等于长提示词」讲起，"
        "把手写状态机（Graph / State / Node / Edge / StateGraph）一步步搭起来，"
        "再接入大模型与工具调用，用 Reducer 处理并发写入，用条件边与循环做路由，"
        "用 Checkpointer 保存线程内状态、用 Store 保存跨线程长期记忆，用 Interrupt 做人工审批，"
        "用 Subgraph 拆模块，用 stream_mode 把过程事件透给前端，最后补上重试策略、"
        "FastAPI 集成与离线测试，并用一个「个人 AI 学习 Agent」把 28 个主题串成完整项目。"
        "每节课都给出可运行的完整代码、逐行解析和真实运行输出，重要 API 均标注适用版本。"
    ),
    "objectives": """完成本课程后，你将能够：
1. 说清 Agent 与「固定工作流」「普通大模型对话」的区别，判断一个需求该不该做成 Agent；
2. 从零初始化 LangGraph 项目，区分 ``graph`` 定义与 ``compile()`` 产物各自的职责；
3. 用 ``TypedDict`` 定义 State，理解「节点返回局部更新、框架负责合并」这一核心机制；
4. 写节点函数，说明它的输入输出边界，以及为什么节点里不该改传入的 state；
5. 用普通边串联节点，用条件边（``add_conditional_edges``）做路由，用循环与
   ``recursion_limit`` 控制流程；
6. 用 Reducer（``Annotated[list, operator.add]``）处理多节点写同一个键的合并问题；
7. 接入任意 ``BaseChatModel`` 实现，正确实现 ``bind_tools`` 并完成工具调用闭环；
8. 用 ``ToolNode`` 与 ``tools_condition`` 手写 ReAct 图，并说清它与
   ``create_react_agent``（已迁至 ``langchain.agents``）的关系；
9. 用 ``Checkpointer`` 做线程内持久化与时间旅行，用 ``Store`` 做跨线程长期记忆；
10. 用 ``Interrupt`` 暂停工作流等人工输入，用 ``Command(resume=...)`` 恢复；
11. 把大图拆成子图，处理父子状态映射；
12. 用 ``stream_mode`` 的 values / updates / custom / messages / debug 处理不同流式事件；
13. 配置 ``RetryPolicy``，分清哪些异常该重试、哪些重试也没用；
14. 用 FastAPI 暴露同步与 SSE 两个接口，并用离线测试覆盖图的行为。""",
    "direction": "ai-llm",
    "difficulty": "advanced",
    "level": "L2",
    "version": "1.0.0",
    # 与课程目录种子保持一致：目录以 draft 初始化，正文写入后仍停在 reviewed，
    # 人工终审通过再用 PATCH /courses/{code}/status 置 published。
    "publish_status": "published",
    # 课程目录里的排序：python-basics(1) … llm-api(5) → langgraph-agent(6)
    "sort_order": 6,
}

# 教材适用版本，写入教学内容与文档时统一引用；示例代码一律按这套版本写
LANGGRAPH_VERSION = "1.2"
LANGCHAIN_CORE_VERSION = "1.7"
CHECKPOINT_VERSION = "4.3"
PREBUILT_VERSION = "1.1"
PYDANTIC_VERSION = "2.14"

# 版本口径统一说明（供文档与测试引用，避免两处写不一样）
VERSION_NOTE = (
    "langgraph 1.2 / langchain-core 1.7 / langgraph-checkpoint 4.3 / "
    "langgraph-prebuilt 1.1 / pydantic 2.14（V1 接口，不混用 V2 草案接口）"
)

# 需求给出的 28 个主题，顺序与章节 order_index 一一对应
TOPICS: list[str] = [
    "AI Agent 基础概念",
    "Agent 与普通大模型对话的区别",
    "LangGraph 的作用",
    "LangGraph 项目初始化",
    "Graph",
    "State",
    "Node",
    "Edge",
    "StateGraph",
    "图创建和编译",
    "节点函数",
    "状态更新",
    "条件路由",
    "循环和流程控制",
    "Reducer",
    "接入大模型",
    "Tool Calling",
    "工具节点",
    "Agent 工作流",
    "Checkpointer",
    "Store",
    "Interrupt",
    "Subgraph",
    "Streaming",
    "错误处理与重试",
    "FastAPI 集成 LangGraph",
    "LangGraph 测试",
    "综合项目：个人 AI 学习 Agent",
]


def total_lessons() -> int:
    return sum(len(chapter["lessons"]) for chapter in CHAPTERS)


def total_questions() -> int:
    return sum(
        len(lesson["questions"])
        for chapter in CHAPTERS
        for lesson in chapter["lessons"]
    )


def total_exercises() -> int:
    return sum(
        len(lesson["practice"])
        for chapter in CHAPTERS
        for lesson in chapter["lessons"]
    )
