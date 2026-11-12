"""课程目录与学习路线测试（阶段 2）。

覆盖：
- 5 个课程方向与 7 门课程的目录完整性、方向关联、能力等级；
- 章节课时目录规模与 code 规则；
- 课程先修依赖图：无环、引用存在、拓扑顺序、前置/后续查询；
- 学习路径：缺基础补学提示、已掌握跳过、按知识点跳级；
- 种子幂等、非法先修拒绝、API 行为。
"""

import uuid

import pytest
from sqlalchemy import func, insert, select
from sqlalchemy.exc import IntegrityError

from app.models.course import (
    Chapter,
    Course,
    CourseDirection,
    CourseDirectionLink,
    CourseKnowledgePointPrerequisite,
    CoursePrerequisite,
    KnowledgePoint,
    Lesson,
)
from app.seed import course_catalog_seed
from app.seed.course_catalog_seed import (
    CATALOG_COURSES,
    DIRECTIONS,
    seed_course_catalog,
)
from app.seed.course_seed import seed_courses
from app.services.course_catalog_service import (
    CourseCatalogService,
    find_cycles,
    topological_order,
)

EXPECTED_COURSES = 7
# 阶段 4D 把 langgraph-agent 从目录占位（12 章 / 32 课时）扩成正式课程（28 章 / 47 课时），
# 总数随之从 77 / 160 变为 93 / 175
EXPECTED_CHAPTERS = 93
EXPECTED_LESSONS = 175


def _seed(db_session) -> None:
    """写入课程内容与目录种子（顺序与 CLI 一致）。"""
    seed_courses(db_session)
    seed_course_catalog(db_session)


# ---------------------------------------------------------------------------
# 课程方向
# ---------------------------------------------------------------------------


def test_five_directions_created_with_unique_codes(db_session):
    _seed(db_session)

    directions = list(
        db_session.scalars(
            select(CourseDirection).order_by(CourseDirection.order_index)
        ).all()
    )
    assert [item.code for item in directions] == [
        "python-fundamentals",
        "python-engineering",
        "python-backend",
        "ai-llm",
        "ai-agent",
    ]
    assert [item.name for item in directions] == [
        "Python 编程基础",
        "Python 工程与数据库",
        "Python 后端开发",
        "AI 大模型应用开发",
        "AI Agent 与综合项目",
    ]
    assert len({item.code for item in directions}) == 5


def test_directions_are_not_capability_levels(db_session):
    """方向是课程分类，L0/L1/L2 是能力等级，两者不混用。"""
    _seed(db_session)

    direction_codes = {
        item.code for item in db_session.scalars(select(CourseDirection)).all()
    }
    assert not ({"L0", "L1", "L2"} & direction_codes)

    levels = {
        course.recommended_level
        for course in db_session.scalars(select(Course)).all()
    }
    assert levels == {"L0", "L1", "L2"}


# ---------------------------------------------------------------------------
# 七门课程目录
# ---------------------------------------------------------------------------


def test_seven_courses_created_with_complete_metadata(db_session):
    _seed(db_session)

    courses = list(
        db_session.scalars(select(Course).order_by(Course.sort_order)).all()
    )
    assert len(courses) == EXPECTED_COURSES
    assert [course.code for course in courses] == [
        "python-basics",
        "python-advanced",
        "python-database",
        "fastapi-backend",
        "llm-api",
        "langgraph-agent",
        "software-engineering-deploy",
    ]
    assert len({course.code for course in courses}) == EXPECTED_COURSES

    for course in courses:
        assert course.name.strip()
        assert course.description and len(course.description) > 20
        assert course.learning_objectives and len(course.learning_objectives) > 20
        assert course.recommended_level in {"L0", "L1", "L2"}
        assert course.difficulty in {"beginner", "intermediate", "advanced"}
        assert course.version == "1.0.0"
        assert course.publish_status in {"draft", "published", "archived"}
        assert course.estimated_minutes and course.estimated_minutes > 0
        assert course.direction


