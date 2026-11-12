"""教材服务（阶段 3）：课时教材读取、课程大纲、内容状态流转与内容验收。

设计约定：
- 教材内容只经本 Service 读取，Agent 与 API 不直接拼装数据库字段；
- 内容状态遵循 draft → reviewed → published 单向推进，发布前必须通过完整性检查；
- 验收检查全部是确定性规则（长度、字段、关联、关键词、重复度），
  不依赖模型判断，结论可复现。
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.curriculum import BASICS_SCOPE, TERM_LABELS, profile_for
from app.models.course import CourseContent, Exercise, Lesson
from app.models.quiz import Question
from app.repositories.course_repository import CourseRepository
from app.schemas.textbook import (
    AuditCheckOut,
    ContentStatusOut,
    LessonAuditOut,
    LessonTextbookOut,
    TextbookAuditOut,
    TextbookChapterOut,
    TextbookContentOut,
    TextbookExerciseOut,
    TextbookKnowledgePointOut,
    TextbookLessonBrief,
    TextbookOutlineOut,
    TextbookQuestionOut,
)

# 教材必备的 15 个内容模块（与数据库列名一致）
CONTENT_FIELDS: tuple[tuple[str, str], ...] = (
    ("learning_objectives", "学习目标"),
    ("why_learn", "为什么学"),
    ("concept_explanation", "核心概念"),
    ("plain_explanation", "通俗解释"),
    ("syntax_explanation", "语法介绍"),
    ("example_code", "示例代码"),
    ("code_explanation", "逐行解释"),
    ("example_output", "示例输出"),
    ("common_mistakes", "常见错误"),
    ("error_analysis", "错误分析"),
    ("beginner_exercises", "入门练习"),
    ("advanced_exercises", "进阶练习"),
    ("quiz_note", "本节测验"),
    ("summary", "学习总结"),
    ("next_lesson", "下一课建议"),
)

# 内容状态流转：只能按映射推进或回退，避免把未检查内容直接发布
STATUS_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"reviewed"},
    "reviewed": {"published", "draft"},
    "published": {"reviewed"},
}

# 每门课的章节规模与「超纲语法」表都在 app/core/curriculum.py，
# 这里只做转发，避免把某门课的数字与术语写进通用验收逻辑。
# 兼容旧引用：零基础课的超纲表
ADVANCED_TERMS = BASICS_SCOPE

DIFFICULTY_RANK = {"beginner": 0, "intermediate": 1, "advanced": 2}
DUPLICATION_THRESHOLD = 0.5
MIN_PLAIN_LENGTH = 60
# 除示例输出外，模块内容至少要有这么多字，用来挡掉「略」「无」「见上文」这类占位
MIN_MODULE_LENGTH = 10
# 示例输出可能只有一两行结果，单独给一个更低的下限
MIN_OUTPUT_LENGTH = 2

# 判断「示例代码是否像可运行片段」的线索。
# 前 6 个是编程语言关键词；后一组是命令行与配置文件线索——部署、
# 运维类课程的可运行片段本身就是 `git`、`docker`、`nginx`、Dockerfile
# 与 compose 配置，只用编程语言关键词会把它们全部误判为占位内容。
CODE_SAMPLE_TOKENS: tuple[str, ...] = (
    "print",
    "def ",
    "for ",
    "while ",
    "=",
    "import",
    "$ ",
    "git ",
    "docker",
    "curl ",
    "nginx",
    "pytest",
    "alembic",
    "services:",
    "FROM ",
    "RUN ",
    "CMD ",
    "#!/",
)

# 每节测验的题目分类下限：基础理解 / 代码阅读 / 应用练习 各不少于 2 道
CATEGORY_MINIMUMS: dict[str, int] = {
    "基础理解": 2,
    "代码阅读": 2,
    "应用练习": 2,
}

# 需求要求的六种题型：课程整体必须全部出现过
REQUIRED_QUESTION_TYPES: dict[str, str] = {
    "single_choice": "单选",
    "multiple_choice": "多选",
    "true_false": "判断",
    "code_analysis": "代码理解",
    "code_writing": "代码补全",
    "short_answer": "编程思路分析",
}


def _now() -> datetime:
    return datetime.now(UTC)


def _content_out(content: CourseContent | None) -> TextbookContentOut | None:
    if content is None:
        return None
    return TextbookContentOut(
        status=content.status,
        learning_objectives=content.learning_objectives,
        why_learn=content.why_learn,
        concept_explanation=content.concept_explanation,
        plain_explanation=content.plain_explanation,
        syntax_explanation=content.syntax_explanation,
        example_code=content.example_code,
        code_explanation=content.code_explanation,
        example_output=content.example_output,
        common_mistakes=content.common_mistakes,
        error_analysis=content.error_analysis,
        beginner_exercises=content.beginner_exercises,
        advanced_exercises=content.advanced_exercises,
        quiz_note=content.quiz_note,
        summary=content.summary,
        next_lesson=content.next_lesson,
    )


def _exercise_out(exercise: Exercise) -> TextbookExerciseOut:
    return TextbookExerciseOut(
        code=exercise.code,
        title=exercise.title,
        description=exercise.description,
        exercise_type=exercise.exercise_type,
        difficulty=exercise.difficulty,
        reference_answer=exercise.reference_answer,
        explanation=exercise.explanation,
    )


def _question_out(question: Question, kp_code: str) -> TextbookQuestionOut:
    return TextbookQuestionOut(
        code=question.code,
        knowledge_point_code=kp_code,
        question_type=question.question_type,
        stem=question.stem,
        options=question.options,
        correct_answer=question.correct_answer,
        explanation=question.explanation,
        difficulty=question.difficulty,
        category=question.category,
    )


def _missing_modules(content: CourseContent | None) -> list[str]:
    """返回缺失或明显过短的模块名；用来判断内容是否完整、能否发布。"""
    if content is None:
        return [label for _field, label in CONTENT_FIELDS]
    missing: list[str] = []
    for field, label in CONTENT_FIELDS:
        value = (getattr(content, field) or "").strip()
        minimum = MIN_OUTPUT_LENGTH if field == "example_output" else MIN_MODULE_LENGTH
        if not value:
            missing.append(label)
        elif len(value) < minimum:
            missing.append(f"{label}（内容过短）")
    return missing


def _shingles(text: str, size: int = 4) -> set[str]:
    normalized = re.sub(r"\s+", "", text or "")
    return {
        normalized[index : index + size]
        for index in range(max(len(normalized) - size + 1, 0))
    }


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    union = left | right
    return len(left & right) / len(union)


class TextbookService:
    """教材读取与验收。"""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = CourseRepository(db)

    # ------------------------------------------------------------ 课时教材
    def get_lesson_textbook(
        self, lesson_code: str, *, include_draft: bool = False
    ) -> LessonTextbookOut:
        lesson = self.repo.get_lesson_by_code(lesson_code)
        if lesson is None:
            raise HTTPException(status_code=404, detail="课时不存在")

        content = lesson.content
        if content is not None and content.status == "draft" and not include_draft:
            raise HTTPException(
                status_code=404,
                detail="该课时内容尚未通过检查，暂不作为正式教材提供",
            )

        kps = sorted(
            (kp for kp in lesson.knowledge_points if kp.deleted_at is None),
            key=lambda item: item.order_index,
        )
        exercises: list[Exercise] = []
        questions: list[TextbookQuestionOut] = []
        for kp in kps:
            exercises.extend(self.repo.list_exercises_by_knowledge_point(kp.id))
            questions.extend(
                _question_out(question, kp.code)
                for question in self.repo.list_questions_by_knowledge_point(kp.id)
            )

        chapter = lesson.chapter
        course = chapter.course
        return LessonTextbookOut(
            lesson_code=lesson.code,
            lesson_title=lesson.title,
            chapter_code=chapter.code,
            chapter_title=chapter.title,
            course_code=course.code,
            course_name=course.name,
            difficulty=lesson.difficulty,
            estimated_minutes=lesson.estimated_minutes,
            has_content=content is not None,
            content=_content_out(content),
            knowledge_points=[
                TextbookKnowledgePointOut(
                    code=kp.code,
                    name=kp.name,
                    learning_goal=kp.learning_goal,
                    difficulty=kp.difficulty,
                    estimated_minutes=kp.estimated_minutes,
                    mastery_criteria=kp.mastery_criteria,
                )
                for kp in kps
            ],
            exercises=[_exercise_out(item) for item in exercises],
            questions=questions,
        )

    # ------------------------------------------------------------ 课程大纲
    def get_course_textbook(
        self, course_code: str, *, status: str | None = None
    ) -> TextbookOutlineOut:
        course = self.repo.get_course_by_code(course_code)
        if course is None:
            raise HTTPException(status_code=404, detail="课程不存在")

        chapters = sorted(
            (item for item in course.chapters if item.deleted_at is None),
            key=lambda item: item.order_index,
        )
        counts = Counter()
        chapter_outs: list[TextbookChapterOut] = []
        for chapter in chapters:
            lessons = sorted(
                (item for item in chapter.lessons if item.deleted_at is None),
                key=lambda item: item.order_index,
            )
            briefs: list[TextbookLessonBrief] = []
            for lesson in lessons:
                content_status = lesson.content.status if lesson.content else None
                counts[content_status or "missing"] += 1
                if status and content_status != status:
                    continue
                briefs.append(
                    TextbookLessonBrief(
                        code=lesson.code,
                        title=lesson.title,
                        order_index=lesson.order_index,
                        estimated_minutes=lesson.estimated_minutes,
                        knowledge_point_count=len(lesson.knowledge_points),
                        content_status=content_status,
                        has_content=lesson.content is not None,
                    )
                )
            chapter_outs.append(
                TextbookChapterOut(
                    code=chapter.code,
                    title=chapter.title,
                    order_index=chapter.order_index,
                    lesson_count=len(briefs),
                    lessons=briefs,
                )
            )

        total_lessons = sum(
            len([item for item in chapter.lessons if item.deleted_at is None])
            for chapter in chapters
        )
        return TextbookOutlineOut(
            course_code=course.code,
            course_name=course.name,
            version=course.version,
            publish_status=course.publish_status,
            chapter_count=len(chapters),
            lesson_count=total_lessons,
            content_count=counts["draft"]
            + counts["reviewed"]
            + counts["published"],
            reviewed_count=counts["reviewed"],
            published_count=counts["published"],
            draft_count=counts["draft"],
            chapters=chapter_outs,
        )

    # ------------------------------------------------------------ 内容状态
    def set_content_status(
        self, lesson_code: str, status: str
    ) -> ContentStatusOut:
        lesson = self.repo.get_lesson_by_code(lesson_code)
        if lesson is None:
            raise HTTPException(status_code=404, detail="课时不存在")
        content = lesson.content
        if content is None:
            raise HTTPException(status_code=404, detail="该课时尚无教学内容")

        previous = content.status
        if status == previous:
            return ContentStatusOut(
                lesson_code=lesson.code,
                lesson_title=lesson.title,
                status=status,
                previous_status=previous,
            )
        allowed = STATUS_TRANSITIONS.get(previous, set())
        if status not in allowed:
            raise HTTPException(
                status_code=409,
                detail=f"内容状态不能从 {previous} 直接变为 {status}",
            )
        if status == "published":
            missing = _missing_modules(content)
            if missing:
                raise HTTPException(
                    status_code=400,
                    detail="内容模块不完整，不能发布：" + "、".join(missing),
                )

        content.status = status
        self.db.commit()
        return ContentStatusOut(
            lesson_code=lesson.code,
            lesson_title=lesson.title,
            status=status,
            previous_status=previous,
        )

    # ------------------------------------------------------------ 内容验收
    def audit_course(self, course_code: str) -> TextbookAuditOut:
        course = self.repo.get_course_by_code(course_code)
        if course is None:
            raise HTTPException(status_code=404, detail="课程不存在")

        chapters = sorted(
            (item for item in course.chapters if item.deleted_at is None),
            key=lambda item: item.order_index,
        )
        checks: list[AuditCheckOut] = []
        lesson_failures: list[LessonAuditOut] = []

        # 1. 章节数量与顺序（章数由课程 profile 决定）
        profile = profile_for(course_code)
        expected = profile.expected_chapters
        orders = [item.order_index for item in chapters]
        chapter_issues: list[str] = []
        if expected is not None and len(chapters) != expected:
            chapter_issues.append(f"章节数为 {len(chapters)}，应为 {expected}")
        wanted_orders = list(range(1, len(chapters) + 1))
        if orders != wanted_orders:
            chapter_issues.append(f"章节顺序不连续：{orders}")
        checks.append(
            AuditCheckOut(
                key="chapters",
                name=(
                    f"{expected} 个章节存在且顺序连续"
                    if expected is not None
                    else "章节结构完整且顺序连续"
                ),
                passed=not chapter_issues,
                detail=f"实际 {len(chapters)} 章",
                issues=chapter_issues,
            )
        )

        # 2. 每章都有完整课时
        lesson_issues: list[str] = []
        lessons: list[Lesson] = []
        for chapter in chapters:
            chapter_lessons = sorted(
                (item for item in chapter.lessons if item.deleted_at is None),
                key=lambda item: item.order_index,
            )
            if not chapter_lessons:
                lesson_issues.append(f"{chapter.title} 没有课时")
            for lesson in chapter_lessons:
                if not lesson.title or not lesson.estimated_minutes:
                    lesson_issues.append(f"{lesson.code} 缺少标题或预计时长")
                lessons.append(lesson)
        checks.append(
            AuditCheckOut(
                key="lessons",
                name="每个章节都有完整课时",
                passed=not lesson_issues,
                detail=f"共 {len(lessons)} 个课时",
                issues=lesson_issues,
            )
        )

        # 3. 15 个内容模块齐全
        module_issues: list[str] = []
        for lesson in lessons:
            missing = _missing_modules(lesson.content)
            if missing:
                module_issues.append(f"{lesson.code} 缺少：{'、'.join(missing)}")
        checks.append(
            AuditCheckOut(
                key="content_modules",
                name="教材内容 15 个模块齐全",
                passed=not module_issues,
                detail=f"检查 {len(lessons)} 个课时",
                issues=module_issues,
            )
        )

        # 4. 代码示例与输出完整
        code_issues: list[str] = []
        for lesson in lessons:
            content = lesson.content
            if content is None:
                continue
            code = content.example_code or ""
            if not code.strip():
                code_issues.append(f"{lesson.code} 没有示例代码")
                continue
            if not any(token in code for token in CODE_SAMPLE_TOKENS):
                code_issues.append(f"{lesson.code} 示例代码不像可运行片段")
            if not (content.example_output or "").strip():
                code_issues.append(f"{lesson.code} 没有示例输出")
            explained_lines = [
                line
                for line in (content.code_explanation or "").splitlines()
                if line.strip()
            ]
            if len(explained_lines) < 3:
                code_issues.append(f"{lesson.code} 逐行解释不足 3 条")
        checks.append(
            AuditCheckOut(
                key="code",
                name="代码示例、输出与逐行解释完整",
                passed=not code_issues,
                detail=f"检查 {len(lessons)} 个课时",
                issues=code_issues,
            )
        )

        # 5. 初学者友好：通俗解释独立成段且有足够长度
        plain_issues: list[str] = []
        for lesson in lessons:
            content = lesson.content
            if content is None:
                continue
            plain = (content.plain_explanation or "").strip()
            if len(plain) < MIN_PLAIN_LENGTH:
                plain_issues.append(
                    f"{lesson.code} 通俗解释过短（{len(plain)} 字）"
                )
            if plain and plain == (content.concept_explanation or "").strip():
                plain_issues.append(f"{lesson.code} 通俗解释与核心概念完全相同")
            sentences = [
                item for item in re.split(r"[。！？\n]", plain) if item.strip()
            ]
            if sentences:
                average = len(plain) / len(sentences)
                if average > 80:
                    plain_issues.append(
                        f"{lesson.code} 通俗解释句子过长（平均 {average:.0f} 字）"
                    )
        checks.append(
            AuditCheckOut(
                key="beginner_friendly",
                name="通俗解释适合初学者",
                passed=not plain_issues,
                detail="检查解释长度、独立性与句长",
                issues=plain_issues,
            )
        )

        # 6. 练习关联知识点
        exercise_issues: list[str] = []
        exercise_total = 0
        for lesson in lessons:
            kp_ids = {kp.id for kp in lesson.knowledge_points}
            exercises: list[Exercise] = []
            for kp in lesson.knowledge_points:
                exercises.extend(self.repo.list_exercises_by_knowledge_point(kp.id))
            exercise_total += len(exercises)
            if len(exercises) < 2:
                exercise_issues.append(
                    f"{lesson.code} 练习数 {len(exercises)} 少于 2"
                )
            for exercise in exercises:
                if exercise.knowledge_point_id not in kp_ids:
                    exercise_issues.append(
                        f"{exercise.code} 未关联本课时知识点"
                    )
        checks.append(
            AuditCheckOut(
                key="exercises",
                name="练习已关联对应知识点",
                passed=not exercise_issues,
                detail=f"共 {exercise_total} 个练习",
                issues=exercise_issues,
            )
        )

        # 7. 测验题关联正确、题量与题型合规
        question_issues: list[str] = []
        question_total = 0
        type_counter: Counter[str] = Counter()
        for lesson in lessons:
            kp_ids = {kp.id for kp in lesson.knowledge_points}
            lesson_questions: list[Question] = []
            for kp in lesson.knowledge_points:
                lesson_questions.extend(
                    self.repo.list_questions_by_knowledge_point(kp.id)
                )
            question_total += len(lesson_questions)
            if len(lesson_questions) < 6:
                question_issues.append(
                    f"{lesson.code} 题目数 {len(lesson_questions)} 少于 6"
                )
            # 每节必须覆盖基础理解、代码阅读、应用练习，且各不少于 2 道
            category_counter = Counter(
                question.category for question in lesson_questions
            )
            for category, minimum in CATEGORY_MINIMUMS.items():
                if category_counter[category] < minimum:
                    question_issues.append(
                        f"{lesson.code} {category}题只有 "
                        f"{category_counter[category]} 道，少于 {minimum} 道"
                    )
            lesson_rank = DIFFICULTY_RANK.get(lesson.difficulty or "beginner", 0)
            for question in lesson_questions:
                type_counter[question.question_type] += 1
                if question.knowledge_point_id not in kp_ids:
                    question_issues.append(
                        f"{question.code} 未关联本课时知识点"
                    )
                # 允许一节入门课出现少量高一级的进阶题（代码阅读/应用），
                # 但不允许跨两级（如入门课出现 advanced 题）。
                if (
                    DIFFICULTY_RANK.get(question.difficulty, 0)
                    > lesson_rank + 1
                ):
                    question_issues.append(
                        f"{question.code} 难度 {question.difficulty} 明显高于课时难度"
                    )
                if not (question.explanation or "").strip():
                    question_issues.append(f"{question.code} 缺少答案解析")
                if not question.category:
                    question_issues.append(f"{question.code} 缺少题目分类")
        # 六种题型必须都在课程里出现过，否则「题型支持」只是空话
        for question_type, label in REQUIRED_QUESTION_TYPES.items():
            if not type_counter[question_type]:
                question_issues.append(f"课程没有出现「{label}」题")
        checks.append(
            AuditCheckOut(
                key="questions",
                name="测验题题量、分类、题型、关联与解析合规",
                passed=not question_issues,
                detail=f"共 {question_total} 道题，覆盖 {len(type_counter)} 种题型",
                issues=question_issues,
            )
        )

        # 8. 不提前使用未学语法
        scope_issues: list[str] = []
        for lesson in lessons:
            content = lesson.content
            if content is None:
                continue
            chapter_order = lesson.chapter.order_index
            haystack = "\n".join(
                [content.example_code or "", content.syntax_explanation or ""]
            )
            for term, intro_order in profile.scope_terms:
                if chapter_order < intro_order and term in haystack:
                    scope_issues.append(
                        f"{lesson.code} 第 {chapter_order} 章使用了"
                        f"第 {intro_order} 章才讲的{TERM_LABELS.get(term, term)}"
                    )
        checks.append(
            AuditCheckOut(
                key="scope",
                name="不提前使用未学习的语法",
                passed=not scope_issues,
                detail="按章节顺序检查示例代码与语法说明",
                issues=scope_issues,
            )
        )

        # 9. 不同课时内容不大量重复
        duplicate_issues: list[str] = []
        fingerprints: list[tuple[str, set[str]]] = []
        for lesson in lessons:
            content = lesson.content
            if content is None:
                continue
            text = (content.concept_explanation or "") + (
                content.plain_explanation or ""
            )
            fingerprints.append((lesson.code, _shingles(text)))
        for index, (left_code, left) in enumerate(fingerprints):
            for right_code, right in fingerprints[index + 1 :]:
                similarity = _jaccard(left, right)
                if similarity > DUPLICATION_THRESHOLD:
                    duplicate_issues.append(
                        f"{left_code} 与 {right_code} 内容相似度 "
                        f"{similarity:.0%}"
                    )
        stem_counter = Counter(
            re.sub(r"\s+", "", question.stem)
            for lesson in lessons
            for kp in lesson.knowledge_points
            for question in self.repo.list_questions_by_knowledge_point(kp.id)
        )
        for stem, count in stem_counter.items():
            if count > 1:
                duplicate_issues.append(f"存在重复题干（{count} 次）：{stem[:30]}")
        checks.append(
            AuditCheckOut(
                key="duplication",
                name="课时与题目没有大量重复",
                passed=not duplicate_issues,
                detail="按 4 字片段计算相似度，阈值 50%",
                issues=duplicate_issues,
            )
        )

        # 10. 可被计划引用：每个课时都有可排期的知识点
        plan_issues: list[str] = []
        for lesson in lessons:
            schedulable = [
                kp
                for kp in lesson.knowledge_points
                if kp.estimated_minutes and kp.estimated_minutes > 0
            ]
            if not schedulable:
                plan_issues.append(f"{lesson.code} 没有可用于排期的知识点")
            for kp in lesson.knowledge_points:
                if not (kp.mastery_criteria or "").strip():
                    plan_issues.append(f"{kp.code} 缺少掌握标准")
        # 先修关系必须与课程顺序一致：前置知识点排在后面会让排期必然失败
        order_map = {
            kp.id: (lesson.chapter.order_index, kp.order_index)
            for lesson in lessons
            for kp in lesson.knowledge_points
        }
        for lesson in lessons:
            for kp in lesson.knowledge_points:
                for prerequisite in kp.prerequisites:
                    if prerequisite.id not in order_map:
                        continue
                    if order_map[prerequisite.id] > order_map[kp.id]:
                        plan_issues.append(
                            f"{kp.code} 的前置知识点 {prerequisite.code} "
                            f"排在课程更后面，无法排期"
                        )
        checks.append(
            AuditCheckOut(
                key="plan_reference",
                name="学习计划可以引用课时知识点",
                passed=not plan_issues,
                detail=f"共 {sum(len(lesson.knowledge_points) for lesson in lessons)} 个知识点可排期",
                issues=plan_issues,
            )
        )

        # 逐课时汇总失败项，便于定位
        for lesson in lessons:
            failed = [
                check.key
                for check in checks
                if any(
                    issue.startswith(lesson.code) or lesson.code in issue
                    for issue in check.issues
                )
            ]
            if failed:
                lesson_failures.append(
                    LessonAuditOut(
                        lesson_code=lesson.code,
                        lesson_title=lesson.title,
                        passed=False,
                        failed_checks=failed,
                    )
                )

        return TextbookAuditOut(
            course_code=course.code,
            course_name=course.name,
            total_chapters=len(chapters),
            total_lessons=len(lessons),
            total_questions=question_total,
            total_exercises=exercise_total,
            passed=all(check.passed for check in checks),
            checked_at=_now(),
            checks=checks,
            lesson_failures=lesson_failures,
        )
