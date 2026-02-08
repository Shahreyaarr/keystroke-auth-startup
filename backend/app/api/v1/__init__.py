"""
API v1 Routes
"""

from fastapi import APIRouter
from app.api.v1 import auth, users, tenants, keystroke, analytics, billing

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["Tenants"])
api_router.include_router(keystroke.router, prefix="/keystroke", tags=["Keystroke Dynamics"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(billing.router, prefix="/billing", tags=["Billing"])
