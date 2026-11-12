"""课程体系数据访问层（阶段 1：课程 → 章节 → 课时 → 知识点 → 内容/练习；
阶段 2：课程方向、课程级先修与入学知识点）。"""

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, aliased, selectinload

from app.models.course import (
    Chapter,
    Course,
    CourseContent,
    CourseDirection,
    CourseDirectionLink,
    CourseKnowledgePointPrerequisite,
    CoursePrerequisite,
    CourseVersion,
    Exercise,
    KnowledgePoint,
    Lesson,
)
from app.models.quiz import Question


class CourseRepository:
    """课程域的数据库读写。

    查询统一过滤软删除（deleted_at IS NULL）；关系中的软删除子项由 Service 层过滤。
    写操作只做对象增改与 flush，事务提交由 Service 层负责。
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    # ---------------------------------------------------------------- 课程

    def list_courses(
        self,
        *,
        direction: str | None = None,
        difficulty: str | None = None,
        recommended_level: str | None = None,
        publish_status: str | None = "published",
    ) -> list[Course]:
        """按方向/难度/推荐等级/发布状态筛选课程。

        ``publish_status=None`` 或 ``"all"`` 表示不限发布状态；默认只返回已发布课程，
        避免学习入口看到草稿与已归档课程。同方向内按 sort_order 升序。
        """
        stmt = select(Course).where(Course.deleted_at.is_(None))
        if direction:
            # 主方向（courses.direction 冗余字段）与多方向关联任一命中即算属于该方向
            linked_ids = (
                select(CourseDirectionLink.course_id)
                .join(
                    CourseDirection,
                    CourseDirection.id == CourseDirectionLink.direction_id,
                )
                .where(CourseDirection.code == direction)
            )
            stmt = stmt.where(
                or_(Course.direction == direction, Course.id.in_(linked_ids))
            )
        if difficulty:
            stmt = stmt.where(Course.difficulty == difficulty)
        if recommended_level:
            stmt = stmt.where(Course.recommended_level == recommended_level)
        if publish_status and publish_status != "all":
            stmt = stmt.where(Course.publish_status == publish_status)
        stmt = stmt.order_by(Course.sort_order.asc(), Course.created_at.asc()).options(
            selectinload(Course.chapters).options(
                selectinload(Chapter.lessons).options(
                    selectinload(Lesson.content),
                    selectinload(Lesson.knowledge_points),
                ),
                selectinload(Chapter.knowledge_points),
            )
        )
        return list(self.db.scalars(stmt).all())

    def get_course_by_code(self, code: str) -> Course | None:
        """按稳定标识（即唯一 slug）查课程，预取章节、知识点、课时内容与先修关系。"""
        stmt = (
            select(Course)
            .where(Course.code == code, Course.deleted_at.is_(None))
            .options(
                selectinload(Course.directions),
                selectinload(Course.prerequisites),
                selectinload(Course.required_knowledge_points),
                selectinload(Course.chapters).options(
                    selectinload(Chapter.knowledge_points).selectinload(
                        KnowledgePoint.exercises
                    ),
                    selectinload(Chapter.lessons).options(
                        selectinload(Lesson.content),
                        selectinload(Lesson.knowledge_points).selectinload(
                            KnowledgePoint.exercises
                        ),
                    ),
                ),
            )
        )
        return self.db.scalars(stmt).first()

    def add_course(self, course: Course) -> Course:
        self.db.add(course)
        self.db.flush()
        return course

    def find_course_by_code_any(self, code: str) -> Course | None:
        """按 code 查课程（含已软删除行）：唯一约束覆盖全部行，创建前需据此判重。"""
        return self.db.scalars(select(Course).where(Course.code == code)).first()

    def set_publish_status(self, course: Course, status: str) -> Course:
        """切换课程发布状态（草稿 / 已发布 / 已归档）。"""
        course.publish_status = status
        self.db.flush()
        return course

    # ---------------------------------------------------------------- 章节

    def get_chapter_by_code(self, code: str) -> Chapter | None:
        """按稳定标识查章节，预取课程、知识点与课时（测验范围校验与课时列表用）。"""
        stmt = (
            select(Chapter)
            .where(Chapter.code == code, Chapter.deleted_at.is_(None))
            .options(
                selectinload(Chapter.course),
                selectinload(Chapter.knowledge_points),
                selectinload(Chapter.lessons).selectinload(Lesson.content),
            )
        )
        return self.db.scalars(stmt).first()

    def get_course_knowledge_points(
        self, course_code: str
    ) -> list[KnowledgePoint] | None:
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

    # ---------------------------------------------------------------- 课时

    def get_course_knowledge_points_with_lessons(
        self, course_code: str
    ) -> list[KnowledgePoint] | None:
        """课程全部知识点（阶段 6）：预取章节/课程、归属课时与课时内容、前置关系。

        与 ``get_course_knowledge_points`` 的区别是额外校验「不存在的课时」：
        计划生成和每日任务都要读 ``kp.lesson``，这里一次预取避免 N+1 查询，
        并保证 Service 能判定课时是否真实属于该课程。
        """
        course = self.db.scalars(
            select(Course).where(
                Course.code == course_code, Course.deleted_at.is_(None)
            )
        ).first()
        if course is None:
            return None
        stmt = (
            select(KnowledgePoint)
            .join(Chapter, KnowledgePoint.chapter_id == Chapter.id)
            .where(
                Chapter.course_id == course.id,
                Chapter.deleted_at.is_(None),
                KnowledgePoint.deleted_at.is_(None),
            )
            .order_by(
                Chapter.order_index.asc(),
                KnowledgePoint.order_index.asc(),
                KnowledgePoint.code.asc(),
            )
            .options(
                selectinload(KnowledgePoint.chapter).selectinload(Chapter.course),
                selectinload(KnowledgePoint.lesson).selectinload(Lesson.content),
                selectinload(KnowledgePoint.prerequisites),
            )
        )
        return list(self.db.scalars(stmt).all())

    def get_lesson_by_code(self, code: str) -> Lesson | None:
        """按稳定标识查课时，预取所属章节/课程、教学内容与知识点。"""
        stmt = (
            select(Lesson)
            .where(Lesson.code == code, Lesson.deleted_at.is_(None))
            .options(
                selectinload(Lesson.chapter).selectinload(Chapter.course),
                selectinload(Lesson.content),
                selectinload(Lesson.knowledge_points).selectinload(
                    KnowledgePoint.prerequisites
                ),
            )
        )
        return self.db.scalars(stmt).first()

    def get_lesson_content(self, lesson_id) -> CourseContent | None:
        stmt = select(CourseContent).where(CourseContent.lesson_id == lesson_id)
        return self.db.scalars(stmt).first()

    # ------------------------------------------------------------ 知识点/练习

    def get_knowledge_point_by_code(self, code: str) -> KnowledgePoint | None:
        """按稳定标识查知识点，预取所属章节、所属课时、练习与前置知识点。"""
        stmt = (
            select(KnowledgePoint)
            .where(KnowledgePoint.code == code, KnowledgePoint.deleted_at.is_(None))
            .options(
                selectinload(KnowledgePoint.chapter),
                selectinload(KnowledgePoint.lesson),
                selectinload(KnowledgePoint.exercises),
                selectinload(KnowledgePoint.prerequisites),
            )
        )
        return self.db.scalars(stmt).first()

    def list_exercises_by_knowledge_point(self, kp_id) -> list[Exercise]:
        stmt = (
            select(Exercise)
            .where(
                Exercise.knowledge_point_id == kp_id,
                Exercise.deleted_at.is_(None),
            )
            .order_by(Exercise.order_index.asc(), Exercise.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())

    def list_questions_by_knowledge_point(self, kp_id) -> list[Question]:
        """知识点下的测验题（只读，供课程内容浏览用；组卷仍走 QuestionRepository）。"""
        stmt = (
            select(Question)
            .where(Question.knowledge_point_id == kp_id)
            .order_by(Question.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())

    # ---------------------------------------------------------------- 版本

    def add_version(self, course_version: CourseVersion) -> CourseVersion:
        self.db.add(course_version)
        self.db.flush()
        return course_version

    def list_versions(self, course_id) -> list[CourseVersion]:
        stmt = (
            select(CourseVersion)
            .where(CourseVersion.course_id == course_id)
            .order_by(CourseVersion.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def get_version(self, course_id, version: str) -> CourseVersion | None:
        stmt = select(CourseVersion).where(
            CourseVersion.course_id == course_id,
            CourseVersion.version == version,
        )
        return self.db.scalars(stmt).first()

    # ------------------------------------------------------------ 课程方向
    # 阶段 2：方向是课程分类，与能力等级（courses.recommended_level）正交。

    def list_directions(self) -> list[CourseDirection]:
        stmt = select(CourseDirection).order_by(
            CourseDirection.order_index.asc(), CourseDirection.code.asc()
        )
        return list(self.db.scalars(stmt).all())

    def get_direction_by_code(self, code: str) -> CourseDirection | None:
        return self.db.scalars(
            select(CourseDirection).where(CourseDirection.code == code)
        ).first()

    def add_direction(self, direction: CourseDirection) -> CourseDirection:
        self.db.add(direction)
        self.db.flush()
        return direction

    def get_direction_link(self, course_id, direction_id) -> CourseDirectionLink | None:
        return self.db.get(
            CourseDirectionLink,
            {"course_id": course_id, "direction_id": direction_id},
        )

    def add_direction_link(
        self, course_id, direction_id
    ) -> CourseDirectionLink:
        link = CourseDirectionLink(course_id=course_id, direction_id=direction_id)
        self.db.add(link)
        self.db.flush()
        return link

    def delete_direction_link(self, link: CourseDirectionLink) -> None:
        self.db.delete(link)
        self.db.flush()

    def list_direction_links_for_course(self, course_id) -> list[CourseDirectionLink]:
        stmt = select(CourseDirectionLink).where(
            CourseDirectionLink.course_id == course_id
        )
        return list(self.db.scalars(stmt).all())

    # ------------------------------------------------------- 课程目录 / 先修

    def list_courses_for_catalog(
        self, *, publish_status: str | None = None
    ) -> list[Course]:
        """目录总览用的课程列表：预取方向、先修与章节/课时计数所需关系。"""
        stmt = (
            select(Course)
            .where(Course.deleted_at.is_(None))
            .options(
                selectinload(Course.directions),
                selectinload(Course.prerequisites),
                selectinload(Course.required_knowledge_points),
                selectinload(Course.chapters).options(
                    selectinload(Chapter.lessons),
                    selectinload(Chapter.knowledge_points),
                ),
            )
            .order_by(Course.sort_order.asc(), Course.created_at.asc())
        )
        if publish_status and publish_status != "all":
            stmt = stmt.where(Course.publish_status == publish_status)
        return list(self.db.scalars(stmt).all())

    def list_course_prerequisite_edges(self) -> list[tuple[str, str]]:
        """全部课程先修边：(课程 code, 前置课程 code)；用于依赖图与环检测。"""
        target = aliased(Course)
        prerequisite = aliased(Course)
        stmt = (
            select(target.code, prerequisite.code)
            .join(CoursePrerequisite, CoursePrerequisite.course_id == target.id)
            .join(
                prerequisite,
                prerequisite.id == CoursePrerequisite.prerequisite_course_id,
            )
            .where(target.deleted_at.is_(None))
        )
        return [(row[0], row[1]) for row in self.db.execute(stmt).all()]

    def get_course_prerequisite(
        self, course_id, prerequisite_course_id
    ) -> CoursePrerequisite | None:
        return self.db.get(
            CoursePrerequisite,
            {
                "course_id": course_id,
                "prerequisite_course_id": prerequisite_course_id,
            },
        )

    def add_course_prerequisite(
        self, course_id, prerequisite_course_id
    ) -> CoursePrerequisite:
        edge = CoursePrerequisite(
            course_id=course_id, prerequisite_course_id=prerequisite_course_id
        )
        self.db.add(edge)
        self.db.flush()
        return edge

    def delete_course_prerequisite(self, edge: CoursePrerequisite) -> None:
        self.db.delete(edge)
        self.db.flush()

    def list_course_knowledge_point_edges(self) -> list[tuple[str, str]]:
        """全部「课程—入学知识点」引用边：(课程 code, 知识点 code)。"""
        stmt = (
            select(Course.code, KnowledgePoint.code)
            .join(
                CourseKnowledgePointPrerequisite,
                CourseKnowledgePointPrerequisite.course_id == Course.id,
            )
            .join(
                KnowledgePoint,
                KnowledgePoint.id
                == CourseKnowledgePointPrerequisite.knowledge_point_id,
            )
            .where(Course.deleted_at.is_(None))
        )
        return [(row[0], row[1]) for row in self.db.execute(stmt).all()]

    def get_course_kp_prerequisite(
        self, course_id, knowledge_point_id
    ) -> CourseKnowledgePointPrerequisite | None:
        return self.db.get(
            CourseKnowledgePointPrerequisite,
            {"course_id": course_id, "knowledge_point_id": knowledge_point_id},
        )

    def add_course_kp_prerequisite(
        self, course_id, knowledge_point_id
    ) -> CourseKnowledgePointPrerequisite:
        link = CourseKnowledgePointPrerequisite(
            course_id=course_id, knowledge_point_id=knowledge_point_id
        )
        self.db.add(link)
        self.db.flush()
        return link

    def delete_course_kp_prerequisite(
        self, link: CourseKnowledgePointPrerequisite
    ) -> None:
        self.db.delete(link)
        self.db.flush()

    def list_knowledge_point_codes(self) -> list[str]:
        """全部未删除知识点的 code（依赖图引用完整性检查用）。"""
        stmt = select(KnowledgePoint.code).where(KnowledgePoint.deleted_at.is_(None))
        return [row[0] for row in self.db.execute(stmt).all()]

    def list_course_dependents(self, course_id) -> list[Course]:
        """直接以某门课为先修的后续课程（反向边查询）。"""
        stmt = (
            select(Course)
            .join(
                CoursePrerequisite, CoursePrerequisite.course_id == Course.id
            )
            .where(
                CoursePrerequisite.prerequisite_course_id == course_id,
                Course.deleted_at.is_(None),
            )
            .order_by(Course.sort_order.asc(), Course.code.asc())
        )
        return list(self.db.scalars(stmt).all())