def test_all_seven_courses_are_published_for_learning(db_session):
    """阶段 4E：software-engineering-deploy 补齐教材后，7 门课全部正式发布。

    发布状态由课程目录决定；草稿态的门槛校验见 test_phase6 的
    test_draft_course_and_missing_lesson_cannot_enter_formal_plan。
    """
    _seed(db_session)

    statuses = {
        course.code: course.publish_status
        for course in db_session.scalars(select(Course)).all()
    }
    assert {
        code for code, status in statuses.items() if status == "published"
    } == {
        "python-basics",
        "python-advanced",
        "python-database",
        "fastapi-backend",
        "llm-api",
        "langgraph-agent",
        "software-engineering-deploy",
    }
    assert all(status != "draft" for status in statuses.values())


def test_course_direction_links_support_multiple_directions(db_session):
    _seed(db_session)

    service = CourseCatalogService(db_session)
    catalog = service.get_catalog()

    by_code = {course.code: course for group in catalog.directions for course in group.courses}
    # 一门课可属多个方向
    assert set(by_code["python-advanced"].direction_codes) == {
        "python-fundamentals",
        "python-engineering",
    }
    assert set(by_code["langgraph-agent"].direction_codes) == {"ai-llm", "ai-agent"}
    # 主方向必须在关联方向集合中
    for course in by_code.values():
        assert course.direction in course.direction_codes


def test_each_course_has_chapter_and_lesson_catalog(db_session):
    _seed(db_session)

    courses = list(db_session.scalars(select(Course)).all())
    total_lessons = 0
    for course in courses:
        chapters = sorted(course.chapters, key=lambda item: item.order_index)
        assert chapters, f"{course.code} 没有章节"
        assert [chapter.order_index for chapter in chapters] == list(
            range(1, len(chapters) + 1)
        )
        for chapter in chapters:
            lessons = sorted(chapter.lessons, key=lambda item: item.order_index)
            assert lessons, f"{chapter.code} 没有课时"
            assert [lesson.order_index for lesson in lessons] == list(
                range(1, len(lessons) + 1)
            )
            for lesson in lessons:
                assert lesson.title.strip()
                assert lesson.description
                assert lesson.estimated_minutes and lesson.estimated_minutes > 0
            total_lessons += len(lessons)

    assert (
        db_session.scalar(select(func.count()).select_from(Chapter))
        == EXPECTED_CHAPTERS
    )
    assert total_lessons == EXPECTED_LESSONS
    assert db_session.scalar(select(func.count()).select_from(Lesson)) == EXPECTED_LESSONS


def test_lesson_codes_follow_catalog_rule(db_session):
    """课时 code 形如「章节 code-lesson-NN」，全库唯一。"""
    _seed(db_session)

    lessons = list(db_session.scalars(select(Lesson)).all())
    codes = [lesson.code for lesson in lessons]
    assert len(codes) == len(set(codes))
    for lesson in lessons:
        chapter_code = lesson.chapter.code
        assert lesson.code.startswith(f"{chapter_code}-lesson-")
        assert len(lesson.code) <= 64


# ---------------------------------------------------------------------------
# 依赖图
# ---------------------------------------------------------------------------


def test_dependency_graph_is_acyclic(db_session):
    _seed(db_session)

    graph = CourseCatalogService(db_session).get_dependency_graph()
    assert graph.valid is True
    assert graph.course_count == EXPECTED_COURSES
    assert graph.edge_count == 9
    assert graph.cycles == []
    assert graph.self_references == []
    assert graph.missing_course_references == []
    assert graph.missing_knowledge_point_references == []

    # 拓扑顺序：每条边的前置课程都排在依赖它的课程之前
    position = {code: index for index, code in enumerate(graph.topological_order)}
    assert len(position) == EXPECTED_COURSES
    for edge in graph.edges:
        assert position[edge.prerequisite_code] < position[edge.course_code]


