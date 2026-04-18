from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, timedelta
from typing import List, Optional
from bson import ObjectId
from ..database import get_collection
from ..dependencies import get_current_active_user, require_role
from ..models import Leave

router = APIRouter()

def calculate_leave_days(start_date_str, end_date_str):
    """Calculate number of leave days excluding weekends"""
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    
    days = 0
    current = start_date
    while current <= end_date:
        # Exclude Saturdays (5) and Sundays (6)
        if current.weekday() < 5:  # Monday to Friday
            days += 1
        current += timedelta(days=1)
    return days

@router.get("/balance")
async def get_leave_balance(current_user = Depends(get_current_active_user)):
    """Get available leave days from user document"""
    user = await get_collection("users").find_one({"email": current_user.email})
    balance = user.get("leave_balance", 12) if user else 12
    return {"available": balance}

@router.get("/my-requests")
async def get_my_leave_requests(current_user = Depends(get_current_active_user)):
    leaves = await get_collection("leaves").find({"user_email": current_user.email}).sort("created_at", -1).to_list(50)
    return [{"id": str(l["_id"]), **{k:v for k,v in l.items() if k != "_id"}} for l in leaves]

@router.get("/pending")
async def get_pending_leaves(current_user = Depends(require_role(["admin", "manager", "hr"]))):
    """Get all pending leave requests for HR/Admin/Manager"""
    leaves = await get_collection("leaves").find({"status": "Pending"}).sort("created_at", -1).to_list(100)
    result = []
    for leave in leaves:
        user = await get_collection("users").find_one({"email": leave["user_email"]})
        result.append({
            "id": str(leave["_id"]),
            "user_email": leave["user_email"],
            "user_name": user.get("full_name", leave["user_email"]) if user else leave["user_email"],
            "leave_type": leave["leave_type"],
            "start_date": leave["start_date"],
            "end_date": leave["end_date"],
            "reason": leave.get("reason", ""),
            "status": leave["status"],
            "created_at": leave["created_at"]
        })
    return result

@router.post("/")
async def apply_leave(leave_data: dict, current_user = Depends(get_current_active_user)):
    """Apply for a new leave."""
    required = ["leave_type", "start_date", "end_date"]
    for field in required:
        if field not in leave_data:
            raise HTTPException(status_code=400, detail=f"Missing field: {field}")
    
    # Calculate leave days
    leave_days = calculate_leave_days(leave_data["start_date"], leave_data["end_date"])
    
    # Check if user has enough balance
    user = await get_collection("users").find_one({"email": current_user.email})
    current_balance = user.get("leave_balance", 12)
    
    if leave_days > current_balance:
        raise HTTPException(status_code=400, detail=f"Insufficient leave balance. You have {current_balance} days available, but requested {leave_days} days.")
    
    leave = {
        "user_email": current_user.email,
        "leave_type": leave_data["leave_type"],
        "start_date": leave_data["start_date"],
        "end_date": leave_data["end_date"],
        "leave_days": leave_days,
        "reason": leave_data.get("reason", ""),
        "status": "Pending",
        "created_at": datetime.utcnow(),
        "approved_by": None,
        "approved_at": None
    }
    result = await get_collection("leaves").insert_one(leave)
    
    # Get user details
    user_name = user.get("full_name", current_user.email)
    
    # Notify all HR and Admin users about new leave request
    hr_admins = await get_collection("users").find({"role": {"$in": ["admin", "hr", "manager"]}}).to_list(100)
    
    for admin in hr_admins:
        await get_collection("notifications").insert_one({
            "user_email": admin["email"],
            "title": "New Leave Request",
            "message": f"{user_name} requested {leave_days} days of {leave_data['leave_type']} leave from {leave_data['start_date']} to {leave_data['end_date']}",
            "type": "info",
            "is_read": False,
            "created_at": datetime.utcnow(),
            "link": f"/leave-management.html?leave_id={str(result.inserted_id)}"
        })
    
    # Notify the employee that request was submitted
    await get_collection("notifications").insert_one({
        "user_email": current_user.email,
        "title": "Leave Request Submitted",
        "message": f"Your {leave_data['leave_type']} leave request for {leave_days} days has been submitted and is pending approval.",
        "type": "info",
        "is_read": False,
        "created_at": datetime.utcnow()
    })
    
    return {"message": "Leave request submitted", "id": str(result.inserted_id), "leave_days": leave_days}

