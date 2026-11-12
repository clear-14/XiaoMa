"""课程体系业务层：课程/章节/课时/知识点/教学内容/练习/题库浏览与课程版本。

分层约束：Agent 与 API 均只经本 Service 访问课程数据，不直接触达 Repository 或 SQL。
"""

import math
import re
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.course import (
    COURSE_PUBLISH_STATUSES,
    Chapter,
    Course,
    CourseContent,
    CourseVersion,
    Exercise,
    KnowledgePoint,
    Lesson,
)
from app.repositories.course_repository import CourseRepository
from app.schemas.course import (
    ChapterBrief,
    ChapterOut,
    CourseBrief,
    CourseContentOut,
    CourseDetail,
    CourseSummary,
    CourseVersionDetail,
    CourseVersionSummary,
    DirectionBrief,
    ExerciseOut,
    KnowledgePointDetail,
    KnowledgePointResourcesOut,
    KnowledgePointSummary,
    LearningResource,
    LessonDetail,
    LessonSummary,
    QuestionOut,
)


# ---------------------------------------------------------------------------
# 模型 → Schema 转换
# ---------------------------------------------------------------------------


def _visible(items) -> list:
    """过滤软删除子项（关系级联预取会包含已删除行）。"""
    return [item for item in items if item.deleted_at is None]


def _kp_summary(kp: KnowledgePoint) -> KnowledgePointSummary:
    return KnowledgePointSummary(
        id=kp.id,
        code=kp.code,
        name=kp.name,
        difficulty=kp.difficulty,
        estimated_minutes=kp.estimated_minutes,
        order_index=kp.order_index,
    )


def _lesson_summary(lesson: Lesson) -> LessonSummary:
    return LessonSummary(
        id=lesson.id,
        code=lesson.code,
        title=lesson.title,
        description=lesson.description,
        difficulty=lesson.difficulty,
        estimated_minutes=lesson.estimated_minutes,
        order_index=lesson.order_index,
        knowledge_point_count=len(_visible(lesson.knowledge_points)),
        has_content=lesson.content is not None,
    )


def _chapter_out(chapter: Chapter) -> ChapterOut:
    kps = _visible(chapter.knowledge_points)
    return ChapterOut(
        id=chapter.id,
        code=chapter.code,
        title=chapter.title,
        description=chapter.description,
        order_index=chapter.order_index,
        knowledge_points=[_kp_summary(kp) for kp in kps],
        lessons=[_lesson_summary(lesson) for lesson in _visible(chapter.lessons)],
    )


def _course_summary(course: Course) -> CourseSummary:
    chapters = _visible(course.chapters)
    lesson_count = sum(len(_visible(ch.lessons)) for ch in chapters)
    kp_count = sum(len(_visible(ch.knowledge_points)) for ch in chapters)
    return CourseSummary(
        id=course.id,
        code=course.code,
        slug=course.slug,
        name=course.name,
        description=course.description,
        direction=course.direction,
        difficulty=course.difficulty,
        recommended_level=course.recommended_level,
        estimated_minutes=course.estimated_minutes,
        version=course.version,
        publish_status=course.publish_status,
        sort_order=course.sort_order,
        chapter_count=len(chapters),
        lesson_count=lesson_count,
        knowledge_point_count=kp_count,
    )


def _content_out(content: CourseContent | None) -> CourseContentOut | None:
    if content is None:
        return None
    return CourseContentOut(
        learning_objectives=content.learning_objectives,
        concept_explanation=content.concept_explanation,
        syntax_explanation=content.syntax_explanation,
        example_code=content.example_code,
        code_explanation=content.code_explanation,
        common_mistakes=content.common_mistakes,
        summary=content.summary,
    )


def _exercise_out(exercise: Exercise) -> ExerciseOut:
    return ExerciseOut(
        id=exercise.id,
        code=exercise.code,
        title=exercise.title,
        description=exercise.description,
        exercise_type=exercise.exercise_type,
        difficulty=exercise.difficulty,
        reference_answer=exercise.reference_answer,
        explanation=exercise.explanation,
        order_index=exercise.order_index,
    )


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


