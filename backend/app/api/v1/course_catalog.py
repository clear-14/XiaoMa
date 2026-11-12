"""课程目录与学习路线接口（阶段 2）。

路径分组：
- ``/course-directions``：课程方向（课程分类，与 L0/L1/L2 能力等级正交）；
- ``/course-catalog``：目录总览与依赖图检查；
- ``/courses/{code}/prerequisites``、``/next-courses``：前置与后续课程；
- ``/courses/{code}/learning-path``：学习路径建议（跳过已掌握、缺基础补学）。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.course import CourseDifficulty, CourseLevel
from app.schemas.course_catalog import (
    CourseCatalogOut,
    CourseKnowledgePointPrerequisiteCreate,
    CourseRelationsOut,
    DependencyGraphOut,
    DirectionOut,
    KnowledgePointBrief,
    LearningPathOut,
    PrerequisiteCreate,
)
from app.services.course_catalog_service import CourseCatalogService
from app.services.mastery_service import MasteryService

router = APIRouter(tags=["course-catalog"])


def _split_codes(value: str | None) -> list[str]:
    """把逗号分隔的 code 列表解析为去空白的列表。"""
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


@router.get("/course-directions", response_model=list[DirectionOut])
def list_course_directions(db: Session = Depends(get_db)) -> list[DirectionOut]:
    """课程方向列表（含各方向课程数），按目录顺序排列。"""
    return CourseCatalogService(db).list_directions()


@router.get("/course-catalog", response_model=CourseCatalogOut)
def get_course_catalog(
    direction: str | None = Query(default=None, description="按方向 code 筛选"),
    recommended_level: CourseLevel | None = Query(
        default=None, description="按推荐能力等级筛选：L0/L1/L2"
    ),
    difficulty: CourseDifficulty | None = Query(
        default=None, description="按课程难度筛选"
    ),
    publish_status: str = Query(
        default="all",
        description="发布状态：draft / published / archived / all（默认全部，目录管理视图）",
    ),
    db: Session = Depends(get_db),
) -> CourseCatalogOut:
    """课程目录总览：按方向分组，附章节/课时规模与直接先修课程。"""
    return CourseCatalogService(db).get_catalog(
        direction=direction,
        recommended_level=recommended_level,
        difficulty=difficulty,
        publish_status=publish_status,
    )


@router.get("/course-catalog/dependency-graph", response_model=DependencyGraphOut)
def get_dependency_graph(db: Session = Depends(get_db)) -> DependencyGraphOut:
    """课程先修依赖图：边、环检测、引用完整性与拓扑顺序。"""
    return CourseCatalogService(db).get_dependency_graph()


@router.get(
    "/courses/{course_code}/prerequisites", response_model=CourseRelationsOut
)
def get_course_prerequisites(
    course_code: str, db: Session = Depends(get_db)
) -> CourseRelationsOut:
    """查询课程的前置课程：直接关系与传递闭包。"""
    return CourseCatalogService(db).get_prerequisites(course_code)


@router.get(
    "/courses/{course_code}/next-courses", response_model=CourseRelationsOut
)
def get_next_courses(
    course_code: str, db: Session = Depends(get_db)
) -> CourseRelationsOut:
    """查询学完该课程后可进入的后续课程：直接与传递。"""
    return CourseCatalogService(db).get_next_courses(course_code)


@router.post(
    "/courses/{course_code}/prerequisites",
    response_model=CourseRelationsOut,
    status_code=201,
)
def add_course_prerequisite(
    course_code: str,
    payload: PrerequisiteCreate,
    db: Session = Depends(get_db),
) -> CourseRelationsOut:
    """新增先修关系：校验课程存在、拒绝自引用与循环依赖，重复添加幂等。"""
    return CourseCatalogService(db).add_prerequisite(
        course_code, payload.prerequisite_code
    )


@router.delete(
    "/courses/{course_code}/prerequisites/{prerequisite_code}",
    response_model=CourseRelationsOut,
)
def remove_course_prerequisite(
    course_code: str,
    prerequisite_code: str,
    db: Session = Depends(get_db),
) -> CourseRelationsOut:
    """删除先修关系（不存在时返回 404）。"""
    return CourseCatalogService(db).remove_prerequisite(
        course_code, prerequisite_code
    )


@router.get(
    "/courses/{course_code}/learning-path", response_model=LearningPathOut
)
def get_learning_path(
    course_code: str,
    mastered: str | None = Query(
        default=None, description="已掌握的知识点 code，逗号分隔（仅 preview=true 时生效）"
    ),
    mastered_courses: str | None = Query(
        default=None, description="已掌握的课程 code，逗号分隔（仅 preview=true 时生效）"
    ),
    preview: bool = Query(
        default=False,
        description=(
            "预览模式：用请求里的 code 计算跳过（纯演算，不写入任何记录）。"
            "默认 false：只采信后端掌握证据，自述不会让路径变成可跳级"
        ),
    ),
    db: Session = Depends(get_db),
) -> LearningPathOut:
    """学习路径建议：能否开始、缺哪些前置课程/知识点、哪些可跳过。

    阶段 5 起默认按「实际掌握证据」计算；``preview=true`` 才使用请求参数，
    避免仅凭一次请求就宣布局部或全部先修已满足。
    """
    if preview:
        return CourseCatalogService(db).get_learning_path(
            course_code,
            mastered_course_codes=_split_codes(mastered_courses),
            mastered_knowledge_point_codes=_split_codes(mastered),
        )
    verified = sorted(MasteryService(db).mastered_kp_codes())
    return CourseCatalogService(db).get_learning_path(
        course_code,
        mastered_knowledge_point_codes=verified,
    )


@router.post(
    "/courses/{course_code}/required-knowledge-points",
    response_model=list[KnowledgePointBrief],
    status_code=201,
)
def add_required_knowledge_point(
    course_code: str,
    payload: CourseKnowledgePointPrerequisiteCreate,
    db: Session = Depends(get_db),
) -> list[KnowledgePointBrief]:
    """登记课程的入学知识点（可跨课程），返回更新后的完整清单。"""
    return CourseCatalogService(db).add_required_knowledge_point(
        course_code, payload.knowledge_point_code
    )


@router.delete(
    "/courses/{course_code}/required-knowledge-points/{knowledge_point_code}",
    response_model=list[KnowledgePointBrief],
)
def remove_required_knowledge_point(
    course_code: str,
    knowledge_point_code: str,
    db: Session = Depends(get_db),
) -> list[KnowledgePointBrief]:
    """移除课程的入学知识点，返回更新后的完整清单。"""
    return CourseCatalogService(db).remove_required_knowledge_point(
        course_code, knowledge_point_code
    )
