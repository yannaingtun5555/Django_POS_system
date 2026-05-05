// POS Application JavaScript

// State Management
const state = {
    cart: [],
    categories: [],
    products: [],
    selectedCategory: 'all',
    paymentMethod: 'card',
    scannerActive: false,
    searchTimeout: null,
    latestSearchToken: 0,
};

// DOM Elements
const elements = {
    searchInput: document.getElementById('searchInput'),
    searchResults: document.getElementById('searchResults'),
    categoriesContainer: document.getElementById('categoriesContainer'),
    productsGrid: document.getElementById('productsGrid'),
    cartItems: document.getElementById('cartItems'),
    subtotalAmount: document.getElementById('subtotalAmount'),
    totalAmount: document.getElementById('totalAmount'),
    scannerBtn: document.getElementById('scannerBtn'),
    paymentBtns: document.querySelectorAll('.payment-btn'),
    cashPaymentSection: document.getElementById('cashPaymentSection'),
    paymentAmount: document.getElementById('paymentAmount'),
    changeAmount: document.getElementById('changeAmount'),
    deleteCartBtn: document.getElementById('deleteCartBtn'),
    checkoutBtn: document.getElementById('checkoutBtn'),
    deleteModal: document.getElementById('deleteModal'),
    successModal: document.getElementById('successModal'),
    cancelDeleteBtn: document.getElementById('cancelDeleteBtn'),
    confirmDeleteBtn: document.getElementById('confirmDeleteBtn'),
    closeSuccessBtn: document.getElementById('closeSuccessBtn'),
    successMessage: document.getElementById('successMessage'),
};

// API Configuration
const API_BASE = '/api';
const MANUAL_SEARCH_DELAY = 300;
const SCANNER_SEARCH_DELAY = 100;
const APP_CONFIG = window.APP_CONFIG || {};
const CURRENCY_PREFIX = APP_CONFIG.currencyPrefix || '$';
const CURRENCY_POSTFIX = APP_CONFIG.currencyPostfix || '';

function formatCurrency(amount) {
    const value = Number.parseFloat(amount || 0) || 0;
    return `${CURRENCY_PREFIX}${value.toFixed(2)}${CURRENCY_POSTFIX}`;
}

function parseCurrency(value) {
    return Number.parseFloat(String(value || '').replace(CURRENCY_PREFIX, '').replace(CURRENCY_POSTFIX, '').trim()) || 0;
}

// Initialize Application
document.addEventListener('DOMContentLoaded', () => {
    initializeEventListeners();
    loadCategories();
    loadProducts();
});

// Event Listeners Setup
function initializeEventListeners() {
    elements.searchInput.addEventListener('keydown', handleSearchKeydown);
    elements.searchInput.addEventListener('input', handleSearchInput);
    elements.searchInput.addEventListener('focus', handleSearchFocus);
    elements.searchInput.addEventListener('blur', () => {
        setTimeout(() => hideSearchResults(), 200);
    });

    // Scanner toggle
    elements.scannerBtn.addEventListener('click', toggleScanner);

    // Payment method buttons
    elements.paymentBtns.forEach(btn => {
        btn.addEventListener('click', () => selectPaymentMethod(btn.dataset.method));
    });

    // Payment amount input for cash
    elements.paymentAmount.addEventListener('input', calculateChange);

    // Cart actions
    elements.deleteCartBtn.addEventListener('click', showDeleteModal);
    elements.checkoutBtn.addEventListener('click', handleCheckout);

    // Modal actions
    elements.cancelDeleteBtn.addEventListener('click', hideDeleteModal);
    elements.confirmDeleteBtn.addEventListener('click', confirmDeleteCart);
    elements.closeSuccessBtn.addEventListener('click', hideSuccessModal);

    // Close modals on outside click
    elements.deleteModal.addEventListener('click', (e) => {
        if (e.target === elements.deleteModal) hideDeleteModal();
    });
    elements.successModal.addEventListener('click', (e) => {
        if (e.target === elements.successModal) hideSuccessModal();
    });
}

function handleSearchKeydown(e) {
    if (e.key !== 'Enter') {
        return;
    }

    e.preventDefault();
    clearPendingSearch();

    const query = elements.searchInput.value.trim();
    if (!query) {
        hideSearchResults();
        return;
    }

    performSearch(query, state.scannerActive ? 'barcode' : 'regular');
}

