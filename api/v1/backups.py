from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_admin
from core.database import get_db
from models.user import User
from services.backup_service import backup_service

router = APIRouter(prefix="/backups", tags=["System & Backups"])


@router.post(
    "/export",
    response_class=FileResponse,
    summary="Экспорт резервной копии БД в ZIP (только Admin)",
    description="Формирует ZIP-архив с CSV-таблицами основных сущностей и отдаёт его на скачивание.",
)
async def create_backup(
        db: AsyncSession = Depends(get_db),
        _current_user: User = Depends(get_current_admin),
):
    zip_path = await backup_service.create_csv_backup(db)

    return FileResponse(
        path=zip_path,
        filename=zip_path.name,
        media_type="application/zip",
    )