import re
from datetime import datetime
from typing import List, Dict, Any

def validate_email(email: str) -> bool:
    """Basic email validation."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def sanitize_input(text: str) -> str:
    """Remove dangerous characters (simple XSS prevention)."""
    if not text:
        return ""
    return re.sub(r'[<>]', '', text)

def calculate_working_hours(check_in: datetime, check_out: datetime) -> float:
    """Calculate total hours worked."""
    if not check_in or not check_out:
        return 0
    delta = check_out - check_in
    return round(delta.total_seconds() / 3600, 2)

def generate_payslip_html(employee_name: str, month: str, salary: float, deductions: float, net: float) -> str:
    """Generate simple HTML payslip."""
    return f"""
    <html>
    <body>
        <h2>Payslip for {employee_name}</h2>
        <p>Month: {month}</p>
        <p>Gross Salary: ${salary}</p>
        <p>Deductions: ${deductions}</p>
        <p><strong>Net Salary: ${net}</strong></p>
    </body>
    </html>
    """

def format_activity_message(action: str, details: Dict[str, Any]) -> str:
    """Format activity log message."""
    if action == "login":
        return f"User logged in from {details.get('ip', 'unknown IP')}"
    elif action == "create_employee":
        return f"Created employee {details.get('email')}"
    elif action == "delete_project":
        return f"Deleted project {details.get('project_name')}"
    return f"Performed {action}: {details}"