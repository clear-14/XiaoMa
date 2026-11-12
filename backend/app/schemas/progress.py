"""学习进度汇总 Schema（阶段 7）。

**两个轴必须分开，不得合成单一进度条**：
- ``learning_percent``：学习完成度（我是否花时间学完这段内容）；
- ``mastery_percent``：已验证掌握度（系统是否确认我会了）。

「已学完」只代表学习完成度到顶，不代表掌握；掌握只由测验/练习/诊断证据决定
（PRD 6.1）。前端必须分开展示并分别命名。
"""

from pydantic import BaseModel, Field


class ChapterProgressOut(BaseModel):
    """章节级进度。"""

    chapter_code: str
    chapter_title: str
    order_index: int
    kp_total: int
    # 有学习记录（掌握状态不是 not_started）
    kp_started: int
    # 已学完（自述完成及以上），不含仅「学习中」
    kp_learned: int
    # 有验证证据的掌握
    kp_mastered: int
    minutes_total: int
    minutes_learned: int
    learning_percent: float
    mastery_percent: float


class CourseProgressOut(BaseModel):
    """课程级进度（含章节明细）。"""

    course_code: str
    course_name: str
    course_publish_status: str
    kp_total: int
    kp_started: int
    kp_learned: int
    kp_mastered: int
    minutes_total: int
    minutes_learned: int
    learning_percent: float
    mastery_percent: float
    chapters: list[ChapterProgressOut] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
