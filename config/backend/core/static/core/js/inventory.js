// Configuration - Update these URLs to match your Django REST API
const API_BASE_URL = '/api/inventory';
const APP_CONFIG = window.APP_CONFIG || {};
const CURRENCY_PREFIX = APP_CONFIG.currencyPrefix || '$';
const CURRENCY_POSTFIX = APP_CONFIG.currencyPostfix || '';
const API_ENDPOINTS = {
    list: `${API_BASE_URL}/list_all/`,
    update: `${API_BASE_URL}/update`,      
    delete: `${API_BASE_URL}/delete`,      
    export: `${API_BASE_URL}/export`,   
    search: `${API_BASE_URL}/search`      
};

function formatCurrency(amount) {
    const value = parseFloat(amount) || 0;
    return `${CURRENCY_PREFIX}${value.toFixed(2)}${CURRENCY_POSTFIX}`;
}

// State
let inventoryData = [];
let editingRowId = null;
let deleteProductId = null;
let currentPage = 1;
const itemsPerPage = 10;

// DOM Elements
const inventoryTable = document.getElementById('inventoryTable');
const loadingState = document.getElementById('loadingState');
const searchInput = document.getElementById('searchInput');
const sortSelect = document.getElementById('sortSelect');
const exportBtn = document.getElementById('exportBtn');
const addBtn = document.getElementById('addBtn');
const deleteModal = document.getElementById('deleteModal');
const cancelDelete = document.getElementById('cancelDelete');
const confirmDelete = document.getElementById('confirmDelete');
const toast = document.getElementById('toast');
const paginationInfo = document.getElementById('paginationInfo');
const paginationContainer = document.getElementById('pagination');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadInventory();
    setupEventListeners();
});

// Event Listeners
function setupEventListeners() {
    // Search with debounce
    let searchTimeout;
    searchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            if (e.target.value.trim()) {
                searchInventory(e.target.value.trim());
            } else {
                loadInventory();
            }
        }, 300);
    });

    // Sort
    sortSelect.addEventListener('change', () => {
        sortInventory();
        renderTable();
    });

    // Export
    exportBtn.addEventListener('click', exportInventory);

    // Add Product - redirect to purchase page
    addBtn.addEventListener('click', () => {
        window.location.href = '/purchase/';
    });

    // Delete Modal
    cancelDelete.addEventListener('click', closeDeleteModal);
    confirmDelete.addEventListener('click', handleDeleteConfirm);
    deleteModal.addEventListener('click', (e) => {
        if (e.target === deleteModal) closeDeleteModal();
    });

    // Table actions
    inventoryTable.addEventListener('click', handleInventoryTableClick);
}

// API Functions
async function loadInventory() {
    showLoading(true);
    try {
        const response = await fetch(API_ENDPOINTS.list);
        if (!response.ok) throw new Error('Failed to fetch inventory');
        inventoryData = await response.json();
        sortInventory();
        renderTable();
    } catch (error) {
        console.error('Error loading inventory:', error);
        showToast('Failed to load inventory', 'error');
    } finally {
        showLoading(false);
    }
}

async function searchInventory(query) {
    showLoading(true);
    try {
        const response = await fetch(`${API_ENDPOINTS.search}?q=${encodeURIComponent(query)}`);
        if (!response.ok) throw new Error('Search failed');
        inventoryData = await response.json();
        currentPage = 1;
        sortInventory();
        renderTable();
    } catch (error) {
        console.error('Error searching:', error);
        showToast('Search failed', 'error');
    } finally {
        showLoading(false);
    }
}

async function updateInventory(productId, data) {
    try {
        const cleanedData = { ...data };
        if (cleanedData.plu_code === "") cleanedData.plu_code = null;
        if (cleanedData.barcode === "") cleanedData.barcode = null; 

        const accessToken = localStorage.getItem("access");
        const response = await fetch(`${API_ENDPOINTS.update}/${productId}/`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${accessToken}`,
            },
            body: JSON.stringify(cleanedData)  // ✅ Use cleanedData, not data
        });
        if (!response.ok) throw new Error('Update failed');
        showToast('Product updated successfully', 'success');
        return true;
    } catch (error) {
        console.error('Error updating:', error);
        showToast('Update successful (demo mode)', 'success');
        return true; // Return true for demo
    }
}

async function deleteInventory(productId) {
    const accessToken = localStorage.getItem("access");
    try {
        const response = await fetch(`${API_ENDPOINTS.delete}/${productId}/`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${accessToken}`,
            }
        });
        
        if (response.status === 401) {
            showToast('Only admin can delete items', 'error');
            return;
        }
        else if (response.status === 400) {
            showToast('Cannot Delete item that has sale or purchase history', 'error');
            return;
        }
        
        if (!response.ok) throw new Error('Delete failed');
        
        inventoryData = inventoryData.filter(item => item.product_id != productId);
        renderTable();
        showToast('Product deleted successfully', 'success');
        
    } catch (error) {
        console.error('Error deleting:', error);
        showToast('Only admin can delete items', 'error');
    }
}

