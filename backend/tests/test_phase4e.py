"""阶段 4E 验收测试：「软件工程与项目部署」课程教材。

覆盖需求给出的六部分要求：

1. 课程可学（发布状态为 published，7 门课全部对外可见）；
2. 结构对齐（8 章 28 课时，章节与课时 code 由课程目录生成）；
3. 内容完整（每课时 15 个内容模块全部非空，正文有实际体量）；
4. 知识点与先修关系正确（每课 1 个知识点，前置不倒挂、不引用未知知识点）；
5. 练习与测验合规（每课 2 练习、6 题，答案格式符合判分契约且能被真实判分）；
6. 写入幂等，且不影响其它课程的数据。
"""

from sqlalchemy import func, select

from app.models.course import (
    Chapter,
    Course,
    CourseContent,
    CourseKnowledgePointPrerequisite,
    CoursePrerequisite,
    Exercise,
    KnowledgePoint,
    KnowledgePointPrerequisite,
    Lesson,
    LessonKnowledgePoint,
)
from app.models.quiz import Question
from app.seed.course_catalog_seed import CATALOG_COURSES, seed_course_catalog
from app.seed.course_seed import seed_courses
from app.seed.deploy import CHAPTERS, COURSE_CODE, META
from app.seed.phase4e_seed import seed_phase4e
from app.seed.question_seed import seed_questions
from app.seed.textbook_seed import seed_textbook
from app.seed.textbook_writer import CONTENT_MODULES
from app.services.quiz_grading import grade_answer

SED = COURSE_CODE
EXPECTED_CHAPTERS = 8
EXPECTED_LESSONS = 28
EXPECTED_EXERCISES = 56
EXPECTED_QUESTIONS = 168


def _seed(db) -> None:
    # 与 CLI 的初始化顺序一致：基础课内容 → 课程目录 → 题库 → 基础教材 → 阶段 4E
    seed_courses(db)
    seed_course_catalog(db)
    seed_questions(db)
    seed_textbook(db)
    seed_phase4e(db)


def _course(db) -> Course:
    return db.scalars(select(Course).where(Course.code == SED)).one()


def _chapters(db) -> list[Chapter]:
    return sorted(_course(db).chapters, key=lambda item: item.order_index)


def _lessons(db) -> list[Lesson]:
    lessons: list[Lesson] = []
    for chapter in _chapters(db):
        lessons.extend(sorted(chapter.lessons, key=lambda item: item.order_index))
    return lessons


def _content_of(db, lesson: Lesson) -> CourseContent:
    return db.scalars(
        select(CourseContent).where(CourseContent.lesson_id == lesson.id)
    ).one()


# ---------------------------------------------------------------------------
# 一、课程可学
# ---------------------------------------------------------------------------


def test_course_is_published_and_visible(db_session):
    _seed(db_session)
    course = _course(db_session)
    assert course.publish_status == "published"
    assert course.name == META["name"]
    assert course.difficulty == META["difficulty"]

    published = db_session.scalars(
        select(Course.code).where(Course.publish_status == "published")
    ).all()
    assert set(published) == {
        "python-basics",
        "python-advanced",
        "python-database",
        "fastapi-backend",
        "llm-api",
        "langgraph-agent",
        SED,
    }


# ---------------------------------------------------------------------------
# 二、结构对齐课程目录
# ---------------------------------------------------------------------------


def test_chapters_and_lessons_match_catalog(db_session):
    _seed(db_session)
    catalog = next(item for item in CATALOG_COURSES if item["code"] == SED)

    assert len(_chapters(db_session)) == EXPECTED_CHAPTERS == len(catalog["modules"])
    assert len(_lessons(db_session)) == EXPECTED_LESSONS

    expected_codes = {
        f'{module["code"]}-lesson-{index:02d}'
        for module in catalog["modules"]
        for index, _lesson in enumerate(module["lessons"], start=1)
    }
    assert {lesson.code for lesson in _lessons(db_session)} == expected_codes

    # 课时标题与目录一致（目录是标题的唯一来源）
    expected_titles = {
        f'{module["code"]}-lesson-{index:02d}': title
        for module in catalog["modules"]
        for index, (title, *_rest) in enumerate(module["lessons"], start=1)
    }
    assert {
        lesson.code: lesson.title for lesson in _lessons(db_session)
    } == expected_titles


def test_each_lesson_has_all_content_modules(db_session):
    _seed(db_session)
    for lesson in _lessons(db_session):
        content = _content_of(db_session, lesson)
        for db_field, _data_key, label in CONTENT_MODULES:
            text = getattr(content, db_field)
            assert isinstance(text, str), f"{lesson.code} 的「{label}」缺失"
            assert len(text.strip()) >= 10, f"{lesson.code} 的「{label}」内容过短"
        assert content.status == "reviewed"


