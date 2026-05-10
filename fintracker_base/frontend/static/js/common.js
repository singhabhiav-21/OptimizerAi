// Minimal common.js for non-accounts pages
const API_URL = 'http://localhost:8000';
const currentUserId = parseInt(sessionStorage.getItem('user_id'));

// ✅ Redirect to login if not authenticated
if (!currentUserId && window.location.pathname !== '/' && !window.location.pathname.includes('index.html')) {
    alert('Please log in first');
    window.location.href = '/';
}

function logout() {
    sessionStorage.removeItem('user_id');
    sessionStorage.removeItem('email');
    window.location.href = '/';
}