"""
Keystroke Dynamics API Routes
"""

from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
import json
import structlog

from app.core.database import get_db
from app.core.config import settings
from app.ml.keystroke_engine import keystroke_engine
from app.models.user import User
from app.models.keystroke import KeystrokeTemplate, KeystrokeSession
from app.models.auth import AuthLog
from app.schemas.keystroke import (
    KeystrokeData, KeystrokeEnrollmentRequest, KeystrokeVerificationRequest,
    KeystrokeEnrollmentResponse, KeystrokeVerificationResponse,
    KeystrokeTemplateResponse, KeystrokeStatsResponse
)
from app.api.v1.auth import get_current_active_user

logger = structlog.get_logger()
router = APIRouter()


@router.post("/enroll", response_model=KeystrokeEnrollmentResponse)
async def enroll_keystroke(
    request: Request,
    enrollment: KeystrokeEnrollmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Enroll user's keystroke pattern
    
    Requires multiple typing samples to create a biometric template
    """
    # Verify user exists and matches
    user = db.query(User).filter(User.id == enrollment.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check permissions
    if current_user.id != user.id and current_user.role.value not in ['super_admin', 'tenant_admin']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot enroll keystrokes for this user"
        )
    
    # Validate samples
    if len(enrollment.samples) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 3 typing samples required for enrollment"
        )
    
    try:
        # Convert samples to event lists
        sample_events = []
        for sample in enrollment.samples:
            events = [event.dict() for event in sample.events]
            sample_events.append(events)
        
        # Create template
        template_data = keystroke_engine.create_template(sample_events)
        
        # Calculate quality score
        quality_score = keystroke_engine.calculate_quality_score(template_data)
        
        # Check if template already exists
        existing = db.query(KeystrokeTemplate).filter(
            KeystrokeTemplate.user_id == user.id,
            KeystrokeTemplate.is_active == True
        ).first()
        
        if existing:
            # Update existing template
            existing.template_data = json.dumps(template_data)
            existing.enrollment_count = template_data['sample_count']
            existing.avg_dwell_time = sum(
                stats['mean'] for stats in template_data['dwell_stats'].values()
            ) / len(template_data['dwell_stats']) if template_data['dwell_stats'] else None
            existing.avg_flight_time = template_data['flight_stats'].get('mean')
            existing.typing_speed = template_data['typing_speed']
            existing.updated_at = datetime.utcnow()
            template_id = existing.id
        else:
            # Create new template
            new_template = KeystrokeTemplate(
                user_id=user.id,
                tenant_id=user.tenant_id,
                template_data=json.dumps(template_data),
                enrollment_count=template_data['sample_count'],
                avg_dwell_time=sum(
                    stats['mean'] for stats in template_data['dwell_stats'].values()
                ) / len(template_data['dwell_stats']) if template_data['dwell_stats'] else None,
                avg_flight_time=template_data['flight_stats'].get('mean'),
                typing_speed=template_data['typing_speed']
            )
            db.add(new_template)
            db.flush()
            template_id = new_template.id
        
        # Update user enrollment status
        user.is_enrolled = True
        
        # Log enrollment
        auth_log = AuthLog(
            user_id=user.id,
            tenant_id=user.tenant_id,
            event_type="enroll",
            auth_method="keystroke",
            success=True,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        db.add(auth_log)
        db.commit()
        
        # Generate recommendations
        recommendations = []
        if quality_score < 50:
            recommendations.append("Please provide more typing samples for better accuracy")
        if template_data['sample_count'] < 5:
            recommendations.append("Consider providing at least 5 samples for improved reliability")
        if len(template_data['dwell_stats']) < 10:
            recommendations.append("Type more varied characters to improve template coverage")
        
        logger.info(f"Keystroke enrollment successful for user {user.id}, quality={quality_score:.1f}")
        
        return KeystrokeEnrollmentResponse(
            success=True,
            message="Keystroke template created successfully",
            template_id=template_id,
            enrollment_count=template_data['sample_count'],
            quality_score=quality_score,
            recommendations=recommendations
        )
        
    except Exception as e:
        logger.error(f"Enrollment failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Enrollment failed: {str(e)}"
        )


@router.post("/verify", response_model=KeystrokeVerificationResponse)
async def verify_keystroke(
    request: Request,
    verification: KeystrokeVerificationRequest,
    db: Session = Depends(get_db)
):
    """
    Verify keystroke pattern against user's template
    
    Returns authentication result with confidence score
    """
    # Get user
    user = db.query(User).filter(User.id == verification.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if user has enrolled
    if not user.is_enrolled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has not enrolled keystroke pattern"
        )
    
    # Get active template
    template_record = db.query(KeystrokeTemplate).filter(
        KeystrokeTemplate.user_id == user.id,
        KeystrokeTemplate.is_active == True
    ).first()
    
    if not template_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active keystroke template found"
        )
    
    try:
        # Load template
        template = json.loads(template_record.template_data)
        
        # Extract events
        events = [event.dict() for event in verification.keystroke_data.events]
        
        # Verify
        match_score, details = keystroke_engine.verify(template, events)
        
        # Convert to percentage
        confidence_score = match_score * 100
        threshold = settings.AUTHENTICATION_THRESHOLD * 100
        
        # Determine action
        authenticated = confidence_score >= threshold
        
        if confidence_score >= threshold + 15:
            action = "allow"
            challenge_required = False
        elif confidence_score >= threshold:
            action = "allow"
            challenge_required = False
        elif confidence_score >= threshold - 15:
            action = "challenge"
            challenge_required = True
        else:
            action = "deny"
            challenge_required = False
        
        # Update template last used
        template_record.last_used = datetime.utcnow()
        
        # Create session if authenticated
        session_token = None
        session_expires = None
        if authenticated:
            # Generate session token (simplified)
            import secrets
            session_token = secrets.token_urlsafe(32)
            session_expires = datetime.utcnow() + timedelta(minutes=30)
            
            session = KeystrokeSession(
                user_id=user.id,
                tenant_id=user.tenant_id,
                session_token=session_token,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                auth_score=confidence_score,
                auth_result="success" if authenticated else "failed",
                expires_at=session_expires
            )
            db.add(session)
        
        # Log verification
        auth_log = AuthLog(
            user_id=user.id,
            tenant_id=user.tenant_id,
            event_type="verify",
            auth_method="keystroke",
            auth_score=confidence_score,
            success=authenticated,
            failure_reason=None if authenticated else "Low confidence score",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        db.add(auth_log)
        db.commit()
        
        # Risk factors
        risk_factors = []
        if details.get('dwell_score', 1) < 0.5:
            risk_factors.append("Unusual key press timing")
        if details.get('flight_score', 1) < 0.5:
            risk_factors.append("Unusual typing rhythm")
        if details.get('speed_score', 1) < 0.5:
            risk_factors.append("Unusual typing speed")
        
        logger.info(f"Keystroke verification for user {user.id}: score={confidence_score:.1f}, action={action}")
        
        return KeystrokeVerificationResponse(
            success=True,
            authenticated=authenticated,
            confidence_score=round(confidence_score, 2),
            match_score=round(confidence_score, 2),
            threshold=threshold,
            features_matched=details,
            risk_factors=risk_factors,
            action=action,
            challenge_required=challenge_required,
            session_token=session_token,
            session_expires_at=session_expires
        )
        
    except Exception as e:
        logger.error(f"Verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verification failed: {str(e)}"
        )


@router.get("/template/{user_id}", response_model=KeystrokeTemplateResponse)
async def get_template(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get user's keystroke template"""
    # Check permissions
    if current_user.id != user_id and current_user.role.value not in ['super_admin', 'tenant_admin']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access this user's template"
        )
    
    template = db.query(KeystrokeTemplate).filter(
        KeystrokeTemplate.user_id == user_id,
        KeystrokeTemplate.is_active == True
    ).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    return template


