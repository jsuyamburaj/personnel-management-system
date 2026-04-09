from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime
from typing import List, Optional
from bson import ObjectId
from ..database import get_collection
from ..dependencies import get_current_active_user, require_role
from ..models import Payroll

router = APIRouter()

@router.get("/my-payroll")
async def get_my_payroll(
    month: Optional[str] = Query(None, regex="^[0-9]{4}-[0-9]{2}$"),
    current_user = Depends(get_current_active_user)
):
    query = {"user_email": current_user.email}
    if month:
        query["month"] = month
    records = await get_collection("payroll").find(query).sort("month", -1).to_list(12)
    return [{"id": str(p["_id"]), **{k:v for k,v in p.items() if k != "_id"}} for p in records]

@router.get("/")
async def get_all_payroll(
    month: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    current_user = Depends(require_role(["admin", "hr"]))
):
    query = {}
    if month:
        query["month"] = month
    if department:
        # Need to join with users collection
        users = await get_collection("users").find({"department": department}).to_list(100)
        emails = [u["email"] for u in users]
        query["user_email"] = {"$in": emails}
    payrolls = await get_collection("payroll").find(query).to_list(200)
    return [{"id": str(p["_id"]), **{k:v for k,v in p.items() if k != "_id"}} for p in payrolls]

@router.post("/process")
async def process_payroll(
    month: str,
    current_user = Depends(require_role(["admin", "hr"]))
):
    """Generate payroll for all employees for a given month."""
    employees = await get_collection("users").find({"is_active": True}).to_list(100)
    processed = 0
    for emp in employees:
        # Get employee details from employees collection
        emp_detail = await get_collection("employees").find_one({"user_id": str(emp["_id"])})
        salary = emp_detail.get("salary", 0) if emp_detail else 0
        # Calculate deductions, bonuses (simplified)
        net_salary = salary
        payroll_record = {
            "user_email": emp["email"],
            "month": month,
            "basic_salary": salary,
            "allowances": 0,
            "deductions": 0,
            "bonus": 0,
            "net_salary": net_salary,
            "status": "Processed",
            "payslip_url": None
        }
        # Avoid duplicates
        existing = await get_collection("payroll").find_one({"user_email": emp["email"], "month": month})
        if existing:
            await get_collection("payroll").update_one({"_id": existing["_id"]}, {"$set": payroll_record})
        else:
            await get_collection("payroll").insert_one(payroll_record)
        processed += 1
    return {"message": f"Payroll processed for {processed} employees", "month": month}

@router.put("/{payroll_id}")
async def update_payroll_entry(payroll_id: str, update_data: dict, current_user = Depends(require_role(["admin", "hr"]))):
    result = await get_collection("payroll").update_one({"_id": ObjectId(payroll_id)}, {"$set": update_data})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Payroll entry not found")
    return {"message": "Payroll updated"}