"""
Analytics API Routes
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.tenant import Tenant
from app.models.auth import AuthLog
from app.schemas.auth import AuthStatsResponse

router = APIRouter()


def get_current_active_user(db: Session = Depends(), token: str = None):
    from app.api.v1.auth import get_current_active_user as get_user
    return get_user


@router.get("/dashboard")
async def get_dashboard(
    tenant_id: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get dashboard analytics"""
    # Check permissions
    if current_user.role != UserRole.SUPER_ADMIN:
        tenant_id = current_user.tenant_id
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Base query
    query = db.query(AuthLog).filter(AuthLog.created_at >= start_date)
    if tenant_id:
        query = query.filter(AuthLog.tenant_id == tenant_id)
    
    logs = query.all()
    
    # Calculate metrics
    total_auth = len([l for l in logs if l.event_type == "verify"])
    successful_auth = len([l for l in logs if l.event_type == "verify" and l.success])
    failed_auth = total_auth - successful_auth
    
    success_rate = (successful_auth / total_auth * 100) if total_auth > 0 else 0
    
    # Unique users
    unique_users = len(set(l.user_id for l in logs if l.user_id))
    
    # Average auth score
    scores = [l.auth_score for l in logs if l.auth_score is not None]
    avg_score = sum(scores) / len(scores) if scores else 0
    
    # Daily trend
    daily_data = {}
    for log in logs:
        day = log.created_at.strftime("%Y-%m-%d")
        if day not in daily_data:
            daily_data[day] = {"total": 0, "success": 0}
        daily_data[day]["total"] += 1
        if log.success:
            daily_data[day]["success"] += 1
    
    trend = [
        {"date": day, "total": data["total"], "success": data["success"]}
        for day, data in sorted(daily_data.items())
    ]
    
    # Top countries
    country_data = {}
    for log in logs:
        if log.country:
            country_data[log.country] = country_data.get(log.country, 0) + 1
    
    top_countries = [
        {"country": country, "count": count}
        for country, count in sorted(country_data.items(), key=lambda x: x[1], reverse=True)[:5]
    ]
    
    return {
        "summary": {
            "total_authentications": total_auth,
            "successful_authentications": successful_auth,
            "failed_authentications": failed_auth,
            "success_rate": round(success_rate, 2),
            "unique_users": unique_users,
            "average_score": round(avg_score, 2)
        },
        "trend": trend,
        "top_countries": top_countries
    }


@router.get("/auth-trends")
async def get_auth_trends(
    tenant_id: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get authentication trends"""
    if current_user.role != UserRole.SUPER_ADMIN:
        tenant_id = current_user.tenant_id
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(AuthLog).filter(AuthLog.created_at >= start_date)
    if tenant_id:
        query = query.filter(AuthLog.tenant_id == tenant_id)
    
    logs = query.all()
    
    # Hourly distribution
    hourly = {h: 0 for h in range(24)}
    for log in logs:
        hourly[log.created_at.hour] += 1
    
    # Day of week distribution
    dow = {d: 0 for d in range(7)}
    for log in logs:
        dow[log.created_at.weekday()] += 1
    
    # Auth method distribution
    methods = {}
    for log in logs:
        method = log.auth_method or "unknown"
        methods[method] = methods.get(method, 0) + 1
    
    return {
        "hourly_distribution": [{"hour": h, "count": c} for h, c in hourly.items()],
        "day_of_week_distribution": [{"day": d, "count": c} for d, c in dow.items()],
        "auth_methods": [{"method": m, "count": c} for m, c in methods.items()]
    }


@router.get("/fraud-attempts")
async def get_fraud_attempts(
    tenant_id: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get fraud attempt analytics"""
    if current_user.role != UserRole.SUPER_ADMIN:
        tenant_id = current_user.tenant_id
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Failed authentications
    query = db.query(AuthLog).filter(
        AuthLog.created_at >= start_date,
        AuthLog.event_type == "verify",
        AuthLog.success == False
    )
    
    if tenant_id:
        query = query.filter(AuthLog.tenant_id == tenant_id)
    
    failed_logs = query.all()
    
    # Group by user
    user_failures = {}
    for log in failed_logs:
        user_id = log.user_id
        if user_id not in user_failures:
            user_failures[user_id] = []
        user_failures[user_id].append(log)
    
    # Find suspicious users (3+ failures)
    suspicious = [
        {
            "user_id": user_id,
            "failure_count": len(logs),
            "last_attempt": max(l.created_at for l in logs).isoformat(),
            "ip_addresses": list(set(l.ip_address for l in logs if l.ip_address))
        }
        for user_id, logs in user_failures.items()
        if len(logs) >= 3
    ]
    
    # Group by IP
    ip_failures = {}
    for log in failed_logs:
        ip = log.ip_address
        if ip:
            ip_failures[ip] = ip_failures.get(ip, 0) + 1
    
    suspicious_ips = [
        {"ip": ip, "failure_count": count}
        for ip, count in sorted(ip_failures.items(), key=lambda x: x[1], reverse=True)[:10]
    ]
    
    return {
        "total_failed_attempts": len(failed_logs),
        "suspicious_users": suspicious,
        "suspicious_ips": suspicious_ips,
        "average_failures_per_user": len(failed_logs) / len(user_failures) if user_failures else 0
    }


@router.get("/export")
async def export_analytics(
    tenant_id: Optional[str] = None,
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    format: str = Query("json", regex="^(json|csv)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Export analytics data"""
    if current_user.role != UserRole.SUPER_ADMIN:
        tenant_id = current_user.tenant_id
    
    query = db.query(AuthLog).filter(
        AuthLog.created_at >= start_date,
        AuthLog.created_at <= end_date
    )
    
    if tenant_id:
        query = query.filter(AuthLog.tenant_id == tenant_id)
    
    logs = query.all()
    
    data = [
        {
            "id": log.id,
            "user_id": log.user_id,
            "event_type": log.event_type,
            "auth_method": log.auth_method,
            "auth_score": log.auth_score,
            "success": log.success,
            "ip_address": log.ip_address,
            "country": log.country,
            "created_at": log.created_at.isoformat()
        }
        for log in logs
    ]
    
    if format == "csv":
        import csv
        import io
        
        output = io.StringIO()
        if data:
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        
        return {
            "content": output.getvalue(),
            "filename": f"analytics_{start_date.date()}_{end_date.date()}.csv"
        }
    
    return {"data": data, "count": len(data)}
