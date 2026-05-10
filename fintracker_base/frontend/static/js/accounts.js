// ==================== CONFIGURATION ====================


// ==================== AUTH CHECK ====================
async function checkAuth() {
    const res = await fetch('/auth/status', { credentials: 'include' });

    if (!res.ok) {
        window.location.replace('/');
        return false;
    }

    const data = await res.json();
    if (!data.authenticated) {
        window.location.replace('/');
        return false;
    }

    return true;
}

// ==================== MODAL FUNCTIONS ====================
function openModal(id) {
    console.log(`Opening modal: ${id}`);
    const modal = document.getElementById(id);
    if (modal) {
        modal.style.display = 'block';
        const form = modal.querySelector('form');
        if (form) form.reset();
    } else {
        console.error(`Modal with id "${id}" not found`);
    }
}

function closeModal(id) {
    console.log(`Closing modal: ${id}`);
    const modal = document.getElementById(id);
    if (modal) {
        modal.style.display = 'none';
    }
}

window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
    }
};

// ==================== UTILITY FUNCTIONS ====================
function showMessage(message, type = 'success') {
    console.log(`${type.toUpperCase()}: ${message}`);

    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icon = type === 'error' ? '❌' : '✅';

    toast.innerHTML = `
        <span class="toast-icon">${icon}</span>
        <span class="toast-message">${message}</span>
        <span class="toast-close" onclick="this.parentElement.remove()">×</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        if (toast.parentElement) {
            toast.remove();
        }
    }, 5000);
}

async function logout() {
   await fetch('/logout', {
        method: 'POST',
        credentials: 'include'
    });

    sessionStorage.clear();
    localStorage.clear();

    window.location.href = '/';
}


const currencySymbols = {
    'USD': '$', 'EUR': '€', 'GBP': '£', 'JPY': '¥', 'CNY': '¥', 'INR': '₹',
    'AUD': 'A$', 'CAD': 'C$', 'CHF': 'Fr', 'SEK': 'kr', 'NOK': 'kr', 'DKK': 'kr',
    'RUB': '₽', 'BRL': 'R$', 'ZAR': 'R', 'KRW': '₩', 'MXN': '$', 'SGD': 'S$',
    'HKD': 'HK$', 'NZD': 'NZ$', 'TRY': '₺', 'AED': 'د.إ', 'SAR': '﷼', 'PLN': 'zł',
    'THB': '฿', 'MYR': 'RM', 'IDR': 'Rp', 'PHP': '₱', 'CZK': 'Kč', 'ILS': '₪',
    'CLP': '$', 'PKR': '₨', 'EGP': 'E£', 'BTC': '₿', 'ETH': 'Ξ'
};

function getCurrencySymbol(currencyCode) {
    return currencySymbols[currencyCode?.toUpperCase()] || currencyCode || '$';
}

function formatCurrency(amount, currencyCode) {
    const symbol = getCurrencySymbol(currencyCode);
    const formattedAmount = parseFloat(amount || 0).toFixed(2);
    const suffixCurrencies = ['SEK', 'NOK', 'DKK', 'CZK', 'PLN'];
    if (suffixCurrencies.includes(currencyCode?.toUpperCase())) {
        return `${formattedAmount} ${symbol}`;
    }
    return `${symbol}${formattedAmount}`;
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    const options = {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    };
    return date.toLocaleDateString('en-US', options);
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ==================== ACCOUNTS FUNCTIONS ====================
async function loadAccounts() {

    try {
        const res = await fetch('/accounts', {
    credentials: 'include'
    });

        if (!res.ok) {
            throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }

        const accounts = await res.json();
        console.log('Accounts loaded:', accounts);

        const list = document.getElementById('accounts-list');
        if (!list) {
            console.error('accounts-list element not found');
            return;
        }

        if (accounts.length === 0) {
            list.innerHTML = '<div class="empty-state"><p>No accounts found. Add one to get started!</p></div>';
            return;
        }

        list.innerHTML = accounts.map(a => `
            <div class="account-card">
                <div class="account-header">
                    <strong>${escapeHtml(a.account_name)}</strong>
                    <span class="account-balance">${formatCurrency(a.account_balance, a.currency)}</span>
                </div>
                <div class="account-details">
                    <div class="detail-row">
                        <span class="detail-label">Account Type:</span>
                        <span class="detail-value">${escapeHtml(capitalizeFirstWord(a.account_type))}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Currency:</span>
                        <span class="detail-value">${escapeHtml(a.currency)} (${getCurrencySymbol(a.currency)})</span>
                    </div>
                    ${a.platform_name ? `
                    <div class="detail-row">
                        <span class="detail-label">Platform:</span>
                        <span class="detail-value">${escapeHtml(a.platform_name)}</span>
                    </div>
                    ` : ''}
                    <div class="detail-row">
                        <span class="detail-label">Created:</span>
                        <span class="detail-value">${formatDate(a.created_at)}</span>
                    </div>
                </div>
                <div class="account-actions">
                    <button class="btn btn-danger btn-sm" onclick="deleteAccount(${a.account_id}, '${escapeHtml(a.account_name)}', ${a.account_balance})">
                        Delete Account
                    </button>
                    <button class="btn btn-secondary btn-sm" onclick="openUpdateModal(${a.account_id})">
                    Update Account
                    </button>
                </div>
            </div>
        `).join('');

    } catch (error) {
        console.error('Error loading accounts:', error);
        const list = document.getElementById('accounts-list');
        if (list) {
            list.innerHTML = '<div class="error-state"><p>Failed to load accounts. Please refresh the page.</p></div>';
        }
        showMessage(`Failed to load accounts: ${error.message}`, 'error');
    }
}

function capitalizeFirstWord(str) {
    return str.replace(/^\w+/, w => w.charAt(0).toUpperCase() + w.slice(1));
}

async function handleAddAccount(e) {
    e.preventDefault();
    console.log('=== ADD ACCOUNT FORM SUBMITTED ===');


    const name = document.getElementById('account-name').value.trim();
    const type = document.getElementById('account-type').value;
    const balance = parseFloat(document.getElementById('account-balance').value);
    const currency = document.getElementById('account-currency').value.trim();
    const platform = document.getElementById('account-platform').value.trim();

    console.log('Form values:', { name, type, balance, currency, platform });

    if (!name) {
        showMessage('Please enter an account name', 'error');
        return;
    }
    if (!type) {
        showMessage('Please select an account type', 'error');
        return;
    }
    if (isNaN(balance) || balance < 0) {
        showMessage('Please enter a valid balance (0 or greater)', 'error');
        return;
    }
    if (balance > 10000000) {
        showMessage('Balance cannot exceed 10,000,000', 'error');
        return;
    }
    if (!currency) {
        showMessage('Please enter a currency', 'error');
        return;
    }

    const accountData = {
        name: name,
        type: type,
        balance: balance,
        currency: currency,
        platform_name: platform || null
    };

    console.log('Sending account data:', accountData);

    try {
        const response = await fetch('/accounts', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify(accountData)
        });

        const result = await response.json();
        console.log('Response:', response.status, result);

        if (response.ok) {
            showMessage('Account added successfully!');
            closeModal('addAccount');
            e.target.reset();
            document.getElementById('account-currency').value = 'USD';
            await loadAccounts();
        } else {
            showMessage(result.detail || 'Failed to add account', 'error');
        }
    } catch (error) {
        console.error('Error adding account:', error);
        showMessage('Connection error. Please check your internet and try again.', 'error');
    }
}

// ==================== DELETE ACCOUNT FUNCTIONS ====================
let accountToDelete = null;

function deleteAccount(accountId, accountName, accountBalance) {
    console.log(`Initiating delete for account ${accountId}`);
    accountToDelete = accountId;

    const infoDiv = document.getElementById('account-to-delete-info');
    if (infoDiv) {
        infoDiv.innerHTML = `
            <strong style="color: #1a202c; font-size: 16px; display: block; margin-bottom: 8px;">
                📊 ${escapeHtml(accountName)}
            </strong>
            <span style="color: #666; font-size: 14px; display: block; margin-bottom: 4px;">
                💰 Balance: $${parseFloat(accountBalance || 0).toFixed(2)}
            </span>
            <span style="color: #999; font-size: 13px;">
                🆔 Account ID: ${accountId}
            </span>
        `;
    }

    const passwordField = document.getElementById('delete-password');
    if (passwordField) {
        passwordField.value = '';
    }

    openModal('deleteConfirmModal');
}

function closeDeleteModal() {
    accountToDelete = null;
    closeModal('deleteConfirmModal');

    const passwordField = document.getElementById('delete-password');
    if (passwordField) {
        passwordField.value = '';
    }
}

async function handleDeleteAccount(e) {
    e.preventDefault();

    if (!accountToDelete) {
        showMessage('No account selected for deletion', 'error');
        return;
    }

    const password = document.getElementById('delete-password').value;

    if (!password) {
        showMessage('Please enter your password', 'error');
        return;
    }

    console.log(`Confirming delete for account ${accountToDelete}`);

    const deleteBtn = e.target.querySelector('.btn-danger');
    const originalText = deleteBtn.innerHTML;
    deleteBtn.disabled = true;
    deleteBtn.innerHTML = '⏳ Deleting...';

    try {
        const response = await fetch(`/accounts/${accountToDelete}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({ password: password })
        });

        const result = await response.json();
        console.log('Delete response:', response.status, result);

        if (response.ok) {
            showMessage('Account deleted successfully!');
            closeDeleteModal();
            await loadAccounts();
        } else {
            showMessage(result.detail || 'Failed to delete account. Check your password.', 'error');
        }
    } catch (error) {
        console.error('Error deleting account:', error);
        showMessage('Connection error. Please try again.', 'error');
    } finally {
        deleteBtn.disabled = false;
        deleteBtn.innerHTML = originalText;
    }
}
// ===================== UPDATE ACCOUNT (IMPROVED) ========================

