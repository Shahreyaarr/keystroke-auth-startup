"""
Tenant Management API Routes
"""

from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.config import settings
from app.core.security import generate_tenant_id
from app.models.user import User, UserRole
from app.models.tenant import Tenant, TenantConfig, SubscriptionPlan
from app.models.auth import AuthLog
from app.schemas.tenant import (
    TenantCreate, TenantResponse, TenantUpdate,
    TenantConfigUpdate, TenantConfigResponse, TenantUsageResponse
)
from app.api.v1.auth import get_current_active_user, require_role

router = APIRouter()


@router.get("", response_model=List[TenantResponse])
async def list_tenants(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    plan: Optional[SubscriptionPlan] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPER_ADMIN]))
):
    """List all tenants (super admin only)"""
    query = db.query(Tenant)
    
    if search:
        query = query.filter(
            (Tenant.name.ilike(f"%{search}%")) |
            (Tenant.email.ilike(f"%{search}%"))
        )
    
    if plan:
        query = query.filter(Tenant.plan == plan)
    
    if is_active is not None:
        query = query.filter(Tenant.is_active == is_active)
    
    tenants = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return [TenantResponse.model_validate(t) for t in tenants]


@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant_data: TenantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPER_ADMIN]))
):
    """Create a new tenant (super admin only)"""
    # Check slug uniqueness
    existing = db.query(Tenant).filter(Tenant.slug == tenant_data.name.lower().replace(' ', '-')).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant with similar name already exists"
        )
    
    # Create tenant
    tenant = Tenant(
        id=generate_tenant_id(),
        name=tenant_data.name,
        slug=tenant_data.name.lower().replace(' ', '-'),
        email=tenant_data.email,
        phone=tenant_data.phone,
        address=tenant_data.address,
        plan=tenant_data.plan,
        billing_email=tenant_data.billing_email,
        gst_number=tenant_data.gst_number,
        is_trial=True,
        trial_ends_at=datetime.utcnow() + timedelta(days=settings.TRIAL_DAYS)
    )
    
    db.add(tenant)
    db.flush()
    
    # Create default config
    config = TenantConfig(tenant_id=tenant.id)
    db.add(config)
    
    db.commit()
    db.refresh(tenant)
    
    return tenant


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get tenant by ID"""
    # Check permissions
    if current_user.role != UserRole.SUPER_ADMIN and current_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access this tenant"
        )
    
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    return tenant


@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str,
    tenant_data: TenantUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update tenant"""
    # Check permissions
    if current_user.role != UserRole.SUPER_ADMIN and current_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot update this tenant"
        )
    
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    # Update fields
    update_data = tenant_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tenant, field, value)
    
    db.commit()
    db.refresh(tenant)
    
    return tenant


@router.get("/{tenant_id}/config", response_model=TenantConfigResponse)
async def get_tenant_config(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get tenant configuration"""
    # Check permissions
    if current_user.role != UserRole.SUPER_ADMIN and current_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access this tenant's config"
        )
    
    config = db.query(TenantConfig).filter(TenantConfig.tenant_id == tenant_id).first()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Config not found"
        )
    
    return config


@router.put("/{tenant_id}/config", response_model=TenantConfigResponse)
async def update_tenant_config(
    tenant_id: str,
    config_data: TenantConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update tenant configuration"""
    # Check permissions
    if current_user.role != UserRole.SUPER_ADMIN and current_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot update this tenant's config"
        )
    
    config = db.query(TenantConfig).filter(TenantConfig.tenant_id == tenant_id).first()
    
    if not config:
        config = TenantConfig(tenant_id=tenant_id)
        db.add(config)
    
    # Update fields
    update_data = config_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)
    
    db.commit()
    db.refresh(config)
    
    return config


@router.get("/{tenant_id}/usage", response_model=TenantUsageResponse)
async def get_tenant_usage(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get tenant usage statistics"""
    # Check permissions
    if current_user.role != UserRole.SUPER_ADMIN and current_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access this tenant's usage"
        )
    
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    # Calculate API usage percentage
    api_percentage = (tenant.api_calls_count / tenant.api_calls_limit * 100) if tenant.api_calls_limit > 0 else 0
    
    # Calculate user usage percentage
    user_percentage = (tenant.users_count / tenant.users_limit * 100) if tenant.users_limit > 0 else 0
    
    # Get auth success rate
    auth_logs = db.query(AuthLog).filter(
        AuthLog.tenant_id == tenant_id,
        AuthLog.event_type == "verify"
    ).all()
    
    success_rate = 0
    avg_score = 0
    if auth_logs:
        successful = len([l for l in auth_logs if l.success])
        success_rate = (successful / len(auth_logs)) * 100
        
        scores = [l.auth_score for l in auth_logs if l.auth_score is not None]
        if scores:
            avg_score = sum(scores) / len(scores)
    
    return TenantUsageResponse(
        tenant_id=tenant_id,
        api_calls_this_month=tenant.api_calls_count,
        api_calls_limit=tenant.api_calls_limit,
        api_calls_percentage=round(api_percentage, 2),
        users_count=tenant.users_count,
        users_limit=tenant.users_limit,
        users_percentage=round(user_percentage, 2),
        auth_success_rate=round(success_rate, 2),
        avg_auth_score=round(avg_score, 2)
    )


@router.put("/{tenant_id}/status")
async def update_tenant_status(
    tenant_id: str,
    is_active: bool,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPER_ADMIN]))
):
    """Activate/deactivate tenant (super admin only)"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    tenant.is_active = is_active
    db.commit()
    
    return {"message": f"Tenant {'activated' if is_active else 'deactivated'} successfully"}
