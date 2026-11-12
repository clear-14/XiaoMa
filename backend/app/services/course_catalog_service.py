"""课程目录与学习路线业务层（阶段 2）。

职责：
- 课程方向（课程分类）的查询与分组；
- 课程目录总览（方向 → 课程 → 章节/课时规模）；
- 课程先修依赖图：构建、环检测、拓扑排序、引用完整性检查；
- 前置 / 后续课程查询（直接关系与传递闭包）；
- 学习路径建议：已掌握内容跳过、前置课程跳级、缺失基础知识点补学提示。

分层约束：API 与 Agent 只经本 Service 访问课程目录数据，不直连 Repository 或 SQL。
依赖图算法为模块级纯函数，可脱离数据库单独测试。
"""

from __future__ import annotations

import heapq
from collections import defaultdict, deque

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.course import Course, CourseDirection
from app.repositories.course_repository import CourseRepository
from app.schemas.course import CourseBrief, DirectionBrief
from app.schemas.course_catalog import (
    CourseCatalogItem,
    CourseCatalogOut,
    CourseRelationsOut,
    DependencyGraphOut,
    DirectionGroup,
    DirectionOut,
    KnowledgePointBrief,
    KnowledgePointReferenceOut,
    LearningPathOut,
    MissingKnowledgePointOut,
    PrerequisiteEdgeOut,
    SkippedCourseOut,
)


# ---------------------------------------------------------------------------
# 依赖图算法（纯函数）
# ---------------------------------------------------------------------------


def find_cycles(nodes: list[str], edges: list[tuple[str, str]]) -> list[list[str]]:
    """用三色标记 DFS 找出全部环。

    ``edges`` 中每条边为 ``(课程, 前置课程)``，即「课程依赖前置课程」。
    返回的每个环是从起点回到起点的 code 序列，已规范到字典序最小起点并去重。
    """
    adjacency: dict[str, list[str]] = defaultdict(list)
    for course, prerequisite in edges:
        adjacency[course].append(prerequisite)

    white, gray, black = 0, 1, 2
    color = {node: white for node in nodes}
    stack: list[str] = []
    found: list[list[str]] = []

    def visit(node: str) -> None:
        color[node] = gray
        stack.append(node)
        for nxt in adjacency.get(node, []):
            if nxt not in color:
                continue
            if color[nxt] == white:
                visit(nxt)
            elif color[nxt] == gray:
                start = stack.index(nxt)
                found.append(stack[start:] + [nxt])
        stack.pop()
        color[node] = black

    for node in nodes:
        if color[node] == white:
            visit(node)

    unique: dict[tuple[str, ...], list[str]] = {}
    for cycle in found:
        normalized = _normalize_cycle(cycle)
        unique.setdefault(tuple(normalized), normalized)
    return list(unique.values())


def _normalize_cycle(cycle: list[str]) -> list[str]:
    """把环旋转到字典序最小起点，便于去重与稳定断言。"""
    body = cycle[:-1]
    if not body:
        return cycle
    index = min(range(len(body)), key=lambda i: body[i])
    rotated = body[index:] + body[:index]
    return rotated + [rotated[0]]


def topological_order(
    nodes: list[str], edges: list[tuple[str, str]]
) -> list[str]:
    """Kahn 拓扑排序：前置课程排在依赖它的课程之前。

    存在环时返回空列表（无法给出确定的先后顺序）。
    """
    children: dict[str, list[str]] = defaultdict(list)
    indegree = {node: 0 for node in nodes}
    seen_edges: set[tuple[str, str]] = set()
    for course, prerequisite in edges:
        if course not in indegree or prerequisite not in indegree:
            continue
        if (course, prerequisite) in seen_edges:
            continue
        seen_edges.add((course, prerequisite))
        children[prerequisite].append(course)
        indegree[course] += 1

    heap = [node for node, degree in indegree.items() if degree == 0]
    heapq.heapify(heap)
    order: list[str] = []
    while heap:
        node = heapq.heappop(heap)
        order.append(node)
        for child in sorted(children.get(node, [])):
            indegree[child] -= 1
            if indegree[child] == 0:
                heapq.heappush(heap, child)
    return order if len(order) == len(indegree) else []


