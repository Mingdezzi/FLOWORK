let currentStoreOrderController = null;

class StoreOrderController {
    constructor() {
        this.csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        this.selectedVariantId = null;
        this.variantsCache = [];
        
        this.dom = {
            dateInput: document.getElementById('req-date'),
            reqPnInput: document.getElementById('req-pn'),
            searchBtn: document.getElementById('btn-search-prod'),
            searchResults: document.getElementById('search-results'),
            colorSelect: document.getElementById('req-color'),
            sizeSelect: document.getElementById('req-size'),
            btnSubmit: document.getElementById('btn-submit-order') || document.getElementById('btn-submit-return')
        };

        this.boundHandleGlobalClick = this.handleGlobalClick.bind(this);
        this.init();
    }

    init() {
        const today = new Date().toISOString().split('T')[0];
        if (this.dom.dateInput) this.dom.dateInput.value = today;

        if (this.dom.searchBtn) {
            this.dom.searchBtn.addEventListener('click', () => this.searchProduct());
        }

        if (this.dom.colorSelect) {
            this.dom.colorSelect.addEventListener('change', () => this.handleColorChange());
        }

        if (this.dom.sizeSelect) {
            this.dom.sizeSelect.addEventListener('change', () => {
                this.selectedVariantId = this.dom.sizeSelect.value;
            });
        }

        if (this.dom.btnSubmit) {
            this.dom.btnSubmit.addEventListener('click', () => this.submitRequest());
        }

        document.body.addEventListener('click', this.boundHandleGlobalClick);
    }

    destroy() {
        document.body.removeEventListener('click', this.boundHandleGlobalClick);
    }

    async searchProduct() {
        const query = this.dom.reqPnInput.value.trim();
        if (!query) return;
        
        const url = document.body.dataset.productSearchUrl;
        try {
            const res = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': this.csrfToken },
                body: JSON.stringify({ query })
            });
            const data = await res.json();
            
            this.dom.searchResults.innerHTML = '';
            this.dom.searchResults.style.display = 'block';
            
            if(data.products && data.products.length > 0) {
                data.products.forEach(p => {
                    const item = document.createElement('button');
                    item.className = 'list-group-item list-group-item-action';
                    item.textContent = `${p.product_name} (${p.product_number})`;
                    item.onclick = (e) => { 
                        e.preventDefault(); 
                        this.selectProduct(p.product_number); 
                    };
                    this.dom.searchResults.appendChild(item);
                });
            } else {
                this.dom.searchResults.innerHTML = '<div class="p-2">검색 결과 없음</div>';
            }
        } catch(e) { console.error(e); }
    }

    async selectProduct(pn) {
        this.dom.searchResults.style.display = 'none';
        this.dom.reqPnInput.value = pn;
        
        try {
            const detailRes = await fetch('/api/sales/search_products', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': this.csrfToken },
                body: JSON.stringify({ query: pn, mode: 'detail_stock' })
            });
            const detailData = await detailRes.json();
            
            this.dom.colorSelect.innerHTML = '<option value="">선택</option>';
            this.dom.sizeSelect.innerHTML = '<option value="">선택</option>';
            this.dom.colorSelect.disabled = false;
            this.dom.sizeSelect.disabled = true;
            
            this.variantsCache = detailData.variants || [];
            const colors = [...new Set(this.variantsCache.map(v => v.color))];
            colors.forEach(c => {
                const op = document.createElement('option');
                op.value = c; 
                op.textContent = c;
                this.dom.colorSelect.appendChild(op);
            });
        } catch(e) { console.error(e); }
    }

    handleColorChange() {
        const color = this.dom.colorSelect.value;
        this.dom.sizeSelect.innerHTML = '<option value="">선택</option>';
        
        const sizes = this.variantsCache.filter(v => v.color === color);
        sizes.forEach(v => {
            const op = document.createElement('option');
            op.value = v.variant_id; 
            op.textContent = v.size;
            this.dom.sizeSelect.appendChild(op);
        });
        this.dom.sizeSelect.disabled = false;
    }

    async submitRequest() {
        if (!this.selectedVariantId) { alert('상품을 선택하세요.'); return; }
        const qty = document.getElementById('req-qty').value;
        const url = document.body.dataset.apiCreate;

        try {
            const res = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': this.csrfToken },
                body: JSON.stringify({
                    variant_id: this.selectedVariantId,
                    quantity: qty,
                    date: this.dom.dateInput.value
                })
            });
            const data = await res.json();
            if (data.status === 'success') {
                alert(data.message);
                window.location.reload();
            } else {
                alert(data.message);
            }
        } catch(e) { alert('오류 발생'); }
    }

    async handleGlobalClick(e) {
        const urlPrefix = document.body.dataset.apiStatusPrefix;
        if (!urlPrefix) return;

        if (e.target.classList.contains('btn-approve')) {
            const id = e.target.dataset.id;
            const reqQty = e.target.dataset.qty;
            const confQty = prompt('확정 수량을 입력하세요:', reqQty);
            
            if (confQty !== null) {
                await this.updateStatus(urlPrefix + id + '/status', 'APPROVED', confQty);
            }
        }
        if (e.target.classList.contains('btn-reject')) {
            if (!confirm('거절하시겠습니까?')) return;
            const id = e.target.dataset.id;
            await this.updateStatus(urlPrefix + id + '/status', 'REJECTED', 0);
        }
    }

    async updateStatus(url, status, qty) {
        try {
            const res = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': this.csrfToken },
                body: JSON.stringify({ status: status, confirmed_quantity: qty })
            });
            const data = await res.json();
            if (data.status === 'success') {
                alert(data.message);
                window.location.reload();
            } else {
                alert(data.message);
            }
        } catch(e) { alert('통신 오류'); }
    }
}

document.addEventListener('turbo:load', () => {
    if (document.getElementById('store-order-list-container') || 
        document.getElementById('req-pn') || 
        document.querySelector('.btn-approve')) {
        
        if (currentStoreOrderController) {
            currentStoreOrderController.destroy();
        }
        currentStoreOrderController = new StoreOrderController();
    }
});

document.addEventListener('turbo:before-cache', () => {
    if (currentStoreOrderController) {
        currentStoreOrderController.destroy();
        currentStoreOrderController = null;
    }
});