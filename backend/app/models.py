from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from bson import ObjectId

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")

class User(BaseModel):
    id: Optional[str] = None
    email: EmailStr
    full_name: Optional[str] = None
    role: str = "employee"  # admin, manager, developer, tester, hr, employee
    department: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class UserInDB(User):
    hashed_password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    role: Optional[str] = None
    client_ip: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

class Employee(BaseModel):
    user_id: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    address: Optional[str] = None
    join_date: Optional[datetime] = None
    skills: List[str] = []
    salary: float = 0
    status: str = "Active"  # Active, On Leave, Inactive

class Project(BaseModel):
    name: str
    description: str
    start_date: datetime
    end_date: Optional[datetime] = None
    status: str = "Planning"  # Planning, Active, Completed, On Hold
    manager_id: str
    team_members: List[str] = []
    progress: int = 0  # 0-100

class Task(BaseModel):
    title: str
    description: str
    project_id: str
    assigned_to: str
    assigned_by: str
    priority: str = "Medium"  # Low, Medium, High
    status: str = "Pending"  # Pending, In Progress, Completed
    due_date: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

class Attendance(BaseModel):
    user_email: str
    date: str  # YYYY-MM-DD
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    total_hours: float = 0
    status: str = "Present"  # Present, Absent, Late, Half Day

class Leave(BaseModel):
    user_email: str
    start_date: datetime
    end_date: datetime
    leave_type: str  # Annual, Sick, Personal, Unpaid
    reason: str
    status: str = "Pending"  # Pending, Approved, Rejected
    approved_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Payroll(BaseModel):
    user_email: str
    month: str  # YYYY-MM
    basic_salary: float
    allowances: float = 0
    deductions: float = 0
    bonus: float = 0
    net_salary: float
    status: str = "Pending"  # Pending, Processed, Paid
    payslip_url: Optional[str] = None

class Notification(BaseModel):
    user_email: str
    title: str
    message: str
    type: str  # info, success, warning, error
    is_read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ActivityLog(BaseModel):
    user_email: str
    action: str
    details: str
    ip_address: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class Message(BaseModel):
    sender: str
    receiver: str
    content: str
    is_read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)