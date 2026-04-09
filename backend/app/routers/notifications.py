from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId
from datetime import datetime
from ..database import get_collection
from ..dependencies import get_current_active_user

router = APIRouter()

@router.get("/")
async def get_notifications(
    skip: int = 0,
    limit: int = 20,
    unread_only: bool = False,
    current_user = Depends(get_current_active_user)
):
    query = {"user_email": current_user.email}
    if unread_only:
        query["is_read"] = False
    notifications = await get_collection("notifications").find(query).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return [{"id": str(n["_id"]), **{k:v for k,v in n.items() if k != "_id"}} for n in notifications]

@router.put("/{notif_id}/read")
async def mark_as_read(notif_id: str, current_user = Depends(get_current_active_user)):
    result = await get_collection("notifications").update_one(
        {"_id": ObjectId(notif_id), "user_email": current_user.email},
        {"$set": {"is_read": True}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Marked as read"}

@router.put("/read-all")
async def mark_all_read(current_user = Depends(get_current_active_user)):
    await get_collection("notifications").update_many(
        {"user_email": current_user.email, "is_read": False},
        {"$set": {"is_read": True}}
    )
    return {"message": "All notifications marked as read"}

@router.delete("/{notif_id}")
async def delete_notification(notif_id: str, current_user = Depends(get_current_active_user)):
    result = await get_collection("notifications").delete_one({"_id": ObjectId(notif_id), "user_email": current_user.email})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Notification deleted"}