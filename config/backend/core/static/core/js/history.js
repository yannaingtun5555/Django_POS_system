const API_BASE = '/api'; // Change this to your API base URL
const APP_CONFIG = window.APP_CONFIG || {};
const CURRENCY_PREFIX = APP_CONFIG.currencyPrefix || '$';
const CURRENCY_POSTFIX = APP_CONFIG.currencyPostfix || '';

function formatCurrency(amount) {
    const value = Number.parseFloat(amount || 0) || 0;
    return `${CURRENCY_PREFIX}${value.toFixed(2)}${CURRENCY_POSTFIX}`;
}

// Fetch and display activities
async function loadActivities() {
    const loading = document.getElementById('loading');
    const errorContainer = document.getElementById('errorContainer');
    const table = document.getElementById('activityTable');
    const emptyState = document.getElementById('emptyState');
    const tableBody = document.getElementById('tableBody');

    loading.style.display = 'block';
    table.style.display = 'none';
    emptyState.style.display = 'none';
    errorContainer.innerHTML = '';

    try {
        const response = await fetch(`${API_BASE}/dashboard/recentactivity/`);
        if (!response.ok) throw new Error('Failed to fetch activities');

        const data = await response.json();
        loading.style.display = 'none';

        if (data.length === 0) {
            emptyState.style.display = 'block';
            return;
        }

        tableBody.innerHTML = '';
        data.forEach(activity => {
            const row = document.createElement('tr');
            const formattedDate = new Date(activity.activity_date).toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });

            const badgeClass = activity.activity_type === 'SALE' ? 'badge-sale' : 'badge-purchase';
            const badgeText = activity.activity_type === 'SALE' ? 'SALE' : 'PURCHASE';

            row.innerHTML = `
                <td><span class="activity-badge ${badgeClass}">${badgeText}</span></td>
                <td>${activity.activity_id}</td>
                <td>${formattedDate}</td>
                <td>${formatCurrency(activity.amount)}</td>
                <td>${activity.user_id}</td>
            `;

            row.onclick = () => viewDetails(activity);
            tableBody.appendChild(row);
        });

        table.style.display = 'table';
    } catch (error) {
        loading.style.display = 'none';
        errorContainer.innerHTML = `<div class="error-message">Error loading activities: ${error.message}</div>`;
    }
}

// View activity details
async function viewDetails(activity) {
    const modal = document.getElementById('detailModal');
    const modalBody = document.getElementById('modalBody');
    const modalTitle = document.getElementById('modalTitle');

    try {
        const accessToken = localStorage.getItem("access");
        if (activity.activity_type === 'SALE') {
            const response = await fetch(`${API_BASE}/sales/detail/${activity.activity_id}/`,{
                method: 'GET',
                headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${accessToken}`,
            }
            });
            if (!response.ok) throw new Error('Failed to fetch sale details');
            const details = await response.json();
            displaySaleVoucher(details, modalTitle, modalBody);
        } else {
            const response = await fetch(`${API_BASE}/purchase/detail/${activity.activity_id}/`,{
                method: 'GET',
                headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${accessToken}`,
                }
            });
            if (!response.ok) throw new Error('Failed to fetch purchase details');
            const details = await response.json();
            displayPurchaseVoucher(details, modalTitle, modalBody);
        }
        modal.classList.add('show');
    } catch (error) {
        alert('Error loading details: ' + error.message);
    }
}

// Display sale voucher
function displaySaleVoucher(sale, titleEl, bodyEl) {
    titleEl.textContent = `Sale Details - ${sale.trans_id}`;

    let itemsHTML = '';
    if (sale.items && Array.isArray(sale.items)) {
        itemsHTML = `
            <div class="voucher-section">
                <div class="voucher-section-title">Items</div>
                <table class="items-table">
                    <thead>
                        <tr>
                            <th>Product</th>
                            <th>Qty</th>
                            <th>Price</th>
                            <th>Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${sale.items.map(item => `
                            <tr>
                                <td>${item.product_name || 'N/A'}</td>
                                <td>${item.quantity || 0}</td>
                                <td>${formatCurrency(item.unit_price)}</td>
                                <td>${formatCurrency(item.line_total)}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }

    bodyEl.innerHTML = `
        <div class="voucher-section">
            <div class="voucher-grid">
                <div class="voucher-item">
                    <div class="voucher-item-label">Transaction ID</div>
                    <div class="voucher-item-value">${sale.trans_id}</div>
                </div>
                <div class="voucher-item">
                    <div class="voucher-item-label">User ID</div>
                    <div class="voucher-item-value">${sale.user_id}</div>
                </div>
                <div class="voucher-item">
                    <div class="voucher-item-label">Transaction Date</div>
                    <div class="voucher-item-value">${new Date(sale.trans_date).toLocaleDateString()}</div>
                </div>
                <div class="voucher-item">
                    <div class="voucher-item-label">Payment Method</div>
                    <div class="voucher-item-value">${sale.payment_method || 'N/A'}</div>
                </div>
                <div class="voucher-item">
                    <div class="voucher-item-label">Amount</div>
                    <div class="voucher-item-value">${formatCurrency(sale.total_amount)}</div>
                </div>
                <div class="voucher-item">
                    <div class="voucher-item-label">Payment</div>
                    <div class="voucher-item-value">${formatCurrency(sale.payment)}</div>
                </div>
                <div class="voucher-item">
                    <div class="voucher-item-label">Change</div>
                    <div class="voucher-item-value">${formatCurrency(sale.change)}</div>
                </div>
                <div class="voucher-item">
                    <div class="voucher-item-label">Status</div>
                    <div class="voucher-item-value">${sale.status || 'N/A'}</div>
                </div>
            </div>
        </div>

        ${itemsHTML}

        <div class="divider"></div>

        <div class="voucher-section">
            <div class="voucher-grid">
                <div class="voucher-item">
                    <div class="voucher-item-label">Created At</div>
                    <div class="voucher-item-value">${new Date(sale.created_at).toLocaleString()}</div>
                </div>
            </div>
        </div>
    `;
}