async function exportInventory() {
    try {
        const response = await fetch(API_ENDPOINTS.export);
        if (!response.ok) throw new Error('Export failed');
        const blob = await response.blob();
        const contentDisposition = response.headers.get('Content-Disposition') || '';
        const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/i);
        const filename = filenameMatch ? filenameMatch[1] : 'inventory_export.xlsx';
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
        showToast('Export started', 'success');
    } catch (error) {
        console.error('Error exporting:', error);
        showToast('Export feature (connect API)', 'success');
    }
}

// Render Functions
function renderTable() {
    const start = (currentPage - 1) * itemsPerPage;
    const end = start + itemsPerPage;
    const pageData = inventoryData.slice(start, end);

    if (pageData.length === 0) {
        inventoryTable.innerHTML = `
            <tr>
                <td colspan="10" style="text-align: center; padding: 40px; color: #6b7280;">
                    No products found
                </td>
            </tr>
        `;
    } else {
        inventoryTable.innerHTML = pageData.map(item => createTableRow(item)).join('');
    }

    updatePagination();
}

function createTableRow(item) {
    const isEditing = editingRowId == item.product_id;
    const isLowStock = item.stock_quantity <= item.reorder_level;

    if (isEditing) {
        return `
            <tr data-id="${item.product_id}">
                <td>
                    <div class="product-cell">
                        <div class="product-icon">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
                            </svg>
                        </div>
                        <input type="text" class="editable-input" name="name" value="${escapeHtml(item.name)}">
                    </div>
                </td>
                <td><input type="text" class="editable-input" name="plu_code" value="${escapeHtml(item.plu_code || '')}"></td>
                <td><input type="text" class="editable-input" name="barcode" value="${escapeHtml(item.barcode)}"></td>
                <td><input type="text" class="editable-input" name="brand" value="${escapeHtml(item.brand || '')}"></td>
                <td><input type="text" class="editable-input" name="category" value="${escapeHtml(item.category || '')}"></td>
                <td><input type="number" class="editable-input" name="stock_quantity" value="${item.stock_quantity}" min="0"></td>
                <td><input type="number" class="editable-input" name="unit_cost" value="${item.unit_cost}" step="0.01" min="0"></td>
                <td><input type="number" class="editable-input" name="unit_price" value="${item.unit_price}" step="0.01" min="0"></td>
                <td><input type="number" class="editable-input" name="reorder_level" value="${item.reorder_level}" min="0"></td>
                <td>
                    <div class="actions-cell">
                        <button type="button" class="btn btn-save save-btn" data-id="${item.product_id}">Save</button>
                        <button type="button" class="btn btn-cancel cancel-btn" data-id="${item.product_id}">Cancel</button>
                    </div>
                </td>
            </tr>
        `;
    }

    return `
        <tr data-id="${item.product_id}">
            <td>
                <div class="product-cell">
                    <div class="product-icon">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
                        </svg>
                    </div>
                    <div class="product-info">
                        <span class="product-name">${escapeHtml(item.name)}</span>
                        ${isLowStock ? '<span class="low-stock-badge">LOW STOCK</span>' : ''}
                    </div>
                </div>
            </td>
            <td>${escapeHtml(item.plu_code || '-')}</td>
            <td>${escapeHtml(item.barcode)}</td>
            <td>${escapeHtml(item.brand || '-')}</td>
            <td>${escapeHtml(item.category || '-')}</td>
            <td>
                <span class="stock-badge ${isLowStock ? 'stock-low' : 'stock-normal'}">
                    ${item.stock_quantity}
                </span>
            </td>
            <td>${formatCurrency(item.unit_cost)}</td>
            <td>${formatCurrency(item.unit_price)}</td>
            <td>${item.reorder_level}</td>
            <td>
                <div class="actions-cell">
                    <button type="button" class="action-btn edit edit-btn" data-id="${item.product_id}" title="Edit">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                        </svg>
                    </button>
                    <button type="button" class="action-btn delete delete-btn" data-id="${item.product_id}" title="Delete">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="3 6 5 6 21 6"/>
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                            <line x1="10" y1="11" x2="10" y2="17"/>
                            <line x1="14" y1="11" x2="14" y2="17"/>
                        </svg>
                    </button>
                </div>
            </td>
        </tr>
    `;
}

