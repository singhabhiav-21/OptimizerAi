// ==================== CONFIGURATION ====================
const API_URL = 'http://localhost:8000';
let baseCurrency = 'SEK';
let TRANSACTION_CURRENCY = 'SEK';
let weeklyChart = null;
let selectedWeeks = 8;

// ==================== AUTH CHECK ====================
async function checkAuth() {
    try {
        const res = await fetch('/auth/status', {
            credentials: 'include'
        });

        // If explicitly unauthorized, redirect
        if (res.status === 401) {
            console.warn('🔒 Not authenticated (401), redirecting to login');
            sessionStorage.clear();
            localStorage.clear();
            window.location.replace('/');
            return false;
        }

        // If other error, don't redirect (network issues, etc)
        if (!res.ok) {
            console.error(`⚠️ Auth check failed: ${res.status}`);
            return false;
        }

        const data = await res.json();

        if (!data.authenticated || !data.user_id) {
            console.warn('🔒 Not authenticated (no session), redirecting');
            sessionStorage.clear();
            localStorage.clear();
            window.location.replace('/');
            return false;
        }

        // ✅ Authenticated
        console.log(`✅ Authenticated as user ${data.user_id}`);
        baseCurrency = sessionStorage.getItem('base_currency') || 'USD';
        return true;

    } catch (err) {
        console.error('❌ Auth check error:', err);
        // Network errors shouldn't trigger redirect
        // (might be temporary connection issue)
        return false;
    }
}
// ==================== UTILITY FUNCTIONS ====================
function showMessage(message, type = 'success') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${type === 'error' ? '' : ''}</span>
        <span class="toast-message">${message}</span>
        <span class="toast-close" onclick="this.parentElement.remove()">×</span>
    `;

    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
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


function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateStr) {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    if (date.toDateString() === today.toDateString()) return 'Today';
    if (date.toDateString() === yesterday.toDateString()) return 'Yesterday';

    return date.toLocaleDateString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric'
    });
}

function getCurrencySymbol(code) {
    const symbols = {
        'USD': '$', 'EUR': '€', 'GBP': '£', 'JPY': '¥', 'SEK': 'kr',
        'INR': '₹', 'AUD': 'A$', 'CAD': 'C$', 'NOK': 'kr', 'DKK': 'kr'
    };
    return symbols[code] || code;
}

function formatCurrency(amount, code) {
    const symbol = getCurrencySymbol(code);
    const formatted = parseFloat(amount || 0).toFixed(2);

    if (['SEK', 'NOK', 'DKK'].includes(code)) {
        return `${formatted} ${symbol}`;
    }
    return `${symbol}${formatted}`;
}

// ==================== CURRENCY SELECTOR ====================
function addCurrencySelector() {
    const header = document.querySelector('.header');
    if (!header || document.getElementById('currency-selector')) return;

    const html = `
        <div style="display: flex; align-items: center; gap: 15px;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <label style="font-size: 14px; color: #666; font-weight: 500;">
                    💱 Currency:
                </label>
                <select id="currency-selector" style="
                    padding: 8px 12px;
                    border: 2px solid #e5e7eb;
                    border-radius: 6px;
                    font-size: 14px;
                    cursor: pointer;
                    background: white;
                " onchange="changeCurrency(this.value)">
                    <option value="USD"> USD</option>
                    <option value="EUR"> EUR</option>
                    <option value="GBP"> GBP</option>
                    <option value="SEK"> SEK</option>
                    <option value="INR"> INR</option>
                    <option value="JPY"> JPY</option>
                    <option value="CAD"> CAD</option>
                    <option value="AUD"> AUD</option>
                </select>
            </div>
        </div>
    `;

    const existingBtn = header.querySelector('button');
    if (existingBtn) existingBtn.remove();
    header.insertAdjacentHTML('beforeend', html);

    const selector = document.getElementById('currency-selector');
    if (selector) selector.value = baseCurrency;
}

function changeCurrency(newCurrency) {
    baseCurrency = newCurrency;
    sessionStorage.setItem('base_currency', newCurrency);
    showMessage(`Currency changed to ${newCurrency}`, 'success');

    loadDashboard();}

// ==================== WEEK SELECTOR ====================
function addWeekSelector() {
    const chartSection = document.querySelector('.section');
    if (!chartSection) return;

    // Check if selector already exists
    if (document.getElementById('week-selector-container')) return;

    const html = `
        <div id="week-selector-container" style="
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 15px;
            padding: 15px;
            background: #f9fafb;
            border-radius: 8px;
            border: 1px solid #e5e7eb;
        ">
            <div style="display: flex; align-items: center; gap: 10px;">
                <label style="font-size: 14px; color: #374151; font-weight: 600;">
                    Time Period:
                </label>
                <select id="week-selector" style="
                    padding: 8px 16px;
                    border: 2px solid #e5e7eb;
                    border-radius: 6px;
                    font-size: 14px;
                    cursor: pointer;
                    background: white;
                    font-weight: 500;
                    min-width: 150px;
                " onchange="changeWeekPeriod(this.value)">
                    <option value="2">Last 2 Weeks</option>
                    <option value="4">Last 4 Weeks</option>
                    <option value="6">Last 6 Weeks</option>
                    <option value="8" selected>Last 8 Weeks</option>
                    <option value="10">Last 10 Weeks</option>
                    <option value="12">Last 12 Weeks</option>
                    <option value="16">Last 16 Weeks</option>
                    <option value="18">Last 18 Weeks</option>                        
                </select>
            </div>
            <div id="date-range-display" style="
                font-size: 13px;
                color: #6b7280;
                padding: 6px 12px;
                background: white;
                border-radius: 6px;
                font-weight: 500;
            ">Loading...</div>
        </div>
    `;

    // Insert before the white chart container
    const chartContainer = chartSection.querySelector('div[style*="background: white"]');
    if (chartContainer) {
        chartContainer.insertAdjacentHTML('beforebegin', html);
    }
}

function changeWeekPeriod(weeks) {
    selectedWeeks = parseInt(weeks);
    showMessage(`Showing last ${weeks} weeks`, 'success');
    loadWeeklyChart();
}

function updateDateRangeDisplay(startDate, endDate) {
    const display = document.getElementById('date-range-display');
    if (!display) return;

    try {
        // Parse dates more robustly - handle both Date objects and strings
        let start, end;

        if (typeof startDate === 'string') {
            start = new Date(startDate + 'T00:00:00'); // Add time to avoid timezone issues
        } else {
            start = new Date(startDate);
        }

        if (typeof endDate === 'string') {
            end = new Date(endDate + 'T00:00:00');
        } else {
            end = new Date(endDate);
        }

        // Check if dates are valid
        if (isNaN(start.getTime()) || isNaN(end.getTime())) {
            console.error('Invalid dates:', startDate, endDate);
            display.textContent = 'Date range unavailable';
            return;
        }

        const startStr = start.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        });
        const endStr = end.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        });

        display.textContent = `${startStr} → ${endStr}`;
        display.style.display = 'block'; // Make sure it's visible
    } catch (error) {
        console.error('Date parsing error:', error, 'Start:', startDate, 'End:', endDate);
        display.textContent = 'Date range unavailable';
    }
}


// ==================== CHART RENDERING ====================
function renderWeeklyChart(weeklyData) {
    const canvas = document.getElementById('weekly-chart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');

    // Destroy existing chart
    if (weeklyChart) {
        weeklyChart.destroy();
    }

    if (!weeklyData || weeklyData.length === 0) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.font = '16px Arial';
        ctx.fillStyle = '#666';
        ctx.textAlign = 'center';
        ctx.fillText('No transactions found for the selected period', canvas.width / 2, canvas.height / 2);
        return;
    }

    // Format labels
    const labels = weeklyData.map(d => {
        const date = new Date(d.date);

        // Check if date is valid
        if (isNaN(date.getTime())) {
            console.error('Invalid date:', d.date);
            return 'Invalid';
        }

        if (selectedWeeks <= 8) {
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        } else {
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: '2-digit' });
        }
    });

    const income = weeklyData.map(d => d.income);
    const expenses = weeklyData.map(d => d.expenses);

    // Calculate totals
    const totalIncome = income.reduce((a, b) => a + b, 0);
    const totalExpenses = expenses.reduce((a, b) => a + b, 0);
    const netAmount = totalIncome - totalExpenses;

    weeklyChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Income',
                    data: income,
                    backgroundColor: 'rgba(16, 185, 129, 0.2)',
                    borderColor: 'rgba(16, 185, 129, 1)',
                    borderWidth: 3,
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    pointBackgroundColor: 'rgba(16, 185, 129, 1)',
                    tension: 0.3,
                    fill: true
                },
                {
                    label: 'Expenses',
                    data: expenses,
                    backgroundColor: 'rgba(239, 68, 68, 0.2)',
                    borderColor: 'rgba(239, 68, 68, 1)',
                    borderWidth: 3,
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    pointBackgroundColor: 'rgba(239, 68, 68, 1)',
                    tension: 0.3,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        font: { size: 14, weight: 'bold' },
                        padding: 15
                    }
                },
                title: {
                    display: true,
                    text: [
                        `Last ${selectedWeeks} Weeks - Income vs Expenses`],
                    font: { size: 16, weight: 'bold' },
                    padding: 20,
                    color: '#1f2937'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.dataset.label || '';
                            const value = formatCurrency(context.parsed.y, baseCurrency);
                            return `${label}: ${value}`;
                        },
                        afterLabel: function(context) {
                            const income = context.chart.data.datasets[0].data[context.dataIndex];
                            const expenses = context.chart.data.datasets[1].data[context.dataIndex];
                            const net = income - expenses;
                            return `Net: ${formatCurrency(net, baseCurrency)}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return formatCurrency(value, baseCurrency);
                        }
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });

    // Update summary stats
    updateChartSummary(totalIncome, totalExpenses, netAmount);
}

