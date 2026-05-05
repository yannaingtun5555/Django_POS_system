// ===== API Configuration =====
const API_BASE_URL = '/api'; // Change this to your Django API base URL
const APP_CONFIG = window.APP_CONFIG || {};
const CURRENCY_PREFIX = APP_CONFIG.currencyPrefix || '$';
const CURRENCY_POSTFIX = APP_CONFIG.currencyPostfix || '';

// ===== Application State =====
const state = {
    cart: [],
    searchResults: [],
    selectedItem: null,
    searchTimeout: null
};

// ===== DOM Elements =====
const elements = {
    // Search
    productSearch: document.getElementById('productSearch'),
    searchDropdown: document.getElementById('searchDropdown'),
    supplierName: document.getElementById('supplierName'),
    
    // Cart
    cartTableBody: document.getElementById('cartTableBody'),
    cartEmpty: document.getElementById('cartEmpty'),
    
    // Summary
    totalItems: document.getElementById('totalItems'),
    totalQuantity: document.getElementById('totalQuantity'),
    totalCost: document.getElementById('totalCost'),
    paymentMethod: document.getElementById('paymentMethod'),
    purchaseNotes: document.getElementById('purchaseNotes'),
    
    // Buttons
    addNewItemBtn: document.getElementById('addNewItemBtn'),
    savePurchaseBtn: document.getElementById('savePurchaseBtn'),
    
    // Existing Item Modal
    existingItemModal: document.getElementById('existingItemModal'),
    existingItemName: document.getElementById('existingItemName'),
    existingItemPid: document.getElementById('existingItemPid'),
    existingUnitCost: document.getElementById('existingUnitCost'),
    existingUnitPrice: document.getElementById('existingUnitPrice'),
    existingQuantity: document.getElementById('existingQuantity'),
    closeExistingModal: document.getElementById('closeExistingModal'),
    cancelExistingBtn: document.getElementById('cancelExistingBtn'),
    addExistingToCartBtn: document.getElementById('addExistingToCartBtn'),
    
    // New Item Modal
    newItemModal: document.getElementById('newItemModal'),
    newProductName: document.getElementById('newProductName'),
    newBrand: document.getElementById('newBrand'),
    newCategory: document.getElementById('newCategory'),
    newPluCode: document.getElementById('newPluCode'),
    newBarcode: document.getElementById('newBarcode'),
    newReorderLevel: document.getElementById('newReorderLevel'),
    newUnitCost: document.getElementById('newUnitCost'),
    newUnitPrice: document.getElementById('newUnitPrice'),
    newStockQuantity: document.getElementById('newStockQuantity'),
    closeNewModal: document.getElementById('closeNewModal'),
    cancelNewBtn: document.getElementById('cancelNewBtn'),
    addNewToCartBtn: document.getElementById('addNewToCartBtn'),
    
    // Toast
    toast: document.getElementById('toast'),
    toastMessage: document.getElementById('toastMessage')
};

// ===== Utility Functions =====
function formatCurrency(amount) {
    const value = parseFloat(amount) || 0;
    return `${CURRENCY_PREFIX}${value.toFixed(2)}${CURRENCY_POSTFIX}`;
}

