document.addEventListener('DOMContentLoaded', () => {

    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

    const getToday = () => {
        const date = new Date();
        const year = date.getFullYear();
        const month = (date.getMonth() + 1).toString().padStart(2, '0');
        const day = date.getDate().toString().padStart(2, '0');
        return `${year}-${month}-${day}`;
    };

    const receptionToggles = document.getElementById('reception-method-toggles');
    const addressWrapper = document.getElementById('address-fields-wrapper');
    const addressRequiredText = document.getElementById('address-required-text');

    function toggleAddressFields() {
        if (!receptionToggles || !addressWrapper) return;
        
        const selected = receptionToggles.querySelector('input[name="reception_method"]:checked');
        if (selected && selected.value === '택배수령') {
            addressWrapper.style.display = 'block';
            addressRequiredText.style.display = 'block';
            document.getElementById('address1').required = true;
            document.getElementById('address2').required = true;
        } else {
            addressWrapper.style.display = 'none';
            addressRequiredText.style.display = 'none';
            document.getElementById('address1').required = false;
            document.getElementById('address2').required = false;
        }
    }
    
    if (receptionToggles) {
        receptionToggles.addEventListener('change', toggleAddressFields);
    }

    const statusSelect = document.getElementById('order_status');
    const shippingWrapper = document.getElementById('shipping-fields-wrapper');
    const completionWrapper = document.getElementById('completion-date-wrapper');
    const completionInput = document.getElementById('completed_at');

    function toggleStatusFields() {
        if (!statusSelect) return;
        
        const selectedStatus = statusSelect.value;
        
        if (selectedStatus === '택배 발송') {
            shippingWrapper.style.display = 'block';
        } else {
            shippingWrapper.style.display = 'none';
        }
        
        if (selectedStatus === '완료') {
            completionWrapper.style.display = 'block';
            if (!completionInput.value) {
                completionInput.value = getToday();
            }
        } else {
            completionWrapper.style.display = 'none';
        }
    }

    if (statusSelect) {
        statusSelect.addEventListener('change', toggleStatusFields);
    }

    const searchAddressBtn = document.getElementById('btn-search-address');
    if (searchAddressBtn) {
        searchAddressBtn.addEventListener('click', () => {
            new daum.Postcode({
                oncomplete: function(data) {
                    document.getElementById('postcode').value = data.zonecode; 
                    document.getElementById('address1').value = data.roadAddress || data.jibunAddress;
                    document.getElementById('address2').focus();
                }
            }).open();
        });
    }

    const productNumberInput = document.getElementById('product_number');
    const productNameInput = document.getElementById('product_name');
    const colorSelect = document.getElementById('color');
    const sizeSelect = document.getElementById('size');
    const statusText = document.getElementById('product-lookup-status');
    const searchButton = document.getElementById('btn-product-search');
    const searchResultsDiv = document.getElementById('product-search-results');
    
    const lookupUrl = document.body.dataset.productLookupUrl;
    const searchUrl = document.body.dataset.productSearchUrl;
    
    const currentColor = document.body.dataset.currentColor;
    const currentSize = document.body.dataset.currentSize;

    function resetSelects(message) {
        colorSelect.innerHTML = `<option value="">${message}</option>`;
        sizeSelect.innerHTML = `<option value="">${message}</option>`;
    }

    function populateSelects(data) {
        colorSelect.innerHTML = '<option value="">-- 컬러 선택 --</option>';
        data.colors.forEach(color => {
            const selected = (color === currentColor) ? 'selected' : '';
            colorSelect.insertAdjacentHTML('beforeend', `<option value="${color}" ${selected}>${color}</option>`);
        });

        sizeSelect.innerHTML = '<option value="">-- 사이즈 선택 --</option>';
        data.sizes.forEach(size => {
            const selected = (size === currentSize) ? 'selected' : '';
            sizeSelect.insertAdjacentHTML('beforeend', `<option value="${size}" ${selected}>${size}</option>`);
        });
    }

    async function fetchProductOptions(productNumber) {
        if (!productNumber) {
            productNameInput.value = '';
            statusText.textContent = '';
            resetSelects('-- 품번 먼저 조회 --');
            return;
        }

        statusText.textContent = '상품 옵션 조회 중...';
        statusText.classList.remove('text-danger');
        resetSelects('-- 조회 중 --');
        
        try {
            const response = await fetch(lookupUrl, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken 
                },
                body: JSON.stringify({ product_number: productNumber })
            });
            const data = await response.json();

            if (response.ok && data.status === 'success') {
                productNameInput.value = data.product_name;
                productNumberInput.value = data.product_number;
                statusText.textContent = `상품명: ${data.product_name}`;
                populateSelects(data);
            } else {
                statusText.textContent = data.message || '상품 조회 실패';
                statusText.classList.add('text-danger');
                resetSelects('-- 조회 실패 --');
            }
        } catch (error) {
            console.error('Product lookup error:', error);
            statusText.textContent = '서버 통신 오류.';
            statusText.classList.add('text-danger');
            resetSelects('-- 조회 오류 --');
        }
    }

    if(searchButton) {
        searchButton.addEventListener('click', async () => {
            const query = productNumberInput.value.trim();
            if (!query) {
                statusText.textContent = '검색할 품번이나 품명을 입력하세요.';
                statusText.classList.add('text-danger');
                searchResultsDiv.style.display = 'none';
                return;
            }
            
            statusText.textContent = '상품 목록 검색 중...';
            statusText.classList.remove('text-danger');
            searchResultsDiv.innerHTML = '<div class="list-group-item">검색 중...</div>';
            searchResultsDiv.style.display = 'block';

            try {
                const response = await fetch(searchUrl, {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken 
                    },
                    body: JSON.stringify({ query: query })
                });
                const data = await response.json();
                
                searchResultsDiv.innerHTML = '';

                if (response.ok && data.status === 'success') {
                    statusText.textContent = `${data.products.length}개의 상품을 찾았습니다.`;
                    data.products.forEach(product => {
                        const itemHtml = `
                            <button type="button" class="list-group-item list-group-item-action" 
                                    data-pn="${product.product_number}" data-name="${product.product_name}">
                                <div class="fw-bold">${product.product_name}</div>
                                <div class="small text-muted">${product.product_number}</div>
                            </button>`;
                        searchResultsDiv.insertAdjacentHTML('beforeend', itemHtml);
                    });
                } else {
                    statusText.textContent = data.message || '검색 실패';
                    statusText.classList.add('text-danger');
                    searchResultsDiv.innerHTML = `<div class="list-group-item text-danger">${data.message || '검색 실패'}</div>`;
                }
            } catch (error) {
                console.error('Product search error:', error);
                statusText.textContent = '검색 중 서버 오류 발생';
                statusText.classList.add('text-danger');
                searchResultsDiv.innerHTML = `<div class="list-group-item text-danger">검색 중 서버 오류</div>`;
            }
        });
    }

    if(searchResultsDiv) {
        searchResultsDiv.addEventListener('click', (e) => {
            const target = e.target.closest('.list-group-item-action');
            if (!target) return;
            e.preventDefault();
            
            const productNumber = target.dataset.pn;
            productNumberInput.value = productNumber;
            searchResultsDiv.style.display = 'none';
            searchResultsDiv.innerHTML = '';
            fetchProductOptions(productNumber);
        });
    }

    if(productNumberInput) {
        productNumberInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                searchButton.click();
            }
        });
    }

    document.addEventListener('click', (e) => {
        if(productNumberInput) {
            const searchContainer = productNumberInput.closest('.position-relative');
            if (searchContainer && !searchContainer.contains(e.target)) {
                searchResultsDiv.style.display = 'none';
            }
        }
    });

    const processingTableBody = document.getElementById('processing-table-body');
    const addRowBtn = document.getElementById('btn-add-processing-row');
    const rowTemplate = document.getElementById('processing-row-template');

    if (addRowBtn) {
        addRowBtn.addEventListener('click', () => {
            addProcessingRow();
        });
    }

    if (processingTableBody) {
        processingTableBody.addEventListener('click', (e) => {
            if (e.target.closest('.btn-delete-row')) {
                if (processingTableBody.querySelectorAll('tr').length > 1) {
                    e.target.closest('tr').remove();
                } else {
                    alert('최소 1개의 처리 내역이 필요합니다.');
                }
            }
        });
    }
    
    function addProcessingRow() {
        if (!rowTemplate) return;
        const newRow = rowTemplate.content.cloneNode(true);
        processingTableBody.appendChild(newRow);
    }

    const deleteBtn = document.getElementById('btn-delete-order');
    const deleteForm = document.getElementById('delete-order-form');
    if (deleteBtn && deleteForm) {
        deleteBtn.addEventListener('click', () => {
            if (confirm('🚨 경고!\n\n이 주문 내역을 정말로 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다.')) {
                deleteForm.submit();
            }
        });
    }

    const orderForm = document.getElementById('order-form');
    if (orderForm) {
        orderForm.addEventListener('submit', (e) => {
            if(receptionToggles) {
                const selectedMethod = receptionToggles.querySelector('input[name="reception_method"]:checked');
                if (selectedMethod && selectedMethod.value === '택배수령') {
                    if (!document.getElementById('address1').value || !document.getElementById('address2').value) {
                        e.preventDefault();
                        alert('택배수령 시에는 기본주소와 상세주소가 모두 필요합니다.');
                        document.getElementById('address1').focus();
                        return;
                    }
                }
            }
            
            if(processingTableBody) {
                const processingRows = processingTableBody.querySelectorAll('tr');
                if (processingRows.length === 0) {
                     e.preventDefault();
                     alert('상품 처리가 최소 1개 이상 필요합니다.');
                     addRowBtn.focus();
                     return;
                }
                
                const sourceSelects = processingTableBody.querySelectorAll('select[name="processing_source"]');
                for (const select of sourceSelects) {
                    if (!select.value) {
                        e.preventDefault();
                        alert('상품 처리의 [주문처]는 필수 항목입니다. 비어있는 행을 확인해주세요.');
                        select.focus();
                        return;
                    }
                }
            }
        });
    }

    toggleAddressFields();
    toggleStatusFields();
    
    if (productNumberInput && productNumberInput.value) {
        fetchProductOptions(productNumberInput.value);
    }

    const enableEditBtn = document.getElementById('btn-enable-edit');
    if (enableEditBtn) {
        enableEditBtn.addEventListener('click', (e) => {
            e.preventDefault();
            
            document.body.dataset.pageMode = 'edit';

            const fieldsToEnable = document.querySelectorAll('.editable-on-demand');
            fieldsToEnable.forEach(field => {
                field.disabled = false;
                field.readOnly = false;
            });
            
            document.getElementById('created_at').focus();
        });
    }

});