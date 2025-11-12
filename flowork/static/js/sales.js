document.addEventListener('DOMContentLoaded', () => {
    const urls = JSON.parse(document.body.dataset.apiUrls);
    
    // State
    let currentMode = 'sales'; // 'sales' or 'refund'
    let cart = []; 
    let isOnline = false;
    let currentRefundSaleId = null;

    // DOM Elements
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

        detailModal: new bootstrap.Modal(document.getElementById('detail-modal')),
        detailModalTitle: document.getElementById('detail-modal-title'),
        detailModalTbody: document.getElementById('detail-modal-tbody'),

        recordsModal: new bootstrap.Modal(document.getElementById('records-modal')),
        recordsModalTitle: document.getElementById('records-modal-title'),
        recordsModalTbody: document.getElementById('records-modal-tbody'),
    };

    // Init Dates
    const today = new Date();
    const oneMonthAgo = new Date();
    oneMonthAgo.setMonth(today.getMonth() - 1);
    
    dom.saleDate.valueAsDate = today;
    dom.refundEnd.valueAsDate = today;
    dom.refundStart.valueAsDate = oneMonthAgo;

    // Event Listeners
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

    function setMode(mode) {
        currentMode = mode;
        cart = []; renderCart(); // 모드 변경 시 카트 초기화
        dom.leftTbody.innerHTML = ''; // 검색 결과 초기화
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
            dom.refundActions.style.display = 'flex'; // flex로 표시
            document.getElementById('right-panel-title').innerHTML = '<i class="bi bi-arrow-return-left"></i> 환불 목록';
        }
    }

    async function performSearch() {
        const query = dom.searchInput.value.trim();
        if (!query) return;

        // 좌측 테이블 헤더 설정
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
                headers: {'Content-Type': 'application/json'},
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
            // 판매모드: 상세 정보 모달 -> 카트 담기
            dom.detailModalTitle.textContent = `${item.product_name} (${item.product_number})`;
            dom.detailModalTbody.innerHTML = '<tr><td colspan="6">로딩중...</td></tr>';
            dom.detailModal.show();

            // 상세 재고 조회 API 호출 (기존 product_variants 사용)
            const res = await fetch(urls.searchSalesProducts, { 
                method: 'POST', 
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ query: item.product_number, mode: 'detail_stock' }) // 상세 조회를 위한 모드
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
                    addToCart({...item, ...v, quantity: 1}); // v contains variant_id, size, prices
                    dom.detailModal.hide();
                };
                tr.querySelector('.btn-add').addEventListener('click', addHandler);
                tr.addEventListener('dblclick', addHandler);
                dom.detailModalTbody.appendChild(tr);
            });

        } else {
            // 환불모드: 판매 기록 목록 조회
            dom.recordsModalTitle.textContent = `판매 기록: ${item.product_number} (${item.color})`;
            dom.recordsModalTbody.innerHTML = '<tr><td colspan="8">조회중...</td></tr>';
            dom.recordsModal.show();

            const res = await fetch(urls.getRefundRecords, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
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
            // 환불 카트 로드 (할인 정보 등 포함)
            cart = data.items.map(i => ({
                variant_id: i.variant_id,
                product_name: i.name,
                product_number: i.pn,
                color: i.color,
                size: i.size,
                original_price: i.original_price || i.price,
                sale_price: i.price, // 단위 판매가
                discount_amount: i.discount_amount,
                quantity: i.quantity
            }));
            renderCart();
        }
    }

    function addToCart(item) {
        // item: variant_id, product_name, product_number, color, size, original_price, sale_price, discount_amount(def 0)
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
                discount_amount: 0, // 추가 할인 초기값
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

        // Event Listeners for Inputs
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

    // API Submission Functions
    async function submitSale() {
        if (cart.length === 0) return alert('등록할 상품이 없습니다.');
        if (!confirm('판매를 등록하시겠습니까?')) return;

        try {
            const payload = {
                items: cart.map(i => ({
                    variant_id: i.variant_id,
                    quantity: i.quantity,
                    price: i.sale_price, // 기본 판매가
                    discount_amount: i.discount_amount // 추가 할인액
                })),
                sale_date: dom.saleDate.value,
                is_online: isOnline
            };

            const res = await fetch(urls.submitSales, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
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
            const res = await fetch(urls.refund.replace('999999', currentRefundSaleId), {method: 'POST'});
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