function generateTempId() {
    return 'new_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

function showToast(message, type = 'default') {
    elements.toast.className = 'toast active ' + type;
    elements.toastMessage.textContent = message;
    
    setTimeout(() => {
        elements.toast.classList.remove('active');
    }, 3000);
}

function debounce(func, delay) {
    return function(...args) {
        clearTimeout(state.searchTimeout);
        state.searchTimeout = setTimeout(() => func.apply(this, args), delay);
    };
}

// ===== API Functions =====
async function searchProducts(query) {
    if (!query || query.length < 1) {
        state.searchResults = [];
        renderSearchResults();
        return;
    }
    
    // Show loading state
    elements.searchDropdown.classList.add('active');
    elements.searchDropdown.innerHTML = '<div class="search-loading">Searching...</div>';
    
    try {
        const response = await fetch(`${API_BASE_URL}/inventory/search?q=${encodeURIComponent(query)}`);
        
        if (!response.ok) {
            throw new Error('Search failed');
        }
        
        const data = await response.json();
        const mappedData = data.map(item => ({
            pid: item.product_id,
            name: item.name,
            price: parseFloat(item.unit_price) || 0
        }));
        state.searchResults = mappedData.slice(0, 5); // Max 5 results
        renderSearchResults();
    } catch (error) {
        console.error('Search error:', error);
        elements.searchDropdown.innerHTML = '<div class="search-no-results">Error searching products</div>';
        
        // Demo: Use mock data for testing without API
        state.searchResults = getMockSearchResults(query);
        renderSearchResults();
    }
}

async function createPurchase(payload) {
    const accessToken = localStorage.getItem("access");
    try {
        const response = await fetch(`${API_BASE_URL}/purchases/create/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${accessToken}`,
            },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            const errorData = await response.json(); // Get the actual error from Django
            console.log("Validation Error Details:", errorData); // READ THIS IN CONSOLE
            throw new Error('Purchase creation failed');
        }
        
        return await response.json();
    } catch (error) {
        console.error('Purchase error:', error);
        throw error;
    }
}

// ===== Mock Data for Testing =====
function getMockSearchResults(query) {
    const mockProducts = [
        { pid: 1, name: 'Organic Almond Milk 1L', price: 4.50 },
        { pid: 2, name: 'Whole Wheat Bread', price: 3.20 },
        { pid: 3, name: 'Avocado (Hass)', price: 2.00 },
        { pid: 4, name: 'Rice 1kg Premium', price: 3.00 },
        { pid: 5, name: 'Sugar White 500g', price: 2.50 },
        { pid: 6, name: 'Olive Oil Extra Virgin', price: 8.99 },
        { pid: 7, name: 'Fresh Eggs 12pk', price: 5.50 },
        { pid: 8, name: 'Butter Unsalted 250g', price: 4.00 }
    ];
    
    const lowerQuery = query.toLowerCase();
    return mockProducts
        .filter(p => p.name.toLowerCase().includes(lowerQuery) || p.pid.toString().includes(query))
        .slice(0, 5);
}

// ===== Render Functions =====
function renderSearchResults() {
    if (state.searchResults.length === 0) {
        if (elements.productSearch.value.length > 0) {
            elements.searchDropdown.innerHTML = '<div class="search-no-results">No products found</div>';
            elements.searchDropdown.classList.add('active');
        } else {
            elements.searchDropdown.classList.remove('active');
        }
        return;
    }
    
    elements.searchDropdown.innerHTML = state.searchResults.map(item => `
        <div class="search-result-item" data-pid="${item.pid}" data-name="${item.name}" data-price="${item.price}">
            <span class="search-result-pid">PID: ${item.pid}</span>
            <span class="search-result-name">${item.name}</span>
            <span class="search-result-price">${formatCurrency(item.price)}</span>
        </div>
    `).join('');
    
    elements.searchDropdown.classList.add('active');
    
    // Add click handlers
    elements.searchDropdown.querySelectorAll('.search-result-item').forEach(item => {
        item.addEventListener('click', () => {
            const pid = parseInt(item.dataset.pid);
            const name = item.dataset.name;
            const price = parseFloat(item.dataset.price);
            openExistingItemModal({ pid, name, price });
        });
    });
}

