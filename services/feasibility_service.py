from typing import Dict, Any, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.exceptions import NotFoundException
from models.order import Order
from models.drone import DroneVariant, DroneVariantMaterial
from models.warehouse import WarehouseDroneStock, WarehouseMaterialStock


class FeasibilityService:
    @staticmethod
    async def check_order_feasibility(order_id: int, db: AsyncSession) -> Dict[str, Any]:
        """
        Проверка выполнимости заказа по двум уровням:
        1. Наличие готовых дронов на складе.
        2. Наличие материалов на складе для сборки недостающих дронов.
        """
        # Явно загружаем items у заказа через selectinload
        order_res = await db.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.order_id == order_id)
        )
        order = order_res.scalar_one_or_none()

        if not order:
            raise NotFoundException("Заказ не найден")

        drones_ready = True
        missing_variants: List[Dict[str, Any]] = []

        # ШАГ 1: Проверка готовой продукции
        for item in order.items:
            stock_res = await db.execute(
                select(WarehouseDroneStock).where(WarehouseDroneStock.variant_id == item.variant_id)
            )
            stocks = stock_res.scalars().all()
            total_available = sum(s.quantity for s in stocks)

            if total_available < item.quantity:
                drones_ready = False
                missing_variants.append({
                    "variant_id": item.variant_id,
                    "needed": item.quantity - total_available
                })

        drone_message = (
            "✅ На складе достаточно готовых дронов для выполнения заказа!"
            if drones_ready
            else f"⚠️ Готовой продукции недостаточно! Требуется произвести: {len(missing_variants)} позиций."
        )

        # ШАГ 2: Проверка материалов (BOM) для недостающих дронов
        materials_ready = True
        missing_materials: List[Dict[str, Any]] = []

        if not drones_ready:
            required_materials: Dict[int, float] = {}

            for missing in missing_variants:
                # Явно загружаем bom_materials у варианта дрона через selectinload
                var_res = await db.execute(
                    select(DroneVariant)
                    .options(selectinload(DroneVariant.bom_materials))
                    .where(DroneVariant.variant_id == missing["variant_id"])
                )
                variant = var_res.scalar_one_or_none()

                if variant:
                    for bom in variant.bom_materials:
                        mat_id = int(getattr(bom, "material_id"))
                        needed_qty = float(getattr(bom, "quantity")) * missing["needed"]
                        required_materials[mat_id] = required_materials.get(mat_id, 0.0) + needed_qty

            # Проверка совокупных остатков материалов на складах
            for mat_id, qty_needed in required_materials.items():
                mat_stock_res = await db.execute(
                    select(WarehouseMaterialStock).where(WarehouseMaterialStock.material_id == mat_id)
                )
                mat_stocks = mat_stock_res.scalars().all()
                mat_available = sum(float(ms.quantity) for ms in mat_stocks)

                if mat_available < qty_needed:
                    materials_ready = False
                    missing_materials.append({
                        "material_id": mat_id,
                        "needed": qty_needed,
                        "available": mat_available
                    })

            material_message = (
                "✅ На складах материалов достаточно компонентов для сборки недостающих дронов."
                if materials_ready
                else f"❌ Недостаточно материалов на складе! Отсутствует {len(missing_materials)} наименований компонентов."
            )
        else:
            material_message = "ℹ️ Проверка материалов не требуется (готовая продукция в наличии)."

        return {
            "order_id": order_id,
            "is_feasible": drones_ready or materials_ready,
            "drone_status_message": drone_message,
            "material_status_message": material_message,
            "missing_variants": missing_variants,
            "missing_materials": missing_materials
        }


feasibility_service = FeasibilityService()