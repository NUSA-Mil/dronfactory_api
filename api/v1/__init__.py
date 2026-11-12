from fastapi import APIRouter
from api.v1.auth import router as auth_router
from api.v1.drones import router as drones_router
from api.v1.audit_logs import router as audit_logs_router
from api.v1.categories import router as categories_router
from api.v1.materials import router as materials_router
from api.v1.warehouses import router as warehouses_router
from api.v1.warehouse_documents import router as warehouse_documents_router
from api.v1.news import router as news_router
from api.v1.orders import router as orders_router
from api.v1.roles import router as roles_router
from api.v1.users import router as users_router
from api.v1.user_addresses import router as user_addresses_router
from api.v1.invoices import router as invoices_router
from api.v1.backups import router as backups_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(drones_router)
api_router.include_router(audit_logs_router)
api_router.include_router(categories_router)
api_router.include_router(materials_router)
api_router.include_router(warehouses_router)
api_router.include_router(warehouse_documents_router)
api_router.include_router(news_router)
api_router.include_router(orders_router)
api_router.include_router(roles_router)
api_router.include_router(users_router)
api_router.include_router(user_addresses_router)
api_router.include_router(invoices_router)
api_router.include_router(backups_router)