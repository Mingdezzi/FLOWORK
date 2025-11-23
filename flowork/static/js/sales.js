/**
 * Sales POS Application Logic
 * Refactored to use Class-based structure and Common Utilities
 */

class SalesApp {
    constructor() {
        this.urls = JSON.parse(document.body.dataset.apiUrls);
        this.mode = 'sales'; // 'sales' or 'refund'
        this.cart = [];
        this.heldCart = null;
        this.isOnline = false;
        this.refundSaleId = null;
        this.config = { amount_discounts: [] };
        
        this.dom = this.cacheDom();
        this.init();
    }

    cacheDom() {
        return {
            leftPanel: document.getElementById('sales-left-panel'),
            dateSales: document.getElementById('date-area-sales'),
            dateRefund: document.getElementById('date-area-refund'),
            saleDate: document.getElementById('sale-date'),
            refundStart: document.getElementById('refund-start'),
            refundEnd: document.getElementById('refund-end'),
            modeSales: document.getElementById('mode-sales'),
            modeRefund: document.getElementById('mode-refund'),
            searchInput: document.getElementById('search-input'),
            btnSearch: document.getElementById('btn-search'),
            leftThead: document.getElementById('left-table-head'),
            leftTbody: document.getElementById('left-table-body'),
            cartTbody: document.getElementById('cart-tbody'),
            totalQty: document.getElementById('total-qty'),
            totalAmt: document.getElementById('total-amount'),
            salesActions: document.getElementById('sales-actions'),
            refundActions: document.getElementById('refund-actions'),
            refundInfo: document.getElementById('refund-target-info'),
            btnSubmitSale: document.getElementById('btn-submit-sale'),
            btnSubmitRefund: document.getElementById('btn-submit-refund'),
            btnCancelRefund: document.getElementById('btn-cancel-refund'),
            btnToggleOnline: document.getElementById('btn-toggle-online'),
            btnClearCart: document.getElementById('btn-clear-cart'),
            btnHold: document.getElementById('btn-hold-sale'),
            btnDiscount: document.getElementById('btn-apply-discount'),
            detailModal: new bootstrap.Modal(document.getElementById('detail-modal')),
            recordsModal: new bootstrap.Modal(document.getElementById('records-modal'))
        };
    }

    init() {
        // 날짜 초기화
        const today = new Date();
        const lastMonth = new Date();
        lastMonth.setMonth(today.getMonth() - 1);
        
        this.dom.saleDate.value = Flowork.fmtDate(today);
        this.dom.refundEnd.value = Flowork.fmtDate(today);
        this.dom.refundStart.value = Flowork.fmtDate(lastMonth);

        // 설정 로드
        this.loadSettings();

        // 이벤트 바인딩
        this.dom.modeSales.addEventListener('change', () => this.setMode('sales'));
        this.dom.modeRefund.addEventListener('change', () => this.setMode('refund'));
        
        this.dom.searchInput.addEventListener('keydown', (e) => { if(e.key==='Enter') this.search(); });
        this.dom.btnSearch.addEventListener('click', () => this.search());
        
        this.dom.btnToggleOnline.addEventListener('click', () => this.toggleOnline());
        this.dom.btnClearCart.addEventListener('click', () => { this.cart = []; this.renderCart(); });
        
        this.dom.btnSubmitSale.addEventListener('click', () => this.submitSale());
        this.dom.btnSubmitRefund.addEventListener('click', () => this.submitRefund());
        this.dom.btnCancelRefund.addEventListener('click', () => this.resetRefund());
        
        this.dom.btnHold.addEventListener('click', () => this.toggleHold());
        this.dom.btnDiscount.addEventListener('click', () => this.applyAutoDiscount());

        // 모달 닫힘 이벤트 (포커스 복귀)
        ['detail-modal', 'records-modal'].forEach(id => {
            document.getElementById(id).addEventListener('hidden.bs.modal', () => {
                this.dom.searchInput.focus();
            });
        });
    }

    async loadSettings() {
        try {
            const data = await Flowork.get(this.urls.salesSettings);
            if (data.status === 'success') this.config = data.config;
        } catch (e) { console.error("Settings Load Failed", e); }
    }

