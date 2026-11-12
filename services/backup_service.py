import csv
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.config import settings
from core.logger import app_logger
from models import User, Material, Drone, Order, WarehouseDocument


class BackupService:
    @staticmethod
    async def create_csv_backup(db: AsyncSession) -> Path:
        """Экспорт таблиц БД в CSV-файлы и упаковка в ZIP-архив"""
        settings.BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        zip_path = settings.BACKUPS_DIR / f"backup_{timestamp}.zip"

        tables_to_backup = [
            ("users", User),
            ("materials", Material),
            ("drones", Drone),
            ("orders", Order),
            ("warehouse_documents", WarehouseDocument),
        ]

        temp_csv_files = []
        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for table_name, model_cls in tables_to_backup:
                    result = await db.execute(select(model_cls))
                    records = result.scalars().all()

                    if not records:
                        continue

                    csv_filename = f"{table_name}.csv"
                    csv_filepath = settings.BACKUPS_DIR / csv_filename
                    temp_csv_files.append(csv_filepath)

                    # Получение списка колонок модели
                    columns = [c.name for c in model_cls.__table__.columns]

                    with open(csv_filepath, mode="w", newline="", encoding="utf-8") as f:
                        writer = csv.writer(f)
                        writer.writerow(columns)
                        for record in records:
                            writer.writerow([getattr(record, col) for col in columns])

                    zip_file.write(csv_filepath, arcname=csv_filename)

            app_logger.info(f"Резервная копия успешно создана: {zip_path.name}")
            return zip_path
        finally:
            # Очистка временных CSV-файлов
            for csv_file in temp_csv_files:
                if csv_file.exists():
                    csv_file.unlink()


backup_service = BackupService()