class CourseService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = CourseRepository(db)

    # ---------------------------------------------------------------- 课程

    def list_courses(
        self,
        *,
        direction: str | None = None,
        difficulty: str | None = None,
        recommended_level: str | None = None,
        publish_status: str | None = "published",
    ) -> list[CourseSummary]:
        """课程列表：支持按方向、难度、推荐等级、发布状态筛选。"""
        courses = self.repo.list_courses(
            direction=direction,
            difficulty=difficulty,
            recommended_level=recommended_level,
            publish_status=publish_status,
        )
        return [_course_summary(course) for course in courses]

    def get_course_detail(self, code: str) -> CourseDetail:
        course = self.repo.get_course_by_code(code)
        if course is None:
            raise HTTPException(status_code=404, detail="课程不存在")
        chapters = _visible(course.chapters)
        summary = _course_summary(course)
        return CourseDetail(
            **summary.model_dump(),
            learning_objectives=course.learning_objectives,
            chapters=[_chapter_out(ch) for ch in chapters],
            directions=[
                DirectionBrief(code=direction.code, name=direction.name)
                for direction in course.directions
            ],
            prerequisites=[
                CourseBrief(code=item.code, name=item.name)
                for item in _visible(course.prerequisites)
            ],
            required_knowledge_points=[
                _kp_summary(kp) for kp in _visible(course.required_knowledge_points)
            ],
        )

    def create_course(
        self,
        *,
        code: str,
        name: str,
        description: str | None = None,
        learning_objectives: str | None = None,
        direction: str | None = None,
        difficulty: str | None = None,
        recommended_level: str | None = None,
        estimated_minutes: int | None = None,
        version: str = "1.0.0",
        publish_status: str = "draft",
        sort_order: int = 0,
    ) -> CourseSummary:
        """创建课程（默认草稿；唯一 slug 即 code，重复则拒绝）。"""
        if publish_status not in COURSE_PUBLISH_STATUSES:
            raise HTTPException(status_code=400, detail="课程发布状态不合法")
        if self.repo.find_course_by_code_any(code) is not None:
            raise HTTPException(status_code=409, detail="课程标识（slug）已存在")
        course = Course(
            code=code,
            name=name,
            description=description,
            learning_objectives=learning_objectives,
            direction=direction,
            difficulty=difficulty,
            recommended_level=recommended_level,
            estimated_minutes=estimated_minutes,
            version=version,
            publish_status=publish_status,
            sort_order=sort_order,
        )
        self.repo.add_course(course)
        self.db.commit()
        course = self.repo.get_course_by_code(code)
        assert course is not None  # 刚创建成功，保证存在
        return _course_summary(course)

    def update_publish_status(self, code: str, status: str) -> CourseSummary:
        """切换课程发布状态：draft 草稿 / published 已发布 / archived 已归档。"""
        if status not in COURSE_PUBLISH_STATUSES:
            raise HTTPException(status_code=400, detail="课程发布状态不合法")
        course = self.repo.get_course_by_code(code)
        if course is None:
            raise HTTPException(status_code=404, detail="课程不存在")
        self.repo.set_publish_status(course, status)
        self.db.commit()
        course = self.repo.get_course_by_code(code)
        assert course is not None
        return _course_summary(course)

    # ------------------------------------------------------------ 章节 / 课时

    def list_chapters(self, code: str) -> list[ChapterOut]:
        course = self.repo.get_course_by_code(code)
        if course is None:
            raise HTTPException(status_code=404, detail="课程不存在")
        return [_chapter_out(ch) for ch in _visible(course.chapters)]

    def list_lessons(self, course_code: str, chapter_code: str) -> list[LessonSummary]:
        """查询指定章节下的课时（校验章节归属该课程）。"""
        course = self.repo.get_course_by_code(course_code)
        if course is None:
            raise HTTPException(status_code=404, detail="课程不存在")
        chapter = next(
            (ch for ch in _visible(course.chapters) if ch.code == chapter_code), None
        )
        if chapter is None:
            raise HTTPException(status_code=404, detail="章节不存在")
        return [_lesson_summary(lesson) for lesson in _visible(chapter.lessons)]

    def get_lesson(self, lesson_code: str) -> LessonDetail:
        """查询课时内容：所属课程/章节、教学内容与知识点。"""
        lesson = self.repo.get_lesson_by_code(lesson_code)
        if lesson is None:
            raise HTTPException(status_code=404, detail="课时不存在")
        return LessonDetail(
            id=lesson.id,
            code=lesson.code,
            title=lesson.title,
            description=lesson.description,
            difficulty=lesson.difficulty,
            estimated_minutes=lesson.estimated_minutes,
            order_index=lesson.order_index,
            module=ChapterBrief(code=lesson.chapter.code, title=lesson.chapter.title),
            course=CourseBrief(
                code=lesson.chapter.course.code, name=lesson.chapter.course.name
            ),
            content=_content_out(lesson.content),
            knowledge_points=[
                _kp_summary(kp) for kp in _visible(lesson.knowledge_points)
            ],
        )

    # ------------------------------------------------------- 知识点 / 练习 / 题库

    def get_knowledge_point(self, code: str) -> KnowledgePointDetail:
        kp = self.repo.get_knowledge_point_by_code(code)
        if kp is None:
            raise HTTPException(status_code=404, detail="知识点不存在")
        prerequisites = _visible(kp.prerequisites)
        exercises = _visible(kp.exercises)
        questions = self.repo.list_questions_by_knowledge_point(kp.id)
        return KnowledgePointDetail(
            id=kp.id,
            code=kp.code,
            name=kp.name,
            learning_goal=kp.learning_goal,
            difficulty=kp.difficulty,
            estimated_minutes=kp.estimated_minutes,
            mastery_criteria=kp.mastery_criteria,
            resources=(
                [LearningResource(**r) for r in kp.resources] if kp.resources else None
            ),
            order_index=kp.order_index,
            chapter=ChapterBrief(code=kp.chapter.code, title=kp.chapter.title),
            lesson=_lesson_summary(kp.lesson) if kp.lesson is not None else None,
            prerequisites=[_kp_summary(p) for p in prerequisites],
            exercise_count=len(exercises),
            question_count=len(questions),
        )

    def list_exercises(self, kp_code: str) -> list[ExerciseOut]:
        """查询知识点练习（含参考答案与解析）。"""
        kp = self.repo.get_knowledge_point_by_code(kp_code)
        if kp is None:
            raise HTTPException(status_code=404, detail="知识点不存在")
        return [
            _exercise_out(item)
            for item in self.repo.list_exercises_by_knowledge_point(kp.id)
        ]

    def list_questions(self, kp_code: str, *, include_answer: bool = False) -> list[QuestionOut]:
        """查询知识点测验题。

        默认不返回正确答案与解析，避免影响正式测验；``include_answer=True`` 时
        返回题库完整内容（课程内容核对/管理用途）。
        """
        kp = self.repo.get_knowledge_point_by_code(kp_code)
        if kp is None:
            raise HTTPException(status_code=404, detail="知识点不存在")
        questions = self.repo.list_questions_by_knowledge_point(kp.id)
        return [
            QuestionOut(
                id=question.id,
                code=question.code,
                stem=question.stem,
                question_type=question.question_type,
                options=question.options,
                difficulty=question.difficulty,
                correct_answer=question.correct_answer if include_answer else None,
                explanation=question.explanation if include_answer else None,
            )
            for question in questions
        ]

    # ---------------------------------------------------------------- 版本

    def save_version(
        self, code: str, *, version: str | None = None, note: str | None = None
    ) -> CourseVersionDetail:
        """保存课程版本快照（同版本号不覆盖，返回 409）。"""
        course = self.repo.get_course_by_code(code)
        if course is None:
            raise HTTPException(status_code=404, detail="课程不存在")
        target_version = (version or course.version).strip()
        if not target_version:
            raise HTTPException(status_code=400, detail="课程版本号不能为空")
        if self.repo.get_version(course.id, target_version) is not None:
            raise HTTPException(
                status_code=409, detail=f"课程版本 {target_version} 已存在"
            )
        snapshot = self._build_snapshot(course)
        record = CourseVersion(
            course_id=course.id,
            version=target_version,
            snapshot=snapshot,
            note=note,
        )
        self.repo.add_version(record)
        self.db.commit()
        return CourseVersionDetail(
            id=record.id,
            version=record.version,
            note=record.note,
            created_at=record.created_at,
            snapshot=record.snapshot,
        )

    def list_versions(self, code: str) -> list[CourseVersionSummary]:
        course = self.repo.get_course_by_code(code)
        if course is None:
            raise HTTPException(status_code=404, detail="课程不存在")
        return [
            CourseVersionSummary(
                id=item.id,
                version=item.version,
                note=item.note,
                created_at=item.created_at,
            )
            for item in self.repo.list_versions(course.id)
        ]

    def get_version(self, code: str, version: str) -> CourseVersionDetail:
        course = self.repo.get_course_by_code(code)
        if course is None:
            raise HTTPException(status_code=404, detail="课程不存在")
        record = self.repo.get_version(course.id, version)
        if record is None:
            raise HTTPException(status_code=404, detail="课程版本不存在")
        return CourseVersionDetail(
            id=record.id,
            version=record.version,
            note=record.note,
            created_at=record.created_at,
            snapshot=record.snapshot,
        )

    def _build_snapshot(self, course: Course) -> dict:
        """构建可 JSON 序列化的课程结构快照（UUID/时间统一转字符串）。"""
        modules: list[dict] = []
        for chapter in _visible(course.chapters):
            lessons: list[dict] = []
            for lesson in _visible(chapter.lessons):
                content = _content_out(lesson.content)
                lessons.append(
                    {
                        "code": lesson.code,
                        "title": lesson.title,
                        "description": lesson.description,
                        "difficulty": lesson.difficulty,
                        "estimated_minutes": lesson.estimated_minutes,
                        "order_index": lesson.order_index,
                        "content": content.model_dump() if content else None,
                        "knowledge_points": [
                            {
                                "code": kp.code,
                                "name": kp.name,
                                "learning_goal": kp.learning_goal,
                                "difficulty": kp.difficulty,
                                "estimated_minutes": kp.estimated_minutes,
                                "mastery_criteria": kp.mastery_criteria,
                                "resources": kp.resources,
                                "order_index": kp.order_index,
                                "exercises": [
                                    _exercise_out(exercise).model_dump(
                                        mode="json"
                                    )
                                    for exercise in _visible(kp.exercises)
                                ],
                            }
                            for kp in _visible(lesson.knowledge_points)
                        ],
                    }
                )
            modules.append(
                {
                    "code": chapter.code,
                    "title": chapter.title,
                    "description": chapter.description,
                    "order_index": chapter.order_index,
                    "lessons": lessons,
                }
            )
        return {
            "course": {
                "code": course.code,
                "slug": course.slug,
                "name": course.name,
                "description": course.description,
                "learning_objectives": course.learning_objectives,
                "direction": course.direction,
                "difficulty": course.difficulty,
                "recommended_level": course.recommended_level,
                "estimated_minutes": course.estimated_minutes,
                "version": course.version,
                "publish_status": course.publish_status,
                "sort_order": course.sort_order,
                "created_at": _iso(course.created_at),
                "updated_at": _iso(course.updated_at),
            },
            "modules": modules,
        }

    # ------------------------------------------------------------ 资源检索

    def search_learning_resources(
        self,
        query: str,
        *,
        course_code: str | None = None,
        limit: int = 5,
    ) -> list[KnowledgePointResourcesOut]:
        """按关键词检索知识点中已登记的学习资源。

        只返回数据库里真实存在的资源；不联网检索、不生成不存在的链接。
        query 为空时返回课程内前若干个有资源的知识点。

        查询非空时按相关度排序：整句命中知识点名称优先；关键词命中名称的
        权重最高，其次为学习目标、章节标题、掌握标准；关键词按课程内稀有度
        加权，避免「Python」这类通用词压过「变量」「函数」等具体主题。
        内部 code 不参与文本匹配，但可直接用完整 code 精确查询。
        """
        if limit < 1:
            raise ValueError("limit 必须大于 0")

        if course_code:
            codes = [course_code]
        else:
            codes = [course.code for course in self.repo.list_courses()]

        all_kps: list[KnowledgePoint] = []
        seen: set[str] = set()
        for code in codes:
            kps = self.repo.get_course_knowledge_points(code)
            if kps is None:
                if course_code:
                    raise HTTPException(status_code=404, detail="课程不存在")
                continue
            for kp in kps:
                if kp.deleted_at is not None or kp.code in seen:
                    continue
                all_kps.append(kp)
                seen.add(kp.code)

        normalized = (query or "").strip()
        if not normalized:
            return _first_resource_groups(all_kps, limit)

        # 完整知识点 code 是精确标识，直接返回该知识点，不混入其他模糊结果。
        exact_code = [
            kp for kp in all_kps if kp.code.casefold() == normalized.casefold()
        ]
        if exact_code:
            return _first_resource_groups(exact_code, limit)

        tokens = _resource_query_tokens(normalized)
        query_lower = normalized.casefold()
        haystacks = {kp.code: _resource_haystack(kp) for kp in all_kps}
        weights = _resource_token_weights(tokens, haystacks)

        ranked: list[tuple[float, int, KnowledgePoint]] = []
        for order, kp in enumerate(all_kps):
            if not kp.resources:
                continue
            score = _resource_match_score(
                kp,
                query_lower=query_lower,
                tokens=tokens,
                weights=weights,
            )
            if score > 0:
                ranked.append((score, order, kp))
        ranked.sort(key=lambda item: (-item[0], item[1]))

        matches: list[KnowledgePointResourcesOut] = []
        for _score, _order, kp in ranked:
            resources = _valid_resources(kp.resources)
            if not resources:
                continue
            matches.append(_resource_group(kp, resources))
            if len(matches) >= limit:
                break
        return matches


