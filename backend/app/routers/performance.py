from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timedelta
from bson import ObjectId
from ..database import get_collection
from ..dependencies import get_current_active_user, require_role

router = APIRouter()

@router.get("/my-rating")
async def get_my_performance_rating(current_user = Depends(get_current_active_user)):
    """Get performance rating for current user."""
    rating = await get_collection("performance").find_one({"user_email": current_user.email})
    if not rating:
        return {"average_rating": 0, "reviews": []}
    return {"average_rating": rating.get("average_rating", 0), "reviews": rating.get("reviews", [])}

@router.post("/rate")
async def rate_employee(
    employee_email: str,
    rating: int,
    feedback: str,
    current_user = Depends(require_role(["manager", "admin"]))
):
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    
    # Update or create performance record
    perf = await get_collection("performance").find_one({"user_email": employee_email})
    new_review = {
        "rater": current_user.email,
        "rating": rating,
        "feedback": feedback,
        "date": datetime.utcnow()
    }
    if perf:
        reviews = perf.get("reviews", [])
        reviews.append(new_review)
        avg = sum(r["rating"] for r in reviews) / len(reviews)
        await get_collection("performance").update_one(
            {"_id": perf["_id"]},
            {"$set": {"reviews": reviews, "average_rating": round(avg, 2)}}
        )
    else:
        await get_collection("performance").insert_one({
            "user_email": employee_email,
            "reviews": [new_review],
            "average_rating": rating
        })
    return {"message": "Performance rating submitted"}

@router.get("/team")
async def get_team_performance(current_user = Depends(require_role(["manager", "admin"]))):
    """Get performance ratings for manager's team."""
    team = await get_collection("users").find({"department": current_user.department}).to_list(100)
    result = []
    for member in team:
        perf = await get_collection("performance").find_one({"user_email": member["email"]})
        result.append({
            "email": member["email"],
            "name": member.get("full_name", ""),
            "average_rating": perf.get("average_rating", 0) if perf else 0
        })
    return result

@router.get("/productivity-score")
async def get_productivity_score(current_user = Depends(get_current_active_user)):
    """Calculate a simple productivity score based on task completion."""
    # Tasks completed in last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    completed = await get_collection("tasks").count_documents({
        "assigned_to": current_user.email,
        "status": "Completed",
        "completed_at": {"$gte": thirty_days_ago}
    })
    total_assigned = await get_collection("tasks").count_documents({
        "assigned_to": current_user.email,
        "created_at": {"$gte": thirty_days_ago}
    })
    score = (completed / total_assigned * 100) if total_assigned > 0 else 0
    return {"productivity_score": round(score, 2), "tasks_completed": completed, "total_tasks": total_assigned}