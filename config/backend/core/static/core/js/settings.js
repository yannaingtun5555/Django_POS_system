// DOM Elements
const addUserBtn = document.getElementById('addUserBtn');
const reportBugBtn = document.getElementById('reportBugBtn');
const logoutBtn = document.getElementById('logoutBtn');
const userModal = document.getElementById('userModal');
const closeModalBtn = document.getElementById('closeModalBtn');
const cancelBtn = document.getElementById('cancelBtn');
const userForm = document.getElementById('userForm');
const userMessage = document.getElementById('userMessage');
const notification = document.getElementById('notification');
const shopNameInput = document.getElementById('shopName');
const currencyInput = document.getElementById('currency');
const saveChangesBtn = document.getElementById('saveChangesBtn');

// API Base URL - Change this to your actual API endpoint
const API_BASE_URL = window.location.origin;
const APP_CONFIG = window.APP_CONFIG || {};
const DEFAULT_SHOP_NAME = APP_CONFIG.shopName || 'POS';
const DEFAULT_CURRENCY_PREFIX = APP_CONFIG.currencyPrefix || '$';

// =====================
// Modal Functions
// =====================
function getAccessToken() {
    return localStorage.getItem('access');
}

function getRefreshToken() {
    return localStorage.getItem('refresh');
}
// Open Add User Modal
addUserBtn.addEventListener('click', () => {
    userForm.reset();
    userMessage.textContent = '';
    userMessage.className = 'message';
    userModal.classList.add('active');
});

// Close Modal
closeModalBtn.addEventListener('click', () => {
    userModal.classList.remove('active');
});

cancelBtn.addEventListener('click', () => {
    userModal.classList.remove('active');
});

// Close modal when clicking outside
userModal.addEventListener('click', (e) => {
    if (e.target === userModal) {
        userModal.classList.remove('active');
    }
});

// =====================
// User Registration
// =====================

userForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value.trim();
    const email = document.getElementById('email').value.trim();
    const firstName = document.getElementById('firstName').value.trim();
    const lastName = document.getElementById('lastName').value.trim();
    const role = document.getElementById('role').value.trim();

    // Validation
    if (!username || !password || !firstName || !lastName || !role) {
        showUserMessage('Please fill in all required fields', 'error');
        return;
    }

    if (password.length < 8) {
        showUserMessage('Password must be at least 8 characters long', 'error');
        return;
    }

    if (email && !isValidEmail(email)) {
        showUserMessage('Please enter a valid email address', 'error');
        return;
    }

    // Build payload
    const payload = {
        username,
        password,
        first_name: firstName,
        last_name: lastName,
        role
    };

    // Only add email if provided
    if (email) {
        payload.email = email;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/auth/register/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAccessToken()}`,
            },
            body: JSON.stringify(payload),
            credentials: 'include' // Include cookies for authentication
        });

        if (response.status === 403) {
            showUserMessage('Only admin can create the user', 'error');
        } else if (response.status === 401) {
            showUserMessage('Unauthorized', 'error');
        } else if (response.status === 201 || response.ok) {
            showUserMessage('User created successfully', 'success');
            userForm.reset();
            setTimeout(() => {
                userModal.classList.remove('active');
            }, 1500);
        } else {
            const errorData = await response.json().catch(() => ({}));
            showUserMessage(errorData.message || `Error: ${response.statusText}`, 'error');
        }
    } catch (error) {
        console.error('Error creating user:', error);
        showUserMessage('An error occurred while creating the user', 'error');
    }
});

// Show message in modal
function showUserMessage(message, type) {
    userMessage.textContent = message;
    userMessage.className = `message ${type}`;
}

// =====================
// Report Bug
// =====================

reportBugBtn.addEventListener('click', () => {
    const creatorEmail = 'yan9htun1910@gmail.com';
    const subject = `${DEFAULT_SHOP_NAME} - Bug Report`;
    const body = 'Please describe the bug you found:';
    const gmailURL = `https://mail.google.com/mail/?view=cm&fs=1&to=${creatorEmail}&su=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    window.open(gmailURL, '_blank');
});

// =====================
// Logout
// =====================

logoutBtn.addEventListener('click', async () => {
    try {
        const refreshToken = getRefreshToken();
        const response = await fetch(`${API_BASE_URL}/api/auth/logout/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAccessToken()}`,
            },
            body: JSON.stringify(refreshToken ? { refresh: refreshToken } : {}),
            credentials: 'include'
        });

        if (response.ok) {
            localStorage.removeItem('access');
            localStorage.removeItem('refresh');
            showNotification('Logged out successfully', 'success');
            // Redirect to login page after 1 second
            setTimeout(() => {
                window.location.href = '/login'; // Update with your login page URL
            }, 1000);
        } else {
            showNotification('Logout failed', 'error');
        }
    } catch (error) {
        console.error('Error during logout:', error);
        showNotification('An error occurred during logout', 'error');
    }
});

// =====================
// General Settings
// =====================

// Load settings on page load
document.addEventListener('DOMContentLoaded', async () => {
    await loadSettings();
});

// Load settings from API
async function loadSettings() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/auth/config/`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAccessToken()}`,
            },
            credentials: 'include'
        });

        if (response.ok) {
            const data = await response.json();
            if (data.data && data.data.settings) {
                const settings = data.data.settings;
                shopNameInput.value = settings.SHOP_NAME || '';
                currencyInput.value = settings.CURRENCY_PREFIX || DEFAULT_CURRENCY_PREFIX;
            }
        } else {
            console.error('Failed to load settings');
            showNotification('Failed to load settings', 'error');
        }
    } catch (error) {
        console.error('Error loading settings:', error);
        showNotification('An error occurred while loading settings', 'error');
    }
}

// Save settings
saveChangesBtn.addEventListener('click', async () => {
    const shopName = shopNameInput.value.trim();
    const currency = currencyInput.value.trim();

    if (!shopName) {
        showNotification('Please enter a shop name', 'error');
        return;
    }

    const payload = {
        SHOP_NAME: shopName,
        CURRENCY_PREFIX: currency
    };

    try {
        const response = await fetch(`${API_BASE_URL}/api/auth/update_config/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAccessToken()}`,
            },
            body: JSON.stringify(payload),
            credentials: 'include'
        });

        if (response.ok) {
            showNotification('Settings saved successfully', 'success');
        } else {
            const errorData = await response.json().catch(() => ({}));
            showNotification(errorData.message || 'Failed to save settings', 'error');
        }
    } catch (error) {
        console.error('Error saving settings:', error);
        showNotification('An error occurred while saving settings', 'error');
    }
});

// =====================
// Utility Functions
// =====================

// Show notification toast
function showNotification(message, type) {
    notification.textContent = message;
    notification.className = `notification ${type} show`;

    // Auto-hide after 3 seconds
    setTimeout(() => {
        notification.classList.remove('show');
    }, 3000);
}

// Email validation
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// =====================
// Log current API configuration
// =====================

console.log('[v0] POS Settings Page Loaded');
console.log('[v0] API Base URL:', API_BASE_URL);
console.log('[v0] Endpoints:');
console.log('  - Register: POST /api/auth/register/');
console.log('  - Logout: POST /api/auth/logout/');
console.log('  - Config: GET /api/auth/config/');
console.log('  - Update Config: POST /api/auth/update_config/');
