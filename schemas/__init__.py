from schemas.common import BaseSchema, LocalizedText, LocalizedDescription
from schemas.role import RoleResponse
from schemas.user import (
    UserCreate,
    UserUpdate,
    UserChangePassword,
    UserResponse,
    UserAddressCreate,
    UserAddressResponse,
)
from schemas.token import Token, TokenPayload, RefreshTokenRequest
from schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse
from schemas.material import MaterialCreate, MaterialUpdate, MaterialResponse
from schemas.drone import (
    DroneCreate,
    DroneUpdate,
    DroneResponse,
    DroneVariantCreate,
    DroneVariantUpdate,
    DroneVariantResponse,
    DroneVariantMaterialCreate,
    DroneVariantMaterialUpdate,
    DroneVariantMaterialResponse,
)
from schemas.warehouse import (
    WarehouseCreate,
    WarehouseUpdate,
    WarehouseResponse,
    WarehouseMaterialStockCreate,
    WarehouseMaterialStockUpdate,
    WarehouseMaterialStockResponse,
    WarehouseDroneStockCreate,
    WarehouseDroneStockUpdate,
    WarehouseDroneStockResponse,
)
from schemas.warehouse_document import (
    WarehouseDocumentCreate,
    WarehouseDocumentStatusUpdate,
    WarehouseDocumentResponse,
    WarehouseDocMaterialItemCreate,
    WarehouseDocDroneItemCreate,
)
from schemas.order import OrderCreate, OrderStatusUpdate, OrderResponse, OrderItemCreate, OrderItemResponse
from schemas.invoice import InvoiceCreate, InvoiceResponse
from schemas.news import NewsCreate, NewsUpdate, NewsResponse
from schemas.audit_log import AuditLogResponse

__all__ = [
    "BaseSchema",
    "LocalizedText",
    "LocalizedDescription",
    "RoleResponse",
    "UserCreate",
    "UserUpdate",
    "UserChangePassword",
    "UserResponse",
    "UserAddressCreate",
    "UserAddressResponse",
    "Token",
    "TokenPayload",
    "RefreshTokenRequest",
    "CategoryCreate",
    "CategoryUpdate",
    "CategoryResponse",
    "MaterialCreate",
    "MaterialUpdate",
    "MaterialResponse",
    "DroneCreate",
    "DroneUpdate",
    "DroneResponse",
    "DroneVariantCreate",
    "DroneVariantUpdate",
    "DroneVariantResponse",
    "DroneVariantMaterialCreate",
    "DroneVariantMaterialUpdate",
    "DroneVariantMaterialResponse",
    "WarehouseCreate",
    "WarehouseUpdate",
    "WarehouseResponse",
    "WarehouseMaterialStockCreate",
    "WarehouseMaterialStockUpdate",
    "WarehouseMaterialStockResponse",
    "WarehouseDroneStockCreate",
    "WarehouseDroneStockUpdate",
    "WarehouseDroneStockResponse",
    "WarehouseDocumentCreate",
    "WarehouseDocumentStatusUpdate",
    "WarehouseDocumentResponse",
    "WarehouseDocMaterialItemCreate",
    "WarehouseDocDroneItemCreate",
    "OrderCreate",
    "OrderStatusUpdate",
    "OrderResponse",
    "OrderItemCreate",
    "OrderItemResponse",
    "InvoiceCreate",
    "InvoiceResponse",
    "NewsCreate",
    "NewsUpdate",
    "NewsResponse",
    "AuditLogResponse",
]