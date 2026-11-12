import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.deps import get_current_storekeeper
from core.database import get_db
from core.exceptions import BadRequestException, InsufficientStockException, NotFoundException
from core.logger import log_audit
from models.user import User
from models.warehouse import (
    DocStatusEnum,
    DocTypeEnum,
    WarehouseDocDroneItem,
    WarehouseDocMaterialItem,
    WarehouseDocument,
    WarehouseDroneStock,
    WarehouseMaterialStock,
)
from schemas.warehouse_document import (
    WarehouseDocumentCreate,
    WarehouseDocumentResponse,
    WarehouseDocumentStatusUpdate,
)

router = APIRouter(prefix="/warehouse-documents", tags=["Warehouse Documents & Operations"])


@router.get(
    "",
    response_model=List[WarehouseDocumentResponse],
    summary="Получить журнал складских документов",
)
async def get_warehouse_documents(
    warehouse_id: Optional[int] = Query(None, description="Фильтр по складу"),
    doc_type: Optional[DocTypeEnum] = Query(None, description="Тип (incoming, write_off, inventory)"),
    doc_status: Optional[DocStatusEnum] = Query(None, alias="status", description="Статус (draft, completed, cancelled)"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_storekeeper),
):
    offset = (page - 1) * limit
    stmt = select(WarehouseDocument)

    if warehouse_id:
        stmt = stmt.where(WarehouseDocument.warehouse_id == warehouse_id)
    if doc_type:
        stmt = stmt.where(WarehouseDocument.doc_type == doc_type)
    if doc_status:
        stmt = stmt.where(WarehouseDocument.status == doc_status)

    stmt = stmt.order_by(WarehouseDocument.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get(
    "/{document_id}",
    response_model=WarehouseDocumentResponse,
    summary="Получить документ по ID",
)
async def get_warehouse_document_by_id(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_storekeeper),
):
    stmt = (
        select(WarehouseDocument)
        .options(
            selectinload(WarehouseDocument.material_items),
            selectinload(WarehouseDocument.drone_items),
        )
        .where(WarehouseDocument.document_id == document_id)
    )
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    if not doc:
        raise NotFoundException("Складской документ не найден")
    return doc


@router.post(
    "",
    response_model=WarehouseDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новый складской документ (Черновик)",
)
async def create_warehouse_document(
    doc_in: WarehouseDocumentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_storekeeper),
):
    user_id_int = int(getattr(current_user, "user_id"))
    doc_number = f"DOC-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    doc = WarehouseDocument(
        document_number=doc_number,
        warehouse_id=doc_in.warehouse_id,
        created_by=user_id_int,
        doc_type=doc_in.doc_type,
        status=DocStatusEnum.draft,
        reason=doc_in.reason,
        order_id=doc_in.order_id,
    )
    db.add(doc)
    await db.flush()

    doc_id_int = int(getattr(doc, "document_id"))

    if doc_in.material_items:
        for m_item in doc_in.material_items:
            db.add(
                WarehouseDocMaterialItem(
                    document_id=doc_id_int,
                    material_id=m_item.material_id,
                    quantity=m_item.quantity,
                )
            )

    if doc_in.drone_items:
        for d_item in doc_in.drone_items:
            db.add(
                WarehouseDocDroneItem(
                    document_id=doc_id_int,
                    variant_id=d_item.variant_id,
                    quantity=d_item.quantity,
                )
            )

    await db.commit()

    stmt = (
        select(WarehouseDocument)
        .options(
            selectinload(WarehouseDocument.material_items),
            selectinload(WarehouseDocument.drone_items),
        )
        .where(WarehouseDocument.document_id == doc_id_int)
    )
    res = await db.execute(stmt)
    return res.scalar_one()


@router.patch(
    "/{document_id}/status",
    response_model=WarehouseDocumentResponse,
    summary="Проведение документа (изменение статуса на completed/cancelled)",
)
async def process_warehouse_document(
    document_id: int,
    status_in: WarehouseDocumentStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_storekeeper),
):
    stmt = (
        select(WarehouseDocument)
        .options(
            selectinload(WarehouseDocument.material_items),
            selectinload(WarehouseDocument.drone_items),
        )
        .where(WarehouseDocument.document_id == document_id)
    )
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()

    if not doc:
        raise NotFoundException("Складской документ не найден")

    if doc.status != DocStatusEnum.draft:
        raise BadRequestException("Провести или отменить можно только документ в статусе draft")

    new_status = status_in.status

    if new_status == DocStatusEnum.completed:
        # Проведение документа: транзакционное обновление остатков
        # 1. ОБРАБОТКА МАТЕРИАЛОВ
        for m_item in doc.material_items:
            stock_stmt = select(WarehouseMaterialStock).where(
                and_(
                    WarehouseMaterialStock.warehouse_id == doc.warehouse_id,
                    WarehouseMaterialStock.material_id == m_item.material_id,
                )
            )
            stock_res = await db.execute(stock_stmt)
            m_stock = stock_res.scalar_one_or_none()

            if not m_stock:
                # Если записи остатка нет, создаем новую
                m_stock = WarehouseMaterialStock(
                    warehouse_id=doc.warehouse_id,
                    material_id=m_item.material_id,
                    quantity=0.0,
                )
                db.add(m_stock)

            current_qty = float(getattr(m_stock, "quantity"))
            item_qty = float(m_item.quantity)

            if doc.doc_type == DocTypeEnum.incoming:
                setattr(m_stock, "quantity", current_qty + item_qty)
            elif doc.doc_type == DocTypeEnum.write_off:
                if current_qty < item_qty:
                    raise InsufficientStockException(
                        f"Недостаточно материала (ID: {m_item.material_id}) на складе для списания"
                    )
                setattr(m_stock, "quantity", current_qty - item_qty)
            elif doc.doc_type == DocTypeEnum.inventory:
                setattr(m_stock, "quantity", item_qty)

        # 2. ОБРАБОТКА ДРОНОВ
        for d_item in doc.drone_items:
            d_stock_stmt = select(WarehouseDroneStock).where(
                and_(
                    WarehouseDroneStock.warehouse_id == doc.warehouse_id,
                    WarehouseDroneStock.variant_id == d_item.variant_id,
                )
            )
            d_stock_res = await db.execute(d_stock_stmt)
            d_stock = d_stock_res.scalar_one_or_none()

            if not d_stock:
                d_stock = WarehouseDroneStock(
                    warehouse_id=doc.warehouse_id,
                    variant_id=d_item.variant_id,
                    quantity=0,
                )
                db.add(d_stock)

            current_d_qty = int(getattr(d_stock, "quantity"))
            item_d_qty = int(d_item.quantity)

            if doc.doc_type == DocTypeEnum.incoming:
                setattr(d_stock, "quantity", current_d_qty + item_d_qty)
            elif doc.doc_type == DocTypeEnum.write_off:
                if current_d_qty < item_d_qty:
                    raise InsufficientStockException(
                        f"Недостаточно дронов (Variant ID: {d_item.variant_id}) на складе для списания"
                    )
                setattr(d_stock, "quantity", current_d_qty - item_d_qty)
            elif doc.doc_type == DocTypeEnum.inventory:
                setattr(d_stock, "quantity", item_d_qty)

        doc.processed_at = datetime.now(timezone.utc)

    doc.status = new_status
    await db.commit()

    log_audit(
        user_id=int(getattr(current_user, "user_id")),
        ip_address="127.0.0.1",
        category="WAREHOUSE",
        action=f"DOC_{new_status.value.upper()}",
        details=f"Складской документ {doc.document_number} переведен в статус {new_status.value}",
    )

    return doc