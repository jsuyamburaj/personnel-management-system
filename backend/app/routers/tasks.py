from fastapi import APIRouter, Depends
from app.auth import get_current_active_user

router = APIRouter()

@router.get("/my-tasks")
async def get_my_tasks(current_user = Depends(get_current_active_user)):
    tasks = await get_collection("tasks").find({"assigned_to": current_user.email}).to_list(50)
    return [{"id": str(t["_id"]), "title": t["title"], "priority": t.get("priority", "Medium"), "status": t["status"]} for t in tasks]