def test_dependency_graph_matches_design(db_session):
    """对齐需求给出的依赖链：基础 → 进阶 → 数据库/大模型 → FastAPI/LangGraph → 部署。"""
    _seed(db_session)

    edges = {
        (course.code, prerequisite.code)
        for course in db_session.scalars(select(Course)).all()
        for prerequisite in course.prerequisites
    }
    assert edges == {
        ("python-advanced", "python-basics"),
        ("python-database", "python-advanced"),
        ("fastapi-backend", "python-advanced"),
        ("fastapi-backend", "python-database"),
        ("llm-api", "python-advanced"),
        ("langgraph-agent", "python-advanced"),
        ("langgraph-agent", "llm-api"),
        (
            "software-engineering-deploy",
            "fastapi-backend",
        ),
        (
            "software-engineering-deploy",
            "langgraph-agent",
        ),
    }


def test_cycle_detection_flags_injected_cycle(db_session):
    """人为制造环（基础课依赖部署课）时，检查应报出环并判定为无效。"""
    _seed(db_session)

    basics = db_session.scalars(
        select(Course).where(Course.code == "python-basics")
    ).one()
    deploy = db_session.scalars(
        select(Course).where(Course.code == "software-engineering-deploy")
    ).one()
    db_session.add(
        CoursePrerequisite(course_id=basics.id, prerequisite_course_id=deploy.id)
    )
    db_session.commit()

    graph = CourseCatalogService(db_session).get_dependency_graph()
    assert graph.valid is False
    assert graph.cycles, "应检测到循环依赖"
    assert graph.topological_order == []
    cycle = graph.cycles[0]
    assert cycle[0] == cycle[-1]
    assert "python-basics" in cycle and "software-engineering-deploy" in cycle


def test_cycle_algorithm_handles_self_loop_and_deep_chain():
    assert find_cycles(["a"], [("a", "a")]) == [["a", "a"]]
    edges = [("b", "a"), ("c", "b"), ("d", "c")]
    assert find_cycles(["a", "b", "c", "d"], edges) == []
    assert topological_order(["a", "b", "c", "d"], edges) == ["a", "b", "c", "d"]


