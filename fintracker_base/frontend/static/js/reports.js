
// -----------------------------
// Global state (NON-AUTH)
// -----------------------------
let reportToDelete = null;

// -----------------------------
// Init on page load
// -----------------------------
document.addEventListener('DOMContentLoaded', async () => {
    try {
        const res = await fetch('/auth/status', {
            credentials: 'include'
        });

        if (!res.ok) throw new Error('Auth failed');

        const data = await res.json();

        if (!data.authenticated) {
            window.location.href = '/';
            return;
        }
        initPage();

        const userRes = await fetch('/me', { credentials: 'include' });
        if (userRes.ok) {
            const user = await userRes.json();
            document.getElementById('user-btn').textContent = user.email;
        }

    } catch (err) {
        window.location.href = '/';
    }
});

// -----------------------------
// Page setup
// -----------------------------
function initPage() {
    const monthInput = document.getElementById('reportMonth');
    const today = new Date();
    const maxMonth = today.toISOString().substring(0, 7);

    monthInput.max = maxMonth;
    monthInput.value = maxMonth;

    loadReports();

    document
        .getElementById('generateReportForm')
        .addEventListener('submit', handleGenerateReport);
}

// -----------------------------
// Load reports (SERVER decides user)
// -----------------------------
function displayReportsAudit(reports) {
    const tbody = document.getElementById('reportsTableBody');
    tbody.innerHTML = '';

    reports.forEach((report, index) => {
        const row = document.createElement('tr');

        if (index % 2 === 0) {
            row.style.background = '#ffffff';
        }

        row.innerHTML = `                                
            <td>
                <span class="period-badge">${formatMonth(report.report_month)}</span>
            </td>
            <td>
                <span class="spending-amount">SEK ${formatNumber(report.total_spending)}</span>
            </td>
            <td>
                <span class="transaction-count">
                     ${report.transaction_count}
                </span>
            </td>
            <td style="color: #6b7280; font-size: 13px;">
                ${formatDateFull(report.generated_at)}
            </td>          
            <td>
                <div class="action-btns">
                    <button class="btn-action btn-download" onclick="downloadReport('${report.report_month}')">
                        Download
                    </button>                   
                    <button class="btn-action btn-delete" onclick="showDeleteModal(${report.report_id})">
                        Delete
                    </button>
                </div>
            </td>
        `;

        tbody.appendChild(row);
    });
}


function updateStatistics(reports) {
    const totalReports = reports.length;
    const totalSpending = reports.reduce((sum, r) => sum + parseFloat(r.total_spending || 0), 0);
    const totalTransactions = reports.reduce((sum, r) => sum + parseInt(r.transaction_count || 0), 0);
    const avgTransactions = totalReports > 0 ? Math.round(totalTransactions / totalReports) : 0;
    const latestMonth = totalReports > 0 ? formatMonth(reports[0].report_month) : '-';

    document.getElementById('totalReports').textContent = totalReports;
    document.getElementById('totalSpending').textContent = `SEK ${formatNumber(totalSpending)}`;
    document.getElementById('latestMonth').textContent = latestMonth;
    document.getElementById('avgTransactions').textContent = avgTransactions;
}


async function loadReports() {
    const loadingState = document.getElementById('loadingState');
    const emptyState = document.getElementById('emptyState');
    const reportsTable = document.getElementById('reportsTable');

    loadingState.style.display = 'block';
    emptyState.style.display = 'none';
    reportsTable.style.display = 'none';

    try {
        console.log('🔍 Fetching reports...');

        const response = await fetch('/api/reports', {
            credentials: 'include'
        });

        console.log('📥 Response status:', response.status);

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            console.error('❌ Error response:', errorData);
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }

        const data = await response.json();
        console.log('✅ Reports loaded:', data);

        loadingState.style.display = 'none';

        if (!data.reports || data.reports.length === 0) {
            emptyState.style.display = 'block';
            updateStatistics([]);
            return;
        }

        displayReportsAudit(data.reports);
        updateStatistics(data.reports);
        reportsTable.style.display = 'block';

    } catch (err) {
        console.error('❌ Load reports error:', err);
        loadingState.style.display = 'none';
        showMessage(`Failed to load reports: ${err.message}`, 'error');
    }
}

// -----------------------------
// Generate report
// -----------------------------
async function handleGenerateReport(e) {
    e.preventDefault();

    const month = document.getElementById('reportMonth').value;
    if (!month) {
        showMessage('Please select a month', 'error');
        return;
    }

    toggleGenerateBtn(true);

    try {
        const response = await fetch('/api/reports/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ month })
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.detail);

        showMessage(`✓ Report generated for ${formatMonth(month)}. Click Download to view it.`, 'success');
        await loadReports()

    } catch (err) {
        showMessage(err.message || 'Failed to generate report', 'error');
    } finally {
        toggleGenerateBtn(false);
    }
}

// -----------------------------
// Download report
// -----------------------------
async function downloadReport(month) {
    try {
        const response = await fetch(`/api/reports/download?month=${month}`, {
            credentials: 'include'
        });

        if (!response.ok) throw new Error();

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);

        const a = document.createElement('a');
        a.href = url;
        a.download = `financial_report_${month}.pdf`;
        document.body.appendChild(a);
        a.click();

        URL.revokeObjectURL(url);
        a.remove();

    } catch {
        showMessage('Failed to download report', 'error');
    }
}

// -----------------------------
// Delete report
// -----------------------------
async function deleteReport(reportId) {
    try {
        const response = await fetch(`/api/reports/${reportId}`, {
            method: 'DELETE',
            credentials: 'include'
        });

        if (!response.ok) throw new Error();

        showMessage('✓ Report deleted', 'success');
        closeDeleteModal();
        setTimeout(loadReports, 500);

    } catch {
        showMessage('Failed to delete report', 'error');
    }
}

// -----------------------------
// UI helpers
// -----------------------------
function toggleGenerateBtn(loading) {
    const btn = document.getElementById('generateBtn');
    btn.disabled = loading;
    btn.querySelector('.btn-text').style.display = loading ? 'none' : 'inline';
    btn.querySelector('.loader').style.display = loading ? 'block' : 'none';
}

function showDeleteModal(id) {
    reportToDelete = id;
    document.getElementById('deleteModal').classList.add('active');
    document.getElementById('confirmDeleteBtn').onclick = () => deleteReport(id);
}

function closeDeleteModal() {
    reportToDelete = null;
    document.getElementById('deleteModal').classList.remove('active');
}

function showMessage(text, type) {
    const el = document.getElementById('generateMessage');
    el.textContent = text;
    el.className = `message ${type}`;
    el.style.display = 'block';
    setTimeout(() => el.style.display = 'none', 4000);
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

// -----------------------------
// Formatting helpers
// -----------------------------
function formatMonth(month) {
    const [y, m] = month.split('-');
    return new Date(y, m - 1).toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
}

function formatDateFull(d) {
     if (!d) return '-';

    const date = new Date(d);
    if (isNaN(date)) return '-';

    const yyyy = date.getFullYear();
    const mm = String(date.getMonth() + 1).padStart(2, '0');
    const dd = String(date.getDate()).padStart(2, '0');
    const hh = String(date.getHours()).padStart(2, '0');
    const min = String(date.getMinutes()).padStart(2, '0');

    return `${yyyy}-${mm}-${dd} ${hh}:${min}`;
}

function formatNumber(n) {
    return Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2 });
}

// -----------------------------
// Modal click outside
// -----------------------------
window.onclick = e => {
    if (e.target.classList.contains('modal-overlay')) closeDeleteModal();
};