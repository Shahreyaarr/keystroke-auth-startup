"""
Keystroke Dynamics Models - Biometric templates and sessions
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON, LargeBinary
from sqlalchemy.orm import relationship
from app.core.database import Base


class KeystrokeTemplate(Base):
    """User's keystroke biometric template"""
    __tablename__ = "keystroke_templates"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    tenant_id = Column(String(50), ForeignKey("tenants.id"), nullable=False)
    
    # Template data (encrypted)
    template_data = Column(Text, nullable=False)  # JSON string of features
    template_vector = Column(LargeBinary, nullable=True)  # Serialized ML model input
    
    # Template metadata
    enrollment_count = Column(Integer, default=0)  # Number of samples used
    is_active = Column(Boolean, default=True)
    
    # Feature statistics
    avg_dwell_time = Column(Float, nullable=True)
    avg_flight_time = Column(Float, nullable=True)
    typing_speed = Column(Float, nullable=True)  # WPM
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_used = Column(DateTime, nullable=True)
    
    # Relationship
    user = relationship("User", back_populates="keystroke_templates")
    
    def __repr__(self):
        return f"<KeystrokeTemplate(id={self.id}, user_id={self.user_id})>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "enrollment_count": self.enrollment_count,
            "is_active": self.is_active,
            "avg_dwell_time": self.avg_dwell_time,
            "avg_flight_time": self.avg_flight_time,
            "typing_speed": self.typing_speed,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class KeystrokeSession(Base):
    """Keystroke authentication session"""
    __tablename__ = "keystroke_sessions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tenant_id = Column(String(50), ForeignKey("tenants.id"), nullable=False)
    
    # Session data
    session_token = Column(String(255), unique=True, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    device_fingerprint = Column(String(255), nullable=True)
    
    # Authentication result
    auth_score = Column(Float, nullable=True)  # 0-100
    auth_result = Column(String(20), nullable=True)  # success, failed, challenged
    
    # Continuous auth data
    keystroke_data = Column(JSON, default=list)  # List of keystroke events
    
    # Session status
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "auth_score": self.auth_score,
            "auth_result": self.auth_result,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }
