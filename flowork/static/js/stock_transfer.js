let currentStockTransferApp = null;

class StockTransferApp {
    constructor() {
        this.csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        this.selectedVariantId = null;
        this.variantsCache = [];

        this.dom = {
            reqPnInput: document.getElementById('req-pn'),
            searchBtn: document.getElementById('btn-search-prod'),
            searchResults: document.getElementById('search-results'),
            colorSelect: document.getElementById('req-color'),
            sizeSelect: document.getElementById('req-size'),
            submitReqBtn: document.getElementById('btn-submit-request')
        };

        this.boundHandleClick = this.handleClick.bind(this);
        this.init();
    }

    init() {
        document.body.addEventListener('click', this.boundHandleClick);

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

        if (this.dom.submitReqBtn) {
            this.dom.submitReqBtn.addEventListener('click', () => this.submitRequest());
        }
    }

    destroy() {
        document.body.removeEventListener('click', this.boundHandleClick);
    }

    async handleClick(e) {
        if (e.target.classList.contains('btn-ship')) {
            if (!confirm('출고 확정하시겠습니까?\n(확정 시 내 매장 재고가 차감됩니다.)')) return;
            await this.updateStatus(e.target.dataset.id, 'ship');
        }
        if (e.target.classList.contains('btn-reject')) {
            if (!confirm('요청을 거부하시겠습니까?')) return;
            await this.updateStatus(e.target.dataset.id, 'reject');
        }
        if (e.target.classList.contains('btn-receive')) {
            if (!confirm('물품을 수령하셨습니까?\n(확정 시 내 매장 재고가 증가합니다.)')) return;
            await this.updateStatus(e.target.dataset.id, 'receive');
        }
    }

    async updateStatus(id, action) {
        try {
            const res = await fetch(`/api/stock_transfer/${id}/${action}`, {
                method: 'POST',
                headers: { 'X-CSRFToken': this.csrfToken }
            });
            const data = await res.json();
            if (data.status === 'success') {
                alert(data.message);
                window.location.reload();
            } else {
                alert(data.message);
            }
        } catch (err) {
            alert('서버 통신 오류');
        }
    }

    async searchProduct() {
        const query = this.dom.reqPnInput.value.trim();
        if (!query) return;
        
        const url = document.body.dataset.productSearchUrl;
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': this.csrfToken },
            body: JSON.stringify({ query })
        });
        const data = await res.json();
        
        this.dom.searchResults.innerHTML = '';
        this.dom.searchResults.style.display = 'block';
        
        if(data.products) {
            data.products.forEach(p => {
                const item = document.createElement('button');
                item.className = 'list-group-item list-group-item-action';
                item.textContent = `${p.product_name} (${p.product_number})`;
                item.onclick = () => this.selectProduct(p.product_number);
                this.dom.searchResults.appendChild(item);
            });
        } else {
            this.dom.searchResults.innerHTML = '<div class="p-2">검색 결과 없음</div>';
        }
    }

    async selectProduct(pn) {
        this.dom.searchResults.style.display = 'none';
        this.dom.reqPnInput.value = pn;
        
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
        const sourceId = document.getElementById('req-source-store').value;
        const qty = document.getElementById('req-qty').value;
        
        if(!sourceId || !this.selectedVariantId || !qty) {
            alert('모든 항목을 입력하세요.'); return;
        }
        
        try {
            const res = await fetch('/api/stock_transfer/request', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': this.csrfToken },
                body: JSON.stringify({
                    source_store_id: sourceId,
                    variant_id: this.selectedVariantId,
                    quantity: qty
                })
            });
            const data = await res.json();
            if(data.status === 'success') {
                alert('요청되었습니다.');
                window.location.reload();
            } else {
                alert(data.message);
            }
        } catch(e) { alert('오류 발생'); }
    }
}

document.addEventListener('turbo:load', () => {
    if (document.querySelector('.btn-ship') || 
        document.querySelector('.btn-receive') || 
        document.getElementById('requestModal')) {
        
        if (currentStockTransferApp) {
            currentStockTransferApp.destroy();
        }
        currentStockTransferApp = new StockTransferApp();
    }
});

document.addEventListener('turbo:before-cache', () => {
    if (currentStockTransferApp) {
        currentStockTransferApp.destroy();
        currentStockTransferApp = null;
    }
});