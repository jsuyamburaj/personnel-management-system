from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime
from typing import List, Optional
from bson import ObjectId
from ..database import get_collection
from ..dependencies import get_current_active_user

router = APIRouter()

@router.get("/conversations")
async def get_conversations(current_user = Depends(get_current_active_user)):
    """Get list of users the current user has chatted with."""
    pipeline = [
        {"$match": {"$or": [{"sender": current_user.email}, {"receiver": current_user.email}]}},
        {"$sort": {"created_at": -1}},
        {"$group": {"_id": {"$cond": [{"$eq": ["$sender", current_user.email]}, "$receiver", "$sender"]}}}
    ]
    results = await get_collection("messages").aggregate(pipeline).to_list(None)
    return [{"user": r["_id"]} for r in results if r["_id"]]

@router.get("/with/{other_user}")
async def get_messages(
    other_user: str,
    skip: int = 0,
    limit: int = 50,
    current_user = Depends(get_current_active_user)
):
    query = {
        "$or": [
            {"sender": current_user.email, "receiver": other_user},
            {"sender": other_user, "receiver": current_user.email}
        ]
    }
    messages = await get_collection("messages").find(query).sort("created_at", 1).skip(skip).limit(limit).to_list(limit)
    # Mark as read
    await get_collection("messages").update_many(
        {"sender": other_user, "receiver": current_user.email, "is_read": False},
        {"$set": {"is_read": True}}
    )
    return [{"id": str(m["_id"]), **{k:v for k,v in m.items() if k != "_id"}} for m in messages]

@router.post("/send")
async def send_message(receiver: str, content: str, current_user = Depends(get_current_active_user)):
    message = {
        "sender": current_user.email,
        "receiver": receiver,
        "content": content,
        "is_read": False,
        "created_at": datetime.utcnow()
    }
    result = await get_collection("messages").insert_one(message)
    return {"message": "Sent", "id": str(result.inserted_id)}