@router.put("/{leave_id}/approve")
async def approve_leave(leave_id: str, current_user = Depends(require_role(["admin", "manager", "hr"]))):
    leave = await get_collection("leaves").find_one({"_id": ObjectId(leave_id)})
    if not leave:
        raise HTTPException(status_code=404, detail="Leave not found")
    
    # Calculate leave days if not already calculated
    leave_days = leave.get("leave_days")
    if not leave_days:
        leave_days = calculate_leave_days(leave["start_date"], leave["end_date"])
    
    # Get current user balance
    user = await get_collection("users").find_one({"email": leave["user_email"]})
    current_balance = user.get("leave_balance", 12)
    
    # Check if enough balance (double-check)
    if leave_days > current_balance:
        raise HTTPException(status_code=400, detail=f"Cannot approve: Employee has only {current_balance} days available")
    
    # Deduct leave days from employee balance
    new_balance = current_balance - leave_days
    
    await get_collection("users").update_one(
        {"email": leave["user_email"]},
        {"$set": {"leave_balance": new_balance}}
    )
    
    # Update leave status
    await get_collection("leaves").update_one(
        {"_id": ObjectId(leave_id)},
        {"$set": {
            "status": "Approved", 
            "approved_by": current_user.email, 
            "approved_at": datetime.utcnow(),
            "deducted_days": leave_days
        }}
    )
    
    # Get approver name
    approver = await get_collection("users").find_one({"email": current_user.email})
    approver_name = approver.get("full_name", current_user.email) if approver else current_user.email
    
    # Notify employee about approval with balance info
    await get_collection("notifications").insert_one({
        "user_email": leave["user_email"],
        "title": "Leave Request Approved ✅",
        "message": f"Your {leave['leave_type']} leave request for {leave_days} days has been approved by {approver_name}. Remaining balance: {new_balance} days.",
        "type": "success",
        "is_read": False,
        "created_at": datetime.utcnow()
    })
    
    return {"message": "Leave approved", "remaining_balance": new_balance}

@router.put("/{leave_id}/reject")
async def reject_leave(leave_id: str, current_user = Depends(require_role(["admin", "manager", "hr"]))):
    leave = await get_collection("leaves").find_one({"_id": ObjectId(leave_id)})
    if not leave:
        raise HTTPException(status_code=404, detail="Leave not found")
    
    leave_days = leave.get("leave_days", calculate_leave_days(leave["start_date"], leave["end_date"]))
    
    await get_collection("leaves").update_one(
        {"_id": ObjectId(leave_id)},
        {"$set": {"status": "Rejected", "approved_by": current_user.email, "approved_at": datetime.utcnow()}}
    )
    
    # Get approver name
    approver = await get_collection("users").find_one({"email": current_user.email})
    approver_name = approver.get("full_name", current_user.email) if approver else current_user.email
    
    # Notify employee about rejection (no balance deduction)
    await get_collection("notifications").insert_one({
        "user_email": leave["user_email"],
        "title": "Leave Request Rejected ❌",
        "message": f"Your {leave['leave_type']} leave request for {leave_days} days has been rejected by {approver_name}. No days were deducted from your balance.",
        "type": "danger",
        "is_read": False,
        "created_at": datetime.utcnow()
    })
    
    return {"message": "Leave rejected"}

@router.get("/history")
async def get_leave_history(current_user = Depends(get_current_active_user)):
    """Get leave history with balance changes"""
    leaves = await get_collection("leaves").find({"user_email": current_user.email}).sort("created_at", -1).to_list(50)
    user = await get_collection("users").find_one({"email": current_user.email})
    current_balance = user.get("leave_balance", 12)
    
    total_taken = 0
    for leave in leaves:
        if leave["status"] == "Approved":
            total_taken += leave.get("leave_days", calculate_leave_days(leave["start_date"], leave["end_date"]))
    
    return {
        "current_balance": current_balance,
        "total_taken": total_taken,
        "history": [{
            "id": str(l["_id"]),
            "leave_type": l["leave_type"],
            "start_date": l["start_date"],
            "end_date": l["end_date"],
            "leave_days": l.get("leave_days", calculate_leave_days(l["start_date"], l["end_date"])),
            "status": l["status"],
            "created_at": l["created_at"],
            "approved_at": l.get("approved_at")
        } for l in leaves]
    }