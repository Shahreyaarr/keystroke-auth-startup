"""
Tenant Schemas
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from app.models.tenant import SubscriptionPlan


class TenantBase(BaseModel):
    """Base tenant schema"""
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = None


class TenantCreate(TenantBase):
    """Tenant creation schema"""
    plan: SubscriptionPlan = SubscriptionPlan.STARTER
    billing_email: Optional[EmailStr] = None
    gst_number: Optional[str] = Field(None, max_length=50)


class TenantUpdate(BaseModel):
    """Tenant update schema"""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = None
    is_active: Optional[bool] = None
    billing_email: Optional[EmailStr] = None


class TenantConfigUpdate(BaseModel):
    """Tenant configuration update"""
    logo_url: Optional[str] = None
    primary_color: Optional[str] = Field(None, regex=r"^#[0-9A-Fa-f]{6}$")
    secondary_color: Optional[str] = Field(None, regex=r"^#[0-9A-Fa-f]{6}$")
    custom_domain: Optional[str] = None
    email_from_name: Optional[str] = Field(None, max_length=100)
    auth_threshold: Optional[int] = Field(None, ge=0, le=100)
    mfa_required: Optional[bool] = None
    session_timeout: Optional[int] = Field(None, ge=5, le=480)
    features: Optional[Dict[str, Any]] = None


class TenantConfigResponse(BaseModel):
    """Tenant configuration response"""
    logo_url: Optional[str]
    primary_color: str
    secondary_color: str
    custom_domain: Optional[str]
    email_from_name: Optional[str]
    auth_threshold: int
    mfa_required: bool
    session_timeout: int
    features: Dict[str, Any]


class TenantResponse(TenantBase):
    """Tenant response schema"""
    id: str
    slug: str
    plan: SubscriptionPlan
    is_active: bool
    is_trial: bool
    trial_ends_at: Optional[datetime]
    api_calls_count: int
    api_calls_limit: int
    users_count: int
    users_limit: int
    created_at: datetime
    config: Optional[TenantConfigResponse]
    
    class Config:
        from_attributes = True


class TenantUsageResponse(BaseModel):
    """Tenant usage statistics"""
    tenant_id: str
    api_calls_this_month: int
    api_calls_limit: int
    api_calls_percentage: float
    users_count: int
    users_limit: int
    users_percentage: float
    auth_success_rate: float
    avg_auth_score: float
