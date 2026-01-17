document.addEventListener('DOMContentLoaded', () => {
    
    const apiFetchVariantUrl = document.body.dataset.apiFetchVariantUrl;
    const bulkUpdateActualStockUrl = document.body.dataset.bulkUpdateActualStockUrl;

    const barcodeInput = document.getElementById('barcode-input');
    const tableBody = document.getElementById('scan-table-body');
    const statusAlert = document.getElementById('scan-status-alert');
    const statusMessage = document.getElementById('scan-status-message');
    const totalStatus = document.getElementById('scan-total-status');
    const clearBtn = document.getElementById('clear-scan-btn');
    const submitBtn = document.getElementById('submit-scan-btn');
    const toggleScanBtn = document.getElementById('toggle-scan-btn');

    let isScanningEnabled = false;

    const korToEngMap = { 'ㅂ': 'q', 'ㅈ': 'w', 'ㄷ': 'e', 'ㄱ': 'r', 'ㅅ': 't', 'ㅛ': 'y', 'ㅕ': 'u', 'ㅑ': 'i', 'ㅐ': 'o', 'ㅔ': 'p', 'ㅁ': 'a', 'ㄴ': 's', 'ㅇ': 'd', 'ㄹ': 'f', 'ㅎ': 'g', 'ㅗ': 'h', 'ㅓ': 'j', 'ㅏ': 'k', 'ㅣ': 'l', 'ㅋ': 'z', 'ㅌ': 'x', 'ㅊ': 'c', 'ㅍ': 'v', 'ㅠ': 'b', 'ㅜ': 'n', 'ㅡ': 'm', 'ㅃ': 'Q', 'ㅉ': 'W', 'ㄸ': 'E', 'ㄲ': 'R', 'ㅆ': 'T', 'ㅒ': 'O', 'ㅖ': 'P' };

    if(barcodeInput) {
        barcodeInput.addEventListener('input', (e) => {
            const originalValue = e.target.value;
            const selectionStart = e.target.selectionStart;
            const regex = /[^A-Za-z0-9-]/g;
            const convertedValue = originalValue.replace(regex, (match) => { return korToEngMap[match] || ''; });
            if (originalValue !== convertedValue) {
                e.target.value = convertedValue;
                e.target.setSelectionRange(selectionStart, selectionStart);
            }
        });
    }

    const showScanError = (message) => {
        statusMessage.textContent = message;
        statusAlert.classList.remove('alert-success');
        statusAlert.classList.add('alert-danger');
        statusAlert.style.display = 'block';
    };

    if(toggleScanBtn) {
        toggleScanBtn.addEventListener('click', () => {
            isScanningEnabled = !isScanningEnabled;
            barcodeInput.disabled = !isScanningEnabled;
            if (isScanningEnabled) {
                toggleScanBtn.innerHTML = '<i class="bi bi-power me-1"></i> 리딩 OFF';
                toggleScanBtn.classList.remove('btn-success');
                toggleScanBtn.classList.add('btn-danger');
                barcodeInput.placeholder = '바코드 스캔 대기 중...';
                barcodeInput.focus();
            } else {
                toggleScanBtn.innerHTML = '<i class="bi bi-power me-1"></i> 리딩 ON';
                toggleScanBtn.classList.remove('btn-danger');
                toggleScanBtn.classList.add('btn-success');
                barcodeInput.placeholder = '리딩 OFF 상태...';
            }
        });
    }

    if(barcodeInput) {
        barcodeInput.addEventListener('keydown', (e) => {
            if (!isScanningEnabled) return;
            if (e.key === 'Enter' || e.keyCode === 13) {
                e.preventDefault();
                const barcode = barcodeInput.value.trim();
                if (barcode) {
                    barcodeInput.disabled = true;
                    toggleScanBtn.disabled = true;
                    fetchAndAddItem(barcode);
                    barcodeInput.value = '';
                }
            }
        });
    }

    const fetchAndAddItem = (barcode) => {
        fetch(apiFetchVariantUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ barcode: barcode })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                statusAlert.style.display = 'none';
                addItemToTable(data);
            } else {
                showScanError(data.message);
            }
        })
        .catch(error => {
            console.error('API Fetch 오류:', error);
            showScanError('서버 통신 오류.');
        })
        .finally(() => {
            if (isScanningEnabled) {
                barcodeInput.disabled = false;
                barcodeInput.focus();
            }
            toggleScanBtn.disabled = false;
        });
    };

    const addItemToTable = (item) => {
        const cleanedDbBarcode = item.barcode.replace(/-/g, '').toUpperCase();
        const existingRow = document.getElementById(`row-${cleanedDbBarcode}`);
        if (existingRow) {
            const quantityInput = existingRow.querySelector('.scan-quantity-input');
            quantityInput.value = parseInt(quantityInput.value) + 1;
            quantityInput.dispatchEvent(new Event('input'));
            existingRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
            existingRow.classList.add('table-info');
            setTimeout(() => existingRow.classList.remove('table-info'), 500);
        } else {
            const newRow = tableBody.insertRow(0);
            newRow.id = `row-${cleanedDbBarcode}`;
            newRow.dataset.barcode = item.barcode;
            newRow.dataset.storeStock = item.store_stock;
            newRow.innerHTML = `
                <td><div class="fw-bold">${item.product_number}</div><div class="small text-muted">${item.product_name}</div></td>
                <td>${item.color || ''}</td>
                <td>${item.size || ''}</td>
                <td class="store-stock">${item.store_stock}</td>
                <td>
                    <div class="input-group input-group-sm justify-content-center">
                        <button class="btn btn-outline-danger btn-sm btn-dec" type="button">-</button>
                        <input type="number" class="form-control scan-quantity-input" value="1" min="0">
                        <button class="btn btn-outline-primary btn-sm btn-inc" type="button">+</button>
                    </div>
                </td>
                <td class="scan-diff"></td>`;
            updateRowShortfall(newRow);
            newRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        updateTotalStatus();
    };

    const updateRowShortfall = (row) => {
        const storeStock = parseInt(row.dataset.storeStock, 10);
        const actualStock = parseInt(row.querySelector('.scan-quantity-input').value, 10) || 0;
        const diff = storeStock - actualStock;
        const diffCell = row.querySelector('.scan-diff');
        diffCell.textContent = diff;
        diffCell.className = 'scan-diff';
        if (diff > 0) diffCell.classList.add('positive');
        else if (diff < 0) diffCell.classList.add('negative');
    };

    const updateTotalStatus = () => {
        const rows = tableBody.querySelectorAll('tr');
        let totalItems = 0;
        rows.forEach(row => { totalItems += parseInt(row.querySelector('.scan-quantity-input').value, 10) || 0; });
        totalStatus.innerHTML = `총 <strong>${rows.length}</strong> 개 품목 (<strong>${totalItems}</strong>개)`;
    };

    if(tableBody) {
        tableBody.addEventListener('input', (e) => {
            if (e.target.classList.contains('scan-quantity-input')) {
                const row = e.target.closest('tr');
                if (parseInt(e.target.value) < 0 || e.target.value === '') { e.target.value = 0; }
                updateRowShortfall(row);
                updateTotalStatus();
            }
        });

        tableBody.addEventListener('click', (e) => {
            const button = e.target.closest('button');
            if (!button) return;
            const row = button.closest('tr');
            const quantityInput = row.querySelector('.scan-quantity-input');
            let quantity = parseInt(quantityInput.value, 10) || 0;
            if (button.classList.contains('btn-inc')) { quantityInput.value = quantity + 1; }
            else if (button.classList.contains('btn-dec')) { quantityInput.value = Math.max(0, quantity - 1); }
            quantityInput.dispatchEvent(new Event('input'));
        });
    }

    if(submitBtn) {
        submitBtn.addEventListener('click', () => {
            const rows = tableBody.querySelectorAll('tr');
            if (rows.length === 0) { alert('저장할 상세 검색이 없습니다.'); return; }
            if (!confirm(`총 ${rows.length}개 품목의 실사재고를 DB에 저장(업데이트)합니다.\n\n[주의]\n이 목록에 없는 상품의 실사재고는 변경되지 않습니다.\n계속하시겠습니까?`)) { return; }
            const itemsToSubmit = [];
            rows.forEach(row => { itemsToSubmit.push({ barcode: row.dataset.barcode, quantity: parseInt(row.querySelector('.scan-quantity-input').value, 10) || 0 }); });
            submitBtn.disabled = true;
            toggleScanBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 저장 중...';
            
            fetch(bulkUpdateActualStockUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ items: itemsToSubmit })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    alert(data.message);
                    tableBody.innerHTML = '';
                    updateTotalStatus();
                    window.location.reload();
                } else { alert(`저장 오류: ${data.message}`); }
            })
            .catch(error => { console.error('저장 API 오류:', error); alert('서버 통신 중 오류가 발생했습니다.'); })
            .finally(() => {
                submitBtn.disabled = false;
                toggleScanBtn.disabled = false;
                submitBtn.innerHTML = '<i class="bi bi-send-check me-1"></i>최종 저장';
            });
        });
    }
    
    if(clearBtn) {
        clearBtn.addEventListener('click', () => {
            if (tableBody.querySelectorAll('tr').length > 0 && confirm('스캔 목록을 모두 지웁니다. 계속하시겠습니까?')) {
                tableBody.innerHTML = '';
                updateTotalStatus();
                statusAlert.style.display = 'none';
            }
        });
    }
});