// Display purchase voucher
function displayPurchaseVoucher(purchase, titleEl, bodyEl) {
    titleEl.textContent = `Purchase Details - ${purchase.purchase_id}`;

    let itemsHTML = '';
    if (purchase.items && Array.isArray(purchase.items)) {
        itemsHTML = `
            <div class="voucher-section">
                <div class="voucher-section-title">Items</div>
                <table class="items-table">
                    <thead>
                        <tr>
                            <th>Product</th>
                            <th>Qty</th>
                            <th>Cost</th>
                            <th>Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${purchase.items.map(item => `
                            <tr>
                                <td>${item.product_name || 'N/A'}</td>
                                <td>${item.quantity || 0}</td>
                                <td>${formatCurrency(item.unit_cost)}</td>
                                <td>${formatCurrency(item.line_total)}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }

    bodyEl.innerHTML = `
        <div class="voucher-section">
            <div class="voucher-grid">
                <div class="voucher-item">
                    <div class="voucher-item-label">Purchase ID</div>
                    <div class="voucher-item-value">${purchase.purchase_id}</div>
                </div>
                <div class="voucher-item">
                    <div class="voucher-item-label">User ID</div>
                    <div class="voucher-item-value">${purchase.user_id}</div>
                </div>
                <div class="voucher-item">
                    <div class="voucher-item-label">Purchase Date</div>
                    <div class="voucher-item-value">${new Date(purchase.purchase_date).toLocaleDateString()}</div>
                </div>
                <div class="voucher-item">
                    <div class="voucher-item-label">Supplier Name</div>
                    <div class="voucher-item-value">${purchase.supplier_name || 'N/A'}</div>
                </div>
                <div class="voucher-item">
                    <div class="voucher-item-label">Payment Method</div>
                    <div class="voucher-item-value">${purchase.payment_method || 'N/A'}</div>
                </div>
                <div class="voucher-item">
                    <div class="voucher-item-label">Payment</div>
                    <div class="voucher-item-value">${formatCurrency(purchase.payment)}</div>
                </div>
                <div class="voucher-item">
                    <div class="voucher-item-label">Total Cost</div>
                    <div class="voucher-item-value">${formatCurrency(purchase.total_cost)}</div>
                </div>
                <div class="voucher-item">
                    <div class="voucher-item-label">Status</div>
                    <div class="voucher-item-value">${purchase.status || 'N/A'}</div>
                </div>
            </div>
        </div>

        ${itemsHTML}

        <div class="divider"></div>

        <div class="voucher-section">
            <div class="voucher-grid">
                <div class="voucher-item">
                    <div class="voucher-item-label">Created At</div>
                    <div class="voucher-item-value">${new Date(purchase.created_at).toLocaleString()}</div>
                </div>
            </div>
        </div>
    `;
}

// Close modal
function closeModal() {
    const modal = document.getElementById('detailModal');
    modal.classList.remove('show');
}

// Close modal when clicking outside
document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('detailModal');
    
    modal.addEventListener('click', function(event) {
        if (event.target === modal) {
            closeModal();
        }
    });

    // Search functionality
    const searchBox = document.getElementById('searchBox');
    searchBox.addEventListener('keyup', function() {
        const searchTerm = this.value.toLowerCase();
        const tableBody = document.getElementById('tableBody');
        const rows = tableBody.querySelectorAll('tr');

        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(searchTerm) ? '' : 'none';
        });
    });

    // Load activities on page load
    loadActivities();
});