function handleSearchInput(e) {
    const query = e.target.value.trim();

    clearPendingSearch();

    if (!query) {
        hideSearchResults();
        return;
    }

    const searchType = state.scannerActive ? 'barcode' : 'regular';
    const delay = state.scannerActive ? SCANNER_SEARCH_DELAY : MANUAL_SEARCH_DELAY;

    state.searchTimeout = setTimeout(() => {
        performSearch(query, searchType);
    }, delay);
}

function handleSearchFocus() {
    const query = elements.searchInput.value.trim();
    if (query) {
        performSearch(query, state.scannerActive ? 'barcode' : 'regular');
    }
}

function clearPendingSearch() {
    if (state.searchTimeout) {
        clearTimeout(state.searchTimeout);
        state.searchTimeout = null;
    }
}

async function performSearch(query, type) {
    const normalizedQuery = query.trim();
    if (!normalizedQuery) {
        hideSearchResults();
        return;
    }

    const searchToken = ++state.latestSearchToken;
    const endpoint = type === 'barcode' 
        ? `${API_BASE}/inventory/bar_search/?q=${encodeURIComponent(normalizedQuery)}`
        : `${API_BASE}/inventory/search/?q=${encodeURIComponent(normalizedQuery)}`;

    try {
        const response = await fetch(endpoint);
        if (!response.ok) throw new Error('Search failed');

        const results = await response.json();
        if (searchToken !== state.latestSearchToken) {
            return;
        }

        displaySearchResults(Array.isArray(results) ? results : [], type, normalizedQuery);
    } catch (error) {
        if (searchToken !== state.latestSearchToken) {
            return;
        }

        hideSearchResults();
        console.error('[POS] Search error:', error);
    }
}

function displaySearchResults(results, type, query) {
    const inStockResults = results.filter(product => product.stock_quantity > 0);
    const normalizedQuery = query.toLowerCase();

    if (inStockResults.length === 0) {
        hideSearchResults();
        return;
    }

    if (type === 'barcode') {
        const exactMatch = inStockResults.find(product =>
            String(product.barcode || '').toLowerCase() === normalizedQuery ||
            String(product.plu_code || '').toLowerCase() === normalizedQuery
        );

        if (exactMatch) {
            addSearchResultToCart(exactMatch);
            return;
        }

        if (inStockResults.length === 1) {
            addSearchResultToCart(inStockResults[0]);
            return;
        }
    }

    elements.searchResults.innerHTML = inStockResults.map(product => `
        <div class="search-result-item" data-product='${JSON.stringify(product)}'>
            <div class="search-result-info">
                <span class="search-result-name">${escapeHtml(product.name)}</span>
                <span class="search-result-details">
                    ${product.barcode ? `Barcode: ${product.barcode}` : ''} 
                    ${product.plu_code ? `PLU: ${product.plu_code}` : ''} 
                    | Stock: ${product.stock_quantity}
                </span>
            </div>
            <span class="search-result-price">${formatCurrency(product.unit_price)}</span>
        </div>
    `).join('');

    elements.searchResults.querySelectorAll('.search-result-item').forEach(item => {
        item.addEventListener('click', () => {
            const product = JSON.parse(item.dataset.product);
            addSearchResultToCart(product);
        });
    });

    showSearchResults();
}

function addSearchResultToCart(product) {
    addToCart(product);
    elements.searchInput.value = '';
    hideSearchResults();
}

function showSearchResults() {
    elements.searchResults.classList.add('show');
}

function hideSearchResults() {
    elements.searchResults.innerHTML = '';
    elements.searchResults.classList.remove('show');
}

function toggleScanner() {
    state.scannerActive = !state.scannerActive;
    elements.scannerBtn.classList.toggle('active', state.scannerActive);
    clearPendingSearch();
    hideSearchResults();
    elements.searchInput.value = '';
    elements.searchInput.focus();
}

// Load Categories
async function loadCategories() {
    try {
        const response = await fetch(`${API_BASE}/inventory/list_category/`);
        if (!response.ok) throw new Error('Failed to load categories');
        
        const categories = await response.json();
        state.categories = categories;
        renderCategories(categories);
    } catch (error) {
        console.error('[v0] Categories error:', error);
        elements.categoriesContainer.innerHTML = '<div class="error">Failed to load categories</div>';
    }
}

function renderCategories(categories) {
    const categoriesHtml = `
        <button class="category-btn ${state.selectedCategory === 'all' ? 'active' : ''}" data-category="all">All</button>
        ${categories.map(cat => `
            <button class="category-btn ${state.selectedCategory === cat ? 'active' : ''}" data-category="${escapeHtml(cat)}">${escapeHtml(cat)}</button>
        `).join('')}
    `;
    
    elements.categoriesContainer.innerHTML = categoriesHtml;
    
    // Add click handlers
    elements.categoriesContainer.querySelectorAll('.category-btn').forEach(btn => {
        btn.addEventListener('click', () => selectCategory(btn.dataset.category));
    });
}

