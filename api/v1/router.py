from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.catalog.attribute_router import router as attributes_router
from app.modules.catalog.brand_router import router as brands_router
from app.modules.catalog.category_router import router as categories_router
from app.modules.catalog.router import router as products_router
from app.modules.customers.cart_router import router as cart_router
from app.modules.customers.customer_router import router as customers_router
from app.modules.customers.order_router import router as orders_router
from app.modules.pos.register_router import router as cash_registers_router
from app.modules.pos.session_router import router as cash_sessions_router
from app.modules.pos.sale_router import router as sales_router
from app.modules.payments.provider_router import router as payment_providers_router
from app.modules.payments.method_router import router as payment_methods_router
from app.modules.payments.payment_router import router as payments_router
from app.modules.shipping.method_router import router as shipping_methods_router
from app.modules.shipping.shipment_router import router as shipments_router
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
api_router.include_router(customers_router)
api_router.include_router(cart_router)
api_router.include_router(orders_router)
api_router.include_router(cash_registers_router)
api_router.include_router(cash_sessions_router)
api_router.include_router(sales_router)
api_router.include_router(payment_providers_router)
api_router.include_router(payment_methods_router)
api_router.include_router(payments_router)
api_router.include_router(shipping_methods_router)
api_router.include_router(shipments_router)
api_router.include_router(inventory_router)
api_router.include_router(suppliers_router)
api_router.include_router(purchase_orders_router)
api_router.include_router(subscriptions_router)