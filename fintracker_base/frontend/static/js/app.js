// Update this to match your FastAPI server URL

function showForm(formType) {
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    const toggleBtns = document.querySelectorAll('.toggle-btn');

    toggleBtns.forEach(btn => btn.classList.remove('active'));

    if (formType === 'login') {
        loginForm.classList.add('active');
        registerForm.classList.remove('active');
        toggleBtns[0].classList.add('active');
    } else {
        registerForm.classList.add('active');
        loginForm.classList.remove('active');
        toggleBtns[1].classList.add('active');
    }

    // Clear messages
    document.getElementById('login-message').style.display = 'none';
    document.getElementById('register-message').style.display = 'none';
    clearFieldErrors();
}

// Input validation functions
function validateEmail(email) {
    const re = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    return re.test(email) && email.length <= 255;
}

function validatePassword(password) {
    const errors = [];

    if (password.length < 8) {
        errors.push('Password must be at least 8 characters long');
    }
    if (password.length > 128) {
        errors.push('Password must be less than 128 characters');
    }
    if (!/[a-z]/.test(password)) {
        errors.push('Password must contain at least one lowercase letter (a-z)');
    }
    if (!/[A-Z]/.test(password)) {
        errors.push('Password must contain at least one uppercase letter (A-Z)');
    }
    if (!/[0-9]/.test(password)) {
        errors.push('Password must contain at least one number (0-9)');
    }
    if (!/[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(password)) {
        errors.push('Password must contain at least one special character (!@#$%^&*...)');
    }

    return errors;
}

function validateName(name) {
    const errors = [];
    const trimmed = name.trim();

    // Check if name has at least first and last name (space-separated)
    const nameParts = trimmed.split(/\s+/);
    if (nameParts.length < 2) {
        errors.push('Please enter both first and last name (separated by space)');
    }

    if (trimmed.length < 5) {
        errors.push('Name must be at least 5 characters long');
    }
    if (trimmed.length > 100) {
        errors.push('Name must be less than 100 characters');
    }

    if (!/^[a-zA-Z\s'-]+$/.test(trimmed)) {
        if (/[0-9]/.test(trimmed)) {
            errors.push('Name cannot contain numbers');
        }
        if (/[!@#$%^&*()_+=\[\]{}|;:",.<>?\/\\`~]/.test(trimmed)) {
            errors.push('Name cannot contain special characters (except - and \')');
        }
    }

    return errors;
}

function showFieldError(fieldId, messages) {
    const field = document.getElementById(fieldId);
    const errorDiv = field.parentElement.querySelector('.field-error') ||
                     document.createElement('div');
    errorDiv.className = 'field-error';

    if (Array.isArray(messages)) {
        errorDiv.innerHTML = messages.map(msg => `• ${msg}`).join('<br>');
    } else {
        errorDiv.textContent = messages;
    }

    if (!field.parentElement.querySelector('.field-error')) {
        field.parentElement.appendChild(errorDiv);
    }
    field.classList.add('error');
}

function clearFieldErrors() {
    document.querySelectorAll('.field-error').forEach(el => el.remove());
    document.querySelectorAll('.error').forEach(el => el.classList.remove('error'));
}

async function handleLogin(e) {
    e.preventDefault();
    clearFieldErrors();

    const email = document.getElementById('login-email').value.trim();
    const password = document.getElementById('login-password').value;
    const btn = document.getElementById('login-btn');
    const messageDiv = document.getElementById('login-message');

    let hasError = false;

    if (!validateEmail(email)) {
        showFieldError('login-email', 'Please enter a valid email address');
        hasError = true;
    }

    if (!password) {
        showFieldError('login-password', 'Please enter your password');
        hasError = true;
    }

    if (hasError) return;

    btn.disabled = true;
    btn.textContent = 'Logging in...';
    messageDiv.style.display = 'none';

    try {
        const response = await fetch('/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({
                email: email,
                password: password
            })
        });

        const data = await response.json();

        if (response.ok) {

            sessionStorage.setItem('base_currency', 'USD');

            showMessage('login-message', 'Login successful! Redirecting to dashboard...', 'success');

            window.location.href = '/dashboard';  // Changed from ${API_URL}/dashboard
        } else {
            const errorMsg = response.status === 429 ?
                data.detail : 'Invalid email or password';
            showMessage('login-message', errorMsg, 'error');
        }
    } catch (error) {
        showMessage('login-message', 'Connection error. Please try again.', 'error');
        console.error('Error:', error);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Login';
    }
}

async function handleRegister(e) {
    e.preventDefault();
    clearFieldErrors();

    const name = document.getElementById('register-name').value.trim();
    const email = document.getElementById('register-email').value.trim();
    const password = document.getElementById('register-password').value;
    const btn = document.getElementById('register-btn');
    const messageDiv = document.getElementById('register-message');

    let hasError = false;

    const nameErrors = validateName(name);
    if (nameErrors.length > 0) {
        showFieldError('register-name', nameErrors);
        hasError = true;
    }

    if (!validateEmail(email)) {
        showFieldError('register-email', 'Please enter a valid email address');
        hasError = true;
    }

    const passwordErrors = validatePassword(password);
    if (passwordErrors.length > 0) {
        showFieldError('register-password', passwordErrors);
        hasError = true;
    }

    if (hasError) return;

    btn.disabled = true;
    btn.textContent = 'Registering...';
    messageDiv.style.display = 'none';

    try {
        const response = await fetch('/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({
                name: name,
                email: email,
                password: password
            })
        });

        const data = await response.json();

        if (response.ok) {
            showMessage('register-message', 'Registration successful! Please login.', 'success');

            document.getElementById('register-name').value = '';
            document.getElementById('register-email').value = '';
            document.getElementById('register-password').value = '';

            setTimeout(() => {
                showForm('login');
            }, 2000);
        } else {
            showMessage('register-message', data.detail || 'Registration failed', 'error');
        }
    } catch (error) {
        showMessage('register-message', 'Connection error. Please try again.', 'error');
        console.error('Error:', error);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Register';
    }
}

function showMessage(elementId, text, type) {
    const messageDiv = document.getElementById(elementId);
    messageDiv.textContent = text;
    messageDiv.className = `message ${type}`;
    messageDiv.style.display = 'block';
}


// Check if user is already logged in on page load
document.addEventListener('DOMContentLoaded', async () => {

    // Check if we're on the login page and if user is already authenticated
    if (window.location.pathname === '/') {
    try {
        const response = await fetch('/auth/status', {
        credentials: 'include'
        });

        if (response.ok) {
            const data = await response.json();
        if (data.authenticated) {
        window.location.replace('/dashboard');
            }
        }

        if (response.ok) {
            window.location.replace('/dashboard');
        }
    } catch (error) {
        console.log('Not authenticated');
    }
  }
});