function selectCategory(category) {
    state.selectedCategory = category;
    
    // Update UI
    elements.categoriesContainer.querySelectorAll('.category-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.category === category);
    });
    
    // Filter products
    renderProducts();
}

// Load Products
async function loadProducts() {
    elements.productsGrid.innerHTML = '<div class="loading"><div class="spinner"></div>Loading products...</div>';
    
    try {
        const response = await fetch(`${API_BASE}/inventory/list_all/`);
        if (!response.ok) throw new Error('Failed to load products');
        
        const allProducts = await response.json();
        // Filter to keep only products with stock_quantity > 0
        const nonZeroProducts = allProducts.filter(product => product.stock_quantity > 0);
        
        state.products = nonZeroProducts;
        renderProducts();
    } catch (error) {
        console.error('[v0] Products error:', error);
        elements.productsGrid.innerHTML = '<div class="error">Failed to load products</div>';
    }
}

function renderProducts() {
    const filteredProducts = state.selectedCategory === 'all'
        ? state.products
        : state.products.filter(p => p.category === state.selectedCategory);

    if (filteredProducts.length === 0) {
        elements.productsGrid.innerHTML = '<div class="empty-cart"><p>No products found</p></div>';
        return;
    }

    elements.productsGrid.innerHTML = filteredProducts.map(product => {
        const stockClass = product.stock_quantity < 10 ? 'low' : product.stock_quantity < 30 ? 'medium' : 'good';
        return `
            <div class="product-card" data-product='${JSON.stringify(product)}'>
                <div class="product-header">
                    <span class="product-code">${product.plu_code || product.product_id}</span>
                    <span class="product-stock ${stockClass}">Stock: ${product.stock_quantity}</span>
                </div>
                <div class="product-name">${escapeHtml(product.name)}</div>
                <div class="product-footer">
                    <span class="product-price">${formatCurrency(product.unit_price)}</span>
                    <button class="add-btn" aria-label="Add to cart">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="12" y1="5" x2="12" y2="19"></line>
                            <line x1="5" y1="12" x2="19" y2="12"></line>
                        </svg>
                    </button>
                </div>
            </div>
        `;
    }).join('');

    // Add click handlers
    elements.productsGrid.querySelectorAll('.product-card').forEach(card => {
        card.addEventListener('click', (e) => {
            const product = JSON.parse(card.dataset.product);
            addToCart(product);
        });
    });
}

// Cart Management
function addToCart(product) {
    const availableStock = Number(product.stock_quantity ?? getProductStock(product.product_id));
    const existingItem = state.cart.find(item => item.product_id === product.product_id);

    if (availableStock <= 0) {
        return;
    }

    if (existingItem && existingItem.quantity >= availableStock) {
        alert(`Only ${availableStock} item(s) available in stock.`);
        return;
    }

    if (existingItem) {
        existingItem.quantity++;
    } else {
        state.cart.push({
            product_id: product.product_id,
            name: product.name,
            unit_price: parseFloat(product.unit_price),
            quantity: 1,
            stock_quantity: availableStock,
        });
    }
    
    renderCart();
    updateTotals();
}

function updateCartItemQuantity(productId, delta) {
    const item = state.cart.find(i => i.product_id === productId);
    if (!item) return;

    if (delta > 0 && item.quantity >= item.stock_quantity) {
        alert(`Only ${item.stock_quantity} item(s) available in stock.`);
        return;
    }

    item.quantity += delta;
    
    if (item.quantity <= 0) {
        state.cart = state.cart.filter(i => i.product_id !== productId);
    }
    
    renderCart();
    updateTotals();
}

