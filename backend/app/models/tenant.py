"""
Tenant Model - Multi-tenant SaaS architecture
"""

import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, Text, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base


class SubscriptionPlan(str, enum.Enum):
    """Subscription plans"""
    STARTER = "starter"           # ₹2,999/mo
    GROWTH = "growth"             # ₹14,999/mo
    BUSINESS = "business"         # ₹49,999/mo
    ENTERPRISE = "enterprise"     # Custom


class Tenant(Base):
    """Tenant/Organization model"""
    __tablename__ = "tenants"
    
    id = Column(String(50), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, index=True, nullable=False)
    
    # Contact
    email = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)
    
    # Subscription
    plan = Column(Enum(SubscriptionPlan), default=SubscriptionPlan.STARTER)
    plan_expires_at = Column(DateTime, nullable=True)
    is_trial = Column(Boolean, default=True)
    trial_ends_at = Column(DateTime, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Usage tracking
    api_calls_count = Column(Integer, default=0)
    api_calls_limit = Column(Integer, default=10000)  # Monthly limit
    users_count = Column(Integer, default=0)
    users_limit = Column(Integer, default=100)
    
    # Billing
    billing_email = Column(String(255), nullable=True)
    gst_number = Column(String(50), nullable=True)  # For Indian businesses
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = relationship("User", back_populates="tenant")
    config = relationship("TenantConfig", back_populates="tenant", uselist=False)
    subscriptions = relationship("Subscription", back_populates="tenant")
    
    def __repr__(self):
        return f"<Tenant(id={self.id}, name={self.name}, plan={self.plan})>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "email": self.email,
            "phone": self.phone,
            "plan": self.plan.value,
            "is_active": self.is_active,
            "is_trial": self.is_trial,
            "trial_ends_at": self.trial_ends_at.isoformat() if self.trial_ends_at else None,
            "api_calls_count": self.api_calls_count,
            "api_calls_limit": self.api_calls_limit,
            "users_count": self.users_count,
            "users_limit": self.users_limit,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class TenantConfig(Base):
    """Tenant configuration for white-labeling"""
    __tablename__ = "tenant_configs"
    
    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(50), ForeignKey("tenants.id"), unique=True, nullable=False)
    
    # Branding
    logo_url = Column(String(500), nullable=True)
    favicon_url = Column(String(500), nullable=True)
    primary_color = Column(String(7), default="#1976d2")  # Hex color
    secondary_color = Column(String(7), default="#dc004e")
    
    # Custom domain
    custom_domain = Column(String(255), nullable=True, unique=True)
    domain_verified = Column(Boolean, default=False)
    
    # Email templates
    email_from_name = Column(String(100), nullable=True)
    email_from_address = Column(String(255), nullable=True)
    
    # Authentication settings
    auth_threshold = Column(Integer, default=75)  # 0-100
    mfa_required = Column(Boolean, default=False)
    session_timeout = Column(Integer, default=30)  # minutes
    
    # Features
    features = Column(JSON, default=dict)  # Enable/disable features
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    tenant = relationship("Tenant", back_populates="config")
    
    def to_dict(self):
        return {
            "logo_url": self.logo_url,
            "primary_color": self.primary_color,
            "secondary_color": self.secondary_color,
            "custom_domain": self.custom_domain,
            "email_from_name": self.email_from_name,
            "auth_threshold": self.auth_threshold,
            "mfa_required": self.mfa_required,
            "session_timeout": self.session_timeout,
            "features": self.features
        }