function renderCart() {
    if (state.cart.length === 0) {
        elements.cartTableBody.innerHTML = '';
        elements.cartEmpty.classList.remove('hidden');
    } else {
        elements.cartEmpty.classList.add('hidden');
        elements.cartTableBody.innerHTML = state.cart.map((item, index) => `
            <tr data-index="${index}">
                <td>
                    <div class="cart-product-name">
                        ${item.name}
                        ${item.isNew ? '<span class="cart-product-new-badge">NEW</span>' : ''}
                    </div>
                    <div class="cart-product-pid">${item.isNew ? 'New Item' : 'PID: ' + item.pid}</div>
                </td>
                <td>
                    <input type="number" class="cart-input qty-input" value="${item.quantity}" min="1" data-index="${index}">
                </td>
                <td>
                    <input type="number" class="cart-input cost-input" value="${item.unit_cost}" step="0.01" min="0" data-index="${index}">
                </td>
                <td class="cart-subtotal">${formatCurrency(item.subtotal)}</td>
                <td>
                    <button class="btn btn-danger remove-item" data-index="${index}">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </button>
                </td>
            </tr>
        `).join('');
        
        // Add event listeners for quantity/cost changes
        elements.cartTableBody.querySelectorAll('.qty-input').forEach(input => {
            input.addEventListener('change', (e) => {
                const index = parseInt(e.target.dataset.index);
                const newQty = parseInt(e.target.value) || 1;
                updateCartItem(index, 'quantity', newQty);
            });
        });
        
        elements.cartTableBody.querySelectorAll('.cost-input').forEach(input => {
            input.addEventListener('change', (e) => {
                const index = parseInt(e.target.dataset.index);
                const newCost = parseFloat(e.target.value) || 0;
                updateCartItem(index, 'unit_cost', newCost);
            });
        });
        
        // Add event listeners for remove buttons
        elements.cartTableBody.querySelectorAll('.remove-item').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const index = parseInt(e.currentTarget.dataset.index);
                removeFromCart(index);
            });
        });
    }
    
    updateSummary();
}

function updateSummary() {
    const totalItems = state.cart.length;
    const totalQuantity = state.cart.reduce((sum, item) => sum + item.quantity, 0);
    const totalCost = state.cart.reduce((sum, item) => sum + item.subtotal, 0);
    
    elements.totalItems.textContent = totalItems;
    elements.totalQuantity.textContent = totalQuantity;
    elements.totalCost.textContent = formatCurrency(totalCost);
}

// ===== Cart Functions =====
function addToCart(item) {
    // Check if item already exists (for existing products)
    if (!item.isNew) {
        const existingIndex = state.cart.findIndex(cartItem => !cartItem.isNew && cartItem.pid === item.pid);
        if (existingIndex !== -1) {
            // Update quantity instead of adding duplicate
            state.cart[existingIndex].quantity += item.quantity;
            state.cart[existingIndex].subtotal = state.cart[existingIndex].unit_cost * state.cart[existingIndex].quantity;
            showToast(`Updated quantity for ${item.name}`, 'success');
            renderCart();
            return;
        }
    }
    
    state.cart.push(item);
    showToast(`Added ${item.name} to cart`, 'success');
    renderCart();
}

function updateCartItem(index, field, value) {
    if (index >= 0 && index < state.cart.length) {
        state.cart[index][field] = value;
        // Recalculate subtotal
        state.cart[index].subtotal = state.cart[index].unit_cost * state.cart[index].quantity;
        renderCart();
    }
}

function removeFromCart(index) {
    if (index >= 0 && index < state.cart.length) {
        const item = state.cart[index];
        state.cart.splice(index, 1);
        showToast(`Removed ${item.name} from cart`, 'default');
        renderCart();
    }
}

function clearCart() {
    state.cart = [];
    renderCart();
}

// ===== Modal Functions =====
function openExistingItemModal(item) {
    state.selectedItem = item;
    elements.existingItemName.textContent = item.name;
    elements.existingItemPid.value = item.pid;
    elements.existingUnitCost.value = '';
    elements.existingUnitPrice.value = item.price || '';
    elements.existingQuantity.value = 1;
    
    // Clear search
    elements.productSearch.value = '';
    elements.searchDropdown.classList.remove('active');
    
    elements.existingItemModal.classList.add('active');
    elements.existingUnitCost.focus();
}

function closeExistingItemModal() {
    elements.existingItemModal.classList.remove('active');
    state.selectedItem = null;
}

function openNewItemModal() {
    // Clear form
    elements.newProductName.value = '';
    elements.newBrand.value = '';
    elements.newCategory.value = '';
    elements.newPluCode.value = '';
    elements.newBarcode.value = '';
    elements.newReorderLevel.value = 5;
    elements.newUnitCost.value = '';
    elements.newUnitPrice.value = '';
    elements.newStockQuantity.value = 1;
    
    elements.newItemModal.classList.add('active');
    elements.newProductName.focus();
}

function closeNewItemModal() {
    elements.newItemModal.classList.remove('active');
}