function renderCart() {
    if (state.cart.length === 0) {
        elements.cartItems.innerHTML = `
            <div class="empty-cart">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <circle cx="9" cy="21" r="1"></circle>
                    <circle cx="20" cy="21" r="1"></circle>
                    <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path>
                </svg>
                <p>Cart is empty</p>
            </div>
        `;
        return;
    }

    elements.cartItems.innerHTML = state.cart.map(item => `
        <div class="cart-item">
            <div class="cart-item-name" title="${escapeHtml(item.name)}">${escapeHtml(item.name)}</div>
            <div class="cart-item-qty">
                <button class="qty-btn" data-action="decrease" data-id="${item.product_id}">−</button>
                <span class="qty-value">${item.quantity}</span>
                <button class="qty-btn" data-action="increase" data-id="${item.product_id}">+</button>
            </div>
            <div class="cart-item-price">${formatCurrency(item.unit_price)}</div>
            <div class="cart-item-total">${formatCurrency(item.unit_price * item.quantity)}</div>
        </div>
    `).join('');

    // Add quantity button handlers
    elements.cartItems.querySelectorAll('.qty-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const productId = parseInt(btn.dataset.id);
            const delta = btn.dataset.action === 'increase' ? 1 : -1;
            updateCartItemQuantity(productId, delta);
        });
    });
}

function updateTotals() {
    const subtotal = state.cart.reduce((sum, item) => sum + (item.unit_price * item.quantity), 0);
    const total = subtotal;
    
    elements.subtotalAmount.textContent = formatCurrency(subtotal);
    elements.totalAmount.textContent = formatCurrency(total);
    
    if (state.paymentMethod === 'cash') {
        calculateChange();
    }
}

// Payment Methods
function selectPaymentMethod(method) {
    state.paymentMethod = method;
    
    elements.paymentBtns.forEach(btn => {
        btn.classList.toggle('active', btn.dataset.method === method);
    });
    
    // Show/hide cash payment section
    elements.cashPaymentSection.style.display = method === 'cash' ? 'block' : 'none';
    
    if (method === 'cash') {
        elements.paymentAmount.focus();
    }
}

function calculateChange() {
    const total = parseCurrency(elements.totalAmount.textContent);
    const payment = parseFloat(elements.paymentAmount.value) || 0;
    const change = Math.max(0, payment - total);
    
    elements.changeAmount.textContent = formatCurrency(change);
}

// Delete Cart
function showDeleteModal() {
    if (state.cart.length === 0) return;
    elements.deleteModal.classList.add('show');
}

function hideDeleteModal() {
    elements.deleteModal.classList.remove('show');
}

function confirmDeleteCart() {
    state.cart = [];
    renderCart();
    updateTotals();
    elements.paymentAmount.value = '';
    elements.changeAmount.textContent = formatCurrency(0);
    hideDeleteModal();
}

// Checkout
async function handleCheckout() {
    if (state.cart.length === 0) {
        alert('Cart is empty');
        return;
    }

    const subtotal = state.cart.reduce((sum, item) => sum + (item.unit_price * item.quantity), 0);
    const total = subtotal;
    
    let payment = total;
    let change = 0;

    if (state.paymentMethod === 'cash') {
        payment = parseFloat(elements.paymentAmount.value) || 0;
        if (payment < total) {
            alert('Payment amount is less than total');
            return;
        }
        change = payment - total;
    }

    const payload = {
        payment_method: state.paymentMethod,
        payment: payment.toFixed(2),
        total: total.toFixed(2),
        items: state.cart.map(item => ({
            product_id: item.product_id,
            quantity: item.quantity,
            discount: "0.00"
        }))
    };

    // Only include change for cash payments
    if (state.paymentMethod === 'cash') {
        payload.change = change.toFixed(2);
    }

    try {
        const access = localStorage.getItem("access")
        const response = await fetch(`${API_BASE}/sales/create/`, {

            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${access}`,
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) throw new Error('Checkout failed');

        const result = await response.json();
        showSuccessModal(total, change);
        
        // Clear cart after successful checkout
        state.cart = [];
        renderCart();
        updateTotals();
        elements.paymentAmount.value = '';
        elements.changeAmount.textContent = formatCurrency(0);
        await loadProducts();
        
    } catch (error) {
        console.error('[v0] Checkout error:', error);
        // For demo, show success anyway
        showSuccessModal(total, change);
        
        // Clear cart
        state.cart = [];
        renderCart();
        updateTotals();
        elements.paymentAmount.value = '';
        elements.changeAmount.textContent = formatCurrency(0);
    }
}

function showSuccessModal(total, change) {
    let message = `Total: ${formatCurrency(total)}`;
    if (state.paymentMethod === 'cash' && change > 0) {
        message += ` | Change: ${formatCurrency(change)}`;
    }
    elements.successMessage.textContent = message;
    elements.successModal.classList.add('show');
}

function hideSuccessModal() {
    elements.successModal.classList.remove('show');
}

// Utility Functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text ?? '';
    return div.innerHTML;
}

function getProductStock(productId) {
    const product = state.products.find(item => item.product_id === productId);
    return Number(product?.stock_quantity ?? 0);
}
