document.addEventListener('DOMContentLoaded', () => {
    
    const bodyData = document.body.dataset;
    const updateStockUrl = bodyData.updateStockUrl;
    const toggleFavoriteUrl = bodyData.toggleFavoriteUrl;
    const updateActualStockUrl = bodyData.updateActualStockUrl;
    const updateProductDetailsUrl = bodyData.updateProductDetailsUrl;
    const currentProductID = bodyData.productId;

     const stockTable = document.querySelector('.stock-table tbody');
     if (stockTable) {
         stockTable.addEventListener('click', function(e) {
             const stockButton = e.target.closest('button.btn-inc, button.btn-dec');
             if (stockButton) {
                 const barcode = stockButton.dataset.barcode;
                 const change = parseInt(stockButton.dataset.change, 10);
                 const changeText = change === 1 ? "증가" : "감소";
                 if (confirm(`[${barcode}] 상품의 재고를 1 ${changeText}시키겠습니까?`)) {
                     const allButtonsInStack = stockButton.closest('.button-stack').querySelectorAll('button');
                     allButtonsInStack.forEach(btn => btn.disabled = true);
                     updateStockOnServer(barcode, change, allButtonsInStack);
                 }
             }
             const saveButton = e.target.closest('button.btn-save-actual');
             if (saveButton && !saveButton.disabled) {
                 const barcode = saveButton.dataset.barcode;
                 const inputElement = document.getElementById(`actual-${barcode}`);
                 const actualStockValue = inputElement.value;
                 
                 // (수정) 유효성 검사 추가
                if (actualStockValue !== '' && (isNaN(actualStockValue) || parseInt(actualStockValue) < 0)) {
                    alert('실사재고는 0 이상의 숫자만 입력 가능합니다.');
                    inputElement.focus();
                    inputElement.select();
                    return;
                }
                 
                 saveButton.disabled = true;
                 saveActualStock(barcode, actualStockValue, saveButton, inputElement);
             }
         });
     }

     const favButton = document.getElementById('fav-btn');
     if (favButton) {
         favButton.addEventListener('click', function(e) {
             const isFavorite = favButton.classList.contains('btn-warning');
             const actionText = isFavorite ? '즐겨찾기에서 해제' : '즐겨찾기에 추가';
             if (confirm(`⭐ 이 상품을 ${actionText}하시겠습니까?`)) {
                const button = e.target.closest('button');
                const productID = button.dataset.productId;
                button.disabled = true;
                toggleFavoriteOnServer(productID, button);
             }
         });
     }

    const editProductBtn = document.getElementById('edit-product-btn');
    const saveProductBtn = document.getElementById('save-product-btn');
    const cancelEditBtn = document.getElementById('cancel-edit-btn');
    const variantsTbody = document.getElementById('variants-tbody');
    const addVariantBtn = document.getElementById('btn-add-variant');
    const addVariantRow = document.getElementById('add-variant-row');
    const toggleActualStockBtn = document.getElementById('toggle-actual-stock-btn');

    if (editProductBtn) {
        editProductBtn.addEventListener('click', () => {
            if (confirm('✏️ 상품 정보 수정 모드로 전환합니다.\n수정 후에는 반드시 [수정 완료] 버튼을 눌러 저장해주세요.')) {
                document.body.classList.add('edit-mode');
            }
        });
    }

    if (cancelEditBtn) {
        cancelEditBtn.addEventListener('click', () => {
            if (confirm('⚠️ 수정 중인 내용을 취소하고 원래 상태로 되돌립니다.\n계속하시겠습니까?')) {
                document.body.classList.remove('edit-mode');
                window.location.reload();
            }
        });
    }

    if (variantsTbody) {
        variantsTbody.addEventListener('click', (e) => {
            if (e.target.classList.contains('btn-delete-variant') || e.target.closest('.btn-delete-variant')) {
                if (confirm('🗑️ 이 행을 삭제하시겠습니까? [수정 완료]를 눌러야 최종 반영됩니다.')) {
                    const row = e.target.closest('tr');
                    if (row.dataset.variantId) {
                        row.style.display = 'none';
                        row.dataset.action = 'delete';
                    } else {
                        row.remove();
                    }
                }
            }
        });
    }

    if (addVariantBtn) {
         addVariantBtn.addEventListener('click', () => {
            const newColorInput = addVariantRow.querySelector('[data-field="new-color"]');
            const newSizeInput = addVariantRow.querySelector('[data-field="new-size"]');

            const color = newColorInput.value.trim();
            const size = newSizeInput.value.trim();

            if (!color || !size) {
                alert('새 행의 컬러와 사이즈를 입력해주세요.');
                return;
            }

            const newRow = document.createElement('tr');
            newRow.dataset.action = 'add';
            
            newRow.innerHTML = `
                <td class="variant-edit-cell"><input type="text" class="form-control form-control-sm variant-edit-input" data-field="color" value="${color}"></td>
                <td class="variant-edit-cell"><input type="text" class="form-control form-control-sm variant-edit-input" data-field="size" value="${size}"></td>
                <td></td>
                <td class="edit-field">
                     <button class="btn btn-danger btn-sm btn-delete-variant"><i class="bi bi-trash-fill"></i></button>
                </td>
            `;
            variantsTbody.insertBefore(newRow, addVariantRow);

            newColorInput.value = '';
            newSizeInput.value = '';
         });
    }

    if (saveProductBtn) {
        saveProductBtn.addEventListener('click', async () => {
            if (!confirm('💾 수정된 상품 정보를 저장하시겠습니까?\n삭제된 행은 복구되지 않습니다.')) return;

            const productData = {
                product_id: currentProductID,
                product_name: document.getElementById('edit-product-name').value,
                release_year: document.getElementById('edit-release-year').value || null,
                item_category: document.getElementById('edit-item-category').value || null,
                variants: []
            };

            variantsTbody.querySelectorAll('tr[data-variant-id], tr[data-action="add"]').forEach(row => {
                if (row.id === 'add-variant-row' || (row.style.display === 'none' && row.dataset.action !== 'delete')) return;
                
                const action = row.dataset.action || 'update';
                const variantID = row.dataset.variantId || null;

                if (action === 'delete') {
                    productData.variants.push({ variant_id: variantID, action: 'delete' });
                } else {
                     const variant = {
                        variant_id: variantID,
                        action: action,
                        color: row.querySelector('[data-field="color"]').value,
                        size: row.querySelector('[data-field="size"]').value
                    };
                    if (action === 'add' && (!variant.color || !variant.size)) {
                        console.warn("Skipping incomplete new row:", variant);
                        return;
                    }
                    productData.variants.push(variant);
                }
            });

            saveProductBtn.disabled = true;
            saveProductBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 저장 중...';

            try {
                const response = await fetch(updateProductDetailsUrl, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(productData)
                });
                const data = await response.json();

                if (response.ok && data.status === 'success') {
                    alert('상품 정보가 성공적으로 저장되었습니다.');
                    window.location.reload();
                } else {
                    throw new Error(data.message || '저장 중 오류가 발생했습니다.');
                }
            } catch (error) {
                alert(`오류: ${error.message}`);
                saveProductBtn.disabled = false;
                saveProductBtn.innerHTML = '<i class="bi bi-check-lg me-1"></i> 수정 완료';
            }
        });
    }

     const actualStockInputs = document.querySelectorAll('.actual-stock-input');
     const saveActualStockBtns = document.querySelectorAll('.btn-save-actual');
     let isActualStockEnabled = false;

     if (toggleActualStockBtn) {
         toggleActualStockBtn.addEventListener('click', () => {
             if (document.body.classList.contains('edit-mode')) return;

             isActualStockEnabled = !isActualStockEnabled;
             actualStockInputs.forEach(input => { input.disabled = !isActualStockEnabled; });
             saveActualStockBtns.forEach(button => { button.disabled = true; });
             if (isActualStockEnabled) {
                 toggleActualStockBtn.innerHTML = '<i class="bi bi-check-circle-fill me-1"></i> 등록 완료';
                 toggleActualStockBtn.classList.add('active', 'btn-success');
                 toggleActualStockBtn.classList.remove('btn-secondary');
                 if (actualStockInputs.length > 0) {
                     actualStockInputs[0].focus();
                 }
             } else {
                 toggleActualStockBtn.innerHTML = '<i class="bi bi-pencil-square me-1"></i> 실사재고 등록';
                 toggleActualStockBtn.classList.remove('active', 'btn-success');
                 toggleActualStockBtn.classList.add('btn-secondary');
             }
         });
     }

     actualStockInputs.forEach(input => {
        input.addEventListener('input', (e) => {
            const barcode = e.target.dataset.barcode;
            const saveBtn = document.querySelector(`.btn-save-actual[data-barcode="${barcode}"]`);
            if(saveBtn && isActualStockEnabled) {
                saveBtn.disabled = false;
            }
        });
        
        input.addEventListener('keydown', (e) => {
            if (!isActualStockEnabled) return;
            
            const currentBarcode = e.target.dataset.barcode;
            const inputs = Array.from(actualStockInputs);
            const currentIndex = inputs.indexOf(e.target);
            
            if (e.key === 'Enter') {
                e.preventDefault();
                const saveBtn = document.querySelector(`.btn-save-actual[data-barcode="${currentBarcode}"]`);
                if (saveBtn && !saveBtn.disabled) {
                    saveBtn.click();
                } else {
                     const nextInput = inputs[currentIndex + 1];
                     if (nextInput) {
                         nextInput.focus();
                         nextInput.select();
                     }
                }
            } else if (e.key === 'ArrowDown') {
                 e.preventDefault();
                 const nextInput = inputs[currentIndex + 1];
                 if (nextInput) {
                     nextInput.focus();
                     nextInput.select();
                 }
            } else if (e.key === 'ArrowUp') {
                 e.preventDefault();
                 const prevInput = inputs[currentIndex - 1];
                 if (prevInput) {
                     prevInput.focus();
                     prevInput.select();
                 }
            }
        });
        
        input.addEventListener('focus', (e) => {
            if (isActualStockEnabled) {
                e.target.select();
            }
        });
     });


    function updateStockOnServer(barcode, change, buttons) {
        fetch(updateStockUrl, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ barcode: barcode, change: change }) })
        .then(response => response.json()).then(data => {
            if (data.status === 'success') {
                const quantitySpan = document.getElementById(`stock-${data.barcode}`);
                quantitySpan.textContent = data.new_quantity;
                quantitySpan.classList.toggle('text-danger', data.new_quantity === 0);

                updateStockDiffDisplayDirectly(barcode, data.new_stock_diff);
            } else { alert(`재고 오류: ${data.message}`); }
        }).catch(error => { console.error('재고 API 오류:', error); alert('서버 통신 오류.'); }).finally(() => { buttons.forEach(btn => btn.disabled = false); });
    }

    function toggleFavoriteOnServer(productID, button) {
        fetch(toggleFavoriteUrl, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ product_id: productID }) })
        .then(response => response.json()).then(data => {
             if (data.status === 'success') {
                 if (data.new_favorite_status === 1) {
                     button.innerHTML = '<i class="bi bi-star-fill me-1"></i> 즐겨찾기 해제';
                     button.classList.add('btn-warning');
                     button.classList.remove('btn-outline-secondary');
                 } else {
                     button.innerHTML = '<i class="bi bi-star me-1"></i> 즐겨찾기 추가';
                     button.classList.remove('btn-warning');
                     button.classList.add('btn-outline-secondary');
                 }
             } else { alert(`즐겨찾기 오류: ${data.message}`); } })
        .catch(error => { console.error('즐겨찾기 API 오류:', error); alert('서버 통신 오류.'); })
        .finally(() => { button.disabled = false; });
    }

    function saveActualStock(barcode, actualStock, saveButton, inputElement) {
        fetch(updateActualStockUrl, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ barcode: barcode, actual_stock: actualStock }) })
        .then(response => response.json()).then(data => {
            if (data.status === 'success') {
                updateStockDiffDisplayDirectly(barcode, data.new_stock_diff);
                inputElement.value = data.new_actual_stock;
                saveButton.disabled = true;
                inputElement.disabled = !document.getElementById('toggle-actual-stock-btn').classList.contains('active');
                
                 const inputs = Array.from(document.querySelectorAll('.actual-stock-input'));
                 const currentIndex = inputs.indexOf(inputElement);
                 const nextInput = inputs[currentIndex + 1];
                 if (nextInput && document.getElementById('toggle-actual-stock-btn').classList.contains('active')) {
                     nextInput.focus();
                     nextInput.select();
                 }

            } else {
                 alert(`실사재고 저장 오류: ${data.message}`);
                 saveButton.disabled = false;
                 inputElement.disabled = false;
            }
        }).catch(error => {
            console.error('실사재고 API 오류:', error); alert('서버 통신 오류.');
            saveButton.disabled = false;
            inputElement.disabled = false;
        });
    }

    function updateStockDiffDisplayDirectly(barcode, stockDiffValue) {
        const diffSpan = document.getElementById(`diff-${barcode}`);
        if (diffSpan) {
            diffSpan.textContent = stockDiffValue !== '' && stockDiffValue !== null ? stockDiffValue : '-';
            diffSpan.className = 'stock-diff badge ';
            if (stockDiffValue !== '' && stockDiffValue !== null) {
                const diffValueInt = parseInt(stockDiffValue);
                if (!isNaN(diffValueInt)) {
                   if (diffValueInt > 0) diffSpan.classList.add('bg-primary');
                   else if (diffValueInt < 0) diffSpan.classList.add('bg-danger');
                   else diffSpan.classList.add('bg-secondary');
                } else { diffSpan.classList.add('bg-light', 'text-dark'); }
            } else { diffSpan.classList.add('bg-light', 'text-dark'); }
        }
    }
});