// ===== Event Handlers =====
function handleAddExistingToCart() {
    const unitCost = parseFloat(elements.existingUnitCost.value);
    const unitPrice = parseFloat(elements.existingUnitPrice.value);
    const quantity = parseInt(elements.existingQuantity.value) || 1;
    
    if (isNaN(unitCost) || unitCost < 0) {
        showToast('Please enter a valid unit cost', 'error');
        elements.existingUnitCost.focus();
        return;
    }
    
    if (isNaN(unitPrice) || unitPrice < 0) {
        showToast('Please enter a valid unit price', 'error');
        elements.existingUnitPrice.focus();
        return;
    }
    
    if (quantity < 1) {
        showToast('Quantity must be at least 1', 'error');
        elements.existingQuantity.focus();
        return;
    }
    
    const cartItem = {
        pid: state.selectedItem.pid,
        name: state.selectedItem.name,
        unit_cost: unitCost,
        unit_price: unitPrice,
        quantity: quantity,
        subtotal: unitCost * quantity,
        isNew: false
    };
    
    addToCart(cartItem);
    closeExistingItemModal();
}

function handleAddNewToCart() {
    const productName = elements.newProductName.value.trim();
    const brand = elements.newBrand.value.trim();
    const category = elements.newCategory.value.trim();
    const pluCode = elements.newPluCode.value.trim();
    const barcode = elements.newBarcode.value.trim();
    const reorderLevel = parseInt(elements.newReorderLevel.value) || 5;
    const unitCost = parseFloat(elements.newUnitCost.value);
    const unitPrice = parseFloat(elements.newUnitPrice.value);
    const stockQuantity = parseInt(elements.newStockQuantity.value) || 1;
    
    // Validation
    if (!productName) {
        showToast('Please enter a product name', 'error');
        elements.newProductName.focus();
        return;
    }
    
    if (!brand) {
        showToast('Please enter a brand', 'error');
        elements.newBrand.focus();
        return;
    }
    
    if (!category) {
        showToast('Please enter a category', 'error');
        elements.newCategory.focus();
        return;
    }
    
    if (isNaN(unitCost) || unitCost < 0) {
        showToast('Please enter a valid unit cost', 'error');
        elements.newUnitCost.focus();
        return;
    }
    
    if (isNaN(unitPrice) || unitPrice < 0) {
        showToast('Please enter a valid unit price', 'error');
        elements.newUnitPrice.focus();
        return;
    }
    
    if (stockQuantity < 1) {
        showToast('Stock quantity must be at least 1', 'error');
        elements.newStockQuantity.focus();
        return;
    }
    
    const cartItem = {
        pid: generateTempId(),
        name: productName,
        brand: brand,
        category: category,
        plu_code: pluCode,
        barcode: barcode,
        reorder_level: reorderLevel,
        unit_cost: unitCost,
        unit_price: unitPrice,
        quantity: stockQuantity,
        subtotal: unitCost * stockQuantity,
        isNew: true
    };
    
    addToCart(cartItem);
    closeNewItemModal();
}

