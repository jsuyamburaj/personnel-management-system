from fastapi import APIRouter, Depends
from datetime import datetime, timedelta
from ..database import get_collection
from ..dependencies import require_role

router = APIRouter()

@router.get("/dashboard")
async def get_analytics(current_user = Depends(require_role(["admin", "manager"]))):
    """Provide analytics data for charts."""
    total_employees = await get_collection("users").count_documents({"is_active": True})
    active_projects = await get_collection("projects").count_documents({"status": "Active"})
    completed_tasks = await get_collection("tasks").count_documents({"status": "Completed"})
    pending_tasks = await get_collection("tasks").count_documents({"status": {"$ne": "Completed"}})
    
    # Attendance trend last 30 days
    today = datetime.utcnow()
    start = today - timedelta(days=30)
    attendance_data = []
    for i in range(30):
        day = (start + timedelta(days=i)).strftime("%Y-%m-%d")
        count = await get_collection("attendance").count_documents({"date": day})
        attendance_data.append({"date": day, "present": count})
    
    # Department distribution
    pipeline = [
        {"$group": {"_id": "$department", "count": {"$sum": 1}}}
    ]
    dept_stats = await get_collection("users").aggregate(pipeline).to_list(None)
    
    return {
        "total_employees": total_employees,
        "active_projects": active_projects,
        "completed_tasks": completed_tasks,
        "pending_tasks": pending_tasks,
        "attendance_trend": attendance_data,
        "department_distribution": {item["_id"]: item["count"] for item in dept_stats if item["_id"]}
    }