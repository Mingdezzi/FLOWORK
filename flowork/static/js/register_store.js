let currentRegisterStoreApp = null;

class RegisterStoreApp {
    constructor() {
        this.dom = {
            brandSelect: document.getElementById('brand_id'),
            storeSelect: document.getElementById('store_id')
        };
        this.apiBaseUrl = document.body.dataset.apiGetStoresUrl || '/api/brands/0/unregistered_stores';
        this.csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

        this.boundHandleBrandChange = this.handleBrandChange.bind(this);
        this.init();
    }

    init() {
        if (this.dom.brandSelect && this.dom.storeSelect) {
            this.dom.brandSelect.addEventListener('change', this.boundHandleBrandChange);
        }
    }

    destroy() {
        if (this.dom.brandSelect) {
            this.dom.brandSelect.removeEventListener('change', this.boundHandleBrandChange);
        }
    }

    async handleBrandChange() {
        const brandId = this.dom.brandSelect.value;
        
        if (!brandId) {
            this.dom.storeSelect.innerHTML = '<option value="">-- 브랜드를 먼저 선택하세요 --</option>';
            this.dom.storeSelect.disabled = true;
            return;
        }

        this.dom.storeSelect.innerHTML = '<option value="">매장 목록 로드 중...</option>';
        this.dom.storeSelect.disabled = true;

        const fetchUrl = this.apiBaseUrl.replace('/0/', `/${brandId}/`);

        try {
            const response = await fetch(fetchUrl, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                }
            });
            const data = await response.json();

            if (!response.ok || data.status === 'error') {
                throw new Error(data.message || '매장 목록 로드 실패');
            }

            this.dom.storeSelect.innerHTML = '';
            if (data.stores.length === 0) {
                this.dom.storeSelect.innerHTML = '<option value="">-- 가입 가능한 매장이 없습니다 --</option>';
            } else {
                this.dom.storeSelect.innerHTML = '<option value="">-- 매장을 선택하세요 --</option>';
                data.stores.forEach(store => {
                    const option = document.createElement('option');
                    option.value = store.id;
                    option.textContent = `${store.name} (코드: ${store.code})`;
                    this.dom.storeSelect.appendChild(option);
                });
                this.dom.storeSelect.disabled = false;
            }

        } catch (error) {
            console.error('Fetch unregistered stores error:', error);
            this.dom.storeSelect.innerHTML = `<option value="">-- ${error.message} --</option>`;
            this.dom.storeSelect.disabled = true;
        }
    }
}

document.addEventListener('turbo:load', () => {
    if (document.getElementById('register-store-form')) {
        if (currentRegisterStoreApp) {
            currentRegisterStoreApp.destroy();
        }
        currentRegisterStoreApp = new RegisterStoreApp();
    }
});

document.addEventListener('turbo:before-cache', () => {
    if (currentRegisterStoreApp) {
        currentRegisterStoreApp.destroy();
        currentRegisterStoreApp = null;
    }
});