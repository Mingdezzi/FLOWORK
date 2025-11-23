document.addEventListener('DOMContentLoaded', () => {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    const today = new Date().toISOString().split('T')[0];
    
    // 모달 날짜 초기화
    const dateInput = document.getElementById('req-date');
    if (dateInput) dateInput.value = today;

    // --- 상품 검색/선택 로직 (이전 모듈과 유사) ---
    const reqPnInput = document.getElementById('req-pn');
    const searchBtn = document.getElementById('btn-search-prod');
    const searchResults = document.getElementById('search-results');
    const colorSelect = document.getElementById('req-color');
    const sizeSelect = document.getElementById('req-size');
    
    let selectedVariantId = null;
    let variantsCache = [];

    if (searchBtn) {
        searchBtn.addEventListener('click', async () => {
            const query = reqPnInput.value.trim();
            if (!query) return;
            const url = document.body.dataset.productSearchUrl;
            const res = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                body: JSON.stringify({ query })
            });
            const data = await res.json();
            searchResults.innerHTML = '';
            searchResults.style.display = 'block';
            
            if(data.products) {
                data.products.forEach(p => {
                    const item = document.createElement('button');
                    item.className = 'list-group-item list-group-item-action';
                    item.textContent = `${p.product_name} (${p.product_number})`;
                    item.onclick = (e) => { e.preventDefault(); selectProduct(p.product_number); };
                    searchResults.appendChild(item);
                });
            } else {
                searchResults.innerHTML = '<div class="p-2">검색 결과 없음</div>';
            }
        });
    }

    async function selectProduct(pn) {
        searchResults.style.display = 'none';
        reqPnInput.value = pn;
        // 상세 옵션 로드 (sales API 재활용)
        const detailRes = await fetch('/api/sales/search_products', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
            body: JSON.stringify({ query: pn, mode: 'detail_stock' })
        });
        const detailData = await detailRes.json();
        
        colorSelect.innerHTML = '<option value="">선택</option>';
        sizeSelect.innerHTML = '<option value="">선택</option>';
        colorSelect.disabled = false;
        sizeSelect.disabled = true;
        
        variantsCache = detailData.variants || [];
        const colors = [...new Set(variantsCache.map(v => v.color))];
        colors.forEach(c => {
            const op = document.createElement('option');
            op.value = c; op.textContent = c;
            colorSelect.appendChild(op);
        });
    }

    if(colorSelect) {
        colorSelect.addEventListener('change', () => {
            const color = colorSelect.value;
            sizeSelect.innerHTML = '<option value="">선택</option>';
            const sizes = variantsCache.filter(v => v.color === color);
            sizes.forEach(v => {
                const op = document.createElement('option');
                op.value = v.variant_id; op.textContent = v.size;
                sizeSelect.appendChild(op);
            });
            sizeSelect.disabled = false;
        });
        sizeSelect.addEventListener('change', () => { selectedVariantId = sizeSelect.value; });
    }

    // --- 주문/반품 요청 등록 ---
    const btnSubmit = document.getElementById('btn-submit-order') || document.getElementById('btn-submit-return');
    if (btnSubmit) {
        btnSubmit.addEventListener('click', async () => {
            if (!selectedVariantId) { alert('상품을 선택하세요.'); return; }
            const qty = document.getElementById('req-qty').value;
            const url = document.body.dataset.apiCreate;

            const res = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                body: JSON.stringify({
                    variant_id: selectedVariantId,
                    quantity: qty,
                    date: dateInput.value
                })
            });
            const data = await res.json();
            if (data.status === 'success') {
                alert(data.message);
                window.location.reload();
            } else {
                alert(data.message);
            }
        });
    }

    // --- 관리자: 승인/거절 ---
    document.body.addEventListener('click', async (e) => {
        const urlPrefix = document.body.dataset.apiStatusPrefix;
        if (!urlPrefix) return;

        if (e.target.classList.contains('btn-approve')) {
            const id = e.target.dataset.id;
            const reqQty = e.target.dataset.qty;
            const confQty = prompt('확정 수량을 입력하세요:', reqQty);
            
            if (confQty !== null) {
                await updateStatus(urlPrefix + id + '/status', 'APPROVED', confQty);
            }
        }
        if (e.target.classList.contains('btn-reject')) {
            if (!confirm('거절하시겠습니까?')) return;
            const id = e.target.dataset.id;
            await updateStatus(urlPrefix + id + '/status', 'REJECTED', 0);
        }
    });

    async function updateStatus(url, status, qty) {
        try {
            const res = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
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
});