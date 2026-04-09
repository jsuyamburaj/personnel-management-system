from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime
from typing import List, Optional
from bson import ObjectId
from ..database import get_collection
from ..dependencies import get_current_active_user, require_role
from ..models import Leave

router = APIRouter()

@router.get("/balance")
async def get_leave_balance(current_user = Depends(get_current_active_user)):
    """Get available leave days (mock implementation). Store balance in user doc."""
    user = await get_collection("users").find_one({"email": current_user.email})
    balance = user.get("leave_balance", 12) if user else 12
    return {"available": balance}

@router.get("/my-requests")
async def get_my_leave_requests(current_user = Depends(get_current_active_user)):
    leaves = await get_collection("leaves").find({"user_email": current_user.email}).sort("created_at", -1).to_list(50)
    return [{"id": str(l["_id"]), **{k:v for k,v in l.items() if k != "_id"}} for l in leaves]

@router.post("/")
async def apply_leave(leave_data: dict, current_user = Depends(get_current_active_user)):
    """Apply for a new leave."""
    required = ["leave_type", "start_date", "end_date"]
    for field in required:
        if field not in leave_data:
            raise HTTPException(status_code=400, detail=f"Missing field: {field}")
    
    leave = {
        "user_email": current_user.email,
        "leave_type": leave_data["leave_type"],
        "start_date": leave_data["start_date"],
        "end_date": leave_data["end_date"],
        "reason": leave_data.get("reason", ""),
        "status": "Pending",
        "created_at": datetime.utcnow(),
        "approved_by": None
    }
    result = await get_collection("leaves").insert_one(leave)
    # Notify manager
    await get_collection("notifications").insert_one({
        "user_email": "manager@spms.com",  # In real app, fetch manager email
        "title": "New Leave Request",
        "message": f"{current_user.email} requested {leave_data['leave_type']} leave from {leave_data['start_date']} to {leave_data['end_date']}",
        "type": "info",
        "is_read": False,
        "created_at": datetime.utcnow()
    })
    return {"message": "Leave request submitted", "id": str(result.inserted_id)}

@router.put("/{leave_id}/approve")
async def approve_leave(leave_id: str, current_user = Depends(require_role(["manager", "admin"]))):
    leave = await get_collection("leaves").find_one({"_id": ObjectId(leave_id)})
    if not leave:
        raise HTTPException(status_code=404, detail="Leave not found")
    await get_collection("leaves").update_one(
        {"_id": ObjectId(leave_id)},
        {"$set": {"status": "Approved", "approved_by": current_user.email}}
    )
    # Notify employee
    await get_collection("notifications").insert_one({
        "user_email": leave["user_email"],
        "title": "Leave Approved",
        "message": f"Your {leave['leave_type']} leave request has been approved.",
        "type": "success",
        "is_read": False,
        "created_at": datetime.utcnow()
    })
    return {"message": "Leave approved"}

@router.put("/{leave_id}/reject")
async def reject_leave(leave_id: str, current_user = Depends(require_role(["manager", "admin"]))):
    leave = await get_collection("leaves").find_one({"_id": ObjectId(leave_id)})
    if not leave:
        raise HTTPException(status_code=404, detail="Leave not found")
    await get_collection("leaves").update_one(
        {"_id": ObjectId(leave_id)},
        {"$set": {"status": "Rejected", "approved_by": current_user.email}}
    )
    await get_collection("notifications").insert_one({
        "user_email": leave["user_email"],
        "title": "Leave Rejected",
        "message": f"Your {leave['leave_type']} leave request has been rejected.",
        "type": "danger",
        "is_read": False,
        "created_at": datetime.utcnow()
    })
    return {"message": "Leave rejected"}