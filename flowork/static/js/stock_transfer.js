document.addEventListener('DOMContentLoaded', () => {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

    document.body.addEventListener('click', async (e) => {
        if (e.target.classList.contains('btn-ship')) {
            if (!confirm('출고 확정하시겠습니까?\n(확정 시 내 매장 재고가 차감됩니다.)')) return;
            await updateStatus(e.target.dataset.id, 'ship');
        }
        if (e.target.classList.contains('btn-reject')) {
            if (!confirm('요청을 거부하시겠습니까?')) return;
            await updateStatus(e.target.dataset.id, 'reject');
        }
        if (e.target.classList.contains('btn-receive')) {
            if (!confirm('물품을 수령하셨습니까?\n(확정 시 내 매장 재고가 증가합니다.)')) return;
            await updateStatus(e.target.dataset.id, 'receive');
        }
    });

    async function updateStatus(id, action) {
        try {
            const res = await fetch(`/api/stock_transfer/${id}/${action}`, {
                method: 'POST',
                headers: { 'X-CSRFToken': csrfToken }
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

    const reqPnInput = document.getElementById('req-pn');
    const searchBtn = document.getElementById('btn-search-prod');
    const searchResults = document.getElementById('search-results');
    const colorSelect = document.getElementById('req-color');
    const sizeSelect = document.getElementById('req-size');
    const submitReqBtn = document.getElementById('btn-submit-request');
    
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
                    item.onclick = () => selectProduct(p.product_number);
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
        
        const url = document.body.dataset.productLookupUrl;
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
            body: JSON.stringify({ product_number: pn })
        });
        const data = await res.json();
        
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
            op.value = c;
            op.textContent = c;
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
                op.value = v.variant_id; 
                op.textContent = v.size;
                sizeSelect.appendChild(op);
            });
            sizeSelect.disabled = false;
        });
        
        sizeSelect.addEventListener('change', () => {
            selectedVariantId = sizeSelect.value;
        });
    }

    if(submitReqBtn) {
        submitReqBtn.addEventListener('click', async () => {
            const sourceId = document.getElementById('req-source-store').value;
            const qty = document.getElementById('req-qty').value;
            
            if(!sourceId || !selectedVariantId || !qty) {
                alert('모든 항목을 입력하세요.'); return;
            }
            
            try {
                const res = await fetch('/api/stock_transfer/request', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                    body: JSON.stringify({
                        source_store_id: sourceId,
                        variant_id: selectedVariantId,
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
        });
    }
});