@router.delete("/template/{user_id}")
async def delete_template(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete user's keystroke template"""
    # Check permissions
    if current_user.id != user_id and current_user.role.value not in ['super_admin', 'tenant_admin']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete this user's template"
        )
    
    template = db.query(KeystrokeTemplate).filter(
        KeystrokeTemplate.user_id == user_id,
        KeystrokeTemplate.is_active == True
    ).first()
    
    if template:
        template.is_active = False
        
        # Update user enrollment status
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.is_enrolled = False
        
        db.commit()
        logger.info(f"Template deleted for user {user_id}")
    
    return {"message": "Template deleted successfully"}


@router.get("/stats/{user_id}", response_model=KeystrokeStatsResponse)
async def get_stats(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get user's keystroke authentication statistics"""
    # Check permissions
    if current_user.id != user_id and current_user.role.value not in ['super_admin', 'tenant_admin']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access this user's stats"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get template quality
    template = db.query(KeystrokeTemplate).filter(
        KeystrokeTemplate.user_id == user_id,
        KeystrokeTemplate.is_active == True
    ).first()
    
    template_quality = None
    if template:
        try:
            template_data = json.loads(template.template_data)
            template_quality = keystroke_engine.calculate_quality_score(template_data)
        except:
            pass
    
    # Get auth statistics
    auth_logs = db.query(AuthLog).filter(
        AuthLog.user_id == user_id,
        AuthLog.event_type == "verify"
    ).all()
    
    total = len(auth_logs)
    successful = len([l for l in auth_logs if l.success])
    failed = total - successful
    
    avg_score = 0
    if auth_logs:
        scores = [l.auth_score for l in auth_logs if l.auth_score is not None]
        if scores:
            avg_score = sum(scores) / len(scores)
    
    last_auth = None
    if auth_logs:
        last_auth = max(l.created_at for l in auth_logs)
    
    return KeystrokeStatsResponse(
        user_id=user_id,
        is_enrolled=user.is_enrolled,
        template_quality=round(template_quality, 2) if template_quality else None,
        total_authentications=total,
        successful_authentications=successful,
        failed_authentications=failed,
        avg_confidence_score=round(avg_score, 2),
        last_authentication=last_auth
    )
