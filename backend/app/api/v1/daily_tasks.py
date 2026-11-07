"""每日学习任务接口（首页查询或生成当天任务 / 开始学习 / 标记完成）。"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.daily_task import DailyTaskOut, TodayTasksOut
from app.services.daily_task_service import DailyTaskService

router = APIRouter(prefix="/daily-tasks", tags=["daily-tasks"])


@router.get("/today", response_model=TodayTasksOut)
def get_today_tasks(db: Session = Depends(get_db)) -> TodayTasksOut:
    """首页今日任务：查询当天任务，已有直接返回；没有则按学习计划与当前进度生成。

    防重复：同一用户同一天不会重复生成任务。
    """
    return DailyTaskService(db).get_today_tasks()


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