let accountToUpdate = null;

/**
 * Opens the update modal and populates it with account data
 * @param {number} accountId - The ID of the account to update
 */
async function openUpdateModal(accountId) {
    console.log(`Opening update modal for account ${accountId}`);
    accountToUpdate = accountId;



    try {
        // Show loading state
        const modal = document.getElementById('updateAccountModal');
        if (modal) {
            modal.style.display = 'block';

            // Disable form while loading
            const form = document.getElementById('updateAccountForm');
            if (form) {
                const inputs = form.querySelectorAll('input, select, button');
                inputs.forEach(input => input.disabled = true);
            }
        }

        // Fetch account details from API
        const response = await fetch(`/accounts/${accountId}`, {
    credentials: 'include'
    });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const account = await response.json();
        console.log('Account data loaded:', account);

        // Populate form fields with account data
        document.getElementById('update-account-id').value = account.account_id;
        document.getElementById('update-account-name').value = account.account_name || '';
        document.getElementById('update-account-type').value = account.account_type || '';
        document.getElementById('update-account-balance').value = account.account_balance || 0;
        document.getElementById('update-account-currency').value = account.currency || 'USD';
        document.getElementById('update-account-platform').value = account.platform_name || '';

        // Re-enable form inputs
        const form = document.getElementById('updateAccountForm');
        if (form) {
            const inputs = form.querySelectorAll('input, select, button');
            inputs.forEach(input => input.disabled = false);
        }

    } catch (error) {
        console.error('Error fetching account details:', error);
        showMessage(`Failed to load account details: ${error.message}`, 'error');
        closeUpdateModal();
    }
}