def test_prerequisite_edges_reject_unknown_course(db_session):
    """外键保证：指向不存在的课程直接写库会被 SQLite 拒绝。"""
    _seed(db_session)

    course = db_session.scalars(
        select(Course).where(Course.code == "python-advanced")
    ).one()
    db_session.add(
        CoursePrerequisite(
            course_id=course.id,
            prerequisite_course_id=uuid.uuid4(),
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_prerequisite_edge_rejects_self_reference(db_session):
    _seed(db_session)

    course = db_session.scalars(
        select(Course).where(Course.code == "python-advanced")
    ).one()
    db_session.add(
        CoursePrerequisite(course_id=course.id, prerequisite_course_id=course.id)
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


# ---------------------------------------------------------------------------
# 前置 / 后续查询
# ---------------------------------------------------------------------------


def test_prerequisites_query_returns_direct_and_transitive(db_session):
    _seed(db_session)

    relations = CourseCatalogService(db_session).get_prerequisites(
        "software-engineering-deploy"
    )
    assert {item.code for item in relations.direct} == {
        "fastapi-backend",
        "langgraph-agent",
    }
    assert {item.code for item in relations.transitive} == {
        "python-basics",
        "python-advanced",
        "python-database",
        "fastapi-backend",
        "llm-api",
        "langgraph-agent",
    }
    # 传递闭包含直接关系
    assert {item.code for item in relations.direct} <= {
        item.code for item in relations.transitive
    }


def test_next_courses_query_returns_dependents(db_session):
    _seed(db_session)

    relations = CourseCatalogService(db_session).get_next_courses("python-basics")
    assert [item.code for item in relations.direct] == ["python-advanced"]
    assert {item.code for item in relations.transitive} == {
        "python-advanced",
        "python-database",
        "fastapi-backend",
        "llm-api",
        "langgraph-agent",
        "software-engineering-deploy",
    }

    # 叶子课程没有后续
    leaf = CourseCatalogService(db_session).get_next_courses(
        "software-engineering-deploy"
    )
    assert leaf.direct == []
    assert leaf.transitive == []


def test_missing_course_returns_404(db_session):
    from fastapi import HTTPException

    _seed(db_session)
    service = CourseCatalogService(db_session)
    with pytest.raises(HTTPException) as exc:
        service.get_prerequisites("not-exists")
    assert exc.value.status_code == 404
    with pytest.raises(HTTPException) as exc:
        service.get_next_courses("not-exists")
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# 先修写入校验
# ---------------------------------------------------------------------------


def test_add_prerequisite_rejects_self_and_unknown(db_session):
    from fastapi import HTTPException

    _seed(db_session)
    service = CourseCatalogService(db_session)

    with pytest.raises(HTTPException) as exc:
        service.add_prerequisite("python-advanced", "python-advanced")
    assert exc.value.status_code == 400

    with pytest.raises(HTTPException) as exc:
        service.add_prerequisite("python-advanced", "not-exists")
    assert exc.value.status_code == 404


def test_add_prerequisite_rejects_cycle(db_session):
    from fastapi import HTTPException

    _seed(db_session)
    service = CourseCatalogService(db_session)

    # python-basics 依赖 software-engineering-deploy 会形成环路
    with pytest.raises(HTTPException) as exc:
        service.add_prerequisite("python-basics", "software-engineering-deploy")
    assert exc.value.status_code == 409
    assert "循环依赖" in exc.value.detail


def test_add_and_remove_prerequisite_is_idempotent(db_session):
    _seed(db_session)
    service = CourseCatalogService(db_session)

    first = service.add_prerequisite(
        "software-engineering-deploy", "python-database"
    )
    assert "python-database" in {item.code for item in first.direct}

    # 重复添加不产生重复边
    service.add_prerequisite("software-engineering-deploy", "python-database")
    edge_count = db_session.scalar(
        select(func.count()).select_from(CoursePrerequisite)
    )
    assert edge_count == 10

    removed = service.remove_prerequisite(
        "software-engineering-deploy", "python-database"
    )
    assert "python-database" not in {item.code for item in removed.direct}
    assert (
        db_session.scalar(select(func.count()).select_from(CoursePrerequisite))
        == 9
    )

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        service.remove_prerequisite(
            "software-engineering-deploy", "python-database"
        )
    assert exc.value.status_code == 404


def test_required_knowledge_point_management(db_session):
    _seed(db_session)
    service = CourseCatalogService(db_session)

    result = service.add_required_knowledge_point(
        "python-database", "python-basics-06-01"
    )
    assert "python-basics-06-01" in {item.code for item in result}

    # 幂等：重复登记不重复写入
    service.add_required_knowledge_point("python-database", "python-basics-06-01")
    assert (
        db_session.scalar(
            select(func.count()).select_from(CourseKnowledgePointPrerequisite)
        )
        == 16
    )

    removed = service.remove_required_knowledge_point(
        "python-database", "python-basics-06-01"
    )
    assert "python-basics-06-01" not in {item.code for item in removed}

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        service.add_required_knowledge_point("python-database", "not-exists")
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# 学习路径
# ---------------------------------------------------------------------------


def test_learning_path_lists_missing_courses_and_knowledge_points(db_session):
    _seed(db_session)

    path = CourseCatalogService(db_session).get_learning_path("langgraph-agent")
    assert path.ready is False
    assert {item.code for item in path.missing_courses} == {
        "python-basics",
        "python-advanced",
        "llm-api",
    }
    missing_kp_codes = {item.code for item in path.missing_knowledge_points}
    # 本课程的入学知识点也在补学清单中
    assert {"python-basics-05-02", "python-basics-06-03"} <= missing_kp_codes
    assert any("先完成前置课程" in note for note in path.notes)


def test_learning_path_skips_mastered_courses(db_session):
    _seed(db_session)

    path = CourseCatalogService(db_session).get_learning_path(
        "langgraph-agent",
        mastered_course_codes=["python-advanced", "llm-api"],
        mastered_knowledge_point_codes=[
            "python-basics-05-02",
            "python-basics-06-03",
        ],
    )
    assert path.ready is True
    assert path.missing_courses == []
    assert {item.code for item in path.skipped_courses} == {
        "python-advanced",
        "llm-api",
    }
    assert all(item.reason for item in path.skipped_courses)


def test_learning_path_skips_course_after_mastering_required_knowledge_points(db_session):
    """诊断后跳级：前置课程的入学知识点已全部掌握即可跳过该课程。"""
    _seed(db_session)

    advanced = db_session.scalars(
        select(Course).where(Course.code == "python-advanced")
    ).one()
    required = [kp.code for kp in advanced.required_knowledge_points]
    assert required  # 种子已登记入学知识点

    path = CourseCatalogService(db_session).get_learning_path(
        "python-database", mastered_knowledge_point_codes=required
    )
    skipped = {item.code: item.reason for item in path.skipped_courses}
    assert "python-advanced" in skipped
    assert "可跳级" in skipped["python-advanced"]
    assert "python-advanced" not in {item.code for item in path.missing_courses}


def test_learning_path_reports_missing_knowledge_points_only(db_session):
    """前置课程都满足但基础知识点欠缺时，提示补学而不阻止进入课程。"""
    _seed(db_session)

    path = CourseCatalogService(db_session).get_learning_path(
        "python-database",
        mastered_course_codes=["python-advanced"],
    )
    assert path.missing_courses == []
    assert path.ready is False
    assert path.missing_knowledge_points
    assert any("补学" in note for note in path.notes)


# ---------------------------------------------------------------------------
# 种子幂等与校验
# ---------------------------------------------------------------------------


def test_catalog_seed_is_idempotent(db_session):
    _seed(db_session)

    def snapshot() -> dict[str, int]:
        return {
            "directions": db_session.scalar(
                select(func.count()).select_from(CourseDirection)
            ),
            "courses": db_session.scalar(select(func.count()).select_from(Course)),
            "chapters": db_session.scalar(select(func.count()).select_from(Chapter)),
            "lessons": db_session.scalar(select(func.count()).select_from(Lesson)),
            "links": db_session.scalar(
                select(func.count()).select_from(CourseDirectionLink)
            ),
            "edges": db_session.scalar(
                select(func.count()).select_from(CoursePrerequisite)
            ),
            "kp_edges": db_session.scalar(
                select(func.count()).select_from(CourseKnowledgePointPrerequisite)
            ),
        }

    before = snapshot()
    second = seed_course_catalog(db_session)
    assert snapshot() == before
    assert second["prerequisites"] == 0
    assert second["required_knowledge_points"] == 0

    # 内容种子与目录种子交替执行也不会漂移（最终收敛到同一状态）
    seed_courses(db_session)
    seed_course_catalog(db_session)
    assert snapshot() == before


def test_catalog_seed_requires_existing_knowledge_points(db_session):
    """只跑目录种子、缺少内容种子时，应明确报错而不是写入悬挂引用。"""
    with pytest.raises(RuntimeError, match="知识点不存在"):
        seed_course_catalog(db_session)


def test_catalog_definition_has_no_duplicate_codes():
    codes = [item["code"] for item in CATALOG_COURSES]
    assert len(codes) == len(set(codes)) == EXPECTED_COURSES

    direction_codes = [item["code"] for item in DIRECTIONS]
    assert len(direction_codes) == len(set(direction_codes)) == 5


def test_catalog_validation_rejects_dangling_prerequisite(monkeypatch):
    broken = [dict(item) for item in CATALOG_COURSES]
    broken[1] = {**broken[1], "prerequisites": ["not-exists"]}
    monkeypatch.setattr(course_catalog_seed, "CATALOG_COURSES", broken)

    with pytest.raises(ValueError, match="先修课程不存在"):
        course_catalog_seed.validate_catalog()


def test_catalog_validation_rejects_cycle(monkeypatch):
    broken = [dict(item) for item in CATALOG_COURSES]
    broken[0] = {**broken[0], "prerequisites": ["software-engineering-deploy"]}
    monkeypatch.setattr(course_catalog_seed, "CATALOG_COURSES", broken)

    with pytest.raises(ValueError, match="循环"):
        course_catalog_seed.validate_catalog()


def test_catalog_validation_rejects_level_used_as_direction(monkeypatch):
    """把 L0 当方向写进目录应被拒绝，防止分类与等级混用。"""
    broken = [dict(item) for item in CATALOG_COURSES]
    broken[0] = {**broken[0], "direction": "L0", "directions": ["L0"]}
    monkeypatch.setattr(course_catalog_seed, "CATALOG_COURSES", broken)

    with pytest.raises(ValueError, match="主方向不存在"):
        course_catalog_seed.validate_catalog()


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


def _seed_api(factory) -> None:
    db = factory()
    try:
        seed_courses(db)
        seed_course_catalog(db)
    finally:
        db.close()


def test_api_course_directions_and_catalog(api_env):
    client, factory = api_env
    _seed_api(factory)

    resp = client.get("/api/v1/course-directions")
    assert resp.status_code == 200
    directions = resp.json()
    assert [item["code"] for item in directions] == [
        "python-fundamentals",
        "python-engineering",
        "python-backend",
        "ai-llm",
        "ai-agent",
    ]
    assert all(item["course_count"] == 2 for item in directions)

    resp = client.get("/api/v1/course-catalog")
    assert resp.status_code == 200
    catalog = resp.json()
    assert catalog["total_courses"] == EXPECTED_COURSES
    assert catalog["total_chapters"] == EXPECTED_CHAPTERS
    assert catalog["total_lessons"] == EXPECTED_LESSONS

    # 学习入口只看已发布课程（阶段 4E 后 7 门课都已有教材）
    resp = client.get("/api/v1/course-catalog?publish_status=published")
    published = resp.json()
    assert published["total_courses"] == 7
    assert {
        course["code"]
        for group in published["directions"]
        for course in group["courses"]
    } | {
        course["code"] for course in published["ungrouped"]
    } == {
        "python-basics",
        "python-advanced",
        "python-database",
        "fastapi-backend",
        "llm-api",
        "langgraph-agent",
        "software-engineering-deploy",
    }

    resp = client.get("/api/v1/courses?direction=python-engineering")
    assert resp.status_code == 200
    # 阶段 6 起该方向两门课均已正式发布，默认（published）即可见
    assert {item["code"] for item in resp.json()} == {
        "python-advanced",
        "python-database",
    }
    resp = client.get(
        "/api/v1/courses?direction=python-engineering&publish_status=all"
    )
    assert {item["code"] for item in resp.json()} == {
        "python-advanced",
        "python-database",
    }


def test_api_dependency_graph_and_relations(api_env):
    client, factory = api_env
    _seed_api(factory)

    resp = client.get("/api/v1/course-catalog/dependency-graph")
    assert resp.status_code == 200
    graph = resp.json()
    assert graph["valid"] is True
    assert graph["edge_count"] == 9
    assert graph["cycles"] == []

    resp = client.get("/api/v1/courses/python-basics/next-courses")
    assert resp.status_code == 200
    assert [item["code"] for item in resp.json()["direct"]] == ["python-advanced"]

    resp = client.get("/api/v1/courses/software-engineering-deploy/prerequisites")
    assert resp.status_code == 200
    assert {item["code"] for item in resp.json()["direct"]} == {
        "fastapi-backend",
        "langgraph-agent",
    }

    resp = client.get("/api/v1/courses/not-exists/prerequisites")
    assert resp.status_code == 404


def test_api_learning_path_with_mastery(api_env):
    client, factory = api_env
    _seed_api(factory)

    resp = client.get("/api/v1/courses/langgraph-agent/learning-path")
    assert resp.status_code == 200
    path = resp.json()
    assert path["ready"] is False
    assert {item["code"] for item in path["missing_courses"]} == {
        "python-basics",
        "python-advanced",
        "llm-api",
    }

    resp = client.get(
        "/api/v1/courses/langgraph-agent/learning-path"
        "?preview=true"
        "&mastered_courses=python-advanced,llm-api"
        "&mastered=python-basics-05-02,python-basics-06-03"
    )
    assert resp.status_code == 200
    assert resp.json()["ready"] is True
    assert resp.json()["missing_courses"] == []


def test_api_prerequisite_write_validation(api_env):
    client, factory = api_env
    _seed_api(factory)

    resp = client.post(
        "/api/v1/courses/software-engineering-deploy/prerequisites",
        json={"prerequisite_code": "python-database"},
    )
    assert resp.status_code == 201
    assert "python-database" in {
        item["code"] for item in resp.json()["direct"]
    }

    resp = client.post(
        "/api/v1/courses/python-basics/prerequisites",
        json={"prerequisite_code": "python-basics"},
    )
    assert resp.status_code == 400

    resp = client.post(
        "/api/v1/courses/python-basics/prerequisites",
        json={"prerequisite_code": "not-exists"},
    )
    assert resp.status_code == 404

    resp = client.post(
        "/api/v1/courses/python-advanced/prerequisites",
        json={"prerequisite_code": "software-engineering-deploy"},
    )
    assert resp.status_code == 409

    resp = client.delete(
        "/api/v1/courses/software-engineering-deploy/prerequisites/python-database"
    )
    assert resp.status_code == 200
    assert {item["code"] for item in resp.json()["direct"]} == {
        "fastapi-backend",
        "langgraph-agent",
    }


def test_api_course_detail_exposes_directions_and_prerequisites(api_env):
    client, factory = api_env
    _seed_api(factory)

    resp = client.get("/api/v1/courses/fastapi-backend")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["recommended_level"] == "L2"
    assert [item["code"] for item in detail["directions"]] == ["python-backend"]
    assert {item["code"] for item in detail["prerequisites"]} == {
        "python-advanced",
        "python-database",
    }
    assert {item["code"] for item in detail["required_knowledge_points"]} == {
        "python-basics-05-04",
        "python-basics-06-01",
        "python-basics-06-03",
    }


def test_api_catalog_rejects_unknown_direction(api_env):
    client, factory = api_env
    _seed_api(factory)

    resp = client.get("/api/v1/course-catalog?direction=not-exists")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 迁移与新表
# ---------------------------------------------------------------------------


def test_catalog_tables_have_expected_constraints(db_session):
    """方向 code 唯一、方向关联联合主键、先修禁止自引用。"""
    _seed(db_session)

    direction = CourseDirection(code="python-fundamentals", name="重复方向")
    db_session.add(direction)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()

    course = db_session.scalars(
        select(Course).where(Course.code == "python-advanced")
    ).one()
    existing = db_session.scalars(
        select(CourseDirectionLink).where(
            CourseDirectionLink.course_id == course.id
        )
    ).first()
    # 绕过 ORM identity map，直接插入重复的联合主键，验证数据库层约束
    with pytest.raises(IntegrityError):
        db_session.execute(
            insert(CourseDirectionLink).values(
                course_id=existing.course_id, direction_id=existing.direction_id
            )
        )
    db_session.rollback()


def test_knowledge_points_remain_intact_after_catalog_seed(db_session):
    """目录种子不修改既有课程的知识点与题库关系。"""
    seed_courses(db_session)
    before = db_session.scalar(select(func.count()).select_from(KnowledgePoint))
    assert before == 31

    seed_course_catalog(db_session)
    assert (
        db_session.scalar(select(func.count()).select_from(KnowledgePoint))
        == before
    )
    # 新课只建结构化目录，不伪造知识点
    kp_course_codes = {
        kp.chapter.course.code
        for kp in db_session.scalars(select(KnowledgePoint)).all()
    }
    assert kp_course_codes == {"python-basics"}