# ---------------------------------------------------------------------------
# 模型 → Schema
# ---------------------------------------------------------------------------


def _visible(items) -> list:
    """过滤软删除子项（关系级联预取会包含已删除行）。"""
    return [item for item in items if getattr(item, "deleted_at", None) is None]


def _direction_codes(course: Course) -> list[str]:
    """课程关联的方向 code；无关联时回退到主方向字段。"""
    codes = [direction.code for direction in course.directions]
    if not codes and course.direction:
        codes = [course.direction]
    return codes


def _catalog_item(course: Course) -> CourseCatalogItem:
    chapters = _visible(course.chapters)
    lesson_count = sum(len(_visible(chapter.lessons)) for chapter in chapters)
    kp_count = sum(len(_visible(chapter.knowledge_points)) for chapter in chapters)
    return CourseCatalogItem(
        code=course.code,
        slug=course.slug,
        name=course.name,
        description=course.description,
        direction=course.direction,
        direction_codes=_direction_codes(course),
        recommended_level=course.recommended_level,
        difficulty=course.difficulty,
        estimated_minutes=course.estimated_minutes,
        version=course.version,
        publish_status=course.publish_status,
        sort_order=course.sort_order,
        chapter_count=len(chapters),
        lesson_count=lesson_count,
        knowledge_point_count=kp_count,
        prerequisites=[
            item.code for item in _visible(course.prerequisites)
        ],
    )


def _course_brief(course: Course) -> CourseBrief:
    return CourseBrief(code=course.code, name=course.name)


