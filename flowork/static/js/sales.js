document.addEventListener('DOMContentLoaded', () => {
    
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

    const urls = JSON.parse(document.body.dataset.apiUrls);
    
    let currentMode = 'sales';
    let cart = []; 
    let heldCart = null;
    let isOnline = false;
    let currentRefundSaleId = null;
    let salesConfig = { amount_discounts: [] };

    const dom = {
        leftPanel: document.getElementById('sales-left-panel'),
        dateAreaSales: document.getElementById('date-area-sales'),
        dateAreaRefund: document.getElementById('date-area-refund'),
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
        totalAmount: document.getElementById('total-amount'),
        
        salesActions: document.getElementById('sales-actions'),
        refundActions: document.getElementById('refund-actions'),
        refundTargetInfo: document.getElementById('refund-target-info'),
        
        btnSubmitSale: document.getElementById('btn-submit-sale'),
        btnSubmitRefund: document.getElementById('btn-submit-refund'),
        btnCancelRefund: document.getElementById('btn-cancel-refund'),
        btnToggleOnline: document.getElementById('btn-toggle-online'),
        btnClearCart: document.getElementById('btn-clear-cart'),
        
        btnHoldSale: document.getElementById('btn-hold-sale'),
        btnApplyDiscount: document.getElementById('btn-apply-discount'),

        detailModal: new bootstrap.Modal(document.getElementById('detail-modal')),
        detailModalTitle: document.getElementById('detail-modal-title'),
        detailModalTbody: document.getElementById('detail-modal-tbody'),

        recordsModal: new bootstrap.Modal(document.getElementById('records-modal')),
        recordsModalTitle: document.getElementById('records-modal-title'),
        recordsModalTbody: document.getElementById('records-modal-tbody'),
        
        settingsModal: new bootstrap.Modal(document.getElementById('settings-modal')),
    };

    const today = new Date();
    const oneMonthAgo = new Date();
    oneMonthAgo.setMonth(today.getMonth() - 1);
    
    dom.saleDate.valueAsDate = today;
    dom.refundEnd.valueAsDate = today;
    dom.refundStart.valueAsDate = oneMonthAgo;
    
    loadSettings();

    dom.modeSales.addEventListener('change', () => setMode('sales'));
    dom.modeRefund.addEventListener('change', () => setMode('refund'));
    
    dom.searchInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') performSearch(); });
    dom.btnSearch.addEventListener('click', performSearch);
    
    dom.btnToggleOnline.addEventListener('click', () => {
        isOnline = !isOnline;
        dom.btnToggleOnline.textContent = isOnline ? 'ONLINE' : 'OFFLINE';
        dom.btnToggleOnline.classList.toggle('btn-outline-dark');
        dom.btnToggleOnline.classList.toggle('btn-info');
    });

    dom.btnClearCart.addEventListener('click', () => { cart = []; renderCart(); });

    dom.btnSubmitSale.addEventListener('click', submitSale);
    dom.btnSubmitRefund.addEventListener('click', submitRefund);
    dom.btnCancelRefund.addEventListener('click', resetRefund);
    
    dom.btnHoldSale.addEventListener('click', toggleHoldSale);
    dom.btnApplyDiscount.addEventListener('click', applyAutoDiscount);
    
    document.getElementById('btn-save-settings').addEventListener('click', async () => {
        await loadSettings();
        dom.settingsModal.hide();
    });

    const modals = ['detail-modal', 'records-modal', 'settings-modal'];
    modals.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('hidden.bs.modal', () => {
                if (dom.searchInput) dom.searchInput.focus();
            });
        }
    });

    function setMode(mode) {
        currentMode = mode;
        cart = []; renderCart();
        dom.leftTbody.innerHTML = '';
        dom.searchInput.value = '';

        if (mode === 'sales') {
            dom.leftPanel.className = 'sales-left mode-sales-bg';
            dom.dateAreaSales.style.display = 'block';
            dom.dateAreaRefund.style.display = 'none';
            dom.salesActions.style.display = 'block';
            dom.refundActions.style.display = 'none';
            document.getElementById('right-panel-title').innerHTML = '<i class="bi bi-cart4"></i> 판매 목록';
        } else {
            dom.leftPanel.className = 'sales-left mode-refund-bg';
            dom.dateAreaSales.style.display = 'none';
            dom.dateAreaRefund.style.display = 'block';
            dom.salesActions.style.display = 'none';
            dom.refundActions.style.display = 'flex';
            document.getElementById('right-panel-title').innerHTML = '<i class="bi bi-arrow-return-left"></i> 환불 목록';
        }
    }

    async function performSearch() {
        const query = dom.searchInput.value.trim();
        if (!query) return;

        if (currentMode === 'sales') {
            dom.leftThead.innerHTML = `<tr><th>품번</th><th>품명</th><th>컬러</th><th>년도</th><th>최초가</th><th>판매가</th><th>재고</th></tr>`;
        } else {
            dom.leftThead.innerHTML = `<tr><th>품번</th><th>품명</th><th>컬러</th><th>년도</th><th>최초가</th><th>판매가</th><th>판매량</th></tr>`;
        }
        dom.leftTbody.innerHTML = '<tr><td colspan="7" class="text-center">검색 중...</td></tr>';

        try {
            const payload = {
                query: query,
                mode: currentMode,
                start_date: dom.refundStart.value,
                end_date: dom.refundEnd.value
            };

            const res = await fetch(urls.searchSalesProducts, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(payload)
            });
            const data = await res.json();

            dom.leftTbody.innerHTML = '';
            if (data.results.length === 0) {
                dom.leftTbody.innerHTML = '<tr><td colspan="7" class="text-center">검색 결과가 없습니다.</td></tr>';
                return;
            }

            data.results.forEach(item => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td class="fw-bold">${item.product_number}</td>
                    <td>${item.product_name}</td>
                    <td>${item.color}</td>
                    <td>${item.year || '-'}</td>
                    <td class="text-end">${item.original_price.toLocaleString()}</td>
                    <td class="text-end">${item.sale_price.toLocaleString()}</td>
                    <td class="text-center fw-bold">${item.stat_qty}</td>
                `;
                tr.addEventListener('click', () => handleClickResult(item));
                dom.leftTbody.appendChild(tr);
            });

        } catch (e) {
            console.error(e);
            dom.leftTbody.innerHTML = '<tr><td colspan="7" class="text-center text-danger">오류 발생</td></tr>';
        }
    }

    async function handleClickResult(item) {
        if (currentMode === 'sales') {
            dom.detailModalTitle.textContent = `${item.product_name} (${item.product_number})`;
            dom.detailModalTbody.innerHTML = '<tr><td colspan="6">로딩중...</td></tr>';
            dom.detailModal.show();

            const res = await fetch(urls.searchSalesProducts, { 
                method: 'POST', 
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ query: item.product_number, mode: 'detail_stock' })
            });
            const data = await res.json();
            
            dom.detailModalTbody.innerHTML = '';
            data.variants.forEach(v => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${v.color}</td>
                    <td>${v.size}</td>
                    <td>${v.original_price.toLocaleString()}</td>
                    <td>${v.sale_price.toLocaleString()}</td>
                    <td class="${v.stock <= 0 ? 'text-danger' : ''}">${v.stock}</td>
                    <td><button class="btn btn-sm btn-primary btn-add">추가</button></td>
                `;
                const addHandler = () => {
                    addToCart({...item, ...v, quantity: 1});
                    dom.detailModal.hide();
                };
                tr.querySelector('.btn-add').addEventListener('click', addHandler);
                tr.addEventListener('dblclick', addHandler);
                dom.detailModalTbody.appendChild(tr);
            });

        } else {
            dom.recordsModalTitle.textContent = `판매 기록: ${item.product_number} (${item.color})`;
            dom.recordsModalTbody.innerHTML = '<tr><td colspan="8">조회중...</td></tr>';
            dom.recordsModal.show();

            const res = await fetch(urls.getRefundRecords, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    product_number: item.product_number,
                    color: item.color,
                    start_date: dom.refundStart.value,
                    end_date: dom.refundEnd.value
                })
            });
            const data = await res.json();
            
            dom.recordsModalTbody.innerHTML = '';
            if(data.records.length === 0) {
                dom.recordsModalTbody.innerHTML = '<tr><td colspan="8">해당 기간 내 판매 기록이 없습니다.</td></tr>';
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
                    <td class="text-end">${rec.total_amount.toLocaleString()}</td>
                `;
                tr.addEventListener('click', async () => {
                    await loadRefundCart(rec.sale_id, rec.receipt_number);
                    dom.recordsModal.hide();
                });
                dom.recordsModalTbody.appendChild(tr);
            });
        }
    }

    async function loadRefundCart(saleId, receiptNumber) {
        const res = await fetch(urls.saleDetails.replace('999999', saleId));
        const data = await res.json();
        if (data.status === 'success') {
            currentRefundSaleId = saleId;
            dom.refundTargetInfo.textContent = receiptNumber;
            cart = data.items.map(i => ({
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
            renderCart();
        }
    }

    function addToCart(item) {
        const existing = cart.find(c => c.variant_id === item.variant_id);
        if (existing) existing.quantity++;
        else {
            cart.push({
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
        renderCart();
    }

    function renderCart() {
        dom.cartTbody.innerHTML = '';
        let totalQty = 0;
        let totalAmt = 0;

        cart.forEach((item, idx) => {
            const orgPrice = item.original_price || item.sale_price;
            const salePrice = item.sale_price;
            let discountRate = 0;
            if (orgPrice > 0 && orgPrice > salePrice) {
                discountRate = Math.round((1 - (salePrice / orgPrice)) * 100);
            }

            const finalUnitPrice = salePrice - item.discount_amount;
            const subtotal = finalUnitPrice * item.quantity;

            totalQty += item.quantity;
            totalAmt += subtotal;

            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${idx + 1}</td>
                <td class="text-start">
                    <strong>${item.product_name}</strong><br>
                    <small class="text-muted">${item.product_number}</small>
                </td>
                <td>${item.color} / ${item.size}</td>
                <td class="text-end text-muted text-decoration-line-through small">${orgPrice.toLocaleString()}</td>
                <td class="text-end fw-bold">${salePrice.toLocaleString()}</td>
                <td><span class="badge bg-secondary">${discountRate}%</span></td>
                <td>
                    <input type="number" class="form-control form-control-sm cart-input discount-input" 
                           value="${item.discount_amount}" min="0" data-idx="${idx}">
                </td>
                <td>
                    <input type="number" class="form-control form-control-sm cart-input qty-input" 
                           value="${item.quantity}" min="1" data-idx="${idx}">
                </td>
                <td><button class="btn btn-sm btn-outline-danger btn-del" data-idx="${idx}">&times;</button></td>
            `;
            dom.cartTbody.appendChild(tr);
        });

        dom.totalQty.textContent = totalQty;
        dom.totalAmount.textContent = totalAmt.toLocaleString();

        dom.cartTbody.querySelectorAll('.qty-input').forEach(el => {
            el.addEventListener('change', (e) => {
                const i = e.target.dataset.idx;
                const val = parseInt(e.target.value);
                if (val > 0) { cart[i].quantity = val; renderCart(); }
            });
        });
        dom.cartTbody.querySelectorAll('.discount-input').forEach(el => {
            el.addEventListener('change', (e) => {
                const i = e.target.dataset.idx;
                const val = parseInt(e.target.value);
                if (val >= 0) { cart[i].discount_amount = val; renderCart(); }
            });
        });
        dom.cartTbody.querySelectorAll('.btn-del').forEach(el => {
            el.addEventListener('click', (e) => {
                cart.splice(e.target.dataset.idx, 1);
                renderCart();
            });
        });
    }
    
    function toggleHoldSale() {
        if (heldCart) {
            if (confirm('보류된 판매 목록을 복원하시겠습니까? (현재 작성 중인 내용은 사라집니다.)')) {
                cart = JSON.parse(heldCart);
                heldCart = null;
                dom.btnHoldSale.innerHTML = '<i class="bi bi-pause-circle"></i> 판매보류';
                dom.btnHoldSale.classList.remove('btn-danger');
                dom.btnHoldSale.classList.add('btn-warning');
                renderCart();
            }
        } else {
            if (cart.length === 0) return alert('보류할 상품이 없습니다.');
            heldCart = JSON.stringify(cart);
            cart = [];
            dom.btnHoldSale.innerHTML = '<i class="bi bi-play-circle"></i> 보류중 (복원)';
            dom.btnHoldSale.classList.remove('btn-warning');
            dom.btnHoldSale.classList.add('btn-danger');
            renderCart();
        }
    }
    
    function applyAutoDiscount() {
        if (cart.length === 0) return alert('상품이 없습니다.');
        
        let currentTotal = cart.reduce((sum, item) => sum + (item.sale_price * item.quantity), 0);
        let appliedRule = null;
        
        if (salesConfig.amount_discounts) {
            const rules = salesConfig.amount_discounts.sort((a, b) => b.limit - a.limit);
            for (const rule of rules) {
                if (currentTotal >= rule.limit) {
                    appliedRule = rule;
                    break;
                }
            }
        }
        
        if (appliedRule) {
            alert(`${appliedRule.limit.toLocaleString()}원 이상 구매: ${appliedRule.discount.toLocaleString()}원 할인이 적용됩니다.`);
            cart[0].discount_amount += appliedRule.discount;
            renderCart();
        } else {
            alert('적용 가능한 할인 규칙이 없습니다.');
        }
    }

    async function loadSettings() {
        try {
            const res = await fetch(urls.salesSettings);
            const data = await res.json();
            if (data.status === 'success') salesConfig = data.config;
        } catch (e) {}
    }

    async function submitSale() {
        if (cart.length === 0) return alert('등록할 상품이 없습니다.');
        if (!confirm('판매를 등록하시겠습니까?')) return;

        try {
            const payload = {
                items: cart.map(i => ({
                    variant_id: i.variant_id,
                    quantity: i.quantity,
                    price: i.sale_price, 
                    discount_amount: i.discount_amount 
                })),
                sale_date: dom.saleDate.value,
                is_online: isOnline
            };

            const res = await fetch(urls.submitSales, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (data.status === 'success') {
                alert('판매가 등록되었습니다.');
                cart = []; renderCart();
            } else {
                alert('오류: ' + data.message);
            }
        } catch (e) { alert('서버 통신 오류'); }
    }

    async function submitRefund() {
        if (!currentRefundSaleId) return alert('환불할 영수증을 선택해주세요.');
        if (!confirm('이 영수증을 전체 환불 처리하시겠습니까?')) return;

        try {
            const res = await fetch(urls.refund.replace('999999', currentRefundSaleId), {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken
                }
            });
            const data = await res.json();
            if (data.status === 'success') {
                alert('환불 처리되었습니다.');
                resetRefund();
            } else {
                alert(data.message);
            }
        } catch(e) { alert('오류 발생'); }
    }

    function resetRefund() {
        currentRefundSaleId = null;
        dom.refundTargetInfo.textContent = '선택되지 않음';
        cart = []; renderCart();
    }
});