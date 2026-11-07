"""课程体系数据访问层。"""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.course import Chapter, Course, KnowledgePoint


class CourseRepository:
    """课程/章节/知识点的数据库读写。

    查询统一过滤软删除（deleted_at IS NULL）；关系中的软删除子项由 Service 层过滤。
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_courses(self) -> list[Course]:
        """全部未删除课程，按创建时间升序。"""
        stmt = (
            select(Course)
            .where(Course.deleted_at.is_(None))
            .order_by(Course.created_at.asc())
            .options(selectinload(Course.chapters))
        )
        return list(self.db.scalars(stmt).all())

    def get_course_by_code(self, code: str) -> Course | None:
        """按稳定标识查课程，级联预取章节与知识点（章节/知识点按 order_index 排序）。"""
        stmt = (
            select(Course)
            .where(Course.code == code, Course.deleted_at.is_(None))
            .options(
                selectinload(Course.chapters).options(
                    selectinload(Chapter.knowledge_points)
                )
            )
        )
        return self.db.scalars(stmt).first()

    def get_knowledge_point_by_code(self, code: str) -> KnowledgePoint | None:
        """按稳定标识查知识点，预取所属章节与前置知识点。"""
        stmt = (
            select(KnowledgePoint)
            .where(KnowledgePoint.code == code, KnowledgePoint.deleted_at.is_(None))
            .options(
                selectinload(KnowledgePoint.chapter),
                selectinload(KnowledgePoint.prerequisites),
            )
        )
        return self.db.scalars(stmt).first()

    def get_chapter_by_code(self, code: str) -> Chapter | None:
        """按稳定标识查章节，预取课程与知识点（测验范围校验用）。"""
        stmt = (
            select(Chapter)
            .where(Chapter.code == code, Chapter.deleted_at.is_(None))
            .options(
                selectinload(Chapter.course),
                selectinload(Chapter.knowledge_points),
            )
        )
        return self.db.scalars(stmt).first()

    def get_course_knowledge_points(self, course_code: str) -> list[KnowledgePoint] | None:
        """课程全部未删除知识点（含前置关系），按章节与知识点顺序排序。

        课程不存在时返回 None。计划排期与结构校验使用（排期须按课程顺序，
        保证前置知识点先于依赖它的知识点出现）。
        """
        course = self.db.scalars(
            select(Course).where(
                Course.code == course_code, Course.deleted_at.is_(None)
            )
        ).first()
        if course is None:
            return None
        chapters = list(
            self.db.scalars(
                select(Chapter)
                .where(
                    Chapter.course_id == course.id,
                    Chapter.deleted_at.is_(None),
                )
                .order_by(Chapter.order_index.asc())
                .options(
                    selectinload(Chapter.knowledge_points).selectinload(
                        KnowledgePoint.prerequisites
                    )
                )
            ).all()
        )
        kps: list[KnowledgePoint] = []
        for chapter in chapters:
            kps.extend(kp for kp in chapter.knowledge_points if kp.deleted_at is None)
        return kps