def test_textbook_has_real_volume(db_session):
    _seed(db_session)
    contents = [
        _content_of(db_session, lesson) for lesson in _lessons(db_session)
    ]
    total = sum(
        sum(
            len(getattr(content, db_field) or "")
            for db_field, _key, _label in CONTENT_MODULES
        )
        for content in contents
    )
    # 28 课时合计正文（不含练习与题目）应有十万字量级
    assert total > 100_000
    shortest = min(
        sum(
            len(getattr(content, db_field) or "")
            for db_field, _key, _label in CONTENT_MODULES
        )
        for content in contents
    )
    assert shortest > 2_000


def test_example_code_blocks_are_present(db_session):
    """每课都要有可直接照抄的命令/代码与对应输出。"""
    _seed(db_session)
    for lesson in _lessons(db_session):
        content = _content_of(db_session, lesson)
        assert "```" in content.example_code or len(content.example_code) > 80
        assert len(content.example_output) > 20


# ---------------------------------------------------------------------------
# 三、知识点与先修关系
# ---------------------------------------------------------------------------


def test_each_lesson_maps_one_knowledge_point(db_session):
    _seed(db_session)
    for lesson in _lessons(db_session):
        links = db_session.scalars(
            select(LessonKnowledgePoint).where(
                LessonKnowledgePoint.lesson_id == lesson.id
            )
        ).all()
        assert len(links) == 1, f"{lesson.code} 应关联 1 个知识点"
    kps = db_session.scalars(
        select(KnowledgePoint).where(KnowledgePoint.code.like(f"{SED}-%"))
    ).all()
    assert len(kps) == EXPECTED_LESSONS


def test_knowledge_point_prerequisites_are_ordered(db_session):
    """前置知识点必须在本课之前出现，且不引用未知知识点。"""
    _seed(db_session)
    ordered = [
        kp.code
        for kp in db_session.scalars(
            select(KnowledgePoint).where(KnowledgePoint.code.like(f"{SED}-%"))
        ).all()
    ]
    position = {}
    for lesson in _lessons(db_session):
        link = db_session.scalars(
            select(LessonKnowledgePoint).where(
                LessonKnowledgePoint.lesson_id == lesson.id
            )
        ).one()
        kp = db_session.get(KnowledgePoint, link.knowledge_point_id)
        position[kp.code] = len(position)

    assert set(position) == set(ordered)

    id_to_code = {
        kp.id: kp.code
        for kp in db_session.scalars(
            select(KnowledgePoint).where(KnowledgePoint.code.like(f"{SED}-%"))
        ).all()
    }
    for edge in db_session.scalars(select(KnowledgePointPrerequisite)).all():
        current = id_to_code.get(edge.knowledge_point_id)
        required = id_to_code.get(edge.prerequisite_kp_id)
        if current is None:
            continue  # 其它课程内部的前置关系
        assert required in position, f"{current} 引用了未知前置 {required}"
        assert position[required] < position[current], f"{current} 的前置倒挂"


def test_course_prerequisites_and_entry_points(db_session):
    _seed(db_session)
    course = _course(db_session)
    course_codes = {item.id: item.code for item in db_session.scalars(select(Course)).all()}
    prerequisites = {
        course_codes[edge.prerequisite_course_id]
        for edge in db_session.scalars(
            select(CoursePrerequisite).where(CoursePrerequisite.course_id == course.id)
        ).all()
    }
    assert prerequisites == {"fastapi-backend", "langgraph-agent"}

    kp_codes = {
        kp.id: kp.code for kp in db_session.scalars(select(KnowledgePoint)).all()
    }
    entry = {
        kp_codes[link.knowledge_point_id]
        for link in db_session.scalars(
            select(CourseKnowledgePointPrerequisite).where(
                CourseKnowledgePointPrerequisite.course_id == course.id
            )
        ).all()
    }
    assert entry == {"python-basics-05-04"}


# ---------------------------------------------------------------------------
# 四、练习与测验
# ---------------------------------------------------------------------------


def test_exercises_per_lesson(db_session):
    _seed(db_session)
    for lesson in _lessons(db_session):
        exercises = db_session.scalars(
            select(Exercise)
            .where(Exercise.knowledge_point_id.in_(
                select(LessonKnowledgePoint.knowledge_point_id).where(
                    LessonKnowledgePoint.lesson_id == lesson.id
                )
            ))
            .order_by(Exercise.order_index)
        ).all()
        assert len(exercises) == 2, f"{lesson.code} 应有 2 道练习"
        assert [item.order_index for item in exercises] == [1, 2]
        # 入门练习在前，进阶练习在后（难度按内容需要可为 beginner/intermediate/advanced）
        assert exercises[0].difficulty in {"beginner", "intermediate"}
        for item in exercises:
            assert item.reference_answer and item.explanation


def test_questions_per_lesson_and_categories(db_session):
    _seed(db_session)
    total = 0
    for lesson in _lessons(db_session):
        questions = db_session.scalars(
            select(Question).where(
                Question.knowledge_point_id.in_(
                    select(LessonKnowledgePoint.knowledge_point_id).where(
                        LessonKnowledgePoint.lesson_id == lesson.id
                    )
                )
            )
        ).all()
        assert len(questions) == 6, f"{lesson.code} 应有 6 道题"
        assert {item.category for item in questions} == {
            "基础理解",
            "代码阅读",
            "应用练习",
        }
        assert all(item.source == "builtin" and item.status == "approved" for item in questions)
        total += len(questions)
    assert total == EXPECTED_QUESTIONS