class CourseCatalogService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = CourseRepository(db)

    # ---------------------------------------------------------------- 方向

    def list_directions(self) -> list[DirectionOut]:
        """课程方向列表，按 order_index 排序，附各方向课程数。"""
        courses = self.repo.list_courses_for_catalog(publish_status=None)
        counts: dict[str, int] = defaultdict(int)
        for course in courses:
            for code in _direction_codes(course):
                counts[code] += 1
        return [
            DirectionOut(
                id=direction.id,
                code=direction.code,
                name=direction.name,
                description=direction.description,
                order_index=direction.order_index,
                course_count=counts.get(direction.code, 0),
            )
            for direction in self.repo.list_directions()
        ]

    # ---------------------------------------------------------------- 目录

    def get_catalog(
        self,
        *,
        direction: str | None = None,
        recommended_level: str | None = None,
        difficulty: str | None = None,
        publish_status: str | None = None,
    ) -> CourseCatalogOut:
        """课程目录总览：按方向分组，同时给出未归类课程。

        ``publish_status`` 为 None 时包含草稿（目录管理视图）；
        学习入口应传 ``published``。
        """
        courses = self.repo.list_courses_for_catalog(publish_status=publish_status)
        directions = self.repo.list_directions()

        if direction and not any(item.code == direction for item in directions):
            raise HTTPException(status_code=404, detail="课程方向不存在")

        items: list[CourseCatalogItem] = []
        for course in courses:
            if recommended_level and course.recommended_level != recommended_level:
                continue
            if difficulty and course.difficulty != difficulty:
                continue
            if direction and direction not in _direction_codes(course):
                continue
            items.append(_catalog_item(course))

        groups: list[DirectionGroup] = []
        grouped_codes: set[str] = set()
        for item in directions:
            group_courses = [
                course
                for course in items
                if item.code in course.direction_codes
            ]
            if direction and item.code != direction:
                continue
            for course in group_courses:
                grouped_codes.add(course.code)
            groups.append(
                DirectionGroup(
                    direction=DirectionOut(
                        id=item.id,
                        code=item.code,
                        name=item.name,
                        description=item.description,
                        order_index=item.order_index,
                        course_count=len(group_courses),
                    ),
                    courses=group_courses,
                )
            )

        ungrouped = [
            course
            for course in items
            if course.code not in grouped_codes and not course.direction_codes
        ]
        return CourseCatalogOut(
            directions=groups,
            ungrouped=ungrouped,
            total_courses=len(items),
            total_chapters=sum(course.chapter_count for course in items),
            total_lessons=sum(course.lesson_count for course in items),
        )

    # ------------------------------------------------------------ 依赖图

    def get_dependency_graph(self) -> DependencyGraphOut:
        """构建全部课程的先修依赖图，并返回完整性检查结果。"""
        courses = self.repo.list_courses_for_catalog(publish_status=None)
        nodes = [course.code for course in courses]
        node_set = set(nodes)
        edges = self.repo.list_course_prerequisite_edges()

        missing_course_references = [
            PrerequisiteEdgeOut(course_code=course, prerequisite_code=prerequisite)
            for course, prerequisite in edges
            if course not in node_set or prerequisite not in node_set
        ]
        valid_edges = [
            (course, prerequisite)
            for course, prerequisite in edges
            if course in node_set and prerequisite in node_set
        ]
        self_references = [
            course for course, prerequisite in valid_edges if course == prerequisite
        ]

        known_kp_codes = set(self.repo.list_knowledge_point_codes())
        kp_edges = self.repo.list_course_knowledge_point_edges()
        missing_kp_references = [
            KnowledgePointReferenceOut(
                course_code=course, knowledge_point_code=kp_code
            )
            for course, kp_code in kp_edges
            if course not in node_set or kp_code not in known_kp_codes
        ]

        cycles = find_cycles(nodes, valid_edges)
        order = [] if cycles else topological_order(nodes, valid_edges)
        valid = (
            not cycles
            and not missing_course_references
            and not missing_kp_references
            and not self_references
        )
        return DependencyGraphOut(
            valid=valid,
            course_count=len(nodes),
            edge_count=len(valid_edges),
            edges=[
                PrerequisiteEdgeOut(
                    course_code=course, prerequisite_code=prerequisite
                )
                for course, prerequisite in sorted(valid_edges)
            ],
            cycles=cycles,
            missing_course_references=missing_course_references,
            missing_knowledge_point_references=missing_kp_references,
            self_references=sorted(set(self_references)),
            topological_order=order,
        )

    # ------------------------------------------------------- 前置 / 后续

    def get_prerequisites(self, course_code: str) -> CourseRelationsOut:
        """查询某门课的前置课程：直接关系与传递闭包（含多级前置）。"""
        course = self._require_course(course_code)
        direct = _visible(course.prerequisites)
        transitive = self._ancestors(course)
        return CourseRelationsOut(
            course_code=course.code,
            direct=[_course_brief(item) for item in direct],
            transitive=[_course_brief(item) for item in transitive],
        )

    def get_next_courses(self, course_code: str) -> CourseRelationsOut:
        """查询学完某门课后可以直接进入、以及最终可以进入的课程。"""
        course = self._require_course(course_code)
        direct = self.repo.list_course_dependents(course.id)
        seen: dict[str, Course] = {}
        queue = deque(direct)
        while queue:
            node = queue.popleft()
            if node.code in seen or node.deleted_at is not None:
                continue
            seen[node.code] = node
            queue.extend(self.repo.list_course_dependents(node.id))
        transitive = sorted(seen.values(), key=lambda c: (c.sort_order, c.code))
        return CourseRelationsOut(
            course_code=course.code,
            direct=[_course_brief(item) for item in direct],
            transitive=[_course_brief(item) for item in transitive],
        )

    # ------------------------------------------------------------ 学习路径

    def get_learning_path(
        self,
        course_code: str,
        *,
        mastered_course_codes: list[str] | None = None,
        mastered_knowledge_point_codes: list[str] | None = None,
    ) -> LearningPathOut:
        """计算学习路径：能否开始、缺哪些前置课程与知识点、哪些可跳过。

        跳过规则（对应「已掌握内容的跳过」与「诊断后跳级」）：
        - 前置课程在 ``mastered_course_codes`` 中 → 整门跳过；
        - 前置课程要求入学的知识点全部在 ``mastered_knowledge_point_codes`` 中
          → 视为已掌握，跳过（诊断后跳级）。
        """
        course = self._require_course(course_code)
        mastered_courses = set(mastered_course_codes or [])
        mastered_kps = set(mastered_knowledge_point_codes or [])

        def satisfied_reason(node: Course) -> str | None:
            """判断某前置课程是否已满足；返回可读原因，未满足返回 None。"""
            if node.code in mastered_courses:
                return "已标记为掌握"
            required = {
                kp.code for kp in _visible(node.required_knowledge_points)
            }
            if required and required <= mastered_kps:
                return "入学知识点已全部掌握，可跳级"
            return None

        missing_courses: list[Course] = []
        skipped: list[SkippedCourseOut] = []
        seen: set[str] = set()
        queue = deque(_visible(course.prerequisites))
        while queue:
            ancestor = queue.popleft()
            if ancestor.code in seen or ancestor.deleted_at is not None:
                continue
            seen.add(ancestor.code)
            reason = satisfied_reason(ancestor)
            if reason:
                # 已满足的前置不再展开它的前置：掌握一门课即默认其基础已具备，
                # 否则会把「已学过的基础课」也列成待补课程。
                skipped.append(
                    SkippedCourseOut(
                        code=ancestor.code, name=ancestor.name, reason=reason
                    )
                )
                continue
            missing_courses.append(ancestor)
            queue.extend(_visible(ancestor.prerequisites))

        missing_courses.sort(key=lambda item: (item.sort_order, item.code))
        skipped.sort(key=lambda item: (item.code,))

        missing_kps: list[MissingKnowledgePointOut] = []
        seen_kps: set[str] = set()
        for target in missing_courses + [course]:
            for kp in _visible(target.required_knowledge_points):
                if kp.code in mastered_kps or kp.code in seen_kps:
                    continue
                seen_kps.add(kp.code)
                missing_kps.append(
                    MissingKnowledgePointOut(
                        code=kp.code, name=kp.name, course_code=target.code
                    )
                )

        notes: list[str] = []
        if missing_courses:
            notes.append(
                "建议先完成前置课程：" + "、".join(item.name for item in missing_courses)
            )
        if missing_kps:
            notes.append(
                "建议先补学基础知识点：" + "、".join(item.name for item in missing_kps)
            )
        if skipped:
            notes.append(
                "以下前置课程已掌握，可以跳过："
                + "、".join(item.name for item in skipped)
            )
        if not missing_courses and not missing_kps:
            notes.append("前置条件已满足，可以直接开始学习")
        elif not missing_courses:
            notes.append("前置课程已满足，补完基础知识点即可开始")

        return LearningPathOut(
            course_code=course.code,
            course_name=course.name,
            ready=not missing_courses and not missing_kps,
            missing_courses=[_course_brief(item) for item in missing_courses],
            skipped_courses=skipped,
            missing_knowledge_points=missing_kps,
            notes=notes,
        )

    # ------------------------------------------------------- 先修写入（带校验）

    def add_prerequisite(
        self, course_code: str, prerequisite_code: str
    ) -> CourseRelationsOut:
        """新增课程先修关系。

        校验：课程与前置课程都必须存在、不允许自引用、不允许形成循环依赖；
        重复添加按幂等处理，不产生重复边。
        """
        course = self._require_course(course_code)
        if prerequisite_code == course_code:
            raise HTTPException(status_code=400, detail="课程不能以自己为先修课程")
        prerequisite = self._require_course(prerequisite_code)
        if self.repo.get_course_prerequisite(course.id, prerequisite.id) is not None:
            return self.get_prerequisites(course_code)
        if self._depends_on(prerequisite, course.code):
            raise HTTPException(
                status_code=409,
                detail=(
                    f"新增先修关系会形成循环依赖：{prerequisite_code} 已（间接）"
                    f"依赖 {course_code}"
                ),
            )
        self.repo.add_course_prerequisite(course.id, prerequisite.id)
        self.db.commit()
        # 会话常配置 expire_on_commit=False，显式过期以读到最新的先修集合
        self.db.expire_all()
        return self.get_prerequisites(course_code)

    def remove_prerequisite(
        self, course_code: str, prerequisite_code: str
    ) -> CourseRelationsOut:
        course = self._require_course(course_code)
        prerequisite = self._require_course(prerequisite_code)
        edge = self.repo.get_course_prerequisite(course.id, prerequisite.id)
        if edge is None:
            raise HTTPException(status_code=404, detail="该先修关系不存在")
        self.repo.delete_course_prerequisite(edge)
        self.db.commit()
        self.db.expire_all()
        return self.get_prerequisites(course_code)

    def add_required_knowledge_point(
        self, course_code: str, knowledge_point_code: str
    ) -> list[KnowledgePointBrief]:
        """为课程登记入学前应掌握的知识点（可跨课程）。

        校验知识点必须存在；重复登记按幂等处理。
        """
        course = self._require_course(course_code)
        kp = self.repo.get_knowledge_point_by_code(knowledge_point_code)
        if kp is None:
            raise HTTPException(status_code=404, detail="知识点不存在")
        if self.repo.get_course_kp_prerequisite(course.id, kp.id) is None:
            self.repo.add_course_kp_prerequisite(course.id, kp.id)
            self.db.commit()
            self.db.expire_all()
        refreshed = self._require_course(course_code)
        return [
            KnowledgePointBrief(code=item.code, name=item.name)
            for item in _visible(refreshed.required_knowledge_points)
        ]

    def remove_required_knowledge_point(
        self, course_code: str, knowledge_point_code: str
    ) -> list[KnowledgePointBrief]:
        course = self._require_course(course_code)
        kp = self.repo.get_knowledge_point_by_code(knowledge_point_code)
        if kp is None:
            raise HTTPException(status_code=404, detail="知识点不存在")
        link = self.repo.get_course_kp_prerequisite(course.id, kp.id)
        if link is None:
            raise HTTPException(status_code=404, detail="该入学知识点关系不存在")
        self.repo.delete_course_kp_prerequisite(link)
        self.db.commit()
        self.db.expire_all()
        refreshed = self._require_course(course_code)
        return [
            KnowledgePointBrief(code=item.code, name=item.name)
            for item in _visible(refreshed.required_knowledge_points)
        ]

    # ---------------------------------------------------------------- 内部

    def _require_course(self, code: str) -> Course:
        course = self.repo.get_course_by_code(code)
        if course is None:
            raise HTTPException(status_code=404, detail="课程不存在")
        return course

    def _ancestors(self, course: Course) -> list[Course]:
        """全部传递前置课程，按课程展示顺序排序（不含自身）。"""
        seen: dict[str, Course] = {}
        queue = deque(_visible(course.prerequisites))
        while queue:
            node = queue.popleft()
            if node.code in seen or node.deleted_at is not None:
                continue
            seen[node.code] = node
            queue.extend(_visible(node.prerequisites))
        return sorted(seen.values(), key=lambda c: (c.sort_order, c.code))

    def _depends_on(self, course: Course, target_code: str) -> bool:
        """course 是否（直接或间接）依赖 target_code。"""
        seen: set[str] = set()
        queue = deque(_visible(course.prerequisites))
        while queue:
            node = queue.popleft()
            if node.code in seen:
                continue
            seen.add(node.code)
            if node.code == target_code:
                return True
            queue.extend(_visible(node.prerequisites))
        return False


def direction_brief(direction: CourseDirection) -> DirectionBrief:
    """方向的最简展示形态（课程详情用）。"""
    return DirectionBrief(code=direction.code, name=direction.name)
