document.addEventListener('DOMContentLoaded', () => {
    
    // [수정] CSRF 토큰 가져오기
    const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
    const csrfToken = csrfTokenMeta ? csrfTokenMeta.getAttribute('content') : '';

    const bodyData = document.body.dataset;
    const updateStockUrl = bodyData.updateStockUrl;
    const toggleFavoriteUrl = bodyData.toggleFavoriteUrl;
    const updateActualStockUrl = bodyData.updateActualStockUrl;
    const updateProductDetailsUrl = bodyData.updateProductDetailsUrl;
    const currentProductID = bodyData.productId;

    // [신규] (6단계) A/B/C 권한 로직
    const myStoreID = parseInt(bodyData.myStoreId, 10) || 0;
    const storeSelector = document.getElementById('hq-store-selector');
    const variantsTbody = document.getElementById('variants-tbody');
    const rowTemplate = document.getElementById('variant-row-template');
    const addRowTemplate = document.getElementById('add-variant-row-template');
    const toggleActualStockBtn = document.getElementById('toggle-actual-stock-btn');
    
    let isActualStockEnabled = false; // (신규) 실사재고 활성화 상태
    
    /**
     * [신규] (6단계) 재고 테이블을 다시 그리는 함수
     * @param {number} selectedStoreId - 드롭다운에서 선택된 매장 ID
     */
    function renderStockTable(selectedStoreId) {
        if (!variantsTbody || !rowTemplate || !window.allVariants || !window.hqStockData) {
            console.error("테이블 렌더링에 필요한 요소가 없습니다.");
            if(variantsTbody) variantsTbody.innerHTML = '<tr><td colspan="7" class="text-center text-danger p-4">테이블 렌더링 오류. (콘솔 확인)</td></tr>';
            return;
        }

        variantsTbody.innerHTML = ''; // 테이블 비우기 (기존 "매장을 선택하세요" 문구 삭제됨)
        
        // (요청) A/B/C 권한 확인: 선택한 매장이 '내 매장'인가?
        const isMyStore = (selectedStoreId === myStoreID);
        
        // '실사재고' 버튼 표시/숨기기 (내 매장일때만)
        if (toggleActualStockBtn) {
            if (isMyStore) {
                toggleActualStockBtn.style.display = 'inline-block';
            } else {
                toggleActualStockBtn.style.display = 'none';
                // 다른 매장 선택 시, 실사 모드 강제 종료
                if (isActualStockEnabled) {
                    toggleActualStockMode(false); // 실사 모드 끄기
                }
            }
        }
        
        // 옵션(Variant) 목록 순회
        window.allVariants.forEach(variant => {
            // 선택된 매장의 재고 데이터 가져오기 (없으면 빈 객체)
            const storeStockData = window.hqStockData[selectedStoreId]?.[variant.id] || {};
            const storeQty = storeStockData.quantity || 0;
            const actualQty = storeStockData.actual_stock; // (null | undefined | number)
            
            // 과부족(C) 계산
            let diffVal = '-';
            let diffClass = 'bg-light text-dark';
            if (actualQty !== null && actualQty !== undefined) {
                const diff = storeQty - actualQty;
                diffVal = diff;
                if (diff > 0) diffClass = 'bg-primary';
                else if (diff < 0) diffClass = 'bg-danger';
                else diffClass = 'bg-secondary';
            }

            // 템플릿 HTML 복제 및 데이터 바인딩
            const html = rowTemplate.innerHTML
                .replace(/__BARCODE__/g, variant.barcode)
                .replace(/__VARIANT_ID__/g, variant.id)
                .replace(/__COLOR__/g, variant.color || '')
                .replace(/__SIZE__/g, variant.size || '')
                .replace(/__STORE_QTY__/g, storeQty)
                .replace(/__STORE_QTY_CLASS__/g, storeQty === 0 ? 'text-danger' : '')
                .replace(/__HQ_QTY__/g, variant.hq_quantity || 0)
                .replace(/__HQ_QTY_CLASS__/g, (variant.hq_quantity || 0) === 0 ? 'text-danger' : 'text-muted')
                .replace(/__ACTUAL_QTY_VAL__/g, (actualQty !== null && actualQty !== undefined) ? actualQty : '')
                .replace(/__DIFF_VAL__/g, diffVal)
                .replace(/__DIFF_CLASS__/g, diffClass)
                // (A/B/C 권한) 내 매장이면 '수정' UI 표시, 아니면 '숨김'
                .replace(/__SHOW_IF_MY_STORE__/g, isMyStore ? '' : 'd-none')
                // (A 권한) 내 매장이 아니면 '읽기전용' UI 표시
                .replace(/__SHOW_IF_NOT_MY_STORE__/g, isMyStore ? 'd-none' : '');
            
            variantsTbody.insertAdjacentHTML('beforeend', html);
        });
        
        // 옵션이 하나도 없을 경우
        if (window.allVariants.length === 0) {
             variantsTbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted p-4">이 상품의 옵션 정보가 없습니다.</td></tr>';
        }

        // '수정 모드'일 경우, '행 추가' 버튼 추가
        if (document.body.classList.contains('edit-mode') && addRowTemplate) {
            variantsTbody.insertAdjacentHTML('beforeend', addRowTemplate.innerHTML);
        }
        
        // [신규] (6단계) 새로 그려진 DOM에 대해 실사재고 입력기 상태 갱신
        updateActualStockInputsState();
    }
    
    // [신규] (6단계) 매장 선택 시 테이블 다시 그리기
    if (storeSelector) {
        storeSelector.addEventListener('change', () => {
            const selectedStoreId = parseInt(storeSelector.value, 10) || 0;
            renderStockTable(selectedStoreId);
        });
    }

    // --- (기존 로직) ---

     if (variantsTbody) {
         variantsTbody.addEventListener('click', function(e) {
             const stockButton = e.target.closest('button.btn-inc, button.btn-dec');
             if (stockButton) {
                 const barcode = stockButton.dataset.barcode;
                 const change = parseInt(stockButton.dataset.change, 10);
                 const changeText = change === 1 ? "증가" : "감소";
                 
                 // (수정) (6단계) '내 매장'일 때만 작동 (A/B/C 권한)
                 const currentSelectedStoreId = storeSelector ? (parseInt(storeSelector.value, 10) || 0) : myStoreID;
                 
                 if (currentSelectedStoreId !== myStoreID) {
                     alert('재고 수정은 \'내 매장\'이 선택된 경우에만 가능합니다.');
                     return;
                 }
                 
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
                 
                if (actualStockValue !== '' && (isNaN(actualStockValue) || parseInt(actualStockValue) < 0)) {
                    alert('실사재고는 0 이상의 숫자만 입력 가능합니다.');
                    inputElement.focus();
                    inputElement.select();
                    return;
                }
                 
                 saveButton.disabled = true;
                 saveActualStock(barcode, actualStockValue, saveButton, inputElement);
             }
             
             // [신규] (6단계) '행 추가' 버튼 이벤트 리스너 (이벤트 위임)
             const addVariantBtn = e.target.closest('#btn-add-variant');
             if (addVariantBtn) {
                 handleAddVariantRow();
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

    // (추가) 상품 삭제 버튼
    const deleteProductBtn = document.getElementById('delete-product-btn');
    const deleteProductForm = document.getElementById('delete-product-form');
    const productName = document.querySelector('.product-details h2')?.textContent || '이 상품';

    if (deleteProductBtn && deleteProductForm) {
        deleteProductBtn.addEventListener('click', () => {
            if (confirm(`🚨🚨🚨 최종 경고 🚨🚨🚨\n\n'${productName}' (품번: ${currentProductID}) 상품을(를) DB에서 완전히 삭제합니다.\n\n이 상품에 연결된 모든 옵션(Variant), 모든 매장의 재고(StoreStock) 데이터가 영구적으로 삭제되며 복구할 수 없습니다.\n\n정말로 삭제하시겠습니까?`)) {
                deleteProductBtn.disabled = true;
                deleteProductBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 삭제 중...';
                deleteProductForm.submit();
            }
        });
    }

    if (editProductBtn) {
        editProductBtn.addEventListener('click', () => {
            if (confirm('✏️ 상품 정보 수정 모드로 전환합니다.\n수정 후에는 반드시 [수정 완료] 버튼을 눌러 저장해주세요.')) {
                document.body.classList.add('edit-mode');
                // (6단계) 수정 모드 진입 시 테이블 다시 그리기 ('행 추가' 버튼 표시)
                const currentStoreId = storeSelector ? (parseInt(storeSelector.value, 10) || 0) : myStoreID;
                renderStockTable(currentStoreId);
            }
        });
    }

    if (cancelEditBtn) {
        cancelEditBtn.addEventListener('click', () => {
            if (confirm('⚠️ 수정 중인 내용을 취소하고 원래 상태로 되돌립니다.\n계속하시겠습니까?')) {
                document.body.classList.remove('edit-mode');
                // (6단계) 취소 시 테이블 다시 그리기 (원본 상태 복원)
                const currentStoreId = storeSelector ? (parseInt(storeSelector.value, 10) || 0) : myStoreID;
                renderStockTable(currentStoreId);
            }
        });
    }

    if (variantsTbody) {
        variantsTbody.addEventListener('click', (e) => {
            // (6단계) 이벤트 위임으로 '행 삭제' 처리
            const deleteBtn = e.target.closest('.btn-delete-variant');
            if (deleteBtn) {
                if (confirm('🗑️ 이 행을 삭제하시겠습니까? [수정 완료]를 눌러야 최종 반영됩니다.')) {
                    const row = e.target.closest('tr');
                    if (row.dataset.variantId) {
                        row.style.display = 'none';
                        row.dataset.action = 'delete';
                    } else {
                        row.remove(); // 새로 추가된 행(ID 없음)은 즉시 제거
                    }
                }
            }
        });
    }

    // [신규] (6단계) '행 추가' 버튼 클릭 핸들러
    function handleAddVariantRow() {
         const addVariantRow = document.getElementById('add-variant-row'); // 현재 DOM에서 행 찾기
         if (!addVariantRow) return;
         
         const newColorInput = addVariantRow.querySelector('[data-field="new-color"]');
         const newSizeInput = addVariantRow.querySelector('[data-field="new-size"]');

         const color = newColorInput.value.trim();
         const size = newSizeInput.value.trim();

         if (!color || !size) {
             alert('새 행의 컬러와 사이즈를 입력해주세요.');
             return;
         }

         const newRow = document.createElement('tr');
         newRow.dataset.action = 'add'; // 신규 행임을 표시
         
         // (6단계) 템플릿 대신 수동 생성
         newRow.innerHTML = `
             <td class="variant-edit-cell"><input type="text" class="form-control form-control-sm variant-edit-input" data-field="color" value="${color}"></td>
             <td class="variant-edit-cell"><input type="text" class="form-control form-control-sm variant-edit-input" data-field="size" value="${size}"></td>
             <td></td>
             <td></td>
             <td class="view-field"></td>
             <td class="view-field"></td>
             <td class="edit-field">
                  <button class="btn btn-danger btn-sm btn-delete-variant"><i class="bi bi-trash-fill"></i></button>
             </td>
         `;
         // '행 추가' 버튼이 있는 행(addVariantRow) '앞에' 삽입
         variantsTbody.insertBefore(newRow, addVariantRow);

         newColorInput.value = '';
         newSizeInput.value = '';
         newColorInput.focus();
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
            
            // (6단계) 가격 정보 필드 가져오기
            const originalPrice = document.getElementById('edit-original-price-field').value;
            const salePrice = document.getElementById('edit-sale-price-field').value;

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
                        size: row.querySelector('[data-field="size"]').value,
                        // (6단계) 가격 정보 추가
                        original_price: originalPrice,
                        sale_price: salePrice
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
                    headers: { 
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken // [수정] 헤더 추가
                    },
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
    
    // [신규] (6단계) 실사재고 토글 함수
    function toggleActualStockMode(forceState) {
         if (forceState === false) {
             isActualStockEnabled = true; // (토글을 위해 반대로 설정)
         } else if (forceState === true) {
             isActualStockEnabled = false; // (토글을 위해 반대로 설정)
         }

         isActualStockEnabled = !isActualStockEnabled;
         
         updateActualStockInputsState(); // DOM 상태 업데이트
         
         if (isActualStockEnabled) {
             toggleActualStockBtn.innerHTML = '<i class="bi bi-check-circle-fill me-1"></i> 등록 완료';
             toggleActualStockBtn.classList.add('active', 'btn-success');
             toggleActualStockBtn.classList.remove('btn-secondary');
             const firstInput = variantsTbody.querySelector('.actual-stock-input');
             if (firstInput) {
                 firstInput.focus();
             }
         } else {
             toggleActualStockBtn.innerHTML = '<i class="bi bi-pencil-square me-1"></i> 실사재고 등록';
             toggleActualStockBtn.classList.remove('active', 'btn-success');
             toggleActualStockBtn.classList.add('btn-secondary');
         }
    }
    
    // [신규] (6단계) 실사재고 Input/Button 상태 업데이트 (테이블 다시 그릴때 호출)
    function updateActualStockInputsState() {
         const actualStockInputs = variantsTbody.querySelectorAll('.actual-stock-input');
         const saveActualStockBtns = variantsTbody.querySelectorAll('.btn-save-actual');
         
         actualStockInputs.forEach(input => { input.disabled = !isActualStockEnabled; });
         saveActualStockBtns.forEach(button => { button.disabled = true; }); // (저장 버튼은 항상 비활성화로 시작)
         
         // '내 매장'이 아니면 리스너 등록 안함 (A/B/C 권한)
         const currentSelectedStoreId = storeSelector ? (parseInt(storeSelector.value, 10) || 0) : myStoreID;
         
         if (currentSelectedStoreId !== myStoreID) {
             return;
         }
         
         // (이벤트 리스너 등록)
         actualStockInputs.forEach(input => {
            // (주의) 중복 리스너 방지 (간단한 플래그 사용)
            if (input.dataset.listenerAttached) return;
            input.dataset.listenerAttached = 'true';
            
            input.addEventListener('input', (e) => {
                const barcode = e.target.dataset.barcode;
                const saveBtn = document.querySelector(`.btn-save-actual[data-barcode="${barcode}"]`);
                if(saveBtn && isActualStockEnabled) {
                    saveBtn.disabled = false; // (활성화)
                }
            });
            
            input.addEventListener('keydown', (e) => {
                if (!isActualStockEnabled) return;
                
                const currentBarcode = e.target.dataset.barcode;
                const inputs = Array.from(variantsTbody.querySelectorAll('.actual-stock-input'));
                const currentIndex = inputs.indexOf(e.target);
                
                if (e.key === 'Enter') {
                    e.preventDefault();
                    const saveBtn = document.querySelector(`.btn-save-actual[data-barcode="${currentBarcode}"]`);
                    if (saveBtn && !saveBtn.disabled) {
                        saveBtn.click(); // 저장
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
    }

     if (toggleActualStockBtn) {
         toggleActualStockBtn.addEventListener('click', () => {
             if (document.body.classList.contains('edit-mode')) return;
             toggleActualStockMode();
         });
     }
     
    // --- (기존) 서버 통신 함수들 (수정 없음) ---
    
    function updateStockOnServer(barcode, change, buttons) {
        fetch(updateStockUrl, { 
            method: 'POST', 
            headers: { 
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken // [수정] 헤더 추가
            }, 
            body: JSON.stringify({ barcode: barcode, change: change }) 
        })
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
        fetch(toggleFavoriteUrl, { 
            method: 'POST', 
            headers: { 
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken // [수정] 헤더 추가
            }, 
            body: JSON.stringify({ product_id: productID }) 
        })
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
        fetch(updateActualStockUrl, { 
            method: 'POST', 
            headers: { 
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken // [수정] 헤더 추가
            }, 
            body: JSON.stringify({ barcode: barcode, actual_stock: actualStock }) 
        })
        .then(response => response.json()).then(data => {
            if (data.status === 'success') {
                updateStockDiffDisplayDirectly(barcode, data.new_stock_diff);
                inputElement.value = data.new_actual_stock;
                saveButton.disabled = true;
                
                // (6단계) 현재 활성화 상태에 따라 input 비활성화
                inputElement.disabled = !isActualStockEnabled; 
                
                 const inputs = Array.from(variantsTbody.querySelectorAll('.actual-stock-input'));
                 const currentIndex = inputs.indexOf(inputElement);
                 const nextInput = inputs[currentIndex + 1];
                 if (nextInput && isActualStockEnabled) { // (6단계) 활성화 상태 체크
                     nextInput.focus();
                     nextInput.select();
                 }

            } else {
                 alert(`실사재고 저장 오류: ${data.message}`);
                 saveButton.disabled = false;
                 inputElement.disabled = !isActualStockEnabled;
            }
        }).catch(error => {
            console.error('실사재고 API 오류:', error); alert('서버 통신 오류.');
            saveButton.disabled = false;
            inputElement.disabled = !isActualStockEnabled;
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
    
    // [수정] 페이지 로드 시 매장 ID 결정 (드롭다운 없으면 내 매장 ID 사용)
    // 이 부분이 '매장을 선택하세요' 문제를 해결하는 핵심입니다.
    let initialStoreId = 0;
    if (storeSelector) {
        initialStoreId = parseInt(storeSelector.value, 10) || 0;
    } else if (myStoreID) {
        initialStoreId = myStoreID;
    }

    renderStockTable(initialStoreId);
});