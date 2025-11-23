document.addEventListener('DOMContentLoaded', () => {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

    // 1. 출고 확정 / 거부 (Out 페이지)
    document.body.addEventListener('click', async (e) => {
        if (e.target.classList.contains('btn-ship')) {
            if (!confirm('출고 확정하시겠습니까?\n(확정 시 내 매장 재고가 차감됩니다.)')) return;
            await updateStatus(e.target.dataset.id, 'ship');
        }
        if (e.target.classList.contains('btn-reject')) {
            if (!confirm('요청을 거부하시겠습니까?')) return;
            await updateStatus(e.target.dataset.id, 'reject');
        }
        // 2. 입고 확정 (In 페이지)
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

    // 3. 이동 요청 모달 로직 (In 페이지)
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
        
        // 상세 정보 로드 (컬러/사이즈)
        const url = document.body.dataset.productLookupUrl;
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
            body: JSON.stringify({ product_number: pn })
        });
        const data = await res.json();
        
        // (주의: 기존 API는 variant_id를 바로 안 줄 수도 있음. 
        //  정확한 Variant ID 획득을 위해 /api/sales/product_variants 등을 사용하는게 좋으나
        //  여기서는 기존 api_find_product_details 결과를 활용해본다.
        //  만약 id가 없다면 추가 API가 필요함. -> 여기선 sales API 활용 권장)
        
        // 임시: sales API 활용하여 variant ID 확보
        const varRes = await fetch('/api/sales/product_variants', {
             method: 'POST',
             headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
             body: JSON.stringify({ product_id: 9999 }) // 이 로직 수정 필요, 일단 기존 product_search 결과엔 id 있음
        });
        
        // ---------------------------------------------------------
        // (단순화를 위해 product_number로 다시 조회하여 variant list 가져오는 별도 로직 구현)
        // 여기서는 /api/sales/search_products (mode='detail_stock') 을 재활용합니다.
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
                op.value = v.variant_id; // value에 ID 저장
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