    setMode(mode) {
        this.mode = mode;
        this.cart = [];
        this.renderCart();
        this.dom.leftTbody.innerHTML = '';
        this.dom.searchInput.value = '';

        const isSales = (mode === 'sales');
        this.dom.leftPanel.className = isSales ? 'sales-left mode-sales-bg' : 'sales-left mode-refund-bg';
        
        this.dom.dateSales.style.display = isSales ? 'block' : 'none';
        this.dom.dateRefund.style.display = isSales ? 'none' : 'block';
        
        this.dom.salesActions.style.display = isSales ? 'block' : 'none';
        this.dom.refundActions.style.display = isSales ? 'none' : 'flex';
        
        const titleHtml = isSales ? '<i class="bi bi-cart4"></i> 판매 목록' : '<i class="bi bi-arrow-return-left"></i> 환불 목록';
        document.getElementById('right-panel-title').innerHTML = titleHtml;
    }

    toggleOnline() {
        this.isOnline = !this.isOnline;
        const btn = this.dom.btnToggleOnline;
        btn.textContent = this.isOnline ? 'ONLINE' : 'OFFLINE';
        btn.classList.toggle('btn-outline-dark');
        btn.classList.toggle('btn-info');
    }

    async search() {
        const query = this.dom.searchInput.value.trim();
        if (!query) return;

        const headers = this.mode === 'sales' 
            ? ['품번','품명','컬러','년도','최초가','판매가','재고'] 
            : ['품번','품명','컬러','년도','최초가','판매가','판매량'];
        
        this.dom.leftThead.innerHTML = `<tr>${headers.map(h=>`<th>${h}</th>`).join('')}</tr>`;
        this.dom.leftTbody.innerHTML = '<tr><td colspan="7" class="text-center">검색 중...</td></tr>';

        try {
            const payload = {
                query, 
                mode: this.mode,
                start_date: this.dom.refundStart.value,
                end_date: this.dom.refundEnd.value
            };
            
            const data = await Flowork.post(this.urls.searchSalesProducts, payload);
            this.dom.leftTbody.innerHTML = '';

            if (!data.results || data.results.length === 0) {
                this.dom.leftTbody.innerHTML = '<tr><td colspan="7" class="text-center">검색 결과가 없습니다.</td></tr>';
                return;
            }

            data.results.forEach(item => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td class="fw-bold">${item.product_number}</td>
                    <td>${item.product_name}</td>
                    <td>${item.color}</td>
                    <td>${item.year || '-'}</td>
                    <td class="text-end">${Flowork.fmtNum(item.original_price)}</td>
                    <td class="text-end">${Flowork.fmtNum(item.sale_price)}</td>
                    <td class="text-center fw-bold">${item.stat_qty}</td>
                `;
                tr.onclick = () => this.handleResultClick(item);
                this.dom.leftTbody.appendChild(tr);
            });
        } catch (e) {
            this.dom.leftTbody.innerHTML = '<tr><td colspan="7" class="text-center text-danger">오류 발생</td></tr>';
        }
    }

    async handleResultClick(item) {
        if (this.mode === 'sales') {
            this.showDetailModal(item);
        } else {
            this.showRefundRecords(item);
        }
    }

    async showDetailModal(item) {
        const title = document.getElementById('detail-modal-title');
        const tbody = document.getElementById('detail-modal-tbody');
        title.textContent = `${item.product_name} (${item.product_number})`;
        tbody.innerHTML = '<tr><td colspan="6">로딩중...</td></tr>';
        this.dom.detailModal.show();

        try {
            const data = await Flowork.post(this.urls.searchSalesProducts, { 
                query: item.product_number, 
                mode: 'detail_stock' 
            });
            
            tbody.innerHTML = '';
            data.variants.forEach(v => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${v.color}</td>
                    <td>${v.size}</td>
                    <td>${Flowork.fmtNum(v.original_price)}</td>
                    <td>${Flowork.fmtNum(v.sale_price)}</td>
                    <td class="${v.stock <= 0 ? 'text-danger' : ''}">${v.stock}</td>
                    <td><button class="btn btn-sm btn-primary btn-add">추가</button></td>
                `;
                const addHandler = () => {
                    this.addToCart({ ...item, ...v, quantity: 1 });
                    this.dom.detailModal.hide();
                };
                tr.querySelector('.btn-add').onclick = addHandler;
                tr.ondblclick = addHandler;
                tbody.appendChild(tr);
            });
        } catch (e) { tbody.innerHTML = '<tr><td colspan="6">오류 발생</td></tr>'; }
    }

    async showRefundRecords(item) {
        const title = document.getElementById('records-modal-title');
        const tbody = document.getElementById('records-modal-tbody');
        title.textContent = `판매 기록: ${item.product_number} (${item.color})`;
        tbody.innerHTML = '<tr><td colspan="8">조회중...</td></tr>';
        this.dom.recordsModal.show();

        try {
            const data = await Flowork.post(this.urls.getRefundRecords, {
                product_number: item.product_number,
                color: item.color,
                start_date: this.dom.refundStart.value,
                end_date: this.dom.refundEnd.value
            });

            tbody.innerHTML = '';
            if (data.records.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8">기록 없음</td></tr>';
                return;
            }

            data.records.forEach(rec => {
                const tr = document.createElement('tr');
                tr.style.cursor = 'pointer';
                tr.innerHTML = `
                    <td>${rec.sale_date}</td>
                    <td>${rec.receipt_number}</td>
                    <td>${rec.product_number}</td>
                    <td>${rec.product_name}</td>
                    <td>${rec.color}</td>
                    <td>${rec.size}</td>
                    <td>${rec.quantity}</td>
                    <td class="text-end">${Flowork.fmtNum(rec.total_amount)}</td>
                `;
                tr.onclick = async () => {
                    await this.loadRefundCart(rec.sale_id, rec.receipt_number);
                    this.dom.recordsModal.hide();
                };
                tbody.appendChild(tr);
            });
        } catch (e) { tbody.innerHTML = '<tr><td colspan="8">오류 발생</td></tr>'; }
    }

    async loadRefundCart(saleId, receiptNumber) {
        try {
            const url = this.urls.saleDetails.replace('999999', saleId);
            const data = await Flowork.get(url);
            
            if (data.status === 'success') {
                this.refundSaleId = saleId;
                this.dom.refundInfo.textContent = receiptNumber;
                this.cart = data.items.map(i => ({
                    variant_id: i.variant_id,
                    product_name: i.name,
                    product_number: i.pn,
                    color: i.color,
                    size: i.size,
                    original_price: i.original_price || i.price,
                    sale_price: i.price,
                    discount_amount: i.discount_amount,
                    quantity: i.quantity
                }));
                this.renderCart();
            }
        } catch (e) { alert('불러오기 실패'); }
    }

    addToCart(item) {
        const existing = this.cart.find(c => c.variant_id === item.variant_id);
        if (existing) existing.quantity++;
        else {
            this.cart.push({
                variant_id: item.variant_id,
                product_name: item.product_name,
                product_number: item.product_number,
                color: item.color,
                size: item.size,
                original_price: item.original_price,
                sale_price: item.sale_price,
                discount_amount: 0,
                quantity: 1
            });
        }
        this.renderCart();
    }

    renderCart() {
        const tbody = this.dom.cartTbody;
        tbody.innerHTML = '';
        let totalQty = 0;
        let totalAmt = 0;

        this.cart.forEach((item, idx) => {
            const org = item.original_price || item.sale_price;
            const sale = item.sale_price;
            let discountRate = (org > 0 && org > sale) ? Math.round((1 - (sale / org)) * 100) : 0;
            
            const unit = sale - item.discount_amount;
            const sub = unit * item.quantity;
            
            totalQty += item.quantity;
            totalAmt += sub;

            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${idx + 1}</td>
                <td class="text-start">
                    <strong>${item.product_name}</strong><br>
                    <small class="text-muted">${item.product_number}</small>
                </td>
                <td>${item.color} / ${item.size}</td>
                <td class="text-end text-muted text-decoration-line-through small">${Flowork.fmtNum(org)}</td>
                <td class="text-end fw-bold">${Flowork.fmtNum(sale)}</td>
                <td><span class="badge bg-secondary">${discountRate}%</span></td>
                <td><input type="number" class="form-control form-control-sm cart-input disc-in" value="${item.discount_amount}" min="0" data-idx="${idx}"></td>
                <td><input type="number" class="form-control form-control-sm cart-input qty-in" value="${item.quantity}" min="1" data-idx="${idx}"></td>
                <td><button class="btn btn-sm btn-outline-danger btn-del" data-idx="${idx}">&times;</button></td>
            `;
            tbody.appendChild(tr);
        });

        this.dom.totalQty.textContent = Flowork.fmtNum(totalQty);
        this.dom.totalAmt.textContent = Flowork.fmtNum(totalAmt);

        // 이벤트 위임 대신 직접 바인딩 (행 개수가 적으므로)
        tbody.querySelectorAll('.qty-in').forEach(el => {
            el.onchange = (e) => {
                const v = parseInt(e.target.value);
                if (v > 0) { this.cart[e.target.dataset.idx].quantity = v; this.renderCart(); }
            };
        });
        tbody.querySelectorAll('.disc-in').forEach(el => {
            el.onchange = (e) => {
                const v = parseInt(e.target.value);
                if (v >= 0) { this.cart[e.target.dataset.idx].discount_amount = v; this.renderCart(); }
            };
        });
        tbody.querySelectorAll('.btn-del').forEach(el => {
            el.onclick = (e) => {
                this.cart.splice(e.target.dataset.idx, 1);
                this.renderCart();
            };
        });
    }

    toggleHold() {
        const btn = this.dom.btnHold;
        if (this.heldCart) {
            if (confirm('보류된 판매 목록을 복원하시겠습니까?')) {
                this.cart = JSON.parse(this.heldCart);
                this.heldCart = null;
                btn.innerHTML = '<i class="bi bi-pause-circle"></i> 판매보류';
                btn.classList.replace('btn-danger', 'btn-warning');
                this.renderCart();
            }
        } else {
            if (this.cart.length === 0) return alert('상품이 없습니다.');
            this.heldCart = JSON.stringify(this.cart);
            this.cart = [];
            btn.innerHTML = '<i class="bi bi-play-circle"></i> 보류중 (복원)';
            btn.classList.replace('btn-warning', 'btn-danger');
            this.renderCart();
        }
    }

    applyAutoDiscount() {
        if (this.cart.length === 0) return alert('상품이 없습니다.');
        const currentTotal = this.cart.reduce((sum, i) => sum + (i.sale_price * i.quantity), 0);
        
        let rule = null;
        if (this.config.amount_discounts) {
            rule = this.config.amount_discounts.sort((a, b) => b.limit - a.limit).find(r => currentTotal >= r.limit);
        }

        if (rule) {
            alert(`${Flowork.fmtNum(rule.limit)}원 이상: ${Flowork.fmtNum(rule.discount)}원 할인 적용`);
            this.cart[0].discount_amount += rule.discount;
            this.renderCart();
        } else {
            alert('적용 가능한 할인 규칙이 없습니다.');
        }
    }

    async submitSale() {
        if (this.cart.length === 0) return alert('상품이 없습니다.');
        if (!confirm('판매를 등록하시겠습니까?')) return;

        try {
            const payload = {
                items: this.cart.map(i => ({
                    variant_id: i.variant_id,
                    quantity: i.quantity,
                    price: i.sale_price,
                    discount_amount: i.discount_amount
                })),
                sale_date: this.dom.saleDate.value,
                is_online: this.isOnline
            };

            const res = await Flowork.post(this.urls.submitSales, payload);
            if (res.status === 'success') {
                alert('판매 등록 완료');
                this.cart = []; 
                this.renderCart();
            } else {
                alert('오류: ' + res.message);
            }
        } catch (e) { alert('등록 실패'); }
    }

    async submitRefund() {
        if (!this.refundSaleId) return alert('환불할 영수증을 선택하세요.');
        if (!confirm('전체 환불 처리하시겠습니까?')) return;

        try {
            const url = this.urls.refund.replace('999999', this.refundSaleId);
            const res = await Flowork.post(url, {});
            if (res.status === 'success') {
                alert('환불 완료');
                this.resetRefund();
            } else {
                alert(res.message);
            }
        } catch (e) { alert('오류 발생'); }
    }

    resetRefund() {
        this.refundSaleId = null;
        this.dom.refundInfo.textContent = '선택되지 않음';
        this.cart = [];
        this.renderCart();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new SalesApp();
});