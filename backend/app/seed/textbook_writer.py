"""教材写入器（通用版）：把一门课的完整教材幂等写入数据库。

阶段 3 只有「Python 零基础入门」一门课需要写教材，逻辑直接写在
``textbook_seed.py`` 里；阶段 4 起有多门课要写同样的结构，因此把写入流程
抽成通用函数：课程元数据 + 章节 + 课时 + 知识点 + 15 个内容模块 + 练习 + 测验题。

调用方只提供纯数据（``meta`` 与 ``chapters``），写入、同步与统计都在本模块完成。

幂等保证：
- 章节 / 课时 / 知识点 / 内容 / 练习 / 题目全部按稳定 code upsert；
- 「课时—知识点」归属按集合差集同步，重复执行收敛；
- 结构变化后遗留的旧课时（且没有教学内容）会被清理，避免出现空壳课时。
"""

from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.course import (
    Chapter,
    Course,
    CourseContent,
    Exercise,
    KnowledgePoint,
    KnowledgePointPrerequisite,
    Lesson,
    LessonKnowledgePoint,
)
from app.models.quiz import Question

CONTENT_MODULES: tuple[tuple[str, str, str], ...] = (
    ("learning_objectives", "objectives", "学习目标"),
    ("why_learn", "why_learn", "为什么学"),
    ("concept_explanation", "concepts", "核心概念"),
    ("plain_explanation", "plain", "通俗解释"),
    ("syntax_explanation", "syntax", "语法介绍"),
    ("example_code", "example_code", "示例代码"),
    ("code_explanation", "code_lines", "逐行解释"),
    ("example_output", "output", "示例输出"),
    ("common_mistakes", "mistakes", "常见错误"),
    ("error_analysis", "error_analysis", "错误分析"),
    ("beginner_exercises", "beginner_practice", "入门练习"),
    ("advanced_exercises", "advanced_practice", "进阶练习"),
    ("quiz_note", "quiz_note", "本节测验"),
    ("summary", "summary", "学习总结"),
    ("next_lesson", "next_lesson", "下一课建议"),
)


def iter_lessons(chapters: list[dict]):
    """按章序展开全部课时数据。"""
    for chapter_data in chapters:
        for lesson_data in chapter_data["lessons"]:
            yield chapter_data, lesson_data


def kp_legacy_map(chapters: list[dict]) -> dict[str, str]:
    """教材「新 code → 沿用的旧 code」映射，用于复用既有知识点记录。"""
    return {
        kp["code"]: kp["legacy"]
        for _chapter, lesson in iter_lessons(chapters)
        for kp in lesson["knowledge_points"]
        if kp.get("legacy")
    }


def kp_resolver(kps, legacy_map: dict[str, str]) -> dict[str, KnowledgePoint]:
    """按 code 找知识点的查找表，新 code 与旧 code 都指向同一条记录。"""
    by_code = {kp.code: kp for kp in kps}
    for code, legacy in legacy_map.items():
        if legacy in by_code:
            by_code[code] = by_code[legacy]
    return by_code


def _link_lessons(
    db: Session,
    chapters: list[dict],
    lessons_by_code: dict[str, Lesson],
    kp_by_code: dict[str, KnowledgePoint],
) -> tuple[int, int]:
    """同步「课时—知识点」归属，返回 (新增数, 移除数)。"""
    desired: dict[object, list[str]] = {}
    for _chapter, lesson_data in iter_lessons(chapters):
        lesson = lessons_by_code[lesson_data["code"]]
        desired[lesson.id] = [kp["code"] for kp in lesson_data["knowledge_points"]]

    existing = {
        (link.lesson_id, link.knowledge_point_id): link
        for link in db.scalars(select(LessonKnowledgePoint)).all()
        if link.lesson_id in desired
    }

    added = removed = 0
    for lesson_id, codes in desired.items():
        wanted = {kp_by_code[code].id for code in codes}
        current = {kp_id for (lid, kp_id) in existing if lid == lesson_id}
        for kp_id in wanted - current:
            order_index = next(
                index
                for index, code in enumerate(codes)
                if kp_by_code[code].id == kp_id
            )
            db.add(
                LessonKnowledgePoint(
                    lesson_id=lesson_id,
                    knowledge_point_id=kp_id,
                    order_index=order_index,
                )
            )
            added += 1
        for kp_id in current - wanted:
            db.delete(existing[(lesson_id, kp_id)])
            removed += 1
    db.flush()
    return added, removed