/**
 * Closes the update modal and resets the form
 */
function closeUpdateModal() {
    console.log('Closing update modal');
    const modal = document.getElementById('updateAccountModal');
    if (modal) {
        modal.style.display = 'none';
    }

    const form = document.getElementById('updateAccountForm');
    if (form) {
        form.reset();
    }

    accountToUpdate = null;
}

/**
 * Handles the update account form submission
 * @param {Event} e - The form submit event
 */
async function handleUpdateAccount(e) {
    e.preventDefault();
    console.log('=== UPDATE ACCOUNT FORM SUBMITTED ===');

    if (!accountToUpdate) {
        showMessage('No account selected for update', 'error');
        return;
    }


    // Get and validate form values
    const name = document.getElementById('update-account-name').value.trim();
    const type = document.getElementById('update-account-type').value;
    const balance = parseFloat(document.getElementById('update-account-balance').value);
    const currency = document.getElementById('update-account-currency').value.trim();
    const platform = document.getElementById('update-account-platform').value.trim();

    console.log('Update form values:', { name, type, balance, currency, platform });

    // Validation
    if (!name) {
        showMessage('Please enter an account name', 'error');
        return;
    }
    if (!type) {
        showMessage('Please select an account type', 'error');
        return;
    }
    if (isNaN(balance) || balance < 0) {
        showMessage('Please enter a valid balance (0 or greater)', 'error');
        return;
    }
    if (balance > 10000000) {
        showMessage('Balance cannot exceed 10,000,000', 'error');
        return;
    }
    if (!currency) {
        showMessage('Please enter a currency', 'error');
        return;
    }

    // Prepare update data
    const updateData = {
        name: name,
        accountType: type,
        balance: balance,
        currency: currency,
        platform_name: platform || null
    };

    console.log('Sending update data:', updateData);

    // Show loading state on button
    const submitBtn = e.target.querySelector('.btn-primary');
    const originalText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '⏳ Updating...';

    try {
        const response = await fetch(`/accounts/${accountToUpdate}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify(updateData)
        });

        const result = await response.json();
        console.log('Update response:', response.status, result);

        if (response.ok) {
            showMessage('✓ Account updated successfully!', 'success');
            closeUpdateModal();
            await loadAccounts(); // Reload the accounts list
        } else {
            showMessage(result.detail || 'Failed to update account', 'error');
        }
    } catch (error) {
        console.error('Error updating account:', error);
        showMessage('Connection error. Please try again.', 'error');
    } finally {
        // Restore button state
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    }
}


console.log('✅ Account update functionality loaded');
// ==================== INITIALIZATION ====================
document.addEventListener('DOMContentLoaded', async function() {
    console.log('=== ACCOUNTS PAGE INITIALIZED ===');

    if (!checkAuth()) {
        return;
    }



    // Attach Add Account form handler
    const addForm = document.getElementById('addAccountForm');
    if (addForm) {
        addForm.addEventListener('submit', handleAddAccount);
        console.log('✅ Add form submit handler attached');
    } else {
        console.error('❌ Add form not found!');
    }

    // Attach Delete Account form handler
    const deleteForm = document.getElementById('deleteAccountForm');
    if (deleteForm) {
        deleteForm.addEventListener('submit', handleDeleteAccount);
        console.log('✅ Delete form submit handler attached');
    } else {
        console.error('❌ Delete form not found!');
    }

    // ✅ ADD THIS: Attach Update Account form handler
    const updateForm = document.getElementById('updateAccountForm');
    if (updateForm) {
        updateForm.addEventListener('submit', handleUpdateAccount);
        console.log('✅ Update form submit handler attached');
    } else {
        console.error('❌ Update form not found!');
    }

    // Close modal when clicking outside
    window.addEventListener('click', function(event) {
        const updateModal = document.getElementById('updateAccountModal');
        if (event.target === updateModal) {
            closeUpdateModal();
        }
    });

    loadAccounts();
    const userRes = await fetch('/me', { credentials: 'include' });
        if (userRes.ok) {
            const user = await userRes.json();
            document.getElementById('user-btn').textContent = user.email;
        }
});


// ==================== GLOBAL EXPORTS ====================
window.openModal = openModal;
window.closeModal = closeModal;
window.logout = logout;
window.deleteAccount = deleteAccount;
window.loadAccounts = loadAccounts;
window.closeDeleteModal = closeDeleteModal;
window.openUpdateModal = openUpdateModal;
window.closeUpdateModal = closeUpdateModal;

console.log('accounts.js loaded successfully');

// ==================== EXPORTS ====================
// Add these to your existing global exports section