def test_question_answer_contract_matches_grading(db_session):
    """每种题型的答案格式必须能被真实判分函数接受。"""
    _seed(db_session)
    questions = db_session.scalars(
        select(Question).where(Question.code.like("q-sed-%"))
    ).all()
    assert len(questions) == EXPECTED_QUESTIONS
    seen: set[str] = set()
    for question in questions:
        if question.question_type == "true_false":
            assert isinstance(question.correct_answer.get("value"), bool)
            assert question.options is None
        elif question.question_type == "single_choice":
            assert isinstance(question.correct_answer.get("value"), str)
            assert len(question.options or []) == 4
        elif question.question_type == "multiple_choice":
            assert len(question.correct_answer.get("values") or []) >= 2
            assert len(question.options or []) == 4
        else:
            # 主观题：无选项，答案里必须有参考答案与评分关键词
            assert question.options is None
            assert question.correct_answer.get("reference")
            assert question.correct_answer.get("keywords")
        # 选择题用答案键值判分，主观题用参考答案原文提交（应覆盖全部关键词）
        submitted = (
            question.correct_answer
            if question.question_type
            in {"single_choice", "multiple_choice", "true_false"}
            else question.correct_answer["reference"]
        )
        result = grade_answer(question, submitted)
        assert result.is_correct, f"{question.code} 用标准答案判分应为正确"
        seen.add(question.question_type)
    # 课程整体覆盖平台要求的六种题型
    assert seen == {
        "single_choice",
        "multiple_choice",
        "true_false",
        "code_analysis",
        "code_writing",
        "short_answer",
    }


def test_course_audit_passes(db_session):
    """教材验收 10 项确定性检查全部通过。"""
    from app.services.textbook_service import TextbookService

    _seed(db_session)
    audit = TextbookService(db_session).audit_course(SED)
    failed = [f"{check.key}: {check.issues[:3]}" for check in audit.checks if not check.passed]
    assert audit.passed, failed
    assert len(audit.checks) == 10
    assert audit.total_questions == EXPECTED_QUESTIONS
    assert audit.total_exercises == EXPECTED_EXERCISES


# ---------------------------------------------------------------------------
# 五、幂等与其它课程隔离
# ---------------------------------------------------------------------------


def test_seed_is_idempotent(db_session):
    _seed(db_session)
    snapshot = (
        db_session.scalar(select(func.count()).select_from(Lesson)),
        db_session.scalar(select(func.count()).select_from(CourseContent)),
        db_session.scalar(select(func.count()).select_from(Exercise)),
        db_session.scalar(select(func.count()).select_from(Question)),
    )
    stats = seed_phase4e(db_session)
    assert stats[SED]["contents_created"] == 0
    assert stats[SED]["exercises_created"] == 0
    assert stats[SED]["questions_created"] == 0
    assert stats[SED]["lessons_removed"] == 0
    after = (
        db_session.scalar(select(func.count()).select_from(Lesson)),
        db_session.scalar(select(func.count()).select_from(CourseContent)),
        db_session.scalar(select(func.count()).select_from(Exercise)),
        db_session.scalar(select(func.count()).select_from(Question)),
    )
    assert after == snapshot


def test_other_courses_untouched(db_session):
    _seed(db_session)
    before = {
        code: (
            db_session.scalar(
                select(func.count())
                .select_from(Lesson)
                .join(Chapter)
                .join(Course)
                .where(Course.code == code)
            ),
            db_session.scalar(
                select(func.count())
                .select_from(CourseContent)
                .join(Lesson)
                .join(Chapter)
                .join(Course)
                .where(Course.code == code)
            ),
        )
        for code in (
            "python-basics",
            "fastapi-backend",
            "langgraph-agent",
        )
    }
    seed_phase4e(db_session)
    after = {
        code: (
            db_session.scalar(
                select(func.count())
                .select_from(Lesson)
                .join(Chapter)
                .join(Course)
                .where(Course.code == code)
            ),
            db_session.scalar(
                select(func.count())
                .select_from(CourseContent)
                .join(Lesson)
                .join(Chapter)
                .join(Course)
                .where(Course.code == code)
            ),
        )
        for code in before
    }
    assert after == before
    # python-basics 的教材由本测试一并种入，应当有内容；其余课程只校验不被改写
    assert after["python-basics"][0] > 0 and after["python-basics"][1] > 0
    assert all(lessons > 0 for lessons, _contents in after.values())


def test_seed_data_matches_module_definition(db_session):
    """库里落的内容与 ``app.seed.deploy.CHAPTERS`` 完全一致。"""
    _seed(db_session)
    by_code = {lesson.code: lesson for lesson in _lessons(db_session)}
    for chapter in CHAPTERS:
        for lesson_data in chapter["lessons"]:
            content = _content_of(db_session, by_code[lesson_data["code"]])
            for db_field, data_key, _label in CONTENT_MODULES:
                assert getattr(content, db_field) == lesson_data[data_key]
