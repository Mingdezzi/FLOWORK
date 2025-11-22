document.addEventListener('DOMContentLoaded', () => {
    const barcodeInput = document.getElementById('barcode-input');
    const toggleBtn = document.getElementById('toggle-scan-btn');
    const scanTableBody = document.getElementById('scan-table-body');
    const scanStatusAlert = document.getElementById('scan-status-alert');
    const scanStatusMessage = document.getElementById('scan-status-message');
    const scanTotalStatus = document.getElementById('scan-total-status');
    
    const clearBtn = document.getElementById('clear-scan-btn');
    const submitBtn = document.getElementById('submit-scan-btn');

    const fetchUrl = document.body.dataset.apiFetchVariantUrl;
    const updateUrl = document.body.dataset.bulkUpdateActualStockUrl;

    const targetStoreSelect = document.getElementById('target_store_select');
    const exportBtn = document.getElementById('btn-export-excel');
    const resetHiddenInput = document.getElementById('reset_target_store_id');
    const resetForm = document.getElementById('form-reset-stock');

    let isScanning = false;
    let scanList = {}; 
    let targetStoreId = null; 

    if (targetStoreSelect) {
        targetStoreSelect.addEventListener('change', () => {
            targetStoreId = targetStoreSelect.value;
            updateUiForStore(targetStoreId);
            
            if (Object.keys(scanList).length > 0) {
                if (confirm('매장이 변경되어 현재 스캔 목록을 초기화합니다.')) {
                    clearScanList();
                }
            }
        });
        targetStoreId = targetStoreSelect.value;
        updateUiForStore(targetStoreId);
    } else {
        targetStoreId = null;
    }

    function updateUiForStore(storeId) {
        if (exportBtn) {
            const originalHref = exportBtn.getAttribute('href').split('?')[0];
            if (storeId) {
                exportBtn.setAttribute('href', `${originalHref}?target_store_id=${storeId}`);
            } else {
                exportBtn.setAttribute('href', originalHref); 
            }
        }
        
        if (resetHiddenInput) {
            resetHiddenInput.value = storeId || '';
        }
    }

    scanStatusAlert.style.display = 'none';

    toggleBtn.addEventListener('click', () => {
        if (targetStoreSelect && !targetStoreId) {
            alert('작업할 매장을 먼저 선택해주세요.');
            targetStoreSelect.focus();
            return;
        }

        isScanning = !isScanning;
        if (isScanning) {
            toggleBtn.classList.replace('btn-success', 'btn-danger');
            toggleBtn.innerHTML = '<i class="bi bi-power me-1"></i> 리딩 OFF';
            barcodeInput.disabled = false;
            barcodeInput.placeholder = "바코드를 스캔하세요...";
            barcodeInput.focus();
        } else {
            toggleBtn.classList.replace('btn-danger', 'btn-success');
            toggleBtn.innerHTML = '<i class="bi bi-power me-1"></i> 리딩 ON';
            barcodeInput.disabled = true;
            barcodeInput.placeholder = "리딩 OFF 상태...";
            barcodeInput.value = '';
        }
    });

    barcodeInput.addEventListener('keydown', async (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            const barcode = barcodeInput.value.trim();
            if (barcode) {
                await processBarcode(barcode);
            }
            barcodeInput.value = ''; 
        }
    });

    async function processBarcode(barcode) {
        try {
            const response = await fetch(fetchUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({ 
                    barcode: barcode,
                    target_store_id: targetStoreId 
                })
            });

            const data = await response.json();

            if (response.ok && data.status === 'success') {
                addToList(data);
                showStatus(`스캔 성공: ${data.product_name} (${data.color}/${data.size})`, 'success');
            } else {
                showStatus(`오류: ${data.message}`, 'danger');
                playErrorSound(); 
            }

        } catch (error) {
            console.error('Error:', error);
            showStatus('서버 통신 오류 발생', 'danger');
            playErrorSound();
        }
    }

    function addToList(data) {
        const key = data.barcode; 

        if (scanList[key]) {
            scanList[key].scan_quantity += 1;
        } else {
            scanList[key] = {
                ...data,
                scan_quantity: 1
            };
        }
        renderTable();
    }

    function renderTable() {
        scanTableBody.innerHTML = '';
        let totalItems = 0;
        let totalQty = 0;

        const items = Object.values(scanList).reverse(); 

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
            scanTableBody.appendChild(tr);

            totalItems += 1;
            totalQty += item.scan_quantity;
        });

        scanTotalStatus.innerHTML = `총 <strong>${totalItems}</strong> 개 품목 (<strong>${totalQty}</strong>개)`;
        
        document.querySelectorAll('.qty-input').forEach(input => {
            input.addEventListener('change', (e) => {
                const bc = e.target.dataset.barcode;
                const newQty = parseInt(e.target.value);
                if (scanList[bc] && newQty >= 0) {
                    scanList[bc].scan_quantity = newQty;
                    renderTable(); 
                }
            });
        });
    }

    clearBtn.addEventListener('click', () => {
        if (confirm('스캔 목록을 초기화하시겠습니까?')) {
            clearScanList();
        }
    });

    function clearScanList() {
        scanList = {};
        renderTable();
        showStatus('목록이 초기화되었습니다.', 'info');
        barcodeInput.focus();
    }

    submitBtn.addEventListener('click', async () => {
        const items = Object.values(scanList);
        if (items.length === 0) {
            alert('저장할 스캔 내역이 없습니다.');
            return;
        }

        if (targetStoreSelect && !targetStoreId) {
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
                target_store_id: targetStoreId 
            };

            const response = await fetch(updateUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify(payload)
            });

            const result = await response.json();

            if (response.ok && result.status === 'success') {
                alert(result.message);
                scanList = {};
                renderTable();
            } else {
                alert(`저장 실패: ${result.message}`);
            }

        } catch (error) {
            console.error('Save Error:', error);
            alert('서버 통신 중 오류가 발생했습니다.');
        }
    });

    let alertTimeout;
    function showStatus(msg, type) {
        scanStatusMessage.textContent = msg;
        scanStatusAlert.className = `alert alert-${type} alert-dismissible fade show`;
        scanStatusAlert.style.display = 'block';
        
        if (alertTimeout) clearTimeout(alertTimeout);
        alertTimeout = setTimeout(() => {
        }, 3000);
    }

    function playErrorSound() {
    }

    function getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }
    
    if (resetForm) {
        resetForm.addEventListener('submit', (e) => {
            if (targetStoreSelect && !resetHiddenInput.value) {
                e.preventDefault();
                alert('초기화할 매장을 선택해주세요.');
            }
        });
    }
});