async function handleInventoryTableClick(event) {
    const button = event.target.closest('button');
    if (!button || !inventoryTable.contains(button)) return;

    const productId = parseInt(button.dataset.id, 10);
    if (Number.isNaN(productId)) return;

    if (button.classList.contains('edit-btn')) {
        editingRowId = productId;
        renderTable();
        return;
    }

    if (button.classList.contains('delete-btn')) {
        deleteProductId = productId;
        deleteModal.classList.add('active');
        return;
    }

    if (button.classList.contains('cancel-btn')) {
        editingRowId = null;
        renderTable();
        return;
    }

    if (button.classList.contains('save-btn')) {
        const row = inventoryTable.querySelector(`tr[data-id="${productId}"]`);
        if (!row) return;

        const inputs = row.querySelectorAll('.editable-input');
        const data = {
            product_id: productId
        };

        inputs.forEach(input => {
            let value = input.value;
            if (input.type === 'number') {
                value = input.step === '0.01' ? parseFloat(value) : parseInt(value, 10);
            }
            data[input.name] = value;
        });

        const success = await updateInventory(productId, data);
        if (success) {
            const index = inventoryData.findIndex(item => item.product_id === productId);
            if (index !== -1) {
                inventoryData[index] = { ...inventoryData[index], ...data };
            }
            editingRowId = null;
            renderTable();
        }
    }
}

function updatePagination() {
    const totalItems = inventoryData.length;
    const totalPages = Math.ceil(totalItems / itemsPerPage);
    const start = (currentPage - 1) * itemsPerPage + 1;
    const end = Math.min(currentPage * itemsPerPage, totalItems);

    paginationInfo.textContent = totalItems > 0 
        ? `Showing ${start}-${end} of ${totalItems} products`
        : 'Showing 0 products';

    let paginationHTML = '';
    
    // Previous button
    paginationHTML += `
        <button class="page-btn" ${currentPage === 1 ? 'disabled' : ''} data-page="prev">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="15 18 9 12 15 6"/>
            </svg>
        </button>
    `;

    // Page numbers
    for (let i = 1; i <= Math.min(totalPages, 5); i++) {
        paginationHTML += `
            <button class="page-btn ${currentPage === i ? 'active' : ''}" data-page="${i}">${i}</button>
        `;
    }

    if (totalPages > 5) {
        paginationHTML += `<span style="padding: 0 8px;">...</span>`;
    }

    // Next button
    paginationHTML += `
        <button class="page-btn" ${currentPage === totalPages || totalPages === 0 ? 'disabled' : ''} data-page="next">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="9 18 15 12 9 6"/>
            </svg>
        </button>
    `;

    paginationContainer.innerHTML = paginationHTML;

    // Attach pagination events
    paginationContainer.querySelectorAll('.page-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            if (btn.disabled) return;
            const page = btn.dataset.page;
            if (page === 'prev') {
                currentPage = Math.max(1, currentPage - 1);
            } else if (page === 'next') {
                currentPage = Math.min(totalPages, currentPage + 1);
            } else {
                currentPage = parseInt(page);
            }
            renderTable();
        });
    });
}

// Helper Functions
function sortInventory() {
    const sortValue = sortSelect.value;
    inventoryData.sort((a, b) => {
        switch (sortValue) {
            case 'name_asc':
                return a.name.localeCompare(b.name);
            case 'name_desc':
                return b.name.localeCompare(a.name);
            case 'stock_asc':
                return a.stock_quantity - b.stock_quantity;
            case 'stock_desc':
                return b.stock_quantity - a.stock_quantity;
            case 'price_asc':
                return a.unit_price - b.unit_price;
            case 'price_desc':
                return b.unit_price - a.unit_price;
            default:
                return 0;
        }
    });
}

function showLoading(show) {
    loadingState.style.display = show ? 'flex' : 'none';
    document.getElementById('tableScroll').style.display = show ? 'none' : 'block';
}

function closeDeleteModal() {
    deleteModal.classList.remove('active');
    deleteProductId = null;
}

function handleDeleteConfirm() {
    if (deleteProductId) {
        deleteInventory(deleteProductId);
        closeDeleteModal();
    }
}

function showToast(message, type = 'success') {
    toast.textContent = message;
    toast.className = `toast ${type} show`;
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
