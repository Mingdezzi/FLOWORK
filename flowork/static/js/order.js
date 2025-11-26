/**
 * Order Management Logic
 * Refactored to use Class-based structure and Common Utilities
 */

class OrderApp {
    constructor() {
        this.dom = {
            receptionToggles: document.getElementById('reception-method-toggles'),
            addressWrapper: document.getElementById('address-fields-wrapper'),
            addressRequiredText: document.getElementById('address-required-text'),
            statusSelect: document.getElementById('order_status'),
            shippingWrapper: document.getElementById('shipping-fields-wrapper'),
            completionWrapper: document.getElementById('completion-date-wrapper'),
            completionInput: document.getElementById('completed_at'),
            btnSearchAddress: document.getElementById('btn-search-address'),
            pnInput: document.getElementById('product_number'),
            pNameInput: document.getElementById('product_name'),
            colorSelect: document.getElementById('color'),
            sizeSelect: document.getElementById('size'),
            statusText: document.getElementById('product-lookup-status'),
            btnSearch: document.getElementById('btn-product-search'),
            resultsDiv: document.getElementById('product-search-results'),
            processingBody: document.getElementById('processing-table-body'),
            btnAddRow: document.getElementById('btn-add-processing-row'),
            rowTemplate: document.getElementById('processing-row-template'),
            btnDeleteOrder: document.getElementById('btn-delete-order'),
            formOrder: document.getElementById('order-form'),
            formDelete: document.getElementById('delete-order-form'),
            btnEnableEdit: document.getElementById('btn-enable-edit')
        };
        
        this.urls = {
            lookup: document.body.dataset.productLookupUrl,
            search: document.body.dataset.productSearchUrl
        };
        
        this.data = {
            color: document.body.dataset.currentColor,
            size: document.body.dataset.currentSize
        };

        this.init();
    }

    init() {
        if(this.dom.receptionToggles) this.dom.receptionToggles.addEventListener('change', () => this.toggleAddressFields());
        if(this.dom.statusSelect) this.dom.statusSelect.addEventListener('change', () => this.toggleStatusFields());
        
        if(this.dom.btnSearchAddress) {
            this.dom.btnSearchAddress.addEventListener('click', () => {
                new daum.Postcode({
                    oncomplete: (data) => {
                        document.getElementById('postcode').value = data.zonecode;
                        document.getElementById('address1').value = data.roadAddress || data.jibunAddress;
                        document.getElementById('address2').focus();
                    }
                }).open();
            });
        }

        if(this.dom.btnSearch) this.dom.btnSearch.addEventListener('click', () => this.searchProduct());
        if(this.dom.resultsDiv) {
            this.dom.resultsDiv.addEventListener('click', (e) => {
                const target = e.target.closest('.list-group-item-action');
                if(target) {
                    e.preventDefault();
                    this.selectProduct(target.dataset.pn);
                }
            });
        }
        
        if(this.dom.pnInput) {
            this.dom.pnInput.addEventListener('keydown', (e) => {
                if(e.key === 'Enter') { e.preventDefault(); this.dom.btnSearch.click(); }
            });
            // 초기 로드 시 값이 있으면 조회
            if(this.dom.pnInput.value) this.fetchProductOptions(this.dom.pnInput.value);
        }

        // 상품 검색 결과창 닫기
        document.addEventListener('click', (e) => {
            if(this.dom.pnInput) {
                const container = this.dom.pnInput.closest('.position-relative');
                if(container && !container.contains(e.target)) this.dom.resultsDiv.style.display = 'none';
            }
        });

        if(this.dom.btnAddRow) this.dom.btnAddRow.addEventListener('click', () => this.addProcessingRow());
        if(this.dom.processingBody) {
            this.dom.processingBody.addEventListener('click', (e) => {
                if(e.target.closest('.btn-delete-row')) this.deleteProcessingRow(e.target);
            });
        }

        if(this.dom.btnDeleteOrder) {
            this.dom.btnDeleteOrder.addEventListener('click', () => {
                if(confirm('🚨 경고!\n이 주문 내역을 삭제하시겠습니까?')) this.dom.formDelete.submit();
            });
        }

        if(this.dom.formOrder) {
            this.dom.formOrder.addEventListener('submit', (e) => this.validateForm(e));
        }

        if(this.dom.btnEnableEdit) {
            this.dom.btnEnableEdit.addEventListener('click', (e) => {
                e.preventDefault();
                document.body.dataset.pageMode = 'edit';
                document.querySelectorAll('.editable-on-demand').forEach(el => {
                    el.disabled = false; el.readOnly = false;
                });
                document.getElementById('created_at').focus();
            });
        }

        this.toggleAddressFields();
        this.toggleStatusFields();
    }

