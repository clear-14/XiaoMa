"""学习档案接口。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.profile import ProfileOut, ProfileUpdate
from app.services.profile_service import ProfileService

router = APIRouter(tags=["profile"])


@router.get("/profile", response_model=ProfileOut)
def get_profile(db: Session = Depends(get_db)) -> ProfileOut:
    """获取当前用户学习档案。"""
    return ProfileService(db).get_profile()


@router.put("/profile", response_model=ProfileOut)
def update_profile(payload: ProfileUpdate, db: Session = Depends(get_db)) -> ProfileOut:
    """更新当前用户学习档案（仅更新提交的字段，未提交字段保持不变）。"""
    return ProfileService(db).update_profile(payload)
