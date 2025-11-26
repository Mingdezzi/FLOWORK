/**
 * Admin Setting Logic
 * Refactored to use Class-based structure and Common Utilities
 */

class SettingApp {
    constructor() {
        const ds = document.body.dataset;
        this.urls = {
            setBrand: ds.apiBrandNameSetUrl,
            addStore: ds.apiStoresAddUrl,
            updateStore: ds.apiStoreUpdateUrlPrefix,
            delStore: ds.apiStoreDeleteUrlPrefix,
            approveStore: ds.apiStoreApproveUrlPrefix,
            toggleActive: ds.apiStoreToggleActiveUrlPrefix,
            resetStore: ds.apiStoreResetUrlPrefix,
            addStaff: ds.apiStaffAddUrl,
            updateStaff: ds.apiStaffUpdateUrlPrefix,
            delStaff: ds.apiStaffDeleteUrlPrefix,
            loadSettings: ds.apiLoadSettingsUrl,
            updateSetting: ds.apiSettingUrl
        };

        this.dom = this.cacheDom();
        this.init();
    }

    cacheDom() {
        return {
            formBrand: document.getElementById('form-brand-name'),
            btnLoadSettings: document.getElementById('btn-load-settings'),
            statusLoadSettings: document.getElementById('load-settings-status'),
            
            formAddStore: document.getElementById('form-add-store'),
            tableStores: document.getElementById('all-stores-table'),
            statusAddStore: document.getElementById('add-store-status'),
            
            formAddStaff: document.getElementById('form-add-staff'),
            tableStaff: document.getElementById('all-staff-table'),
            statusAddStaff: document.getElementById('add-staff-status'),
            
            formCat: document.getElementById('form-category-config'),
            catContainer: document.getElementById('cat-buttons-container'),
            btnCatAdd: document.getElementById('btn-add-cat-row'),
            catStatus: document.getElementById('category-config-status'),
            
            modalStore: new bootstrap.Modal(document.getElementById('edit-store-modal') || document.createElement('div')),
            modalStaff: new bootstrap.Modal(document.getElementById('edit-staff-modal') || document.createElement('div'))
        };
    }

    init() {
        if(this.dom.formBrand) this.dom.formBrand.addEventListener('submit', (e) => this.setBrandName(e));
        if(this.dom.btnLoadSettings) this.dom.btnLoadSettings.addEventListener('click', () => this.loadSettings());
        if(this.dom.formAddStore) this.dom.formAddStore.addEventListener('submit', (e) => this.addStore(e));
        
        if(this.dom.tableStores) {
            this.dom.tableStores.addEventListener('click', (e) => {
                const btn = e.target.closest('button');
                if(!btn) return;
                if(btn.classList.contains('btn-delete-store')) this.deleteStore(btn);
                if(btn.classList.contains('btn-edit-store')) this.openStoreModal(btn);
                if(btn.classList.contains('btn-approve-store')) this.approveStore(btn);
                if(btn.classList.contains('btn-reset-store')) this.resetStore(btn);
                if(btn.classList.contains('btn-toggle-active-store')) this.toggleStoreActive(btn);
            });
        }

        if(this.dom.formAddStaff) this.dom.formAddStaff.addEventListener('submit', (e) => this.addStaff(e));
        
        if(this.dom.tableStaff) {
            this.dom.tableStaff.addEventListener('click', (e) => {
                const btn = e.target.closest('button');
                if(!btn) return;
                if(btn.classList.contains('btn-delete-staff')) this.deleteStaff(btn);
                if(btn.classList.contains('btn-edit-staff')) this.openStaffModal(btn);
            });
        }

        this.initCategoryForm();
        
        // 모달 저장 버튼 이벤트
        const btnSaveStore = document.getElementById('btn-save-edit-store');
        if(btnSaveStore) btnSaveStore.addEventListener('click', () => this.saveStoreEdit(btnSaveStore));
        
        const btnSaveStaff = document.getElementById('btn-save-edit-staff');
        if(btnSaveStaff) btnSaveStaff.addEventListener('click', () => this.saveStaffEdit(btnSaveStaff));
    }

    async setBrandName(e) {
        e.preventDefault();
        const name = document.getElementById('brand-name-input').value.trim();
        if(!name) return alert('이름 필수');
        
        try {
            const res = await Flowork.post(this.urls.setBrand, { brand_name: name });
            document.getElementById('brand-name-status').innerHTML = `<div class="alert alert-success mt-2">${res.message}</div>`;
        } catch(e) { alert('저장 실패'); }
    }

    async loadSettings() {
        if(!confirm('설정 파일을 로드하시겠습니까?')) return;
        this.dom.btnLoadSettings.disabled = true;
        this.dom.statusLoadSettings.innerHTML = '<div class="alert alert-info">로딩 중...</div>';
        
        try {
            const res = await Flowork.post(this.urls.loadSettings, {});
            this.dom.statusLoadSettings.innerHTML = `<div class="alert alert-success mt-2">${res.message}</div>`;
        } catch(e) {
            this.dom.statusLoadSettings.innerHTML = `<div class="alert alert-danger mt-2">${e.message}</div>`;
        } finally {
            this.dom.btnLoadSettings.disabled = false;
        }
    }

    async addStore(e) {
        e.preventDefault();
        const payload = {
            store_code: document.getElementById('new_store_code').value,
            store_name: document.getElementById('new_store_name').value,
            store_phone: document.getElementById('new_store_phone').value
        };
        
        try {
            const res = await Flowork.post(this.urls.addStore, payload);
            this.dom.statusAddStore.innerHTML = `<div class="alert alert-success">${res.message}</div>`;
            window.location.reload();
        } catch(e) {
            this.dom.statusAddStore.innerHTML = `<div class="alert alert-danger">${e.message}</div>`;
        }
    }

