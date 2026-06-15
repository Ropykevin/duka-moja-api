from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.catalog.attribute_router import router as attributes_router
from app.modules.catalog.brand_router import router as brands_router
from app.modules.catalog.category_router import router as categories_router
from app.modules.catalog.router import router as products_router
from app.modules.inventory.router import router as inventory_router
from app.modules.procurement.purchase_order_router import router as purchase_orders_router
from app.modules.procurement.supplier_router import router as suppliers_router
from app.modules.stores.branch_router import router as branches_router
from app.modules.stores.router import router as stores_router
from app.modules.subscriptions.router import router as subscriptions_router
from app.modules.tenants.router import router as tenants_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(tenants_router)
api_router.include_router(stores_router)
api_router.include_router(branches_router)
api_router.include_router(categories_router)
api_router.include_router(brands_router)
api_router.include_router(attributes_router)
api_router.include_router(products_router)
api_router.include_router(inventory_router)
api_router.include_router(suppliers_router)
api_router.include_router(purchase_orders_router)
api_router.include_router(subscriptions_router)