from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from datetime import datetime, timedelta
from ..database import get_collection
from ..dependencies import get_current_active_user, require_role
from ..models import ActivityLog

router = APIRouter()

@router.get("/")
async def get_activity_logs(
    skip: int = 0,
    limit: int = 50,
    user_email: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    current_user = Depends(require_role(["admin", "manager"]))
):
    """Retrieve activity logs with filters. Admin only or manager for own team."""
    query = {}
    if user_email:
        query["user_email"] = user_email
    if action:
        query["action"] = action
    if from_date or to_date:
        query["timestamp"] = {}
        if from_date:
            query["timestamp"]["$gte"] = from_date
        if to_date:
            query["timestamp"]["$lte"] = to_date
    
    logs = await get_collection("activity_logs").find(query).sort("timestamp", -1).skip(skip).limit(limit).to_list(limit)
    return [{"id": str(log["_id"]), **{k:v for k,v in log.items() if k != "_id"}} for log in logs]

@router.get("/me")
async def get_my_activity_logs(
    skip: int = 0,
    limit: int = 30,
    current_user = Depends(get_current_active_user)
):
    """Get activity logs for the logged-in user."""
    logs = await get_collection("activity_logs").find({"user_email": current_user.email}).sort("timestamp", -1).skip(skip).limit(limit).to_list(limit)
    return [{"id": str(log["_id"]), **{k:v for k,v in log.items() if k != "_id"}} for log in logs]