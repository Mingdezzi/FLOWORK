document.addEventListener('DOMContentLoaded', () => {
    
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

    const bodyData = document.body.dataset;
    
    const setBrandNameUrl = bodyData.apiBrandNameSetUrl;
    
    const addStoreUrl = bodyData.apiStoresAddUrl;
    const updateStoreUrlPrefix = bodyData.apiStoreUpdateUrlPrefix;
    const deleteStoreUrlPrefix = bodyData.apiStoreDeleteUrlPrefix;
    const approveStoreUrlPrefix = bodyData.apiStoreApproveUrlPrefix;
    const toggleStoreActiveUrlPrefix = bodyData.apiStoreToggleActiveUrlPrefix;
    const resetStoreUrlPrefix = bodyData.apiStoreResetUrlPrefix;

    const addStaffUrl = bodyData.apiStaffAddUrl;
    const updateStaffUrlPrefix = bodyData.apiStaffUpdateUrlPrefix;
    const deleteStaffUrlPrefix = bodyData.apiStaffDeleteUrlPrefix;

    const loadSettingsUrl = bodyData.apiLoadSettingsUrl;
    const updateSettingUrl = bodyData.apiSettingUrl;
    const logoUploadUrl = bodyData.apiLogoUploadUrl;

    const brandNameForm = document.getElementById('form-brand-name');
    const brandNameStatus = document.getElementById('brand-name-status');

    const loadSettingsBtn = document.getElementById('btn-load-settings');
    const loadSettingsStatus = document.getElementById('load-settings-status');

    const logoForm = document.getElementById('form-logo-upload');
    const logoStatus = document.getElementById('logo-upload-status');

    const addStoreForm = document.getElementById('form-add-store');
    const addStoreStatus = document.getElementById('add-store-status');
    const storesTableBody = document.getElementById('all-stores-table')?.querySelector('tbody');
    const deleteStoreStatus = document.getElementById('delete-store-status');
    
    const editModalEl = document.getElementById('edit-store-modal');
    const editModal = editModalEl ? new bootstrap.Modal(editModalEl) : null;
    const editForm = document.getElementById('form-edit-store');
    const editCodeInput = document.getElementById('edit_store_code');
    const editNameInput = document.getElementById('edit_store_name');
    const editPhoneInput = document.getElementById('edit_store_phone');
    const editStatus = document.getElementById('edit-store-status');
    const editSaveBtn = document.getElementById('btn-save-edit-store');

    const addStaffForm = document.getElementById('form-add-staff');
    const addStaffStatus = document.getElementById('add-staff-status');
    const staffTableBody = document.getElementById('all-staff-table')?.querySelector('tbody');
    const deleteStaffStatus = document.getElementById('delete-staff-status');
    
    const editStaffModalEl = document.getElementById('edit-staff-modal');
    const editStaffModal = editStaffModalEl ? new bootstrap.Modal(editStaffModalEl) : null;
    const editStaffNameInput = document.getElementById('edit_staff_name');
    const editStaffPositionInput = document.getElementById('edit_staff_position');
    const editStaffContactInput = document.getElementById('edit_staff_contact');
    const editStaffStatus = document.getElementById('edit-staff-status');
    const editStaffSaveBtn = document.getElementById('btn-save-edit-staff');

    const catForm = document.getElementById('form-category-config');
    const catContainer = document.getElementById('cat-buttons-container');
    const btnAddCat = document.getElementById('btn-add-cat-row');
    const catStatus = document.getElementById('category-config-status');
    const catColumns = document.getElementById('cat-columns');


    if (brandNameForm) {
        brandNameForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const brandName = document.getElementById('brand-name-input').value.trim();
            if (!brandName) { alert('브랜드 이름을 입력하세요.'); return; }
            
            const btn = document.getElementById('btn-save-brand-name');
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 저장 중...';
            brandNameStatus.innerHTML = '';

            try {
                const response = await fetch(setBrandNameUrl, {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({ brand_name: brandName })
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.message || '저장 실패');
                
                brandNameStatus.innerHTML = `<div class="alert alert-success mt-2">${data.message}</div>`;
                const headerShopName = document.querySelector('.header-shop-name');
                if (headerShopName) headerShopName.textContent = `${data.brand_name} (본사)`;

            } catch (error) {
                console.error('Brand name save error:', error);
                brandNameStatus.innerHTML = `<div class="alert alert-danger mt-2">오류: ${error.message}</div>`;
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<i class="bi bi-save-fill me-1"></i> 브랜드 이름 저장';
            }
        });
    }

    if (logoForm) {
        logoForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const fileInput = document.getElementById('logo-file-input');
            const file = fileInput.files[0];
            
            if (!file) {
                alert('업로드할 로고 파일을 선택해주세요.');
                return;
            }

            const formData = new FormData();
            formData.append('logo_file', file);

            const btn = document.getElementById('btn-upload-logo');
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 업로드 중...';
            logoStatus.innerHTML = '';

            try {
                const response = await fetch(logoUploadUrl, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrfToken
                    },
                    body: formData
                });
                const data = await response.json();

                if (!response.ok || data.status === 'error') {
                    throw new Error(data.message || '업로드 실패');
                }

                logoStatus.innerHTML = `<div class="alert alert-success mt-2">${data.message}</div>`;

            } catch (error) {
                console.error('Logo upload error:', error);
                logoStatus.innerHTML = `<div class="alert alert-danger mt-2">오류: ${error.message}</div>`;
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<i class="bi bi-upload me-1"></i>로고 업로드';
            }
        });
    }

    if (loadSettingsBtn) {
        loadSettingsBtn.addEventListener('click', async () => {
            if (!confirm('서버에 저장된 브랜드 설정 파일을 로드하여 DB에 적용하시겠습니까?\n(기존 설정이 덮어씌워질 수 있습니다.)')) {
                return;
            }

            loadSettingsBtn.disabled = true;
            loadSettingsStatus.innerHTML = '<div class="alert alert-info">로딩 중...</div>';

            try {
                const response = await fetch(loadSettingsUrl, { 
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrfToken
                    }
                });
                const data = await response.json();

                if (!response.ok) throw new Error(data.message || '설정 로드 실패');

                loadSettingsStatus.innerHTML = `<div class="alert alert-success mt-2">${data.message}</div>`;
            } catch (error) {
                console.error('Settings load error:', error);
                loadSettingsStatus.innerHTML = `<div class="alert alert-danger mt-2">오류: ${error.message}</div>`;
            } finally {
                loadSettingsBtn.disabled = false;
            }
        });
    }

    function addCategoryInputRow(label = '', value = '') {
        const row = document.createElement('div');
        row.className = 'input-group mb-2 cat-row';
        row.innerHTML = `
            <span class="input-group-text">라벨</span>
            <input type="text" class="form-control cat-label" placeholder="예: 신발" value="${label}" required>
            <span class="input-group-text">값</span>
            <input type="text" class="form-control cat-value" placeholder="DB저장값" value="${value}" required>
            <button type="button" class="btn btn-outline-danger btn-remove-cat">
                <i class="bi bi-x-lg"></i>
            </button>
        `;
        catContainer.appendChild(row);
    }

    if (catForm) {
        const savedConfig = window.initialCategoryConfig;

        if (savedConfig) {
            if (savedConfig.columns) {
                catColumns.value = savedConfig.columns;
            }
            if (savedConfig.buttons && Array.isArray(savedConfig.buttons)) {
                catContainer.innerHTML = ''; 
                savedConfig.buttons.forEach(btn => {
                    addCategoryInputRow(btn.label, btn.value);
                });
            }
        } else {
            if (catContainer.children.length === 0) {
                addCategoryInputRow('전체', '전체');
                addCategoryInputRow('신발', '신발');
                addCategoryInputRow('의류', '의류');
                addCategoryInputRow('용품', '용품');
            }
        }

        btnAddCat.addEventListener('click', () => {
            addCategoryInputRow();
        });

        catContainer.addEventListener('click', (e) => {
            if (e.target.closest('.btn-remove-cat')) {
                e.target.closest('.cat-row').remove();
            }
        });

        catForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const rows = catContainer.querySelectorAll('.cat-row');
            const newButtons = [];
            rows.forEach(row => {
                const label = row.querySelector('.cat-label').value.trim();
                const value = row.querySelector('.cat-value').value.trim();
                if (label && value) {
                    newButtons.push({ label, value });
                }
            });

            if (newButtons.length === 0) {
                alert('최소 1개의 버튼이 필요합니다.');
                return;
            }

            const configData = {
                columns: parseInt(catColumns.value),
                buttons: newButtons
            };

            const btn = document.getElementById('btn-save-cat-config');
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 저장 중...';
            catStatus.innerHTML = '';

            try {
                const response = await fetch(updateSettingUrl, {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({
                        key: 'CATEGORY_CONFIG',
                        value: configData
                    })
                });
                const data = await response.json();
                
                if (!response.ok) throw new Error(data.message || '저장 실패');
                
                catStatus.innerHTML = `<div class="alert alert-success mt-2">${data.message}</div>`;

            } catch (error) {
                console.error('Category config save error:', error);
                catStatus.innerHTML = `<div class="alert alert-danger mt-2">오류: ${error.message}</div>`;
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<i class="bi bi-save-fill me-1"></i> 설정 저장';
            }
        });
    }


    if (addStoreForm) {
        addStoreForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const codeInput = document.getElementById('new_store_code');
            const nameInput = document.getElementById('new_store_name');
            const phoneInput = document.getElementById('new_store_phone');

            const storeCode = codeInput.value.trim();
            const storeName = nameInput.value.trim();
            const storePhone = phoneInput.value.trim();

            if (!storeCode || !storeName) { alert('매장 코드와 이름은 필수입니다.'); return; }

            const btn = document.getElementById('btn-add-store');
            btn.disabled = true;
            addStoreStatus.innerHTML = '<div class="alert alert-info">추가 중...</div>';

            try {
                const response = await fetch(addStoreUrl, {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({
                        store_code: storeCode, 
                        store_name: storeName,
                        store_phone: storePhone
                    })
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.message || '추가 실패');
                
                addStoreStatus.innerHTML = `<div class="alert alert-success">${data.message}</div>`;
                codeInput.value = ''; nameInput.value = ''; phoneInput.value = '';
                addStoreRowToTable(data.store); 

            } catch (error) {
                console.error('Add store error:', error);
                addStoreStatus.innerHTML = `<div class="alert alert-danger">추가 실패: ${error.message}</div>`;
            } finally {
                btn.disabled = false;
            }
        });
    }
    
    if (storesTableBody) {
        storesTableBody.addEventListener('click', (e) => {
            const deleteBtn = e.target.closest('.btn-delete-store');
            const editBtn = e.target.closest('.btn-edit-store');
            const approveBtn = e.target.closest('.btn-approve-store');
            const resetBtn = e.target.closest('.btn-reset-store');
            const toggleActiveBtn = e.target.closest('.btn-toggle-active-store');

            if (deleteBtn) handleDeleteStore(deleteBtn);
            else if (editBtn) handleOpenEditModal(editBtn);
            else if (approveBtn) handleApproveStore(approveBtn);
            else if (resetBtn) handleResetStore(resetBtn);
            else if (toggleActiveBtn) handleToggleStoreActive(toggleActiveBtn);
        });
    }

    async function handleDeleteStore(button) {
        const storeId = button.dataset.id;
        const storeName = button.dataset.name;
        if (!confirm(`[${storeName}] 매장을 삭제하시겠습니까?`)) return;

        button.disabled = true;
        deleteStoreStatus.innerHTML = '<div class="alert alert-info">삭제 중...</div>';
        
        try {
            const response = await fetch(`${deleteStoreUrlPrefix}${storeId}`, { 
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': csrfToken
                }
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.message);

            deleteStoreStatus.innerHTML = `<div class="alert alert-success">${data.message}</div>`;
            document.getElementById(`store-row-${storeId}`).remove();
        } catch (error) {
            deleteStoreStatus.innerHTML = `<div class="alert alert-danger">실패: ${error.message}</div>`;
            button.disabled = false;
        }
    }

    function handleOpenEditModal(button) {
        editCodeInput.value = button.dataset.code; 
        editNameInput.value = button.dataset.name;
        editPhoneInput.value = button.dataset.phone;
        editSaveBtn.dataset.storeId = button.dataset.id;
        editStatus.innerHTML = '';
    }

    if (editSaveBtn) {
        editSaveBtn.addEventListener('click', async () => {
            const storeId = editSaveBtn.dataset.storeId;
            const storeCode = editCodeInput.value.trim(); 
            const storeName = editNameInput.value.trim();
            const storePhone = editPhoneInput.value.trim();
            
            if (!storeCode || !storeName) { alert('필수 입력 누락'); return; }

            editSaveBtn.disabled = true;
            editStatus.innerHTML = '<div class="alert alert-info">저장 중...</div>';

            try {
                const response = await fetch(`${updateStoreUrlPrefix}${storeId}`, {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({ store_code: storeCode, store_name: storeName, store_phone: storePhone })
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.message);
                
                editStatus.innerHTML = `<div class="alert alert-success">${data.message}</div>`;
                updateStoreRowInTable(data.store);
                setTimeout(() => { if (editModal) editModal.hide(); }, 1000);

            } catch (error) {
                editStatus.innerHTML = `<div class="alert alert-danger">실패: ${error.message}</div>`;
            } finally {
                editSaveBtn.disabled = false;
            }
        });
    }
    
    async function handleApproveStore(button) {
        const storeId = button.dataset.id;
        if (!confirm(`[${button.dataset.name}] 매장 가입을 승인하시겠습니까?`)) return;
        
        try {
            const response = await fetch(`${approveStoreUrlPrefix}${storeId}`, { 
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken
                }
            });
            if (response.ok) { window.location.reload(); } 
            else { alert('승인 실패'); }
        } catch (e) { console.error(e); }
    }
    
    async function handleToggleStoreActive(button) {
        const storeId = button.dataset.id;
        if (!confirm(`[${button.dataset.name}] 매장 상태를 변경하시겠습니까?`)) return;
        
        try {
            const response = await fetch(`${toggleStoreActiveUrlPrefix}${storeId}`, { 
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken
                }
            });
            if (response.ok) { window.location.reload(); }
        } catch (e) { console.error(e); }
    }

    async function handleResetStore(button) {
        const storeId = button.dataset.id;
        if (!confirm(`[${button.dataset.name}] 매장 등록을 초기화하시겠습니까?\n모든 계정이 삭제됩니다.`)) return;
        
        try {
            const response = await fetch(`${resetStoreUrlPrefix}${storeId}`, { 
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken
                }
            });
            if (response.ok) { window.location.reload(); }
        } catch (e) { console.error(e); }
    }

    function updateStoreRowInTable(store) {
        const row = document.getElementById(`store-row-${store.id}`);
        if (!row) return;
        row.querySelector('[data-field="code"]').textContent = store.store_code;
        row.querySelector('[data-field="name"]').textContent = store.store_name;
        row.querySelector('[data-field="phone"]').textContent = store.phone_number;
        
        const editBtn = row.querySelector('.btn-edit-store');
        if (editBtn) {
            editBtn.dataset.code = store.store_code;
            editBtn.dataset.name = store.store_name;
            editBtn.dataset.phone = store.phone_number;
        }
    }

    function addStoreRowToTable(store) {
        const noItemRow = document.getElementById('no-other-stores');
        if (noItemRow) noItemRow.remove();
        
        const newRowHtml = `
            <tr id="store-row-${store.id}">
                <td data-field="code">${store.store_code}</td>
                <td data-field="name">${store.store_name}</td>
                <td data-field="phone">${store.phone_number}</td>
                <td data-field="manager">${store.manager_name || ''}</td>
                <td class="text-center"><span class="badge bg-light text-dark">X</span></td>
                <td class="text-center"><span class="badge bg-secondary">등록대기</span></td>
                <td>(새로고침 후 작업 가능)</td>
            </tr>`;
        if (storesTableBody) storesTableBody.insertAdjacentHTML('beforeend', newRowHtml);
    }

    if (addStaffForm) {
        addStaffForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const name = document.getElementById('new_staff_name').value.trim();
            const position = document.getElementById('new_staff_position').value.trim();
            const contact = document.getElementById('new_staff_contact').value.trim();

            if (!name) { alert('이름 필수'); return; }
            
            const btn = document.getElementById('btn-add-staff');
            btn.disabled = true;

            try {
                const response = await fetch(addStaffUrl, {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({ name, position, contact })
                });
                const data = await response.json();
                if(response.ok) {
                    addStaffStatus.innerHTML = `<div class="alert alert-success">${data.message}</div>`;
                    window.location.reload();
                } else {
                    throw new Error(data.message);
                }
            } catch (e) {
                addStaffStatus.innerHTML = `<div class="alert alert-danger">${e.message}</div>`;
            } finally {
                btn.disabled = false;
            }
        });
    }
    
    if (staffTableBody) {
        staffTableBody.addEventListener('click', (e) => {
            const deleteBtn = e.target.closest('.btn-delete-staff');
            const editBtn = e.target.closest('.btn-edit-staff');

            if (deleteBtn) handleDeleteStaff(deleteBtn);
            else if (editBtn) handleOpenEditStaffModal(editBtn);
        });
    }

    async function handleDeleteStaff(button) {
        if (!confirm(`[${button.dataset.name}] 직원을 삭제하시겠습니까?`)) return;
        try {
            const response = await fetch(`${deleteStaffUrlPrefix}${button.dataset.id}`, { 
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': csrfToken
                }
            });
            if (response.ok) {
                document.getElementById(`staff-row-${button.dataset.id}`).remove();
            }
        } catch (e) { console.error(e); }
    }

    function handleOpenEditStaffModal(button) {
        editStaffNameInput.value = button.dataset.name;
        editStaffPositionInput.value = button.dataset.position;
        editStaffContactInput.value = button.dataset.contact;
        editStaffSaveBtn.dataset.staffId = button.dataset.id;
        editStaffStatus.innerHTML = '';
    }

    if (editStaffSaveBtn) {
        editStaffSaveBtn.addEventListener('click', async () => {
            const staffId = editStaffSaveBtn.dataset.staffId;
            const name = editStaffNameInput.value.trim();
            const position = editStaffPositionInput.value.trim();
            const contact = editStaffContactInput.value.trim();

            if (!name) { alert('이름 필수'); return; }
            editStaffSaveBtn.disabled = true;

            try {
                const response = await fetch(`${updateStaffUrlPrefix}${staffId}`, {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({ name, position, contact })
                });
                if (response.ok) {
                    window.location.reload();
                } else {
                    alert('수정 실패');
                }
            } catch (e) { console.error(e); } finally {
                editStaffSaveBtn.disabled = false;
            }
        });
    }
});