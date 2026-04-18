from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime
from typing import List, Optional
from bson import ObjectId
from ..database import get_collection
from ..dependencies import get_current_active_user, require_role

router = APIRouter()

@router.get("/my-tasks")
async def get_my_tasks(current_user = Depends(get_current_active_user)):
    """Get tasks assigned to the current user"""
    tasks = await get_collection("tasks").find({"assigned_to": current_user.email}).to_list(50)
    return [{"id": str(t["_id"]), "title": t["title"], "priority": t.get("priority", "Medium"), "status": t["status"], "description": t.get("description", "")} for t in tasks]

@router.post("/")
async def create_task(
    task_data: dict,
    current_user = Depends(require_role(["admin", "manager"]))  # Only admin and manager can create tasks
):
    """Create a new task - Admin and Manager only"""
    required = ["title", "assigned_to"]
    for field in required:
        if field not in task_data:
            raise HTTPException(status_code=400, detail=f"Missing field: {field}")
    
    task = {
        "title": task_data["title"],
        "description": task_data.get("description", ""),
        "project_id": task_data.get("project_id"),
        "assigned_to": task_data["assigned_to"],
        "assigned_by": current_user.email,
        "priority": task_data.get("priority", "Medium"),
        "status": task_data.get("status", "Pending"),
        "due_date": task_data.get("due_date"),
        "created_at": datetime.utcnow(),
        "completed_at": None
    }
    result = await get_collection("tasks").insert_one(task)
    return {"message": "Task created", "id": str(result.inserted_id)}

@router.put("/{task_id}")
async def update_task(
    task_id: str,
    update_data: dict,
    current_user = Depends(get_current_active_user)
):
    """Update task - Anyone can update status, but only admin/manager can reassign"""
    task = await get_collection("tasks").find_one({"_id": ObjectId(task_id)})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check if user is assigned to this task or is admin/manager
    if current_user.role not in ["admin", "manager"] and task["assigned_to"] != current_user.email:
        # Regular employees can only update status of their own tasks
        if "status" not in update_data or len(update_data) > 1:
            raise HTTPException(status_code=403, detail="You can only update status of your own tasks")
    
    await get_collection("tasks").update_one(
        {"_id": ObjectId(task_id)},
        {"$set": update_data}
    )
    return {"message": "Task updated"}

@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    current_user = Depends(require_role(["admin", "manager"]))
):
    """Delete task - Admin and Manager only"""
    result = await get_collection("tasks").delete_one({"_id": ObjectId(task_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task deleted"}