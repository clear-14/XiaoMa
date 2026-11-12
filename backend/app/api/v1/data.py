"""数据备份接口（系统设置页：创建备份、查看列表、下载）。

数据库恢复会替换 SQLite 文件，必须通过 CLI 在后端停止时执行，避免运行中
替换导致连接损坏；恢复前自动备份当前数据，详见 docs/备份与恢复.md。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.backup import BackupOut
from app.services.backup_service import BackupError, BackupInfo, BackupService

router = APIRouter(prefix="/data", tags=["data"])


def _service(db: Session = Depends(get_db)) -> BackupService:
    try:
        return BackupService.from_session(db)
    except BackupError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _to_out(info: BackupInfo) -> BackupOut:
    return BackupOut(
        name=info.name,
        size_bytes=info.size_bytes,
        created_at=info.created_at,
    )


@router.get("/backups", response_model=list[BackupOut])
def list_backups(service: BackupService = Depends(_service)) -> list[BackupOut]:
    """列出数据卷中的备份文件（按时间倒序）。"""
    return [_to_out(item) for item in service.list_backups()]


@router.post("/backups", response_model=BackupOut, status_code=201)
def create_backup(
    service: BackupService = Depends(_service),
) -> BackupOut:
    """立即创建一次 SQLite 一致性备份。"""
    try:
        return _to_out(service.create_backup())
    except BackupError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/backups/{name}")
def download_backup(
    name: str, service: BackupService = Depends(_service)
) -> FileResponse:
    """下载指定备份文件；文件名经过路径穿越校验。"""
    try:
        path = service.resolve_backup(name)
    except BackupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(
        path,
        media_type="application/x-sqlite3",
        filename=name,
    )


@router.delete("/backups/{name}", status_code=204)
def delete_backup(
    name: str, service: BackupService = Depends(_service)
) -> Response:
    """删除指定备份文件。删除操作不可恢复，前端会二次确认。"""
    try:
        path = service.resolve_backup(name)
        path.unlink()
    except BackupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=400, detail=f"删除备份失败：{exc}") from exc
    return Response(status_code=204)
