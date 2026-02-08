"""
Keystroke Dynamics Schemas
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class KeystrokeEvent(BaseModel):
    """Individual keystroke event"""
    key: str = Field(..., description="The key pressed")
    action: str = Field(..., description="Key action: press or release")
    timestamp: int = Field(..., description="Timestamp in milliseconds")
    
    # Optional mobile touch data
    pressure: Optional[float] = Field(None, description="Touch pressure (0-1)")
    touch_area: Optional[float] = Field(None, description="Touch area in pixels")
    x: Optional[float] = Field(None, description="X coordinate")
    y: Optional[float] = Field(None, description="Y coordinate")


class KeystrokeData(BaseModel):
    """Complete keystroke data for analysis"""
    text: str = Field(..., description="The text being typed")
    events: List[KeystrokeEvent] = Field(..., description="List of keystroke events")
    
    # Context
    field_name: Optional[str] = Field(None, description="Field identifier")
    session_id: Optional[str] = Field(None, description="Session identifier")


class KeystrokeEnrollmentRequest(BaseModel):
    """Keystroke enrollment request"""
    user_id: int
    samples: List[KeystrokeData] = Field(..., min_items=3, description="Multiple typing samples")
    passphrase: Optional[str] = Field(None, description="Fixed passphrase if used")


class KeystrokeVerificationRequest(BaseModel):
    """Keystroke verification request"""
    user_id: int
    keystroke_data: KeystrokeData
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class KeystrokeFeatures(BaseModel):
    """Extracted keystroke features"""
    dwell_times: Dict[str, List[float]]  # Key press duration
    flight_times: List[float]  # Time between key releases and next presses
    digraph_times: Dict[str, List[float]]  # Two-key sequence times
    trigraph_times: Optional[Dict[str, List[float]]]  # Three-key sequence times
    typing_speed_wpm: float
    rhythm_consistency: float


class KeystrokeEnrollmentResponse(BaseModel):
    """Keystroke enrollment response"""
    success: bool
    message: str
    template_id: Optional[int]
    enrollment_count: int
    quality_score: float = Field(..., ge=0, le=100, description="Template quality 0-100")
    recommendations: List[str]


class KeystrokeVerificationResponse(BaseModel):
    """Keystroke verification response"""
    success: bool
    authenticated: bool
    confidence_score: float = Field(..., ge=0, le=100, description="Authentication confidence 0-100")
    match_score: float = Field(..., ge=0, le=100, description="Template match score 0-100")
    threshold: float = Field(..., description="Authentication threshold used")
    
    # Details
    features_matched: Optional[Dict[str, Any]]
    risk_factors: List[str]
    
    # Action
    action: str = Field(..., description="allow, challenge, or deny")
    challenge_required: bool = False
    
    # Session
    session_token: Optional[str]
    session_expires_at: Optional[datetime]


class KeystrokeTemplateResponse(BaseModel):
    """Keystroke template response"""
    id: int
    user_id: int
    enrollment_count: int
    is_active: bool
    avg_dwell_time: Optional[float]
    avg_flight_time: Optional[float]
    typing_speed: Optional[float]
    created_at: datetime
    updated_at: datetime
    last_used: Optional[datetime]


class KeystrokeStatsResponse(BaseModel):
    """User keystroke statistics"""
    user_id: int
    is_enrolled: bool
    template_quality: Optional[float]
    total_authentications: int
    successful_authentications: int
    failed_authentications: int
    avg_confidence_score: float
    last_authentication: Optional[datetime]
