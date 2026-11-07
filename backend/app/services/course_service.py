"""课程体系业务层：查询课程/章节/知识点并组装接口数据。"""

import math
import re

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.course import Chapter, Course, KnowledgePoint
from app.repositories.course_repository import CourseRepository
from app.schemas.course import (
    ChapterBrief,
    ChapterOut,
    CourseDetail,
    CourseSummary,
    KnowledgePointDetail,
    KnowledgePointResourcesOut,
    KnowledgePointSummary,
    LearningResource,
)


def _kp_summary(kp: KnowledgePoint) -> KnowledgePointSummary:
    return KnowledgePointSummary(
        id=kp.id,
        code=kp.code,
        name=kp.name,
        difficulty=kp.difficulty,
        estimated_minutes=kp.estimated_minutes,
        order_index=kp.order_index,
    )


def _chapter_out(chapter: Chapter) -> ChapterOut:
    # 关系级联预取含软删除子项，此处过滤保证接口只返回未删除内容
    kps = [kp for kp in chapter.knowledge_points if kp.deleted_at is None]
    return ChapterOut(
        id=chapter.id,
        code=chapter.code,
        title=chapter.title,
        description=chapter.description,
        order_index=chapter.order_index,
        knowledge_points=[_kp_summary(kp) for kp in kps],
    )


class CourseService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = CourseRepository(db)

    def list_courses(self) -> list[CourseSummary]:
        courses = self.repo.list_courses()
        return [
            CourseSummary(
                id=course.id,
                code=course.code,
                name=course.name,
                description=course.description,
                chapter_count=sum(1 for ch in course.chapters if ch.deleted_at is None),
            )
            for course in courses
        ]

    def get_course_detail(self, code: str) -> CourseDetail:
        course = self.repo.get_course_by_code(code)
        if course is None:
            raise HTTPException(status_code=404, detail="课程不存在")
        chapters = [ch for ch in course.chapters if ch.deleted_at is None]
        return CourseDetail(
            id=course.id,
            code=course.code,
            name=course.name,
            description=course.description,
            chapter_count=len(chapters),
            chapters=[_chapter_out(ch) for ch in chapters],
        )

    def list_chapters(self, code: str) -> list[ChapterOut]:
        course = self.repo.get_course_by_code(code)
        if course is None:
            raise HTTPException(status_code=404, detail="课程不存在")
        chapters = [ch for ch in course.chapters if ch.deleted_at is None]
        return [_chapter_out(ch) for ch in chapters]

    def get_knowledge_point(self, code: str) -> KnowledgePointDetail:
        kp = self.repo.get_knowledge_point_by_code(code)
        if kp is None:
            raise HTTPException(status_code=404, detail="知识点不存在")
        prerequisites = [p for p in kp.prerequisites if p.deleted_at is None]
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
            prerequisites=[_kp_summary(p) for p in prerequisites],
        )

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
