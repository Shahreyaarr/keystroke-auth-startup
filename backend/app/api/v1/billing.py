"""
Billing API Routes
"""

from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.models.user import User, UserRole
from app.models.tenant import Tenant, SubscriptionPlan
from app.models.billing import Subscription, Invoice, Payment, SubscriptionStatus, InvoiceStatus

router = APIRouter()


def get_current_active_user(db: Session = Depends()):
    from app.api.v1.auth import get_current_active_user as get_user
    return get_user


PLAN_PRICES = {
    SubscriptionPlan.STARTER: 2999,
    SubscriptionPlan.GROWTH: 14999,
    SubscriptionPlan.BUSINESS: 49999,
    SubscriptionPlan.ENTERPRISE: 0  # Custom pricing
}


@router.get("/plans")
async def get_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get available subscription plans"""
    plans = [
        {
            "id": "starter",
            "name": "Starter",
            "price": 2999,
            "currency": "INR",
            "billing_cycle": "monthly",
            "description": "Perfect for small teams and startups",
            "features": [
                "Up to 100 users",
                "10,000 API calls/month",
                "Basic analytics",
                "Email support",
                "Standard security"
            ],
            "limits": {
                "users": 100,
                "api_calls": 10000
            }
        },
        {
            "id": "growth",
            "name": "Growth",
            "price": 14999,
            "currency": "INR",
            "billing_cycle": "monthly",
            "description": "For growing businesses",
            "features": [
                "Up to 500 users",
                "50,000 API calls/month",
                "Advanced analytics",
                "Priority support",
                "White-label options",
                "Custom branding"
            ],
            "limits": {
                "users": 500,
                "api_calls": 50000
            }
        },
        {
            "id": "business",
            "name": "Business",
            "price": 49999,
            "currency": "INR",
            "billing_cycle": "monthly",
            "description": "For large organizations",
            "features": [
                "Up to 2,000 users",
                "200,000 API calls/month",
                "Enterprise analytics",
                "24/7 phone support",
                "Full white-label",
                "SLA guarantee",
                "Dedicated account manager"
            ],
            "limits": {
                "users": 2000,
                "api_calls": 200000
            }
        },
        {
            "id": "enterprise",
            "name": "Enterprise",
            "price": 0,
            "currency": "INR",
            "billing_cycle": "custom",
            "description": "Custom solution for enterprises",
            "features": [
                "Unlimited users",
                "Unlimited API calls",
                "Custom integrations",
                "On-premise deployment option",
                "Dedicated infrastructure",
                "Custom SLA",
                "Technical account manager"
            ],
            "limits": {
                "users": -1,
                "api_calls": -1
            }
        }
    ]
    
    return {"plans": plans}


@router.post("/subscribe")
async def subscribe(
    plan: SubscriptionPlan,
    billing_cycle: str = "monthly",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Subscribe to a plan"""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.TENANT_ADMIN]:
        raise HTTPException(
            status_code=403,
            detail="Only admins can manage subscriptions"
        )
    
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Check if enterprise (requires contact)
    if plan == SubscriptionPlan.ENTERPRISE:
        return {
            "message": "Please contact sales for Enterprise plan",
            "contact_email": "sales@keystrokeauth.com"
        }
    
    # Calculate period
    if billing_cycle == "yearly":
        period_days = 365
        price = PLAN_PRICES[plan] * 10  # 2 months free
    else:
        period_days = 30
        price = PLAN_PRICES[plan]
    
    # Create or update subscription
    existing = db.query(Subscription).filter(
        Subscription.tenant_id == tenant.id,
        Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL])
    ).first()
    
    now = datetime.utcnow()
    
    if existing:
        existing.plan = plan.value
        existing.amount = price
        existing.billing_cycle = billing_cycle
        existing.current_period_start = now
        existing.current_period_end = now + timedelta(days=period_days)
        existing.status = SubscriptionStatus.ACTIVE
        subscription = existing
    else:
        subscription = Subscription(
            tenant_id=tenant.id,
            plan=plan.value,
            amount=price,
            currency="INR",
            billing_cycle=billing_cycle,
            current_period_start=now,
            current_period_end=now + timedelta(days=period_days),
            status=SubscriptionStatus.ACTIVE
        )
        db.add(subscription)
    
    # Update tenant
    tenant.plan = plan
    tenant.is_trial = False
    tenant.plan_expires_at = subscription.current_period_end
    tenant.api_calls_limit = 10000 if plan == SubscriptionPlan.STARTER else 50000 if plan == SubscriptionPlan.GROWTH else 200000
    tenant.users_limit = 100 if plan == SubscriptionPlan.STARTER else 500 if plan == SubscriptionPlan.GROWTH else 2000
    
    db.commit()
    
    return {
        "message": f"Successfully subscribed to {plan.value} plan",
        "subscription": subscription.to_dict()
    }


@router.get("/invoices")
async def get_invoices(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get invoices for tenant"""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.TENANT_ADMIN]:
        raise HTTPException(
            status_code=403,
            detail="Only admins can view invoices"
        )
    
    query = db.query(Invoice).filter(Invoice.tenant_id == current_user.tenant_id)
    
    total = query.count()
    invoices = query.order_by(Invoice.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    return {
        "items": [inv.to_dict() for inv in invoices],
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/usage")
async def get_usage(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get current usage for tenant"""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.TENANT_ADMIN]:
        raise HTTPException(
            status_code=403,
            detail="Only admins can view usage"
        )
    
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Get current subscription
    subscription = db.query(Subscription).filter(
        Subscription.tenant_id == tenant.id,
        Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL])
    ).first()
    
    return {
        "tenant_id": tenant.id,
        "plan": tenant.plan.value,
        "is_trial": tenant.is_trial,
        "trial_ends_at": tenant.trial_ends_at.isoformat() if tenant.trial_ends_at else None,
        "usage": {
            "api_calls": {
                "used": tenant.api_calls_count,
                "limit": tenant.api_calls_limit,
                "percentage": round(tenant.api_calls_count / tenant.api_calls_limit * 100, 2) if tenant.api_calls_limit > 0 else 0
            },
            "users": {
                "used": tenant.users_count,
                "limit": tenant.users_limit,
                "percentage": round(tenant.users_count / tenant.users_limit * 100, 2) if tenant.users_limit > 0 else 0
            }
        },
        "subscription": subscription.to_dict() if subscription else None
    }