def _sync_prerequisites(
    db: Session,
    chapters: list[dict],
    kp_by_code: dict[str, KnowledgePoint],
) -> tuple[int, int]:
    """写入教材声明的知识点先修边，并清理「前置排在后面」的倒挂边。

    返回 (新增边数, 清理倒挂边数)。只增补声明的边，不删除未声明的边——早期
    版本的先修关系由别的种子维护，贸然删除会破坏既有课程结构。
    """
    sequence: dict = {}
    for chapter_index, chapter_data in enumerate(chapters, start=1):
        for lesson_data in chapter_data["lessons"]:
            for kp_data in lesson_data["knowledge_points"]:
                kp = kp_by_code[kp_data["code"]]
                sequence[kp.id] = (chapter_index, kp.order_index)

    existing = {
        (edge.knowledge_point_id, edge.prerequisite_kp_id)
        for edge in db.scalars(select(KnowledgePointPrerequisite)).all()
    }
    added = 0
    for _chapter, lesson_data in iter_lessons(chapters):
        for kp_data in lesson_data["knowledge_points"]:
            target = kp_by_code[kp_data["code"]]
            for prerequisite_code in kp_data.get("requires", ()):
                prerequisite = kp_by_code[prerequisite_code]
                edge = (target.id, prerequisite.id)
                if edge in existing:
                    continue
                db.add(
                    KnowledgePointPrerequisite(
                        knowledge_point_id=target.id,
                        prerequisite_kp_id=prerequisite.id,
                    )
                )
                existing.add(edge)
                added += 1
    db.flush()

    removed = 0
    for edge in db.scalars(select(KnowledgePointPrerequisite)).all():
        target = sequence.get(edge.knowledge_point_id)
        prerequisite = sequence.get(edge.prerequisite_kp_id)
        if target is None or prerequisite is None:
            continue
        if prerequisite > target:
            db.delete(edge)
            removed += 1
    db.flush()
    return added, removed


