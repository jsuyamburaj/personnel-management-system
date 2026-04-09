from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta
from typing import List, Optional
import logging

from .config import settings
from .database import db
from .models import User, UserInDB, Token, LoginRequest
from .auth import create_access_token, verify_password, get_password_hash
from .dependencies import get_current_user, get_current_active_user, require_role

from .routers import (
    employees, projects, tasks, attendance, leaves, payroll,
    notifications, activity_logs, documents, messages, analytics, performance
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="SPMS API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

# Include routers
app.include_router(employees.router, prefix="/api/employees", tags=["Employees"])
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["Tasks"])
app.include_router(attendance.router, prefix="/api/attendance", tags=["Attendance"])
app.include_router(leaves.router, prefix="/api/leaves", tags=["Leaves"])
app.include_router(payroll.router, prefix="/api/payroll", tags=["Payroll"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(activity_logs.router, prefix="/api/activity-logs", tags=["Activity Logs"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(messages.router, prefix="/api/messages", tags=["Messages"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(performance.router, prefix="/api/performance", tags=["Performance"])

@app.on_event("startup")
async def startup_db_client():
    await db.connect()
    await create_default_admin()
    logger.info("Database connected and initialized")

@app.on_event("shutdown")
async def shutdown_db_client():
    await db.close()
    logger.info("Database disconnected")

async def create_default_admin():
    """Create default admin user if not exists"""
    existing = await db.users.find_one({"email": "admin@spms.com"})
    if not existing:
        admin_user = {
            "email": "admin@spms.com",
            "full_name": "System Administrator",
            "hashed_password": get_password_hash("password123"),
            "role": "admin",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "department": "Management"
        }
        await db.users.insert_one(admin_user)
        logger.info("Default admin user created")
    
    # Create sample employees
    if await db.users.count_documents({}) < 2:
        sample_employees = [
            {"email": "manager@spms.com", "full_name": "Jane Manager", "role": "manager", "department": "Product"},
            {"email": "developer@spms.com", "full_name": "John Developer", "role": "developer", "department": "Engineering"},
            {"email": "hr@spms.com", "full_name": "Sarah HR", "role": "hr", "department": "Human Resources"},
        ]
        for emp in sample_employees:
            emp["hashed_password"] = get_password_hash("password123")
            emp["is_active"] = True
            emp["created_at"] = datetime.utcnow()
            await db.users.insert_one(emp)
        logger.info("Sample users created")

@app.get("/")
async def root():
    return {"message": "SPMS API is running", "version": "1.0.0"}

@app.post("/api/auth/login", response_model=Token)
async def login(login_data: LoginRequest):
    """Login endpoint - returns JWT token"""
    user = await db.users.find_one({"email": login_data.email})
    
    if not user or not verify_password(login_data.password, user["hashed_password"]):
        # Log failed attempt
        await db.failed_logins.insert_one({
            "email": login_data.email,
            "timestamp": datetime.utcnow(),
            "ip": login_data.client_ip if hasattr(login_data, 'client_ip') else "unknown"
        })
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if role matches (optional demo role check)
    if login_data.role and user["role"] != login_data.role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid role. Expected {login_data.role}, but user is {user['role']}"
        )
    
    access_token = create_access_token(
        data={"sub": user["email"], "role": user["role"]}
    )
    
    # Log successful login
    await db.activity_logs.insert_one({
        "user_email": user["email"],
        "action": "login",
        "timestamp": datetime.utcnow(),
        "details": "User logged in successfully"
    })
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "email": user["email"],
            "full_name": user.get("full_name", user["email"]),
            "role": user["role"],
            "department": user.get("department", "")
        }
    }

@app.get("/api/admin/stats")
async def get_admin_stats(current_user: User = Depends(require_role(["admin"]))):
    """Get dashboard statistics for admin"""
    total_employees = await db.users.count_documents({"role": {"$ne": "admin"}})
    active_projects = await db.projects.count_documents({"status": "Active"})
    completed_tasks = await db.tasks.count_documents({"status": "Completed"})
    present_today = await db.attendance.count_documents({
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "check_in": {"$ne": None}
    })
    
    return {
        "total_employees": total_employees,
        "active_projects": active_projects,
        "completed_tasks": completed_tasks,
        "present_today": present_today
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)