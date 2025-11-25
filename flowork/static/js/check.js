let currentCheckApp = null;

class CheckApp {
    constructor() {
        this.dom = {
            barcodeInput: document.getElementById('barcode-input'),
            toggleBtn: document.getElementById('toggle-scan-btn'),
            scanTableBody: document.getElementById('scan-table-body'),
            scanStatusAlert: document.getElementById('scan-status-alert'),
            scanStatusMessage: document.getElementById('scan-status-message'),
            scanTotalStatus: document.getElementById('scan-total-status'),
            clearBtn: document.getElementById('clear-scan-btn'),
            submitBtn: document.getElementById('submit-scan-btn'),
            targetStoreSelect: document.getElementById('target_store_select'),
            exportBtn: document.getElementById('btn-export-excel'),
            resetHiddenInput: document.getElementById('reset_target_store_id'),
            resetForm: document.getElementById('form-reset-stock')
        };

        this.urls = {
            fetch: document.body.dataset.apiFetchVariantUrl,
            update: document.body.dataset.bulkUpdateActualStockUrl
        };

        this.isScanning = false;
        this.scanList = {}; 
        this.targetStoreId = null; 
        this.alertTimeout = null;

        this.init();
    }

    init() {
        if (this.dom.targetStoreSelect) {
            this.dom.targetStoreSelect.addEventListener('change', () => {
                this.targetStoreId = this.dom.targetStoreSelect.value;
                this.updateUiForStore(this.targetStoreId);
                
                if (Object.keys(this.scanList).length > 0) {
                    if (confirm('매장이 변경되어 현재 스캔 목록을 초기화합니다.')) {
                        this.clearScanList();
                    }
                }
            });
            this.targetStoreId = this.dom.targetStoreSelect.value;
            this.updateUiForStore(this.targetStoreId);
        } else {
            this.targetStoreId = null;
        }

        if(this.dom.scanStatusAlert) this.dom.scanStatusAlert.style.display = 'none';

        if(this.dom.toggleBtn) {
            this.dom.toggleBtn.addEventListener('click', () => this.toggleScanning());
        }

        if(this.dom.barcodeInput) {
            this.dom.barcodeInput.addEventListener('keydown', async (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    const barcode = this.dom.barcodeInput.value.trim();
                    if (barcode) {
                        await this.processBarcode(barcode);
                    }
                    this.dom.barcodeInput.value = ''; 
                }
            });
        }

        if(this.dom.clearBtn) {
            this.dom.clearBtn.addEventListener('click', () => {
                if (confirm('스캔 목록을 초기화하시겠습니까?')) {
                    this.clearScanList();
                }
            });
        }

        if(this.dom.submitBtn) {
            this.dom.submitBtn.addEventListener('click', () => this.submitScan());
        }

