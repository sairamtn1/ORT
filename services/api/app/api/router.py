from fastapi import APIRouter

from .v1.auth import router as auth_router
from .v1.crud import router as crud_router
from .v1.health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(crud_router)