    // ... (스토어 관련 나머지 메서드는 패턴이 동일하므로 Flowork.api 적용) ...
    async deleteStore(btn) {
        if(!confirm('삭제하시겠습니까?')) return;
        try {
            await Flowork.api(`${this.urls.delStore}${btn.dataset.id}`, { method: 'DELETE' });
            btn.closest('tr').remove();
        } catch(e) { alert(e.message); }
    }

    openStoreModal(btn) {
        document.getElementById('edit_store_code').value = btn.dataset.code;
        document.getElementById('edit_store_name').value = btn.dataset.name;
        document.getElementById('edit_store_phone').value = btn.dataset.phone;
        document.getElementById('btn-save-edit-store').dataset.storeId = btn.dataset.id;
    }

    async saveStoreEdit(btn) {
        const id = btn.dataset.storeId;
        const payload = {
            store_code: document.getElementById('edit_store_code').value,
            store_name: document.getElementById('edit_store_name').value,
            store_phone: document.getElementById('edit_store_phone').value
        };
        try {
            await Flowork.post(`${this.urls.updateStore}${id}`, payload);
            window.location.reload();
        } catch(e) { alert(e.message); }
    }

    async approveStore(btn) {
        if(!confirm('승인하시겠습니까?')) return;
        try { await Flowork.post(`${this.urls.approveStore}${btn.dataset.id}`, {}); window.location.reload(); }
        catch(e) { alert(e.message); }
    }

    async resetStore(btn) {
        if(!confirm('초기화하시겠습니까?')) return;
        try { await Flowork.post(`${this.urls.resetStore}${btn.dataset.id}`, {}); window.location.reload(); }
        catch(e) { alert(e.message); }
    }

    async toggleStoreActive(btn) {
        if(!confirm('상태 변경?')) return;
        try { await Flowork.post(`${this.urls.toggleActive}${btn.dataset.id}`, {}); window.location.reload(); }
        catch(e) { alert(e.message); }
    }

    // ... (직원 관련 메서드) ...
    async addStaff(e) {
        e.preventDefault();
        const payload = {
            name: document.getElementById('new_staff_name').value,
            position: document.getElementById('new_staff_position').value,
            contact: document.getElementById('new_staff_contact').value
        };
        try {
            await Flowork.post(this.urls.addStaff, payload);
            window.location.reload();
        } catch(e) { alert(e.message); }
    }

    async deleteStaff(btn) {
        if(!confirm('삭제?')) return;
        try {
            await Flowork.api(`${this.urls.delStaff}${btn.dataset.id}`, { method: 'DELETE' });
            btn.closest('tr').remove();
        } catch(e) { alert(e.message); }
    }

    openStaffModal(btn) {
        document.getElementById('edit_staff_name').value = btn.dataset.name;
        document.getElementById('edit_staff_position').value = btn.dataset.position;
        document.getElementById('edit_staff_contact').value = btn.dataset.contact;
        document.getElementById('btn-save-edit-staff').dataset.staffId = btn.dataset.id;
    }

    async saveStaffEdit(btn) {
        const id = btn.dataset.staffId;
        const payload = {
            name: document.getElementById('edit_staff_name').value,
            position: document.getElementById('edit_staff_position').value,
            contact: document.getElementById('edit_staff_contact').value
        };
        try {
            await Flowork.post(`${this.urls.updateStaff}${id}`, payload);
            window.location.reload();
        } catch(e) { alert(e.message); }
    }

    // 카테고리 설정 로직
    initCategoryForm() {
        if(!this.dom.formCat) return;
        
        const saved = window.initialCategoryConfig;
        const addRow = (l='', v='') => {
            const html = `
                <div class="input-group mb-2 cat-row">
                    <span class="input-group-text">라벨</span><input type="text" class="form-control cat-label" value="${l}">
                    <span class="input-group-text">값</span><input type="text" class="form-control cat-value" value="${v}">
                    <button type="button" class="btn btn-outline-danger btn-remove-cat"><i class="bi bi-x-lg"></i></button>
                </div>`;
            this.dom.catContainer.insertAdjacentHTML('beforeend', html);
        };

        if(saved) {
            if(saved.columns) document.getElementById('cat-columns').value = saved.columns;
            if(saved.buttons) {
                this.dom.catContainer.innerHTML = '';
                saved.buttons.forEach(b => addRow(b.label, b.value));
            }
        } else {
            if(this.dom.catContainer.children.length === 0) {
                ['전체','신발','의류','용품'].forEach(t => addRow(t, t));
            }
        }

        this.dom.btnCatAdd.onclick = () => addRow();
        this.dom.catContainer.onclick = (e) => {
            if(e.target.closest('.btn-remove-cat')) e.target.closest('.cat-row').remove();
        };

        this.dom.formCat.onsubmit = async (e) => {
            e.preventDefault();
            const buttons = [];
            this.dom.catContainer.querySelectorAll('.cat-row').forEach(r => {
                const l = r.querySelector('.cat-label').value.trim();
                const v = r.querySelector('.cat-value').value.trim();
                if(l && v) buttons.push({label: l, value: v});
            });
            
            const config = {
                columns: parseInt(document.getElementById('cat-columns').value),
                buttons: buttons
            };
            
            try {
                await Flowork.post(this.urls.updateSetting, { key: 'CATEGORY_CONFIG', value: config });
                this.dom.catStatus.innerHTML = '<div class="alert alert-success mt-2">저장됨</div>';
            } catch(e) {
                this.dom.catStatus.innerHTML = `<div class="alert alert-danger mt-2">${e.message}</div>`;
            }
        };
    }
}

document.addEventListener('DOMContentLoaded', () => new SettingApp());