    toggleAddressFields() {
        if(!this.dom.receptionToggles) return;
        const selected = this.dom.receptionToggles.querySelector('input:checked');
        const isDelivery = selected && selected.value === '택배수령';
        
        this.dom.addressWrapper.style.display = isDelivery ? 'block' : 'none';
        this.dom.addressRequiredText.style.display = isDelivery ? 'block' : 'none';
        document.getElementById('address1').required = isDelivery;
        document.getElementById('address2').required = isDelivery;
    }

    toggleStatusFields() {
        if(!this.dom.statusSelect) return;
        const status = this.dom.statusSelect.value;
        
        this.dom.shippingWrapper.style.display = (status === '택배 발송') ? 'block' : 'none';
        this.dom.completionWrapper.style.display = (status === '완료') ? 'block' : 'none';
        
        if(status === '완료' && !this.dom.completionInput.value) {
            this.dom.completionInput.value = Flowork.fmtDate(new Date());
        }
    }

    async searchProduct() {
        const query = this.dom.pnInput.value.trim();
        if(!query) {
            this.setStatus('검색어를 입력하세요.', true);
            this.dom.resultsDiv.style.display = 'none';
            return;
        }

        this.setStatus('검색 중...', false);
        this.dom.resultsDiv.innerHTML = '<div class="list-group-item">검색 중...</div>';
        this.dom.resultsDiv.style.display = 'block';

        try {
            const data = await Flowork.post(this.urls.search, { query });
            this.dom.resultsDiv.innerHTML = '';
            
            if(data.status === 'success') {
                this.setStatus(`${data.products.length}개 발견`, false);
                data.products.forEach(p => {
                    const html = `<button type="button" class="list-group-item list-group-item-action" data-pn="${p.product_number}">
                        <div class="fw-bold">${p.product_name}</div>
                        <div class="small text-muted">${p.product_number}</div>
                    </button>`;
                    this.dom.resultsDiv.insertAdjacentHTML('beforeend', html);
                });
            } else {
                this.setStatus(data.message, true);
                this.dom.resultsDiv.innerHTML = `<div class="list-group-item text-danger">${data.message}</div>`;
            }
        } catch(e) {
            this.setStatus('오류 발생', true);
            this.dom.resultsDiv.innerHTML = `<div class="list-group-item text-danger">오류 발생</div>`;
        }
    }

    selectProduct(pn) {
        this.dom.pnInput.value = pn;
        this.dom.resultsDiv.style.display = 'none';
        this.fetchProductOptions(pn);
    }

    async fetchProductOptions(pn) {
        if(!pn) return;
        this.setStatus('옵션 조회 중...', false);
        
        try {
            const data = await Flowork.post(this.urls.lookup, { product_number: pn });
            if(data.status === 'success') {
                this.dom.pNameInput.value = data.product_name;
                this.dom.pnInput.value = data.product_number;
                this.setStatus(`상품명: ${data.product_name}`, false);
                
                this.populateSelect(this.dom.colorSelect, data.colors, this.data.color);
                this.populateSelect(this.dom.sizeSelect, data.sizes, this.data.size);
            } else {
                this.setStatus(data.message, true);
            }
        } catch(e) { this.setStatus('조회 오류', true); }
    }

    populateSelect(select, items, currentVal) {
        select.innerHTML = `<option value="">-- 선택 --</option>`;
        items.forEach(i => {
            const selected = (i === currentVal) ? 'selected' : '';
            select.insertAdjacentHTML('beforeend', `<option value="${i}" ${selected}>${i}</option>`);
        });
    }

    setStatus(msg, isError) {
        this.dom.statusText.textContent = msg;
        this.dom.statusText.className = isError ? 'form-text text-danger' : 'form-text';
    }

    addProcessingRow() {
        const clone = this.dom.rowTemplate.content.cloneNode(true);
        this.dom.processingBody.appendChild(clone);
    }

    deleteProcessingRow(btn) {
        if(this.dom.processingBody.querySelectorAll('tr').length > 1) {
            btn.closest('tr').remove();
        } else {
            alert('최소 1개의 처리 내역이 필요합니다.');
        }
    }

    validateForm(e) {
        // 수령 방법 검증
        const selected = this.dom.receptionToggles.querySelector('input:checked');
        if(selected && selected.value === '택배수령') {
            if(!document.getElementById('address1').value) {
                e.preventDefault(); alert('주소를 입력해주세요.'); return;
            }
        }
        // 처리 내역 검증
        const selects = this.dom.processingBody.querySelectorAll('select[name="processing_source"]');
        for(let s of selects) {
            if(!s.value) {
                e.preventDefault(); alert('주문처를 선택해주세요.'); s.focus(); return;
            }
        }
    }
}

document.addEventListener('DOMContentLoaded', () => new OrderApp());