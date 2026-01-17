document.addEventListener('DOMContentLoaded', () => {
    
    const bodyData = document.body.dataset;
    const setBrandNameUrl = bodyData.apiBrandNameSetUrl;
    
    const addStoreUrl = bodyData.apiStoresAddUrl;
    const updateStoreUrlPrefix = bodyData.apiStoreUpdateUrlPrefix;
    const deleteStoreUrlPrefix = bodyData.apiStoreDeleteUrlPrefix;

    // (신규) 직원 API URL
    const addStaffUrl = bodyData.apiStaffAddUrl;
    const updateStaffUrlPrefix = bodyData.apiStaffUpdateUrlPrefix;
    const deleteStaffUrlPrefix = bodyData.apiStaffDeleteUrlPrefix;

    const brandNameForm = document.getElementById('form-brand-name');
    const brandNameStatus = document.getElementById('brand-name-status');

    const addStoreForm = document.getElementById('form-add-store');
    const addStoreStatus = document.getElementById('add-store-status');
    const storesTableBody = document.getElementById('all-stores-table')?.querySelector('tbody');
    const deleteStoreStatus = document.getElementById('delete-store-status');
    
    const editModalEl = document.getElementById('edit-store-modal');
    const editModal = editModalEl ? new bootstrap.Modal(editModalEl) : null;
    const editForm = document.getElementById('form-edit-store');
    const editNameInput = document.getElementById('edit_store_name');
    const editPhoneInput = document.getElementById('edit_store_phone');
    const editHqInput = document.getElementById('edit_is_hq');
    const editStatus = document.getElementById('edit-store-status');
    const editSaveBtn = document.getElementById('btn-save-edit-store');

    // (신규) 직원 관련 DOM 요소
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

    if (brandNameForm) {
        brandNameForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const brandName = document.getElementById('brand-name-input').value.trim();
            if (!brandName) {
                alert('브랜드 이름을 입력하세요.');
                return;
            }
            
            const btn = document.getElementById('btn-save-brand-name');
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 저장 중...';
            brandNameStatus.innerHTML = '';

            try {
                const response = await fetch(setBrandNameUrl, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ brand_name: brandName })
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.message || '저장 실패');
                
                brandNameStatus.innerHTML = `<div class="alert alert-success mt-2">${data.message}</div>`;

                const headerShopName = document.querySelector('.header-shop-name');
                if (headerShopName) headerShopName.textContent = data.brand_name;

            } catch (error) {
                console.error('Brand name save error:', error);
                brandNameStatus.innerHTML = `<div class="alert alert-danger mt-2">오류: ${error.message}</div>`;
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<i class="bi bi-save-fill me-1"></i> 브랜드 이름 저장';
            }
        });
    }

    if (addStoreForm) {
        addStoreForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const nameInput = document.getElementById('new_store_name');
            const phoneInput = document.getElementById('new_store_phone');
            const hqInput = document.getElementById('new_is_hq');

            const storeName = nameInput.value.trim();
            const storePhone = phoneInput.value.trim();
            const isHq = hqInput.checked;

            if (!storeName) {
                alert('매장 이름은 필수입니다.');
                return;
            }

            const btn = document.getElementById('btn-add-store');
            btn.disabled = true;
            addStoreStatus.innerHTML = '<div class="alert alert-info">추가 중...</div>';

            try {
                const response = await fetch(addStoreUrl, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        store_name: storeName,
                        store_phone: storePhone,
                        is_hq: isHq
                    })
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.message || '추가 실패');
                
                addStoreStatus.innerHTML = `<div class="alert alert-success">${data.message}</div>`;
                
                nameInput.value = '';
                phoneInput.value = '';
                hqInput.checked = false;
                
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

            if (deleteBtn) {
                handleDeleteStore(deleteBtn);
            } else if (editBtn) {
                handleOpenEditModal(editBtn);
            }
        });
    }

    async function handleDeleteStore(button) {
        const storeId = button.dataset.id;
        const storeName = button.dataset.name;
        
        if (!confirm(`[${storeName}] 매장 정보를 정말 삭제하시겠습니까?\n(ID: ${storeId})`)) {
            return;
        }

        button.disabled = true;
        deleteStoreStatus.innerHTML = '<div class="alert alert-info">삭제 중...</div>';
        
        try {
            const response = await fetch(`${deleteStoreUrlPrefix}${storeId}`, {
                method: 'DELETE'
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.message || '삭제 실패');

            deleteStoreStatus.innerHTML = `<div class="alert alert-success">${data.message}</div>`;
            
            document.getElementById(`store-row-${storeId}`).remove();
            
            if (storesTableBody.querySelectorAll('tr').length === 0) {
                storesTableBody.innerHTML = `
                    <tr id="no-other-stores">
                        <td colspan="4" class="text-center text-muted">등록된 매장이 없습니다.</td>
                    </tr>`;
            }

        } catch (error) {
            console.error('Delete store error:', error);
            deleteStoreStatus.innerHTML = `<div class="alert alert-danger">삭제 실패: ${error.message}</div>`;
            button.disabled = false;
        }
    }

    function handleOpenEditModal(button) {
        const storeId = button.dataset.id;
        const storeName = button.dataset.name;
        const storePhone = button.dataset.phone;
        const isHq = button.dataset.hq === 'true';

        editNameInput.value = storeName;
        editPhoneInput.value = storePhone;
        editHqInput.checked = isHq;
        editSaveBtn.dataset.storeId = storeId;
        editStatus.innerHTML = '';
    }

    if (editSaveBtn) {
        editSaveBtn.addEventListener('click', async () => {
            const storeId = editSaveBtn.dataset.storeId;
            const storeName = editNameInput.value.trim();
            const storePhone = editPhoneInput.value.trim();
            const isHq = editHqInput.checked;
            
            if (!storeName) {
                editStatus.innerHTML = `<div class="alert alert-danger">매장 이름은 필수입니다.</div>`;
                return;
            }

            editSaveBtn.disabled = true;
            editStatus.innerHTML = '<div class="alert alert-info">저장 중...</div>';

            try {
                const response = await fetch(`${updateStoreUrlPrefix}${storeId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        store_name: storeName,
                        store_phone: storePhone,
                        is_hq: isHq
                    })
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.message || '저장 실패');
                
                editStatus.innerHTML = `<div class="alert alert-success">${data.message}</div>`;
                
                const row = document.getElementById(`store-row-${storeId}`);
                if (row) {
                    row.querySelector('[data-field="name"]').textContent = data.store.store_name;
                    row.querySelector('[data-field="phone"]').textContent = data.store.store_phone;
                    row.querySelector('[data-field="hq"]').innerHTML = data.store.is_hq ? '<i class="bi bi-check-circle-fill text-info"></i>' : '';

                    const editBtn = row.querySelector('.btn-edit-store');
                    editBtn.dataset.name = data.store.store_name;
                    editBtn.dataset.phone = data.store.store_phone;
                    editBtn.dataset.hq = data.store.is_hq ? 'true' : 'false';
                }
                
                setTimeout(() => {
                    if (editModal) editModal.hide();
                    window.location.reload();
                }, 1000);

            } catch (error) {
                console.error('Edit store error:', error);
                editStatus.innerHTML = `<div class="alert alert-danger">수정 실패: ${error.message}</div>`;
            } finally {
                editSaveBtn.disabled = false;
            }
        });
    }


    function addStoreRowToTable(store) {
        const noItemRow = document.getElementById('no-other-stores');
        if (noItemRow) {
            noItemRow.remove();
        }

        const hqIcon = store.is_hq ? '<i class="bi bi-check-circle-fill text-info"></i>' : '';

        const newRowHtml = `
            <tr id="store-row-${store.store_id}">
                <td data-field="name">${store.store_name}</td>
                <td data-field="phone">${store.store_phone}</td>
                <td data-field="hq" class="text-center">${hqIcon}</td>
                <td>
                    <button class="btn btn-info btn-sm py-0 px-1 btn-edit-store" 
                            data-bs-toggle="modal" data-bs-target="#edit-store-modal"
                            data-id="${store.store_id}"
                            data-name="${store.store_name}"
                            data-phone="${store.store_phone}"
                            data-hq="${store.is_hq ? 'true' : 'false'}">
                        <i class="bi bi-pencil-fill"></i>
                    </button>
                    <button class="btn btn-danger btn-sm py-0 px-1 btn-delete-store"
                            data-id="${store.store_id}"
                            data-name="${store.store_name}">
                        <i class="bi bi-trash-fill"></i>
                    </button>
                </td>
            </tr>`;
        storesTableBody.insertAdjacentHTML('beforeend', newRowHtml);
    }

    // --- (신규) 직원 관리 스크립트 ---

    if (addStaffForm) {
        addStaffForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const nameInput = document.getElementById('new_staff_name');
            const positionInput = document.getElementById('new_staff_position');
            const contactInput = document.getElementById('new_staff_contact');

            const staffName = nameInput.value.trim();
            const staffPosition = positionInput.value.trim();
            const staffContact = contactInput.value.trim();

            if (!staffName) {
                alert('직원 이름은 필수입니다.');
                return;
            }

            const btn = document.getElementById('btn-add-staff');
            btn.disabled = true;
            addStaffStatus.innerHTML = '<div class="alert alert-info">추가 중...</div>';

            try {
                const response = await fetch(addStaffUrl, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name: staffName,
                        position: staffPosition,
                        contact: staffContact
                    })
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.message || '추가 실패');
                
                addStaffStatus.innerHTML = `<div class="alert alert-success">${data.message}</div>`;
                
                nameInput.value = '';
                positionInput.value = '';
                contactInput.value = '';
                
                addStaffRowToTable(data.staff);

            } catch (error) {
                console.error('Add staff error:', error);
                addStaffStatus.innerHTML = `<div class="alert alert-danger">추가 실패: ${error.message}</div>`;
            } finally {
                btn.disabled = false;
            }
        });
    }

    if (staffTableBody) {
        staffTableBody.addEventListener('click', (e) => {
            const deleteBtn = e.target.closest('.btn-delete-staff');
            const editBtn = e.target.closest('.btn-edit-staff');

            if (deleteBtn) {
                handleDeleteStaff(deleteBtn);
            } else if (editBtn) {
                handleOpenEditStaffModal(editBtn);
            }
        });
    }

    async function handleDeleteStaff(button) {
        const staffId = button.dataset.id;
        const staffName = button.dataset.name;
        
        if (!confirm(`[${staffName}] 직원을 정말 삭제(비활성)하시겠습니까?\n(ID: ${staffId})\n삭제된 직원은 일정 배정 시 나타나지 않습니다.`)) {
            return;
        }

        button.disabled = true;
        deleteStaffStatus.innerHTML = '<div class="alert alert-info">삭제 중...</div>';
        
        try {
            const response = await fetch(`${deleteStaffUrlPrefix}${staffId}`, {
                method: 'DELETE'
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.message || '삭제 실패');

            deleteStaffStatus.innerHTML = `<div class="alert alert-success">${data.message}</div>`;
            
            document.getElementById(`staff-row-${staffId}`).remove();
            
            if (staffTableBody.querySelectorAll('tr').length === 0) {
                staffTableBody.innerHTML = `
                    <tr id="no-staff">
                        <td colspan="4" class="text-center text-muted">등록된 직원이 없습니다.</td>
                    </tr>`;
            }

        } catch (error) {
            console.error('Delete staff error:', error);
            deleteStaffStatus.innerHTML = `<div class="alert alert-danger">삭제 실패: ${error.message}</div>`;
            button.disabled = false;
        }
    }

    function handleOpenEditStaffModal(button) {
        const staffId = button.dataset.id;
        const staffName = button.dataset.name;
        const staffPosition = button.dataset.position;
        const staffContact = button.dataset.contact;

        editStaffNameInput.value = staffName;
        editStaffPositionInput.value = staffPosition;
        editStaffContactInput.value = staffContact;
        editStaffSaveBtn.dataset.staffId = staffId;
        editStaffStatus.innerHTML = '';
    }

    if (editStaffSaveBtn) {
        editStaffSaveBtn.addEventListener('click', async () => {
            const staffId = editStaffSaveBtn.dataset.staffId;
            const staffName = editStaffNameInput.value.trim();
            const staffPosition = editStaffPositionInput.value.trim();
            const staffContact = editStaffContactInput.value.trim();
            
            if (!staffName) {
                editStaffStatus.innerHTML = `<div class="alert alert-danger">직원 이름은 필수입니다.</div>`;
                return;
            }

            editStaffSaveBtn.disabled = true;
            editStaffStatus.innerHTML = '<div class="alert alert-info">저장 중...</div>';

            try {
                const response = await fetch(`${updateStaffUrlPrefix}${staffId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name: staffName,
                        position: staffPosition,
                        contact: staffContact
                    })
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.message || '저장 실패');
                
                editStaffStatus.innerHTML = `<div class="alert alert-success">${data.message}</div>`;
                
                const row = document.getElementById(`staff-row-${staffId}`);
                if (row) {
                    row.querySelector('[data-field="name"]').textContent = data.staff.name;
                    row.querySelector('[data-field="position"]').textContent = data.staff.position;
                    row.querySelector('[data-field="contact"]').textContent = data.staff.contact;

                    const editBtn = row.querySelector('.btn-edit-staff');
                    editBtn.dataset.name = data.staff.name;
                    editBtn.dataset.position = data.staff.position;
                    editBtn.dataset.contact = data.staff.contact;
                }
                
                setTimeout(() => {
                    if (editStaffModal) editStaffModal.hide();
                }, 1000);

            } catch (error) {
                console.error('Edit staff error:', error);
                editStaffStatus.innerHTML = `<div class="alert alert-danger">수정 실패: ${error.message}</div>`;
            } finally {
                editStaffSaveBtn.disabled = false;
            }
        });
    }

    function addStaffRowToTable(staff) {
        const noItemRow = document.getElementById('no-staff');
        if (noItemRow) {
            noItemRow.remove();
        }

        const newRowHtml = `
            <tr id="staff-row-${staff.id}">
                <td data-field="name">${staff.name}</td>
                <td data-field="position">${staff.position}</td>
                <td data-field="contact">${staff.contact}</td>
                <td>
                    <button class="btn btn-info btn-sm py-0 px-1 btn-edit-staff" 
                            data-bs-toggle="modal" data-bs-target="#edit-staff-modal"
                            data-id="${staff.id}"
                            data-name="${staff.name}"
                            data-position="${staff.position}"
                            data-contact="${staff.contact}">
                        <i class="bi bi-pencil-fill"></i>
                    </button>
                    <button class="btn btn-danger btn-sm py-0 px-1 btn-delete-staff"
                            data-id="${staff.id}"
                            data-name="${staff.name}">
                        <i class="bi bi-trash-fill"></i>
                    </button>
                </td>
            </tr>`;
        staffTableBody.insertAdjacentHTML('beforeend', newRowHtml);
    }
    // --- 직원 관리 스크립트 끝 ---

});