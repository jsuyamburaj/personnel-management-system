from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, timedelta
from typing import Optional, List
from ..database import get_collection
from ..dependencies import get_current_active_user, require_role
from ..models import Attendance

router = APIRouter()

@router.post("/check-in")
async def check_in(current_user = Depends(get_current_active_user)):
    """Record check-in time for today."""
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    existing = await get_collection("attendance").find_one({"user_email": current_user.email, "date": today_str})
    if existing and existing.get("check_in"):
        raise HTTPException(status_code=400, detail="Already checked in today")
    
    now = datetime.utcnow()
    record = {
        "user_email": current_user.email,
        "date": today_str,
        "check_in": now,
        "check_out": None,
        "total_hours": 0,
        "status": "Present"
    }
    if existing:
        await get_collection("attendance").update_one({"_id": existing["_id"]}, {"$set": {"check_in": now}})
    else:
        await get_collection("attendance").insert_one(record)
    
    # Log activity
    await get_collection("activity_logs").insert_one({
        "user_email": current_user.email,
        "action": "check_in",
        "details": f"Checked in at {now}",
        "timestamp": now
    })
    return {"message": "Checked in successfully", "check_in": now}

@router.post("/check-out")
async def check_out(current_user = Depends(get_current_active_user)):
    """Record check-out time and calculate hours."""
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    record = await get_collection("attendance").find_one({"user_email": current_user.email, "date": today_str})
    if not record or not record.get("check_in"):
        raise HTTPException(status_code=400, detail="No check-in found for today")
    if record.get("check_out"):
        raise HTTPException(status_code=400, detail="Already checked out today")
    
    now = datetime.utcnow()
    check_in = record["check_in"]
    total_hours = (now - check_in).total_seconds() / 3600
    await get_collection("attendance").update_one(
        {"_id": record["_id"]},
        {"$set": {"check_out": now, "total_hours": round(total_hours, 2)}}
    )
    await get_collection("activity_logs").insert_one({
        "user_email": current_user.email,
        "action": "check_out",
        "details": f"Checked out at {now}, worked {total_hours:.2f} hours",
        "timestamp": now
    })
    return {"message": "Checked out successfully", "check_out": now, "total_hours": round(total_hours, 2)}

@router.get("/today")
async def get_today_attendance(current_user = Depends(get_current_active_user)):
    """Get today's attendance record."""
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    record = await get_collection("attendance").find_one({"user_email": current_user.email, "date": today_str})
    if not record:
        return {"check_in": None, "check_out": None, "total_hours": 0}
    return {
        "check_in": record.get("check_in"),
        "check_out": record.get("check_out"),
        "total_hours": record.get("total_hours", 0)
    }

@router.get("/history")
async def get_attendance_history(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user = Depends(get_current_active_user)
):
    """Get attendance history for the user."""
    query = {"user_email": current_user.email}
    if start_date:
        query["date"] = {"$gte": start_date}
    if end_date:
        query["date"] = {"$lte": end_date}
    records = await get_collection("attendance").find(query).sort("date", -1).to_list(100)
    return [{k:v for k,v in r.items() if k != "_id"} for r in records]

@router.get("/team")
async def get_team_attendance(
    date: Optional[str] = Query(None),
    current_user = Depends(require_role(["manager", "admin"]))
):
    """Manager view: get attendance of team members."""
    # Get team members (users with same department or managed by current user)
    team = await get_collection("users").find({"department": current_user.department}).to_list(100)
    emails = [u["email"] for u in team if u["email"] != current_user.email]
    if not date:
        date = datetime.utcnow().strftime("%Y-%m-%d")
    records = await get_collection("attendance").find({"user_email": {"$in": emails}, "date": date}).to_list(100)
    return records