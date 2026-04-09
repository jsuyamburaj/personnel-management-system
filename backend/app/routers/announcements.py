from fastapi import APIRouter, Depends
from ..database import get_collection
from ..dependencies import get_current_active_user

router = APIRouter()

@router.get("/")
async def get_announcements(current_user = Depends(get_current_active_user)):
    # Announcements are global; you can add role‑based filtering later
    announcements = await get_collection("announcements").find().sort("created_at", -1).to_list(20)
    return [{"message": a["message"], "created_at": a["created_at"]} for a in announcements]