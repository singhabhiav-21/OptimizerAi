// transactions.js — refactored for cookie-based FastAPI sessions (student project)
// Server session is the ONLY source of truth for authentication

document.addEventListener('DOMContentLoaded', async () => {
    try {
        const res = await fetch('/auth/status', { credentials: 'include' });

        if (res.status === 401) {
            window.location.replace('/');
            return;
        }

        if (!res.ok) throw new Error();

        const data = await res.json();
        if (!data.authenticated) {
            window.location.replace('/');
            return;
        }

        loadTransactions();
        const userRes = await fetch('/me', { credentials: 'include' });
        if (userRes.ok) {
            const user = await userRes.json();
            document.getElementById('user-btn').textContent = user.email;
        }


        const form = document.getElementById('addTransactionForm');
        if (form) form.addEventListener('submit', addTransaction);

        const deleteForm = document.getElementById('deleteTransactionForm');
        if (deleteForm) deleteForm.addEventListener('submit', confirmDeleteTransaction);

    } catch {
        window.location.replace('/');
    }
});

// ==================== MODAL HELPERS ====================
function openModal(id) {
    const m = document.getElementById(id);
    if (m) m.style.display = 'flex';
}

function closeModal(id) {
    const m = document.getElementById(id);
    if (!m) return;
    m.style.display = 'none';
    const f = m.querySelector('form');
    if (f) f.reset();
}

window.onclick = e => {
    if (e.target.classList.contains('modal')) e.target.style.display = 'none';
};

// ==================== TOAST ====================
function showMessage(message, type = 'success') {
const container = document.getElementById('toast-container');
    if (!container) {
        console.warn('Toast container missing:', message);
        return;
    }

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    toast.innerHTML = `
        <div class="toast-icon">
            ${type === 'error' ? '❌' : '✅'}
        </div>
        <div class="toast-message">${escapeHtml(message)}</div>
        <div class="toast-close">&times;</div>
    `;

    container.appendChild(toast);

    toast.querySelector('.toast-close').onclick = () => toast.remove();
    setTimeout(() => toast.remove(), 3000);
}

// ==================== LOAD TRANSACTIONS ====================
async function loadTransactions() {
    try {
        const res = await fetch('/transactions', { credentials: 'include' });
        if (!res.ok) throw new Error();

        const transactions = await res.json();
        const list = document.getElementById('transactions-list');
        if (!list) return;

        if (!transactions.length) {
            list.innerHTML = '<p style="text-align:center;color:#666;padding:40px">No transactions found.</p>';
            return;
        }

        const grouped = {};
        transactions.forEach(t => {
            const d = t.transaction_date || 'No date';
            grouped[d] = grouped[d] || [];
            grouped[d].push(t);
        });

        let html = '';

        Object.keys(grouped)
            .sort()
            .reverse()
            .forEach(date => {
                html += `
                <div class="transaction-date-group">
                    <h3>${formatDate(date)}</h3>
                    <hr class="date-separator">
                `;

                grouped[date].forEach(t => {
                    const amount = parseFloat(t.amount || 0);
                    const isPositive = amount > 0;
                    const sign = isPositive ? '+' : ''
                    const color = isPositive ? '#10b981' : '#ef4444';
                    const colorClass = isPositive ? 'positive' : 'negative';

                    html += `
                    <div class="transaction-card">
                        <div class="transaction-main">
                            <div>
                                <div><strong>${escapeHtml(t.name)}</strong></div>
                                ${t.description ? `<small>${escapeHtml(t.description)}</small>` : ''}
                            </div>
                            <div style="color:${color}">
                                <strong>${sign}${Math.abs(amount).toFixed(2)}kr</strong>
                            </div>
                        </div>
                        <div class="transaction-actions">
                            <button
                                class="btn-delete"
                                onclick="openDeleteModal(
                                    ${t.transaction_id},
                                    '${escapeHtml(t.name).replace(/'/g, "\\'")}',
                                    ${amount}
                                )">
                                Delete
                            </button>
                        </div>
                    </div>
                    `;
                });

                html += '</div>';
            });

        list.innerHTML = html;

    } catch {
        showMessage('Failed to load transactions', 'error');
    }
}

// ==================== ADD TRANSACTION ====================
async function addTransaction(e) {
    e.preventDefault();

    const payload = {
        category_id: Number(document.getElementById('transaction-category').value),
        name: document.getElementById('transaction-name').value.trim(),
        amount: Number(document.getElementById('transaction-amount').value),
        description: document.getElementById('transaction-description').value.trim() || null,
        transaction_date: document.getElementById('transaction-date').value || null
    };

    if (!payload.name || !payload.amount) {
        showMessage('Invalid transaction data', 'error');
        return;
    }

    try {
        const res = await fetch('/transactions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(payload)
        });

        if (!res.ok) throw new Error();

        showMessage('Transaction added');
        closeModal('addTransaction');
        loadTransactions();
        e.target.reset();

    } catch {
        showMessage('Failed to add transaction', 'error');
    }
}

// ==================== DELETE TRANSACTION ====================
let transactionToDelete = null;

function openDeleteModal(id, name, amount) {
    transactionToDelete = id;

    document.getElementById('transaction-to-delete-info').innerHTML = `
        <strong>${name}</strong><br>
        ${amount > 0 ? '+' : ''}$${Math.abs(amount).toFixed(2)}
    `;

    openModal('deleteTransactionModal');
}

function closeDeleteModal() {
    transactionToDelete = null;
    closeModal('deleteTransactionModal');
}

async function confirmDeleteTransaction(e) {
    e.preventDefault();
    if (!transactionToDelete) return;

    try {
        const res = await fetch(`/transactions/${transactionToDelete}`, {
            method: 'DELETE',
            credentials: 'include'
        });

        if (!res.ok) throw new Error();

        showMessage('Transaction deleted');
        closeDeleteModal();
        loadTransactions();

    } catch {
        showMessage('Failed to delete transaction', 'error');
    }
}

// ==================== UTIL ====================
function formatDate(d) {
    if (d === 'No date') return 'No Date';
    const date = new Date(d);
    return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
}

function escapeHtml(t) {
    const div = document.createElement('div');
    div.textContent = t;
    return div.innerHTML;
}

async function logout() {
    try {
        await fetch('/logout', {
            method: 'POST',
            credentials: 'include'
        });
    } finally {
        window.location.replace('/');
    }
}


window.logout = logout;