function updateChartSummary(income, expenses, net) {
    const summaryDiv = document.getElementById('chart-summary');
    if (!summaryDiv) return;

    const netColor = net >= 0 ? '#10b981' : '#ef4444';

    summaryDiv.innerHTML = `
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-top: 20px;">
            <div style="background: #f0fdf4; padding: 15px; border-radius: 8px; border-left: 4px solid #10b981;">
                <div style="font-size: 12px; color: #166534; font-weight: 600; margin-bottom: 5px;">TOTAL INCOME</div>
                <div style="font-size: 20px; font-weight: 700; color: #10b981;">${formatCurrency(income, baseCurrency)}</div>
            </div>
            <div style="background: #fef2f2; padding: 15px; border-radius: 8px; border-left: 4px solid #ef4444;">
                <div style="font-size: 12px; color: #991b1b; font-weight: 600; margin-bottom: 5px;">TOTAL EXPENSES</div>
                <div style="font-size: 20px; font-weight: 700; color: #ef4444;">${formatCurrency(expenses, baseCurrency)}</div>
            </div>
            <div style="background: ${net >= 0 ? '#f0fdf4' : '#fef2f2'}; padding: 15px; border-radius: 8px; border-left: 4px solid ${netColor};">
                <div style="font-size: 12px; color: ${net >= 0 ? '#166534' : '#991b1b'}; font-weight: 600; margin-bottom: 5px;">NET AMOUNT</div>
                <div style="font-size: 20px; font-weight: 700; color: ${netColor};">${formatCurrency(net, baseCurrency)}</div>
            </div>
        </div>
    `;
}

