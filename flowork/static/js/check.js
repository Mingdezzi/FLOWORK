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

    // [수정] 브랜드 관리자용 매장 선택 요소 가져오기
    const targetStoreSelect = document.getElementById('target_store_select');
    const exportBtn = document.getElementById('btn-export-excel');
    const resetHiddenInput = document.getElementById('reset_target_store_id');
    const resetForm = document.getElementById('form-reset-stock');

    let isScanning = false;
    let scanList = {}; // { barcode_cleaned: { variant_id, product_name, ... , quantity } }
    let targetStoreId = null; // 선택된 매장 ID

    // [신규] 초기 매장 ID 설정 및 이벤트 리스너
    if (targetStoreSelect) {
        // 브랜드 관리자일 경우
        targetStoreSelect.addEventListener('change', () => {
            targetStoreId = targetStoreSelect.value;
            updateUiForStore(targetStoreId);
            
            // 매장이 변경되면 기존 스캔 목록 초기화 (데이터 혼동 방지)
            if (Object.keys(scanList).length > 0) {
                if (confirm('매장이 변경되어 현재 스캔 목록을 초기화합니다.')) {
                    clearScanList();
                } else {
                    // 취소 시 이전 값으로 되돌리기 (복잡하면 생략 가능, 여기선 값만 유지)
                }
            }
        });
        // 초기값 설정
        targetStoreId = targetStoreSelect.value;
        updateUiForStore(targetStoreId);
    } else {
        // 매장 관리자일 경우 (targetStoreId는 null -> 서버에서 current_user.store_id 사용)
        targetStoreId = null;
    }

    // [신규] 매장 변경 시 UI(엑셀 링크, 초기화 폼) 업데이트 함수
    function updateUiForStore(storeId) {
        // 엑셀 다운로드 링크 수정
        if (exportBtn) {
            const originalHref = exportBtn.getAttribute('href').split('?')[0];
            if (storeId) {
                exportBtn.setAttribute('href', `${originalHref}?target_store_id=${storeId}`);
            } else {
                exportBtn.setAttribute('href', originalHref); // 혹은 href="#" 처리
            }
        }
        
        // 초기화 폼 히든 값 수정
        if (resetHiddenInput) {
            resetHiddenInput.value = storeId || '';
        }
    }

    // 초기 상태: 알림 숨김
    scanStatusAlert.style.display = 'none';

    // 리딩 ON/OFF 토글
    toggleBtn.addEventListener('click', () => {
        // 브랜드 관리자가 매장을 선택하지 않고 리딩을 켜려 할 때 경고
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

    // 바코드 입력 처리 (Enter 키)
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

    // 바코드 처리 함수
    async function processBarcode(barcode) {
        try {
            // 1. 서버에 바코드 정보 및 재고 조회
            // [수정] target_store_id를 함께 전송
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
                // 2. 스캔 목록에 추가/업데이트
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
        // clean_barcode 등을 키로 사용 (서버가 주는 유니크 키가 좋음, 여기선 barcode 사용)
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

        // 최신 스캔이 위로 오게 하려면 배열로 변환 후 역순 정렬 or prepend 사용
        // 여기서는 단순 순회
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
        
        // 수량 수동 변경 이벤트 리스너
        document.querySelectorAll('.qty-input').forEach(input => {
            input.addEventListener('change', (e) => {
                const bc = e.target.dataset.barcode;
                const newQty = parseInt(e.target.value);
                if (scanList[bc] && newQty >= 0) {
                    scanList[bc].scan_quantity = newQty;
                    renderTable(); // 다시 렌더링해서 과부족 업데이트
                }
            });
        });
    }

    // 목록 초기화
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

    // 최종 저장
    submitBtn.addEventListener('click', async () => {
        const items = Object.values(scanList);
        if (items.length === 0) {
            alert('저장할 스캔 내역이 없습니다.');
            return;
        }

        // 브랜드 관리자가 매장 선택 안했으면 차단
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
                target_store_id: targetStoreId // [수정] 매장 ID 함께 전송
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
                // 페이지 새로고침 없이 계속 작업 가능하도록
            } else {
                alert(`저장 실패: ${result.message}`);
            }

        } catch (error) {
            console.error('Save Error:', error);
            alert('서버 통신 중 오류가 발생했습니다.');
        }
    });

    // 유틸: 상태 메시지 표시
    let alertTimeout;
    function showStatus(msg, type) {
        scanStatusMessage.textContent = msg;
        scanStatusAlert.className = `alert alert-${type} alert-dismissible fade show`;
        scanStatusAlert.style.display = 'block';
        
        if (alertTimeout) clearTimeout(alertTimeout);
        alertTimeout = setTimeout(() => {
            // scanStatusAlert.style.display = 'none'; // 굳이 안 숨겨도 됨
        }, 3000);
    }

    // 유틸: 에러 사운드 (선택 사항)
    function playErrorSound() {
        // 비프음 등 구현 가능
    }

    // 유틸: CSRF 토큰 가져오기 (메타 태그에서)
    function getCsrfToken() {
        // HTML <meta name="csrf-token" content="..."> 가 있다고 가정
        // 없다면 Hidden Input 등에서 가져와야 함. 
        // Flask-WTF를 쓴다면 보통 폼 안에 있거나 메타 태그에 둠.
        // 여기서는 임시로 null 처리하거나, 필요 시 구현.
        // 보통 fetch 시에는 headers에 'X-CSRFToken': ... 를 넣음.
        
        // 예시:
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }
    
    // [추가] 재고 초기화 폼 제출 전 검증
    if (resetForm) {
        resetForm.addEventListener('submit', (e) => {
            if (targetStoreSelect && !resetHiddenInput.value) {
                e.preventDefault();
                alert('초기화할 매장을 선택해주세요.');
            }
        });
    }
});