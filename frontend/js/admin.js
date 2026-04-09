// Admin-specific functions
const API = window.apiRequest || (() => {});

async function loadAdminDashboardStats() {
    try {
        const stats = await API('/admin/stats', 'GET');
        document.getElementById('totalEmployees').innerText = stats.total_employees || 0;
        document.getElementById('activeProjects').innerText = stats.active_projects || 0;
        document.getElementById('completedTasks').innerText = stats.completed_tasks || 0;
        document.getElementById('presentToday').innerText = stats.present_today || 0;
    } catch (error) {
        console.error('Failed to load admin stats:', error);
    }
}

async function loadRecentActivities() {
    const logs = await API('/activity-logs/me?limit=5', 'GET');
    const container = document.getElementById('recentActivities');
    if (!container) return;
    if (logs.length === 0) {
        container.innerHTML = '<div class="text-muted">No recent activities</div>';
        return;
    }
    container.innerHTML = logs.map(log => `
        <div class="activity-item">
            <i class="fas fa-${log.action === 'login' ? 'sign-in-alt' : 'edit'} me-2"></i>
            <span>${log.details}</span>
            <small class="text-muted ms-auto">${new Date(log.timestamp).toLocaleString()}</small>
        </div>
    `).join('');
}

// Role management (simplified)
async function updateUserRole(userId, newRole) {
    return await API(`/employees/${userId}/role`, 'PUT', { role: newRole });
}

// Export for global use
window.loadAdminDashboardStats = loadAdminDashboardStats;
window.loadRecentActivities = loadRecentActivities;
window.updateUserRole = updateUserRole;