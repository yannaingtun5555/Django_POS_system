// API Base URL - adjust based on your Django server
const API_BASE = '/api/dashboard';  // Use relative paths for same-origin
// Utility Functions
const APP_CONFIG = window.APP_CONFIG || {};
const CURRENCY_PREFIX = APP_CONFIG.currencyPrefix || '$';
const CURRENCY_POSTFIX = APP_CONFIG.currencyPostfix || '';

function formatCurrency(amount) {
    const value = Number.parseFloat(amount || 0) || 0;
    return `${CURRENCY_PREFIX}${value.toFixed(2)}${CURRENCY_POSTFIX}`;
}

function formatDate(date) {
    return new Intl.DateTimeFormat('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
    }).format(date);
}

function setCurrentDate() {
    const today = new Date();
    document.getElementById('currentDate').textContent = `Today: ${formatDate(today)}`;
}

// Fetch Total Sales, Profit, and Transactions
async function fetchSalesProfitTransaction() {
    try {
        const response = await fetch(`${API_BASE}/totalsale_profit_transcation/`);
        if (!response.ok) throw new Error('Failed to fetch sales data');
        const data = await response.json();
        const totalSales = Number.parseFloat(data.total_sales ?? data.total_sale ?? 0) || 0;
        const totalProfit = Number.parseFloat(data.total_profit ?? data.profit ?? 0) || 0;
        const totalTransactions = data.total_transactions ?? data.transcation ?? data.transaction ?? 0;

        // Update Total Sales
        document.getElementById('totalSales').textContent = formatCurrency(totalSales);
        const salesChangeEl = document.getElementById('salesChange');
        const salesChange = data.sales_change || 0;
        salesChangeEl.textContent = `${salesChange >= 0 ? '+' : ''}${salesChange}%`;
        salesChangeEl.className = `stat-change ${salesChange >= 0 ? 'positive' : 'negative'}`;

        // Update Profit
        document.getElementById('totalProfit').textContent = formatCurrency(totalProfit);
        const profitChangeEl = document.getElementById('profitChange');
        const profitChange = data.profit_change || 0;
        profitChangeEl.textContent = `${profitChange >= 0 ? '+' : ''}${profitChange}%`;
        profitChangeEl.className = `stat-change ${profitChange >= 0 ? 'positive' : 'negative'}`;

        // Update Transactions
        document.getElementById('totalTransactions').textContent = totalTransactions;
        const transactionChangeEl = document.getElementById('transactionChange');
        const transactionChange = data.transaction_change || 0;
        transactionChangeEl.textContent = `${transactionChange >= 0 ? '+' : ''}${transactionChange}%`;
        transactionChangeEl.className = `stat-change ${transactionChange >= 0 ? 'positive' : 'negative'}`;

    } catch (error) {
        console.error('Error fetching sales/profit/transaction data:', error);
        // Set fallback demo data
        document.getElementById('totalSales').textContent = formatCurrency(4289);
        document.getElementById('salesChange').textContent = '+12%';
        document.getElementById('totalProfit').textContent = formatCurrency(1142.5);
        document.getElementById('profitChange').textContent = '+5%';
        document.getElementById('totalTransactions').textContent = '142';
        document.getElementById('transactionChange').textContent = '-2%';
    }
}

// Fetch Rolling Daily Sales for Chart
async function fetchDailySales() {
    try {
        const response = await fetch(`${API_BASE}/rollingdailysale/`);
        if (!response.ok) throw new Error('Failed to fetch daily sales');
        const data = await response.json();
        const salesArray = Array.isArray(data) ? data : (data.sales || []);
        renderChart(salesArray);
    } catch (error) {
        console.error('Error fetching daily sales:', error);
        renderChart([]);
    }
}

function renderChart(salesData) {
    const chartContainer = document.getElementById('salesChart');
    
    if (salesData.length === 0) {
        chartContainer.innerHTML = '<div class="loading">No sales data available</div>';
        return;
    }

    const normalizedData = salesData.map(item => {
        const amount = Number.parseFloat(item.amount ?? item.total ?? 0) || 0;
        const labelSource = item.time ?? item.date;
        const label = formatChartLabel(labelSource);
        return { amount, label };
    });
    const maxAmount = Math.max(...normalizedData.map(item => item.amount), 0);
    
    chartContainer.innerHTML = normalizedData.map(item => {
        const heightPercent = maxAmount > 0 ? (item.amount / maxAmount) * 100 : 0;
        return `
            <div class="chart-bar-wrapper">
                <div class="chart-bar" style="height: ${heightPercent}%;" title="${formatCurrency(item.amount)}"></div>
                <span class="chart-label">${item.label}</span>
            </div>
        `;
    }).join('');
}

// Fetch Low Stock Items
async function fetchLowStock() {
    try {
        const response = await fetch(`${API_BASE}/lowstock/`);
        if (!response.ok) throw new Error('Failed to fetch low stock');
        const data = await response.json();
        const items = Array.isArray(data) ? data : (data.items || []);
        renderLowStock(items);
    } catch (error) {
        console.error('Error fetching low stock:', error);
        renderLowStock([]);
    }
}