def _first_resource_groups(
    kps: list[KnowledgePoint], limit: int
) -> list[KnowledgePointResourcesOut]:
    """未指定关键词时按课程顺序返回前若干个有资源的知识点。"""
    groups: list[KnowledgePointResourcesOut] = []
    for kp in kps:
        resources = _valid_resources(kp.resources) if kp.resources else []
        if not resources:
            continue
        groups.append(_resource_group(kp, resources))
        if len(groups) >= limit:
            break
    return groups


def _resource_group(
    kp: KnowledgePoint, resources: list[LearningResource]
) -> KnowledgePointResourcesOut:
    return KnowledgePointResourcesOut(
        knowledge_point_code=kp.code,
        knowledge_point_name=kp.name,
        chapter_title=kp.chapter.title,
        resources=resources,
    )


def _resource_query_tokens(query: str) -> list[str]:
    """切分查询关键词，保留中文连续片段并拆开中英文边界。"""
    tokens = re.findall(r"[A-Za-z0-9_+#.]+|[一-鿿]+", query)
    # 去重但保留顺序；单字符关键词区分度过低，不参与匹配。
    return list(dict.fromkeys(token for token in tokens if len(token) >= 2))


def _resource_haystack(kp: KnowledgePoint) -> str:
    """知识点可检索文本；内部 code 不参与普通文本匹配。"""
    return " ".join(
        [
            kp.name,
            kp.learning_goal,
            kp.chapter.title,
            kp.mastery_criteria,
        ]
    ).casefold()


