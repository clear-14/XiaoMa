"""模型配置接口（增删改查、默认模型切换、连接测试）。"""

import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.model_config import (
    ModelConfigCreate,
    ModelConfigOut,
    ModelConfigUpdate,
    TestConnectionOut,
)
from app.services.model_config_service import ModelConfigService

router = APIRouter(prefix="/model-configs", tags=["model-configs"])


@router.get("", response_model=list[ModelConfigOut])
def list_model_configs(db: Session = Depends(get_db)) -> list[ModelConfigOut]:
    """获取全部模型配置（API Key 一律脱敏展示）。"""
    return ModelConfigService(db).list_configs()


@router.post("", response_model=ModelConfigOut, status_code=201)
def create_model_config(
    payload: ModelConfigCreate, db: Session = Depends(get_db)
) -> ModelConfigOut:
    """添加模型配置（API Key 加密保存，响应仅返回脱敏值）。"""
    return ModelConfigService(db).create_config(payload)


@router.get("/{config_id}", response_model=ModelConfigOut)
def get_model_config(config_id: uuid.UUID, db: Session = Depends(get_db)) -> ModelConfigOut:
    """获取模型配置基本信息（脱敏）。"""
    return ModelConfigService(db).get_config(config_id)


@router.put("/{config_id}", response_model=ModelConfigOut)
def update_model_config(
    config_id: uuid.UUID, payload: ModelConfigUpdate, db: Session = Depends(get_db)
) -> ModelConfigOut:
    """编辑模型配置；不提交 api_key 表示保持原密钥不变。"""
    return ModelConfigService(db).update_config(config_id, payload)


@router.delete("/{config_id}", status_code=204)
def delete_model_config(config_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    """删除模型配置；删除默认模型后系统保持无默认状态。"""
    ModelConfigService(db).delete_config(config_id)
    return Response(status_code=204)


@router.post("/{config_id}/default", response_model=ModelConfigOut)
def set_default_model(config_id: uuid.UUID, db: Session = Depends(get_db)) -> ModelConfigOut:
    """将配置设为默认模型（同时取消其他配置的默认标记）。"""
    return ModelConfigService(db).set_default(config_id)


@router.post("/{config_id}/test", response_model=TestConnectionOut)
async def test_model_connection(
    config_id: uuid.UUID, db: Session = Depends(get_db)
) -> TestConnectionOut:
    """测试连接：发送一次最小请求，返回耗时与回复；失败时 ok=false 并说明原因。"""
    return await ModelConfigService(db).test_connection(config_id)