        if (this.dom.resetForm) {
            this.dom.resetForm.addEventListener('submit', (e) => {
                if (this.dom.targetStoreSelect && !this.dom.resetHiddenInput.value) {
                    e.preventDefault();
                    alert('초기화할 매장을 선택해주세요.');
                }
            });
        }
    }

    destroy() {
        if (this.alertTimeout) {
            clearTimeout(this.alertTimeout);
            this.alertTimeout = null;
        }
    }

    updateUiForStore(storeId) {
        if (this.dom.exportBtn) {
            const originalHref = this.dom.exportBtn.getAttribute('href').split('?')[0];
            if (storeId) {
                this.dom.exportBtn.setAttribute('href', `${originalHref}?target_store_id=${storeId}`);
            } else {
                this.dom.exportBtn.setAttribute('href', originalHref);
            }
        }
        
        if (this.dom.resetHiddenInput) {
            this.dom.resetHiddenInput.value = storeId || '';
        }
    }

    toggleScanning() {
        if (this.dom.targetStoreSelect && !this.targetStoreId) {
            alert('작업할 매장을 먼저 선택해주세요.');
            this.dom.targetStoreSelect.focus();
            return;
        }

        this.isScanning = !this.isScanning;
        if (this.isScanning) {
            this.dom.toggleBtn.classList.replace('btn-success', 'btn-danger');
            this.dom.toggleBtn.innerHTML = '<i class="bi bi-power me-1"></i> 리딩 OFF';
            this.dom.barcodeInput.disabled = false;
            this.dom.barcodeInput.placeholder = "바코드를 스캔하세요...";
            this.dom.barcodeInput.focus();
        } else {
            this.dom.toggleBtn.classList.replace('btn-danger', 'btn-success');
            this.dom.toggleBtn.innerHTML = '<i class="bi bi-power me-1"></i> 리딩 ON';
            this.dom.barcodeInput.disabled = true;
            this.dom.barcodeInput.placeholder = "리딩 OFF 상태...";
            this.dom.barcodeInput.value = '';
        }
    }

    async processBarcode(barcode) {
        try {
            const response = await fetch(this.urls.fetch, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: JSON.stringify({ 
                    barcode: barcode,
                    target_store_id: this.targetStoreId 
                })
            });

            const data = await response.json();

            if (response.ok && data.status === 'success') {
                this.addToList(data);
                this.showStatus(`스캔 성공: ${data.product_name} (${data.color}/${data.size})`, 'success');
            } else {
                this.showStatus(`오류: ${data.message}`, 'danger');
            }

        } catch (error) {
            console.error('Error:', error);
            this.showStatus('서버 통신 오류 발생', 'danger');
        }
    }

    addToList(data) {
        const key = data.barcode; 

        if (this.scanList[key]) {
            this.scanList[key].scan_quantity += 1;
        } else {
            this.scanList[key] = {
                ...data,
                scan_quantity: 1
            };
        }
        this.renderTable();
    }

    renderTable() {
        this.dom.scanTableBody.innerHTML = '';
        let totalItems = 0;
        let totalQty = 0;

        const items = Object.values(this.scanList).reverse(); 

        items.forEach(item => {
            const tr = document.createElement('tr');
            
            const diff = item.scan_quantity - item.store_stock;
            let diffClass = '';
            let diffText = diff;
            if (diff > 0) {
                diffClass = 'text-primary fw-bold';
                diffText = `+${diff}`;
            } else if (diff < 0) {
                diffClass = 'text-danger fw-bold';
            } else {
                diffClass = 'text-success';
                diffText = '0 (일치)';
            }

            tr.innerHTML = `
                <td>
                    <div class="fw-bold">${item.product_name}</div>
                    <div class="small text-muted">${item.product_number}</div>
                </td>
                <td>${item.color}</td>
                <td>${item.size}</td>
                <td>${item.store_stock}</td>
                <td>
                    <input type="number" class="form-control form-control-sm qty-input" 
                           style="width: 70px;" 
                           data-barcode="${item.barcode}" 
                           value="${item.scan_quantity}" min="0">
                </td>
                <td class="${diffClass}">${diffText}</td>
            `;
            this.dom.scanTableBody.appendChild(tr);

            totalItems += 1;
            totalQty += item.scan_quantity;
        });

        this.dom.scanTotalStatus.innerHTML = `총 <strong>${totalItems}</strong> 개 품목 (<strong>${totalQty}</strong>개)`;
        
        document.querySelectorAll('.qty-input').forEach(input => {
            input.addEventListener('change', (e) => {
                const bc = e.target.dataset.barcode;
                const newQty = parseInt(e.target.value);
                if (this.scanList[bc] && newQty >= 0) {
                    this.scanList[bc].scan_quantity = newQty;
                    this.renderTable();
                }
            });
        });
    }

    clearScanList() {
        this.scanList = {};
        this.renderTable();
        this.showStatus('목록이 초기화되었습니다.', 'info');
        this.dom.barcodeInput.focus();
    }

    async submitScan() {
        const items = Object.values(this.scanList);
        if (items.length === 0) {
            alert('저장할 스캔 내역이 없습니다.');
            return;
        }

        if (this.dom.targetStoreSelect && !this.targetStoreId) {
            alert('작업할 매장이 선택되지 않았습니다.');
            return;
        }

        if (!confirm(`총 ${items.length}개 품목의 실사 재고를 반영하시겠습니까?\n(기존 실사 재고를 덮어씁니다)`)) {
            return;
        }

        try {
            const payload = {
                items: items.map(item => ({
                    barcode: item.barcode,
                    quantity: item.scan_quantity
                })),
                target_store_id: this.targetStoreId 
            };

            const response = await fetch(this.urls.update, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: JSON.stringify(payload)
            });

            const result = await response.json();

            if (response.ok && result.status === 'success') {
                alert(result.message);
                this.scanList = {};
                this.renderTable();
            } else {
                alert(`저장 실패: ${result.message}`);
            }

        } catch (error) {
            console.error('Save Error:', error);
            alert('서버 통신 중 오류가 발생했습니다.');
        }
    }

    showStatus(msg, type) {
        if(!this.dom.scanStatusMessage || !this.dom.scanStatusAlert) return;
        
        this.dom.scanStatusMessage.textContent = msg;
        this.dom.scanStatusAlert.className = `alert alert-${type} alert-dismissible fade show`;
        this.dom.scanStatusAlert.style.display = 'block';
        
        if (this.alertTimeout) clearTimeout(this.alertTimeout);
        this.alertTimeout = setTimeout(() => {
            if(this.dom.scanStatusAlert) this.dom.scanStatusAlert.style.display = 'none';
        }, 3000);
    }

    getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }
}

document.addEventListener('turbo:load', () => {
    if (document.getElementById('barcode-input')) {
        if (currentCheckApp) {
            currentCheckApp.destroy();
        }
        currentCheckApp = new CheckApp();
    }
});

document.addEventListener('turbo:before-cache', () => {
    if (currentCheckApp) {
        currentCheckApp.destroy();
        currentCheckApp = null;
    }
});