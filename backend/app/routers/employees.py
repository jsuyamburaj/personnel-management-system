from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

from ..database import get_collection
from ..models import Employee
from ..dependencies import get_current_active_user, require_role

router = APIRouter()

@router.get("/")
async def get_employees(
    search: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user = Depends(require_role(["admin", "manager", "hr"]))
):
    """Get all employees with filters"""
    query = {}
    
    if search:
        query["$or"] = [
            {"first_name": {"$regex": search, "$options": "i"}},
            {"last_name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}}
        ]
    
    if department:
        query["department"] = department
    if role:
        query["role"] = role
    if status:
        query["status"] = status
    
    # Get users and join with employee details
    users = await get_collection("users").find(query).to_list(100)
    
    # Enhance with employee data
    employees = []
    for user in users:
        emp_data = await get_collection("employees").find_one({"user_id": str(user["_id"])})
        employees.append({
            "id": str(user["_id"]),
            "email": user["email"],
            "full_name": user.get("full_name", ""),
            "role": user["role"],
            "department": user.get("department", ""),
            "is_active": user.get("is_active", True),
            **({k: v for k, v in emp_data.items() if k not in ["_id", "user_id"]} if emp_data else {})
        })
    
    return employees

@router.post("/")
async def create_employee(
    employee_data: dict,
    current_user = Depends(require_role(["admin", "hr"]))
):
    """Create new employee"""
    # Check if user exists
    existing = await get_collection("users").find_one({"email": employee_data["email"]})
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")
    
    # Create user
    from ..auth import get_password_hash
    user = {
        "email": employee_data["email"],
        "full_name": f"{employee_data.get('first_name', '')} {employee_data.get('last_name', '')}".strip(),
        "hashed_password": get_password_hash("password123"),  # Default password
        "role": employee_data.get("role", "employee"),
        "department": employee_data.get("department"),
        "is_active": True,
        "created_at": datetime.utcnow()
    }
    
    result = await get_collection("users").insert_one(user)
    
    # Create employee record
    employee = {
        "user_id": str(result.inserted_id),
        "first_name": employee_data.get("first_name"),
        "last_name": employee_data.get("last_name"),
        "phone": employee_data.get("phone"),
        "join_date": employee_data.get("join_date"),
        "skills": employee_data.get("skills", "").split(",") if isinstance(employee_data.get("skills"), str) else [],
        "salary": employee_data.get("salary", 0),
        "status": "Active"
    }
    
    await get_collection("employees").insert_one(employee)
    
    # Log activity
    await get_collection("activity_logs").insert_one({
        "user_email": current_user.email,
        "action": "create_employee",
        "details": f"Created employee {employee_data['email']}",
        "timestamp": datetime.utcnow()
    })
    
    return {"message": "Employee created successfully", "id": str(result.inserted_id)}

@router.put("/{employee_id}")
async def update_employee(
    employee_id: str,
    update_data: dict,
    current_user = Depends(require_role(["admin", "hr"]))
):
    """Update employee"""
    result = await get_collection("users").update_one(
        {"_id": ObjectId(employee_id)},
        {"$set": {
            "full_name": update_data.get("full_name"),
            "department": update_data.get("department"),
            "role": update_data.get("role")
        }}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Update employee details
    await get_collection("employees").update_one(
        {"user_id": employee_id},
        {"$set": {
            "phone": update_data.get("phone"),
            "skills": update_data.get("skills", "").split(",") if isinstance(update_data.get("skills"), str) else [],
            "salary": update_data.get("salary")
        }}
    )
    
    return {"message": "Employee updated successfully"}

@router.delete("/{employee_id}")
async def delete_employee(
    employee_id: str,
    current_user = Depends(require_role(["admin"]))
):
    """Delete employee (soft delete)"""
    result = await get_collection("users").update_one(
        {"_id": ObjectId(employee_id)},
        {"$set": {"is_active": False}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    return {"message": "Employee deactivated successfully"}