function renderLowStock(items) {
    const container = document.getElementById('lowStockList');
    
    if (items.length === 0) {
        container.innerHTML = '<div class="loading">All items are well stocked!</div>';
        return;
    }

    container.innerHTML = items.map(item => `
        <div class="alert-item">
            <div class="alert-item-info">
                <h4>${item.name}</h4>
            </div>
            <div class="alert-item-count">
                <div class="count">${item.stock_quantity}</div>
                <div class="label">LEFT</div>
            </div>
        </div>
    `).join('');
}

// Fetch Top Selling Products
async function fetchTopSellings() {
    try {
        const response = await fetch(`${API_BASE}/topsellings/`);
        if (!response.ok) throw new Error('Failed to fetch top sellings');
        const data = await response.json();
        const products = Array.isArray(data) ? data : (data.products || []);
        renderTopProducts(products);
    } catch (error) {
        console.error('Error fetching top products:', error);
        renderTopProducts([]);
    }
}

function renderTopProducts(products) {
    const tbody = document.getElementById('topProductsBody');
    
    if (products.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" style="text-align: center; color: #94a3b8;">No sales data</td></tr>';
        return;
    }

    tbody.innerHTML = products.map(product => `
        <tr>
            <td>${product.name || product.product__name || 'Unknown Product'}</td>
            <td>${product.qty_sold ?? product.total_quantity ?? 0}</td>
            <td>${formatCurrency(Number.parseFloat(product.revenue ?? 0) || 0)}</td>
        </tr>
    `).join('');
}

// Fetch Recent Activity
async function fetchRecentActivity() {
    try {
        const response = await fetch(`${API_BASE}/recentactivity/`);
        if (!response.ok) throw new Error('Failed to fetch recent activity');
        const data = await response.json();
        const activities = Array.isArray(data) ? data : (data.activities || []);
        renderRecentActivity(activities);
    } catch (error) {
        console.error('Error fetching recent activity:', error);
        renderRecentActivity([]);
    }
}

function renderRecentActivity(activities) {
    const activityContainer = document.getElementById('recentActivityList'); // adjust selector
    if (!activityContainer) return;

    if (!activities || activities.length === 0) {
        activityContainer.innerHTML = '<div class="no-activity">No recent activity</div>';
        return;
    }

    const html = activities
        .filter(activity => activity && typeof activity === 'object')
        .map(rawActivity => {
            const normalizedActivity = normalizeRecentActivity(rawActivity);
            const timeAgo = formatTimeAgo(normalizedActivity.activityDate);

            return `
                <div class="activity-card ${normalizedActivity.typeClass}">
                    <div class="activity-icon" aria-hidden="true">${normalizedActivity.icon}</div>
                    <div class="activity-content">
                        <div class="activity-topline">
                            <span class="activity-type ${normalizedActivity.typeClass}">${normalizedActivity.activityType}</span>
                            <span class="activity-date">${timeAgo}</span>
                        </div>
                        <div class="activity-description">${normalizedActivity.description}</div>
                        <div class="activity-meta">
                            <span class="activity-reference">#${normalizedActivity.reference}</span>
                            <span class="activity-amount">${formatCurrency(normalizedActivity.amount)}</span>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

    activityContainer.innerHTML = html || '<div class="no-activity">No recent activity</div>';
}

function normalizeRecentActivity(rawActivity) {
    // Your API gives plain numbers, no nested objects
    const amount = rawActivity.amount ?? rawActivity.total_cost ?? 0;
    const activityId = rawActivity.activity_id;
    const activityType = (rawActivity.activity_type || 'UNKNOWN').toUpperCase();
    const activityDate = rawActivity.activity_date;
    const supplierName = rawActivity.supplier_name || 'supplier';
    const reference = activityId ?? 'N/A';
    let icon = '•';

    let description = '';
    if (activityType === 'SALE') {
        description = `Sale #${activityId} - ${formatCurrency(amount)}`;
        icon = 'S';
    } else if (activityType === 'PURCHASE') {
        description = `Purchase from ${supplierName} - ${formatCurrency(amount)}`;
        icon = 'P';
    } else {
        description = `Activity #${activityId} - ${formatCurrency(amount)}`;
    }

    return {
        activityType,
        activityDate,
        description,
        amount: Number.parseFloat(amount) || 0,
        icon,
        reference,
        typeClass: activityType.toLowerCase(),
    };
}
// Helper to format date
function formatTimeAgo(dateString) {
    if (!dateString) return 'Unknown date';

    const date = new Date(dateString);
    if (Number.isNaN(date.getTime())) return 'Unknown date';

    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} min ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
}

function formatChartLabel(dateValue) {
    if (!dateValue) return '';

    const date = new Date(dateValue);
    if (Number.isNaN(date.getTime())) return String(dateValue);

    return new Intl.DateTimeFormat('en-US', {
        month: 'short',
        day: 'numeric'
    }).format(date);
}

// Reorder button handler
function handleReorder() {
    alert('Reorder functionality - Navigate to purchase orders');
}

// Initialize Dashboard
function initDashboard() {
    setCurrentDate();
    fetchSalesProfitTransaction();
    fetchDailySales();
    fetchLowStock();
    fetchTopSellings();
    fetchRecentActivity();
}

// Auto-refresh every 5 minutes
setInterval(initDashboard, 300000);

// Run on page load
document.addEventListener('DOMContentLoaded', initDashboard);