// ==================== LOAD DASHBOARD ====================
async function loadDashboard() {

    console.log(`Loading dashboard in ${baseCurrency}...`);

    try {
         const response = await fetch(
        `/api/currency/dashboard?base_currency=${baseCurrency}`,
        { credentials: 'include' });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        if (data.success) {
            displayStats(data);
            displayRecentTransactions(data);
            showConversionInfo(data);
            await loadWeeklyChart();
        }

    } catch (error) {
        console.error('Error:', error);
        showMessage('Failed to load dashboard', 'error');
    }
}

async function loadWeeklyChart() {
    try {
        const response = await fetch(
            `/api/weekly-chart?weeks=${selectedWeeks}&base_currency=${baseCurrency}`, {credentials :
                    "include"});

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        console.log('Weekly chart data:', data); // Debug log

        if (data.success && data.weekly_data) {
            renderWeeklyChart(data.weekly_data);

            if (data.summary) {
                updateChartSummary(
                    data.summary.total_income,
                    data.summary.total_expenses,
                    data.summary.total_net
                );
            }

            // Update date range if provided
            if (data.date_range?.start && data.date_range?.end) {
                updateDateRangeDisplay(data.date_range.start, data.date_range.end);
            }
        } else {
            renderWeeklyChart(null);
        }

    } catch (error) {
        console.error('Error loading weekly chart:', error);
        showMessage('Failed to load chart data', 'error');
    }
}

