"""每日学习任务接口（首页查询或生成当天任务 / 开始学习 / 标记完成 / 自主选题）。"""

import uuid

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.daily_task import DailyTaskOut, TodayTasksOut
from app.schemas.study import SelfStudyIn, SelfStudyOut
from app.services.daily_task_service import DailyTaskService
from app.services.self_study_service import SelfStudyService

router = APIRouter(prefix="/daily-tasks", tags=["daily-tasks"])


@router.get("/today", response_model=TodayTasksOut)
def get_today_tasks(
    generate: bool = Query(
        default=True,
        description=(
            "true 保持既有闭环（先查后生成）；false 只查询不生成，"
            "供首页第一步「先查询当日是否已有任务」使用"
        ),
    ),
    db: Session = Depends(get_db),
) -> TodayTasksOut:
    """首页今日任务：先查询当天任务，已有直接返回；没有才按计划与进度生成。

    防重复：同一用户同一天不会重复生成任务；``generate=false`` 时不写任何数据。
    """
    return DailyTaskService(db).get_today_tasks(generate=generate)


@router.post("/today/generate", response_model=TodayTasksOut)
def generate_today_tasks(db: Session = Depends(get_db)) -> TodayTasksOut:
    """首页第二步：仅在当天还没有任务时生成；重复调用幂等返回既有任务。"""
    return DailyTaskService(db).generate_today_tasks()


@router.post("/self-study", response_model=SelfStudyOut)
def create_self_study_task(
    payload: SelfStudyIn, db: Session = Depends(get_db)
) -> SelfStudyOut:
    """自主选题：把指定知识点加入今日学习（阶段 7）。

    - 只接受已发布课程的知识点，草稿课程 / 无归属课时被拒绝；
    - 幂等：当天已有该知识点的任务时返回既有任务（``created=false``）；
    - 已掌握的知识点不重复排学习任务（409），引导去做复习/练习；
    - 未掌握的先修只提示不阻塞（``prerequisite_warnings``）；
    - 计划外课程的知识点允许自选，任务不挂计划。
    """
    return SelfStudyService(db).create_task(payload.knowledge_point_code)


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    """撤回自选任务：只允许撤回「自选且未完成」的任务。

    计划任务归学习计划管理；已完成任务属历史记录，两者均拒绝（409）。
    """
    SelfStudyService(db).delete_task(task_id)
    return Response(status_code=204)


@router.get("/{task_id}", response_model=DailyTaskOut)
def get_task_detail(task_id: uuid.UUID, db: Session = Depends(get_db)) -> DailyTaskOut:
    """查看任务详情（含知识点学习目标/难度/预计时长/掌握标准/资源/前置知识点）。"""
    return DailyTaskService(db).get_task_detail(task_id)


@router.post("/{task_id}/start", response_model=DailyTaskOut)
def start_task(task_id: uuid.UUID, db: Session = Depends(get_db)) -> DailyTaskOut:
    """标记开始学习：任务进入学习中状态，记录开始时间。"""
    return DailyTaskService(db).start_task(task_id)


@router.post("/{task_id}/complete", response_model=DailyTaskOut)
def complete_task(task_id: uuid.UUID, db: Session = Depends(get_db)) -> DailyTaskOut:
    """标记用户已完成：记录任务完成时间。

    只代表任务完成，不代表知识点已掌握（知识点进入待验证状态，
    掌握须经测验验证）。
    """
    return DailyTaskService(db).complete_task(task_id)
