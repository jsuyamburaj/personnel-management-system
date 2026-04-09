// Employee-specific functions
async function loadMyTasks() {
    const tasks = await window.apiRequest('/tasks/my-tasks', 'GET');
    const container = document.getElementById('myTasksList');
    if (!container) return;
    if (tasks.length === 0) {
        container.innerHTML = '<div class="text-muted">No tasks assigned</div>';
        return;
    }
    container.innerHTML = tasks.slice(0, 5).map(task => `
        <div class="task-item d-flex justify-content-between align-items-center border-bottom py-2">
            <span>${task.title}</span>
            <span class="badge bg-${task.priority === 'High' ? 'danger' : task.priority === 'Medium' ? 'warning' : 'success'}">${task.priority}</span>
        </div>
    `).join('');
}

async function loadMyLeaveBalance() {
    const balance = await window.apiRequest('/leaves/balance', 'GET');
    const elem = document.getElementById('leaveBalance');
    if (elem) elem.innerText = balance.available || 0;
}

async function submitLeaveRequest(formData) {
    try {
        await window.apiRequest('/leaves/', 'POST', formData);
        window.showNotification('Leave request submitted', 'success');
        // Refresh leave requests table
        if (typeof loadMyLeaveRequests === 'function') loadMyLeaveRequests();
    } catch (err) {
        window.showNotification('Failed to submit leave', 'error');
    }
}

async function loadMyAttendance() {
    const today = await window.apiRequest('/attendance/today', 'GET');
    const checkInElem = document.getElementById('checkInTime');
    const checkOutElem = document.getElementById('checkOutTime');
    if (checkInElem) checkInElem.innerText = today.check_in ? new Date(today.check_in).toLocaleTimeString() : 'Not checked in';
    if (checkOutElem) checkOutElem.innerText = today.check_out ? new Date(today.check_out).toLocaleTimeString() : 'Not checked out';
}

// Quick check-in/out buttons
async function checkIn() {
    const res = await window.apiRequest('/attendance/check-in', 'POST');
    window.showNotification(res.message, 'success');
    loadMyAttendance();
}

async function checkOut() {
    const res = await window.apiRequest('/attendance/check-out', 'POST');
    window.showNotification(res.message, 'success');
    loadMyAttendance();
}

// Export globals
window.loadMyTasks = loadMyTasks;
window.loadMyLeaveBalance = loadMyLeaveBalance;
window.submitLeaveRequest = submitLeaveRequest;
window.loadMyAttendance = loadMyAttendance;
window.checkIn = checkIn;
window.checkOut = checkOut;