def _resource_token_weights(
    tokens: list[str], haystacks: dict[str, str]
) -> dict[str, float]:
    """按课程内稀有度计算关键词权重（IDF 变体）。

    出现范围越广的词权重越低；例如「Python」会低于「变量」「循环」。
    """
    total = len(haystacks)
    weights: dict[str, float] = {}
    for token in tokens:
        token_lower = token.casefold()
        document_frequency = sum(
            1 for haystack in haystacks.values() if token_lower in haystack
        )
        weights[token] = 1.0 + math.log(
            (total + 1) / (document_frequency + 1)
        )
    return weights


def _resource_match_score(
    kp: KnowledgePoint,
    *,
    query_lower: str,
    tokens: list[str],
    weights: dict[str, float],
) -> float:
    """计算知识点与查询的相关度；命中位置越核心、词越稀有，得分越高。"""
    name = kp.name.casefold()
    goal = kp.learning_goal.casefold()
    chapter = kp.chapter.title.casefold()
    mastery = kp.mastery_criteria.casefold()

    score = 100.0 if query_lower in name else 0.0
    matched = 0
    for token in tokens:
        token_lower = token.casefold()
        weight = weights.get(token, 1.0)
        if token_lower in name:
            score += 10.0 * weight
            matched += 1
        elif token_lower in goal:
            score += 4.0 * weight
            matched += 1
        elif token_lower in chapter:
            score += 3.0 * weight
            matched += 1
        elif token_lower in mastery:
            score += 1.0 * weight
            matched += 1

    if tokens and matched == len(tokens):
        # 所有关键词均命中，优先于只命中通用词的候选。
        score += 10.0
    return score


def _valid_resources(raw: list) -> list[LearningResource]:
    """过滤结构不合法的资源条目，避免把脏数据当作真实资源展示。"""
    resources: list[LearningResource] = []
    for item in raw:
        try:
            resources.append(LearningResource.model_validate(item))
        except (TypeError, ValueError):
            continue
    return resources