// ==================== DISPLAY DATA ====================
function displayStats(data) {
    const stats = data.statistics;
    const currency = data.base_currency;

    updateCard('total-balance', formatCurrency(stats.total_balance, currency), '#10b981');
    updateCard('total-accounts', stats.account_count.toString(), '#3b82f6');
}

function updateCard(id, value, color) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = value;
        element.style.color = color;
    }
}

function displayRecentTransactions(data) {
    const container = document.getElementById('recent-transactions');
    if (!container) return;

    const transactions = data.recent_transactions || [];
    const currency = data.base_currency;

    if (transactions.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 40px; color: #666;">
                <p style="font-size: 16px; margin-bottom: 10px;">No transactions yet</p>              
                <a href="transactions.html" class="btn btn-primary" 
                   style="margin-top: 15px; display: inline-block;">
                    Add Transaction
                </a>
            </div>
        `;
        return;
    }

    const html = transactions.map(t => {
        const amount = parseFloat(t.amount || 0);
        const isPositive = amount > 0;
        const color = isPositive ? '#10b981' : '#ef4444';
        const sign = isPositive ? '+' : '';

        return `
            <div style="
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 15px;
                background: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                margin-bottom: 10px;
                transition: transform 0.2s, box-shadow 0.2s;
            " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 6px rgba(0,0,0,0.1)';" 
               onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='none';">
                <div>
                    <div style="font-weight: 600; color: #1a202c; margin-bottom: 4px;">
                        ${escapeHtml(t.name)}
                    </div>
                    <div style="font-size: 13px; color: #666;">
                        ${formatDate(t.transaction_date)}
                    </div>
                    ${t.description ? `
                        <div style="font-size: 12px; color: #999; margin-top: 4px;">
                            ${escapeHtml(t.description)}
                        </div>
                    ` : ''}
                </div>
                <div style="font-size: 18px; font-weight: 700; color: ${color};">
                    ${sign}${formatCurrency(Math.abs(amount), TRANSACTION_CURRENCY)}
                </div>
            </div>
        `;
    }).join('');

    container.innerHTML = html;
}

function showConversionInfo(data) {
    const accounts = data.accounts || [];
    const currencies = [...new Set(accounts.map(a => a.original_currency))];

    if (currencies.length > 1) {
        const section = document.querySelector('.section-header');
        if (section && !document.getElementById('currency-info')) {
            section.insertAdjacentHTML('beforeend', `
                <div id="currency-info" style="font-size: 12px; color: #666; margin-top: 5px;">
                    💱 Converted from: ${currencies.join(', ')}
                </div>
            `);
        }
    }
}

// ==================== INITIALIZATION ====================
document.addEventListener('DOMContentLoaded', async function() {
    console.log('=== DASHBOARD INITIALIZED ===');

    // ✅ Single auth check at startup
    const authenticated = await checkAuth();
    if (!authenticated) {
        console.warn('Auth failed, stopping initialization');
        return; // Stop here, let the redirect happen
    }



    // ✅ Only initialize if authenticated
    if (typeof Chart === 'undefined') {
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js';
        script.onload = initializeDashboard;
        document.head.appendChild(script);
    } else {
        initializeDashboard();
    }
    const userRes = await fetch('/me', { credentials: 'include' });
        if (userRes.ok) {
            const user = await userRes.json();
            document.getElementById('user-btn').textContent = user.email;
        }
});

function initializeDashboard() {
    console.log('✅ Starting dashboard initialization...');
    addCurrencySelector();
    addWeekSelector();
    loadDashboard();

    // ✅ Refresh every minute
    setInterval(loadDashboard, 60000);
}

// ==================== EXPORTS ====================
window.logout = logout;
window.changeCurrency = changeCurrency;
window.changeWeekPeriod = changeWeekPeriod;

console.log('✅ Dashboard loaded');