"""学习计划接口（创建 → 草稿 → 用户确认 → 生效；调整走新版本）。"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.plan import (
    CurrentPlanOut,
    PlanAdjust,
    PlanCreate,
    PlanOut,
    PlanVersionOut,
)
from app.services.plan_service import PlanService

router = APIRouter(prefix="/plans", tags=["plans"])


@router.post("", response_model=CurrentPlanOut, status_code=201)
def create_plan(payload: PlanCreate, db: Session = Depends(get_db)) -> CurrentPlanOut:
    """创建学习计划：提交初始诊断信息，后端排期并生成草稿，等待用户确认。"""
    return PlanService(db).create_plan(payload)


@router.post("/{plan_id}/confirm", response_model=CurrentPlanOut)
def confirm_plan(plan_id: uuid.UUID, db: Session = Depends(get_db)) -> CurrentPlanOut:
    """确认计划：待确认草稿版本正式生效（旧生效版本保留为历史）。"""
    return PlanService(db).confirm_plan(plan_id)


@router.post("/{plan_id}/adjust", response_model=CurrentPlanOut)
def adjust_plan(
    plan_id: uuid.UUID, payload: PlanAdjust, db: Session = Depends(get_db)
) -> CurrentPlanOut:
    """调整计划（学习目标/每日时长/期望周期）：生成新草稿版本，确认后生效。"""
    return PlanService(db).adjust_plan(plan_id, payload)


@router.get("/current", response_model=CurrentPlanOut)
def get_current_plan(db: Session = Depends(get_db)) -> CurrentPlanOut:
    """查看当前计划：生效版本（含项目）与待确认草稿（如有）。"""
    return PlanService(db).get_current_plan()


@router.get("/{plan_id}", response_model=PlanOut)
def get_plan_detail(plan_id: uuid.UUID, db: Session = Depends(get_db)) -> PlanOut:
    """查看计划详情：计划信息 + 全部历史版本概要。"""
    return PlanService(db).get_plan_detail(plan_id)


@router.get("/{plan_id}/versions/{version_number}", response_model=PlanVersionOut)
def get_plan_version(
    plan_id: uuid.UUID, version_number: int, db: Session = Depends(get_db)
) -> PlanVersionOut:
    """查看历史计划版本详情（含该版本的计划项目）。"""
    return PlanService(db).get_plan_version(plan_id, version_number)
