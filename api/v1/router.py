from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.stores.branch_router import router as branches_router
from app.modules.stores.router import router as stores_router
from app.modules.subscriptions.router import router as subscriptions_router
from app.modules.tenants.router import router as tenants_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(tenants_router)
api_router.include_router(stores_router)
api_router.include_router(branches_router)
api_router.include_router(subscriptions_router)