def write_textbook(
    db: Session,
    *,
    course_code: str,
    meta: dict,
    chapters: list[dict],
    content_status: str = "reviewed",
) -> dict:
    """把一门课的完整教材写入数据库，返回统计信息。

    ``chapters`` 里每节课需要 ``code`` 与 15 个内容模块的数据键；标题、说明、
    难度与时长以课程目录为准（教材侧可选提供 ``title`` 做一致性校验）。
    """
    course = db.scalars(
        select(Course).where(Course.code == course_code)
    ).first()
    if course is None:
        raise RuntimeError(
            f"课程 {course_code} 不存在，请先执行课程目录种子（seed-catalog）"
        )

    stats = {
        "chapters_created": 0,
        "chapters_updated": 0,
        "lessons_created": 0,
        "lessons_removed": 0,
        "knowledges_kept": 0,
        "knowledge_points_created": 0,
        "knowledge_points_reused": 0,
        "contents_created": 0,
        "contents_updated": 0,
        "exercises_created": 0,
        "exercises_updated": 0,
        "questions_created": 0,
        "questions_updated": 0,
        "links_added": 0,
        "links_removed": 0,
        "prerequisite_edges_added": 0,
        "prerequisite_edges_removed": 0,
    }

    # ---------------------------------------------------------------- 课程元数据
    course.name = meta["name"]
    course.description = meta["description"]
    course.learning_objectives = meta["objectives"]
    course.direction = meta.get("direction", course.direction)
    course.difficulty = meta.get("difficulty", course.difficulty)
    course.recommended_level = meta.get("level", course.recommended_level)
    course.version = meta.get("version", course.version)
    course.publish_status = meta.get("publish_status", course.publish_status)
    course.sort_order = meta.get("sort_order", course.sort_order)
    course.estimated_minutes = sum(
        lesson["minutes"] for _ch, lesson in iter_lessons(chapters) if lesson.get("minutes")
    ) or course.estimated_minutes
    db.flush()

    # ---------------------------------------------------------------- 章节
    existing_chapters = {
        chapter.code: chapter
        for chapter in db.scalars(
            select(Chapter).where(Chapter.course_id == course.id)
        ).all()
    }
    chapters_by_code: dict[str, Chapter] = {}
    for chapter_data in chapters:
        chapter = existing_chapters.get(chapter_data["code"])
        if chapter is None:
            chapter = Chapter(course_id=course.id, code=chapter_data["code"])
            db.add(chapter)
            stats["chapters_created"] += 1
        else:
            stats["chapters_updated"] += 1
        chapter.title = chapter_data["title"]
        chapter.description = chapter_data.get("description")
        chapter.order_index = chapter_data["order_index"]
        chapters_by_code[chapter_data["code"]] = chapter
    db.flush()

    # ------------------------------------- 清理不在新目录中的旧课时（仅在无正文时）
    new_lesson_codes = {lesson["code"] for _ch, lesson in iter_lessons(chapters)}
    for lesson in db.scalars(
        select(Lesson).join(Chapter).where(Chapter.course_id == course.id)
    ).all():
        if lesson.code in new_lesson_codes:
            continue
        if lesson.content is not None:
            # 有教学内容说明已经在使用，保留并计数，交由人工处理
            stats["knowledges_kept"] += 1
            continue
        db.execute(
            delete(LessonKnowledgePoint).where(
                LessonKnowledgePoint.lesson_id == lesson.id
            )
        )
        db.delete(lesson)
        stats["lessons_removed"] += 1
    db.flush()

    # ---------------------------------------------------------------- 课时
    existing_lessons = {
        lesson.code: lesson
        for lesson in db.scalars(
            select(Lesson).join(Chapter).where(Chapter.course_id == course.id)
        ).all()
    }
    lessons_by_code: dict[str, Lesson] = {}
    for chapter_data in chapters:
        chapter = chapters_by_code[chapter_data["code"]]
        for order_index, lesson_data in enumerate(chapter_data["lessons"], start=1):
            lesson = existing_lessons.get(lesson_data["code"])
            if lesson is None:
                if lesson_data.get("title") is None:
                    raise RuntimeError(
                        f"课时 {lesson_data['code']} 不存在且未提供标题，"
                        "请先执行课程目录种子（seed-catalog）"
                    )
                lesson = Lesson(code=lesson_data["code"], chapter_id=chapter.id)
                db.add(lesson)
                stats["lessons_created"] += 1
            lesson.chapter_id = chapter.id
            if lesson_data.get("title"):
                lesson.title = lesson_data["title"]
                lesson.description = lesson_data.get("description")
                lesson.difficulty = lesson_data.get(
                    "difficulty", lesson.difficulty or "intermediate"
                )
                lesson.estimated_minutes = lesson_data.get(
                    "minutes", lesson.estimated_minutes
                )
            lesson.order_index = order_index
            lessons_by_code[lesson_data["code"]] = lesson
    db.flush()

    # ---------------------------------------------------------------- 知识点
    legacy_map = kp_legacy_map(chapters)
    all_kps_by_code = {kp.code: kp for kp in db.scalars(select(KnowledgePoint)).all()}
    for chapter_data in chapters:
        chapter = chapters_by_code[chapter_data["code"]]
        # order_index 是「章节内顺序」：跨课时连续编号，避免同一章内两节课的
        # 知识点交错导致学习计划把前置知识点排到后面。
        order_index = 0
        for lesson_data in chapter_data["lessons"]:
            for kp_data in lesson_data["knowledge_points"]:
                order_index += 1
                kp = all_kps_by_code.get(kp_data["code"])
                if kp is None and kp_data.get("legacy"):
                    kp = all_kps_by_code.get(kp_data["legacy"])
                if kp is None:
                    kp = KnowledgePoint(
                        chapter_id=chapter.id, code=kp_data["code"]
                    )
                    db.add(kp)
                    stats["knowledge_points_created"] += 1
                else:
                    stats["knowledge_points_reused"] += 1
                kp.chapter_id = chapter.id
                kp.name = kp_data["name"]
                kp.learning_goal = kp_data["goal"]
                kp.difficulty = kp_data.get(
                    "difficulty", lesson_data.get("difficulty", "intermediate")
                )
                kp.estimated_minutes = kp_data["minutes"]
                kp.mastery_criteria = kp_data["criteria"]
                kp.order_index = order_index
                all_kps_by_code[kp.code] = kp
                all_kps_by_code[kp_data["code"]] = kp
                if kp_data.get("legacy"):
                    all_kps_by_code[kp_data["legacy"]] = kp
        db.flush()

    kp_by_code = kp_resolver(all_kps_by_code.values(), legacy_map)
    stats["links_added"], stats["links_removed"] = _link_lessons(
        db, chapters, lessons_by_code, kp_by_code
    )
    (
        stats["prerequisite_edges_added"],
        stats["prerequisite_edges_removed"],
    ) = _sync_prerequisites(db, chapters, kp_by_code)

    # ---------------------------------------------------------------- 教学内容
    for chapter_data in chapters:
        for lesson_data in chapter_data["lessons"]:
            lesson = lessons_by_code[lesson_data["code"]]
            content = lesson.content
            if content is None:
                content = CourseContent(lesson_id=lesson.id)
                db.add(content)
                lesson.content = content
                stats["contents_created"] += 1
            else:
                stats["contents_updated"] += 1
            for db_field, data_key, _label in CONTENT_MODULES:
                setattr(content, db_field, lesson_data[data_key])
            content.status = content_status
    db.flush()

    # ---------------------------------------------------------------- 练习
    exercise_codes = {
        practice["code"]
        for _ch, lesson in iter_lessons(chapters)
        for practice in lesson["practice"]
    }
    existing_exercises = {
        exercise.code: exercise
        for exercise in db.scalars(
            select(Exercise).where(Exercise.code.in_(exercise_codes))
        ).all()
    }
    for chapter_data in chapters:
        for lesson_data in chapter_data["lessons"]:
            kp_codes = [kp["code"] for kp in lesson_data["knowledge_points"]]
            for order_index, practice in enumerate(lesson_data["practice"], start=1):
                exercise = existing_exercises.get(practice["code"])
                if exercise is None:
                    exercise = Exercise(code=practice["code"])
                    db.add(exercise)
                    stats["exercises_created"] += 1
                else:
                    stats["exercises_updated"] += 1
                exercise.knowledge_point_id = kp_by_code[kp_codes[practice["kp"]]].id
                exercise.title = practice["title"]
                exercise.description = practice["description"]
                exercise.exercise_type = practice["type"]
                exercise.difficulty = practice["difficulty"]
                exercise.reference_answer = practice["answer"]
                exercise.explanation = practice["explanation"]
                exercise.order_index = order_index
    db.flush()

    # ---------------------------------------------------------------- 测验题
    question_codes = {
        question["code"]
        for _ch, lesson in iter_lessons(chapters)
        for question in lesson["questions"]
    }
    existing_questions = {
        question.code: question
        for question in db.scalars(
            select(Question).where(Question.code.in_(question_codes))
        ).all()
    }
    for chapter_data in chapters:
        for lesson_data in chapter_data["lessons"]:
            kp_codes = [kp["code"] for kp in lesson_data["knowledge_points"]]
            for question_data in lesson_data["questions"]:
                question = existing_questions.get(question_data["code"])
                if question is None:
                    question = Question(code=question_data["code"])
                    db.add(question)
                    stats["questions_created"] += 1
                else:
                    stats["questions_updated"] += 1
                options = question_data.get("options")
                question.knowledge_point_id = kp_by_code[
                    kp_codes[question_data["kp"]]
                ].id
                question.question_type = question_data["type"]
                question.stem = question_data["stem"]
                question.options = (
                    [{"key": key, "text": text} for key, text in options]
                    if options
                    else None
                )
                question.correct_answer = question_data["answer"]
                question.explanation = question_data["explanation"]
                question.difficulty = question_data["difficulty"]
                question.category = question_data["category"]
                question.source = "builtin"
                question.status = "approved"
                question.validation_status = "builtin"
    db.flush()

    db.commit()
    stats["lessons_total"] = len(lessons_by_code)
    stats["contents_total"] = db.scalar(
        select(func.count())
        .select_from(CourseContent)
        .join(Lesson)
        .join(Chapter)
        .where(Chapter.course_id == course.id)
    )
    return stats
