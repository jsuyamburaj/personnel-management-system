from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime
from typing import List, Optional
from bson import ObjectId
from ..database import get_collection
from ..dependencies import get_current_active_user, require_role

router = APIRouter()

@router.get("/")
async def get_projects(
    status: Optional[str] = Query(None),
    manager_id: Optional[str] = Query(None),
    current_user = Depends(get_current_active_user)
):
    query = {}
    if status:
        query["status"] = status
    if manager_id:
        query["manager_id"] = manager_id
    # If employee, only show projects they are assigned to
    if current_user.role not in ["admin", "manager"]:
        query["team_members"] = current_user.email
    projects = await get_collection("projects").find(query).to_list(100)
    return [{"id": str(p["_id"]), **{k:v for k,v in p.items() if k != "_id"}} for p in projects]

@router.post("/")
async def create_project(project_data: dict, current_user = Depends(require_role(["admin", "manager"]))):
    required = ["name", "description", "start_date"]
    for field in required:
        if field not in project_data:
            raise HTTPException(status_code=400, detail=f"Missing {field}")
    project = {
        "name": project_data["name"],
        "description": project_data["description"],
        "start_date": project_data["start_date"],
        "end_date": project_data.get("end_date"),
        "status": project_data.get("status", "Planning"),
        "manager_id": current_user.email if current_user.role == "manager" else project_data.get("manager_id"),
        "team_members": project_data.get("team_members", []),
        "progress": project_data.get("progress", 0),
        "created_at": datetime.utcnow()
    }
    result = await get_collection("projects").insert_one(project)
    return {"message": "Project created", "id": str(result.inserted_id)}

@router.put("/{project_id}")
async def update_project(project_id: str, update_data: dict, current_user = Depends(require_role(["admin", "manager"]))):
    result = await get_collection("projects").update_one({"_id": ObjectId(project_id)}, {"$set": update_data})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"message": "Project updated"}

@router.delete("/{project_id}")
async def delete_project(project_id: str, current_user = Depends(require_role(["admin"]))):
    result = await get_collection("projects").delete_one({"_id": ObjectId(project_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"message": "Project deleted"}

@router.post("/{project_id}/assign")
async def assign_to_project(project_id: str, user_email: str, current_user = Depends(require_role(["admin", "manager"]))):
    result = await get_collection("projects").update_one(
        {"_id": ObjectId(project_id)},
        {"$addToSet": {"team_members": user_email}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Project or user not added")
    return {"message": f"User {user_email} assigned to project"}