from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.exceptions import BadRequestException, NotFoundException
from models.warehouse import (
    WarehouseDocument,
    WarehouseMaterialStock,
    WarehouseDroneStock,
    DocStatusEnum,
    DocTypeEnum,
)


class WarehouseService:
    @staticmethod
    async def process_document(document_id: int, db: AsyncSession) -> WarehouseDocument:
        """Проведение складского документа и обновление остатков"""
        result = await db.execute(
            select(WarehouseDocument).where(WarehouseDocument.document_id == document_id)
        )
        doc = result.scalar_one_or_none()

        if not doc:
            raise NotFoundException("Складской документ не найден")

        if doc.status == DocStatusEnum.completed:
            raise BadRequestException("Документ уже проведен")

        if doc.status == DocStatusEnum.cancelled:
            raise BadRequestException("Нельзя провести отмененный документ")

        # 1. Проведение материалов
        for item in doc.material_items:
            stock_res = await db.execute(
                select(WarehouseMaterialStock).where(
                    WarehouseMaterialStock.warehouse_id == doc.warehouse_id,
                    WarehouseMaterialStock.material_id == item.material_id,
                )
            )
            stock = stock_res.scalar_one_or_none()

            if not stock:
                stock = WarehouseMaterialStock(
                    warehouse_id=doc.warehouse_id,
                    material_id=item.material_id,
                    quantity=0.0,
                )
                db.add(stock)

            if doc.doc_type == DocTypeEnum.incoming:
                stock.quantity += item.quantity
            elif doc.doc_type == DocTypeEnum.write_off:
                if stock.quantity < item.quantity:
                    raise BadRequestException(f"Недостаточно материала (ID: {item.material_id}) на складе")
                stock.quantity -= item.quantity
            elif doc.doc_type == DocTypeEnum.inventory:
                stock.quantity = item.quantity

        # 2. Проведение готовой продукции (дронов)
        for item in doc.drone_items:
            stock_res = await db.execute(
                select(WarehouseDroneStock).where(
                    WarehouseDroneStock.warehouse_id == doc.warehouse_id,
                    WarehouseDroneStock.variant_id == item.variant_id,
                )
            )
            stock = stock_res.scalar_one_or_none()

            if not stock:
                stock = WarehouseDroneStock(
                    warehouse_id=doc.warehouse_id,
                    variant_id=item.variant_id,
                    quantity=0,
                )
                db.add(stock)

            if doc.doc_type == DocTypeEnum.incoming:
                stock.quantity += item.quantity
            elif doc.doc_type == DocTypeEnum.write_off:
                if stock.quantity < item.quantity:
                    raise BadRequestException(f"Недостаточно комплектаций дрона (ID: {item.variant_id}) на складе")
                stock.quantity -= item.quantity
            elif doc.doc_type == DocTypeEnum.inventory:
                stock.quantity = item.quantity

        doc.status = DocStatusEnum.completed
        doc.processed_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(doc)
        return doc


warehouse_service = WarehouseService()