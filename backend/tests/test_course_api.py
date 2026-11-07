"""课程体系接口测试（课程列表/详情/章节/知识点）。"""

from app.seed.course_seed import seed_courses
from app.services.course_service import CourseService


def _seed(factory) -> None:
    """在 API 测试的临时数据库中写入课程种子数据。"""
    db = factory()
    try:
        seed_courses(db)
    finally:
        db.close()


def test_list_courses(api_env):
    client, factory = api_env
    _seed(factory)

    resp = client.get("/api/v1/courses")
    assert resp.status_code == 200
    courses = resp.json()
    assert len(courses) == 1
    course = courses[0]
    assert course["code"] == "python-basics"
    assert course["name"] == "Python 通用基础"
    assert course["chapter_count"] == 6
    assert course["description"]


def test_get_course_detail_with_nested_chapters(api_env):
    client, factory = api_env
    _seed(factory)

    resp = client.get("/api/v1/courses/python-basics")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["code"] == "python-basics"
    assert len(detail["chapters"]) == 6
    first = detail["chapters"][0]
    assert first["code"] == "python-basics-01"
    assert first["order_index"] == 1
    assert len(first["knowledge_points"]) == 5
    assert first["knowledge_points"][0]["code"] == "python-basics-01-01"
    # 概要字段不含掌握标准（详情在知识点接口返回）
    assert "mastery_criteria" not in first["knowledge_points"][0]


def test_list_chapters(api_env):
    client, factory = api_env
    _seed(factory)

    resp = client.get("/api/v1/courses/python-basics/chapters")
    assert resp.status_code == 200
    chapters = resp.json()
    assert [c["code"] for c in chapters] == [f"python-basics-0{i}" for i in range(1, 7)]
    # 章节内知识点按 order_index 升序
    kp_codes = [kp["code"] for kp in chapters[0]["knowledge_points"]]
    assert kp_codes == [f"python-basics-01-0{i}" for i in range(1, 6)]


def test_get_knowledge_point_detail_with_prerequisites(api_env):
    client, factory = api_env
    _seed(factory)

    resp = client.get("/api/v1/knowledge-points/python-basics-02-05")
    assert resp.status_code == 200
    kp = resp.json()
    assert kp["name"] == "类型转换"
    assert kp["learning_goal"]
    assert kp["mastery_criteria"]
    assert kp["difficulty"] == "beginner"
    assert kp["estimated_minutes"] == 15
    assert kp["chapter"] == {"code": "python-basics-02", "title": "变量与数据类型"}
    # 前置关系按稳定 code 正确关联
    assert [p["code"] for p in kp["prerequisites"]] == [
        "python-basics-02-02",
        "python-basics-02-03",
    ]


def test_get_knowledge_point_without_prerequisites(api_env):
    client, factory = api_env
    _seed(factory)

    resp = client.get("/api/v1/knowledge-points/python-basics-01-01")
    assert resp.status_code == 200
    assert resp.json()["prerequisites"] == []


def test_not_found_errors(api_env):
    client, factory = api_env
    _seed(factory)

    resp = client.get("/api/v1/courses/no-such-course")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "课程不存在"}

    resp = client.get("/api/v1/courses/no-such-course/chapters")
    assert resp.status_code == 404

    resp = client.get("/api/v1/knowledge-points/no-such-kp")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "知识点不存在"}


# ------------------------------------------------------- 资源检索相关度


def test_search_resources_ranks_specific_topic_before_generic_python(db_session):
    seed_courses(db_session)
    groups = CourseService(db_session).search_learning_resources(
        "Python 变量", limit=5
    )

    assert groups
    assert groups[0].knowledge_point_code == "python-basics-02-01"
    assert groups[0].knowledge_point_name == "变量与赋值"
    codes = [group.knowledge_point_code for group in groups]
    assert codes.index("python-basics-02-01") < codes.index("python-basics-01-01")


def test_search_resources_ranks_function_and_loop_topics_first(db_session):
    seed_courses(db_session)
    service = CourseService(db_session)

    function_groups = service.search_learning_resources("Python 函数", limit=5)
    assert function_groups
    assert function_groups[0].knowledge_point_code in {
        "python-basics-05-01",
        "python-basics-05-05",
    }
    assert function_groups[0].chapter_title == "函数与模块"

    loop_groups = service.search_learning_resources("Python 循环", limit=5)
    assert loop_groups
    assert loop_groups[0].chapter_title == "流程控制"
    assert "循环" in loop_groups[0].knowledge_point_name


def test_search_resources_by_exact_code_returns_only_that_knowledge_point(
    db_session,
):
    seed_courses(db_session)
    groups = CourseService(db_session).search_learning_resources(
        "python-basics-02-01", limit=5
    )

    assert [group.knowledge_point_code for group in groups] == [
        "python-basics-02-01"
    ]


def test_search_resources_without_match_returns_empty(db_session):
    seed_courses(db_session)
    groups = CourseService(db_session).search_learning_resources(
        "不存在的主题", limit=5
    )
    assert groups == []
