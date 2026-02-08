"""
Authentication Logs and API Call Models
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base


class AuthLog(Base):
    """Authentication audit log"""
    __tablename__ = "auth_logs"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    tenant_id = Column(String(50), ForeignKey("tenants.id"), nullable=True)
    
    # Event details
    event_type = Column(String(50), nullable=False)  # login, logout, enroll, verify, failed
    event_description = Column(Text, nullable=True)
    
    # Authentication details
    auth_method = Column(String(50), nullable=True)  # keystroke, password, mfa
    auth_score = Column(Float, nullable=True)
    success = Column(Boolean, nullable=False)
    failure_reason = Column(String(255), nullable=True)
    
    # Request context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    country = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    
    # Device info
    device_type = Column(String(50), nullable=True)
    browser = Column(String(100), nullable=True)
    os = Column(String(100), nullable=True)
    
    # Risk assessment
    risk_score = Column(Float, nullable=True)  # 0-100
    risk_factors = Column(JSON, default=list)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationship
    user = relationship("User", back_populates="auth_logs")
    
    def __repr__(self):
        return f"<AuthLog(id={self.id}, event={self.event_type}, success={self.success})>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "event_type": self.event_type,
            "auth_method": self.auth_method,
            "auth_score": self.auth_score,
            "success": self.success,
            "failure_reason": self.failure_reason,
            "ip_address": self.ip_address,
            "country": self.country,
            "risk_score": self.risk_score,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class APICall(Base):
    """API call tracking for billing and analytics"""
    __tablename__ = "api_calls"
    
    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(50), ForeignKey("tenants.id"), nullable=True)
    api_key_id = Column(Integer, ForeignKey("api_keys.id"), nullable=True)
    
    # Request details
    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer, nullable=False)
    
    # Performance
    response_time_ms = Column(Float, nullable=True)
    
    # Request context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "endpoint": self.endpoint,
            "method": self.method,
            "status_code": self.status_code,
            "response_time_ms": self.response_time_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
