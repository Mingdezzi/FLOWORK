document.addEventListener('DOMContentLoaded', () => {
    
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

    const brandSelect = document.getElementById('brand_id');
    const storeSelect = document.getElementById('store_id');
    const apiBaseUrl = document.body.dataset.apiGetStoresUrl || '/api/brands/0/unregistered_stores';
    
    if (!brandSelect || !storeSelect || !apiBaseUrl) {
        console.error("필수 폼 요소를 찾을 수 없습니다.");
        return;
    }

    brandSelect.addEventListener('change', async () => {
        const brandId = brandSelect.value;
        
        if (!brandId) {
            storeSelect.innerHTML = '<option value="">-- 브랜드를 먼저 선택하세요 --</option>';
            storeSelect.disabled = true;
            return;
        }

        storeSelect.innerHTML = '<option value="">매장 목록 로드 중...</option>';
        storeSelect.disabled = true;

        const fetchUrl = apiBaseUrl.replace('/0/', `/${brandId}/`);

        try {
            const response = await fetch(fetchUrl, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken 
                }
            });
            const data = await response.json();

            if (!response.ok || data.status === 'error') {
                throw new Error(data.message || '매장 목록 로드 실패');
            }

            storeSelect.innerHTML = ''; 
            if (data.stores.length === 0) {
                storeSelect.innerHTML = '<option value="">-- 가입 가능한 매장이 없습니다 --</option>';
            } else {
                storeSelect.innerHTML = '<option value="">-- 매장을 선택하세요 --</option>';
                data.stores.forEach(store => {
                    const option = document.createElement('option');
                    option.value = store.id;
                    option.textContent = `${store.name} (코드: ${store.code})`;
                    storeSelect.appendChild(option);
                });
                storeSelect.disabled = false;
            }

        } catch (error) {
            console.error('Fetch unregistered stores error:', error);
            storeSelect.innerHTML = `<option value="">-- ${error.message} --</option>`;
            storeSelect.disabled = true;
        }
    });
});