async function handleSavePurchase() {
    // Validation
    const supplier = elements.supplierName.value.trim();
    const paymentMethod = elements.paymentMethod.value;
    
    if (!supplier) {
        showToast('Please enter a supplier name', 'error');
        elements.supplierName.focus();
        return;
    }
    
    if (!paymentMethod) {
        showToast('Please select a payment method', 'error');
        elements.paymentMethod.focus();
        return;
    }
    
    if (state.cart.length === 0) {
        showToast('Cart is empty. Add items first.', 'error');
        return;
    }
    
    // Calculate total
    const totalPayment = state.cart.reduce((sum, item) => sum + item.subtotal, 0);
    
    // Build payload
    const items = state.cart.map(item => {
        if (item.isNew) {
            // New item payload
            return {
                barcode: item.barcode || null,
                product_name: item.name,
                quantity: item.quantity,
                unit_cost: item.unit_cost,
                unit_price: item.unit_price,
                brand: item.brand,
                category: item.category,
                plu_code: item.plu_code || null,
                reorder_level: item.reorder_level || 5
            };
        } else {
            // Existing item payload
            return {
                product_id: item.pid,
                quantity: item.quantity,
                unit_cost: item.unit_cost.toFixed(2)
            };
        }
    });
    
    const payload = {
        supplier: supplier,
        payment_method: paymentMethod,
        payment: parseFloat(totalPayment),
        items: items
    };

    
    // Disable button and show loading
    elements.savePurchaseBtn.disabled = true;
    elements.savePurchaseBtn.innerHTML = `
        <svg class="spinner" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10" stroke-dasharray="32" stroke-dashoffset="32">
                <animate attributeName="stroke-dashoffset" dur="1s" repeatCount="indefinite" values="32;0"/>
            </circle>
        </svg>
        Processing...
    `;
    
    try {
        await createPurchase(payload);
        showToast('Purchase saved successfully!', 'success');
        
        // Clear form
        clearCart();
        elements.supplierName.value = '';
        elements.paymentMethod.value = '';
        elements.purchaseNotes.value = '';
        
    } catch (error) {
        showToast('Failed to save purchase. Please try again.', 'error');
        
        // For demo purposes, simulate success
        console.log('Purchase payload:', JSON.stringify(payload, null, 2));
        showToast('Demo: Purchase would be saved with above payload', 'success');
        clearCart();
        elements.supplierName.value = '';
        elements.paymentMethod.value = '';
        elements.purchaseNotes.value = '';
    } finally {
        elements.savePurchaseBtn.disabled = false;
        elements.savePurchaseBtn.innerHTML = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            Save Purchase
        `;
    }
}

// ===== Initialize Event Listeners =====
function initEventListeners() {
    // Search with debounce (500ms)
    const debouncedSearch = debounce((query) => searchProducts(query), 500);
    
    elements.productSearch.addEventListener('input', (e) => {
        debouncedSearch(e.target.value);
    });
    
    // Close search dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.search-group')) {
            elements.searchDropdown.classList.remove('active');
        }
    });
    
    // Add New Item button
    elements.addNewItemBtn.addEventListener('click', openNewItemModal);
    
    // Existing Item Modal
    elements.closeExistingModal.addEventListener('click', closeExistingItemModal);
    elements.cancelExistingBtn.addEventListener('click', closeExistingItemModal);
    elements.addExistingToCartBtn.addEventListener('click', handleAddExistingToCart);
    
    // New Item Modal
    elements.closeNewModal.addEventListener('click', closeNewItemModal);
    elements.cancelNewBtn.addEventListener('click', closeNewItemModal);
    elements.addNewToCartBtn.addEventListener('click', handleAddNewToCart);
    
    // Save Purchase
    elements.savePurchaseBtn.addEventListener('click', handleSavePurchase);
    
    // Close modals on overlay click
    elements.existingItemModal.addEventListener('click', (e) => {
        if (e.target === elements.existingItemModal) {
            closeExistingItemModal();
        }
    });
    
    elements.newItemModal.addEventListener('click', (e) => {
        if (e.target === elements.newItemModal) {
            closeNewItemModal();
        }
    });
    
    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Escape to close modals
        if (e.key === 'Escape') {
            closeExistingItemModal();
            closeNewItemModal();
        }
        
        // Enter to submit in modals
        if (e.key === 'Enter') {
            if (elements.existingItemModal.classList.contains('active')) {
                handleAddExistingToCart();
            } else if (elements.newItemModal.classList.contains('active')) {
                handleAddNewToCart();
            }
        }
        
        // Ctrl+N for new item
        if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
            e.preventDefault();
            openNewItemModal();
        }
        
        // Ctrl+S for save
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            handleSavePurchase();
        }
        
        // Focus search on /
        if (e.key === '/' && !e.target.closest('input, textarea')) {
            e.preventDefault();
            elements.productSearch.focus();
        }
    });
}

// ===== Initialize Application =====
function init() {
    initEventListeners();
    renderCart();
    console.log('POS Purchase Module initialized');
    console.log('Keyboard shortcuts:');
    console.log('  / - Focus search');
    console.log('  Ctrl+N - Add new item');
    console.log('  Ctrl+S - Save purchase');
    console.log('  Escape - Close modals');
}

// Start the application
document.addEventListener('DOMContentLoaded', init);
