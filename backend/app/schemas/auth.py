"""
Authentication Schemas
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime


class Token(BaseModel):
    """JWT Token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: Optional[Dict[str, Any]]


class TokenData(BaseModel):
    """Token payload data"""
    user_id: Optional[int] = None
    email: Optional[str] = None
    role: Optional[str] = None
    tenant_id: Optional[str] = None


class TokenRefreshRequest(BaseModel):
    """Token refresh request"""
    refresh_token: str


class MFAVerifyRequest(BaseModel):
    """MFA verification request"""
    user_id: int
    code: str


class AuthLogResponse(BaseModel):
    """Authentication log response"""
    id: int
    user_id: Optional[int]
    event_type: str
    auth_method: Optional[str]
    auth_score: Optional[float]
    success: bool
    failure_reason: Optional[str]
    ip_address: Optional[str]
    country: Optional[str]
    risk_score: Optional[float]
    risk_factors: List[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class AuthStatsResponse(BaseModel):
    """Authentication statistics"""
    total_logins: int
    successful_logins: int
    failed_logins: int
    success_rate: float
    avg_auth_score: float
    unique_users: int
    top_countries: List[Dict[str, Any]]
    login_trend: List[Dict[str, Any]]


class SecurityEventResponse(BaseModel):
    """Security event response"""
    id: int
    event_type: str
    severity: str  # low, medium, high, critical
    description: str
    ip_address: Optional[str]
    user_id: Optional[int]
    details: Dict[str, Any]
    resolved: bool
    created_at: datetime
    resolved_at: Optional[datetime]
