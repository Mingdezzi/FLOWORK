let currentStockApp = null;

class StockApp {
    constructor() {
        // HTML body에 설정된 데이터 속성 가져오기
        this.dom = {
            analyzeExcelUrl: document.body.dataset.analyzeExcelUrl,
            horizontalSwitches: document.querySelectorAll('.horizontal-mode-switch')
        };
        
        this.pollingInterval = null;
        this.init();
    }

    init() {
        // 1. 매장 재고 업로드 설정 (Store Stock)
        this.setupExcelAnalyzer({
            fileInputId: 'store_stock_excel_file',
            formId: 'form-update-store',
            wrapperId: 'wrapper-store-file',
            statusId: 'status-store-file',
            gridId: 'grid-update-store',
        });
        
        // 2. 본사 재고 업로드 설정 (HQ Stock)
        this.setupExcelAnalyzer({
            fileInputId: 'hq_stock_excel_file_full',
            formId: 'form-update-hq-full',
            wrapperId: 'wrapper-hq-file-full',
            statusId: 'status-hq-file-full',
            gridId: 'grid-update-hq-full',
        });

        // 3. 상품 DB 전체 업로드 설정 (DB Import)
        this.setupExcelAnalyzer({
            fileInputId: 'db_excel_file',
            formId: 'form-import-db',
            wrapperId: 'wrapper-db-file',
            statusId: 'status-db-file',
            gridId: 'grid-import-db',
        });

        // 가로형/세로형 스위치 이벤트 바인딩
        if (this.dom.horizontalSwitches) {
            this.dom.horizontalSwitches.forEach(sw => {
                sw.addEventListener('change', (e) => this.toggleHorizontalMode(e.target));
                // 초기 상태 반영
                this.toggleHorizontalMode(sw);
            });
        }
    }

    destroy() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
    }

    // 가로형(매트릭스) 모드 토글 처리
    toggleHorizontalMode(switchEl) {
        const form = switchEl.closest('form');
        if (!form) return;

        const isHorizontal = switchEl.checked;
        // 'vertical'일 때만 보여야 하는 필드들 (사이즈, 재고 수량 컬럼 등)
        const conditionalFields = form.querySelectorAll('.conditional-field[data-show-if="vertical"]');
        
        conditionalFields.forEach(wrapper => {
            wrapper.style.display = isHorizontal ? 'none' : 'block';
            
            // 숨겨진 필드의 select 요소는 required 속성 해제 (폼 제출 시 오류 방지)
            const select = wrapper.querySelector('select');
            if (select) {
                if (isHorizontal) {
                    select.removeAttribute('required');
                    select.disabled = true; // 값 전송 방지
                } else {
                    // 다시 보일 때는 상황에 따라 required 복구 가능 (여기서는 일단 활성화만)
                    select.disabled = false; 
                }
            }
        });
    }

    setupExcelAnalyzer(config) {
        const { fileInputId, formId, wrapperId, statusId, gridId } = config;
        
        const fileInput = document.getElementById(fileInputId);
        const form = document.getElementById(formId);
        const wrapper = document.getElementById(wrapperId);
        const statusText = document.getElementById(statusId);
        const grid = document.getElementById(gridId);
        
        // 필수 요소가 하나라도 없으면 중단 (해당 권한이 없는 경우 등)
        if (!fileInput || !form || !grid) return;

        const submitButton = form.querySelector('button[type="submit"]');
        const progressBar = form.querySelector('.progress-bar');
        const progressWrapper = form.querySelector('.progress-wrapper');
        const progressStatus = form.querySelector('.progress-status');
        
        const selects = grid.querySelectorAll('select');
        const previews = grid.querySelectorAll('.col-preview');

        let currentPreviewData = {};
        let currentColumnLetters = [];

        // UI 초기화 함수
        const resetUi = () => {
            if (wrapper) {
                wrapper.classList.remove('border-success', 'border-danger', 'bg-success-subtle');
                wrapper.classList.add('bg-light');
            }
            if (statusText) statusText.textContent = '엑셀 파일을 선택하세요.';
            
            grid.style.display = 'none';
            if (submitButton) submitButton.style.display = 'none'; // 분석 전엔 제출 버튼 숨김
            if (progressWrapper) progressWrapper.style.display = 'none';
            
            currentPreviewData = {};
            currentColumnLetters = [];
            
            selects.forEach(sel => { 
                sel.innerHTML = '<option value="">-- 열 선택 --</option>'; 
                sel.disabled = true; 
            });
            previews.forEach(pre => pre.innerHTML = '');
            
            fileInput.value = ''; // 입력 값 초기화
        };

        // 드롭다운 메뉴 채우기
        const populateSelects = () => {
            selects.forEach(select => {
                // 기존 옵션 초기화 (첫 번째 옵션 유지)
                const defaultOption = select.querySelector('option:first-child');
                const defaultText = defaultOption ? defaultOption.textContent : '-- 열 선택 --';
                
                select.innerHTML = `<option value="">${defaultText}</option>`;
                
                currentColumnLetters.forEach(letter => {
                    const option = document.createElement('option');
                    option.value = letter;
                    option.textContent = letter; // A, B, C ...
                    select.appendChild(option);
                });
                
                // 수평 모드 등으로 인해 비활성화된 경우가 아니라면 활성화
                if (!select.closest('.conditional-field') || select.closest('.conditional-field').style.display !== 'none') {
                    select.disabled = false;
                }
            });
        };

        // 파일 선택 시 이벤트 핸들러
        fileInput.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) {
                resetUi();
                return;
            }

            // 로딩 상태 표시
            if (wrapper) {
                wrapper.classList.remove('bg-light', 'border-danger');
                wrapper.classList.add('bg-warning-subtle'); // 로딩 중 색상
            }
            if (statusText) statusText.textContent = '파일 분석 중... 잠시만 기다려주세요.';
            
            grid.style.display = 'none';
            if (submitButton) submitButton.style.display = 'none';

            const formData = new FormData();
            formData.append('excel_file', file);

            try {
                if (!this.dom.analyzeExcelUrl) {
                    throw new Error("API URL이 설정되지 않았습니다. (data-analyze-excel-url missing)");
                }

                const response = await fetch(this.dom.analyzeExcelUrl, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': Flowork.getCsrfToken() }, 
                    body: formData
                });
                
                const data = await response.json();

                if (data.status !== 'success') {
                    throw new Error(data.message || "분석 실패");
                }

                // 분석 성공 시 데이터 저장
                currentPreviewData = data.preview_data;
                currentColumnLetters = data.column_letters;
                
                // 드롭다운 갱신
                populateSelects();

                // 성공 UI 업데이트
                if (wrapper) {
                    wrapper.classList.remove('bg-warning-subtle');
                    wrapper.classList.add('border-success', 'bg-success-subtle');
                }
                if (statusText) statusText.textContent = `분석 완료: ${file.name} (${currentColumnLetters.length}개 열 발견)`;
                
                // 그리드 표시 (CSS Grid 스타일 복구)
                grid.style.display = 'grid';
                
                // 제출 버튼 표시
                if (submitButton) submitButton.style.display = 'block';

            } catch (error) {
                console.error('Analyze Error:', error);
                resetUi();
                
                if (wrapper) {
                    wrapper.classList.remove('bg-warning-subtle');
                    wrapper.classList.add('border-danger', 'bg-danger-subtle');
                }
                if (statusText) statusText.textContent = '분석 실패: 파일을 다시 확인해주세요.';
                
                alert(`[오류] 엑셀 분석 중 문제가 발생했습니다.\n${error.message}`);
            }
        });

        // 컬럼 선택 시 데이터 미리보기 표시
        grid.addEventListener('change', (e) => {
            if (e.target.tagName !== 'SELECT') return;
            
            const letter = e.target.value;
            const previewEl = e.target.closest('.mapping-item')?.querySelector('.col-preview');
            
            if (previewEl) {
                if (letter && currentPreviewData[letter]) {
                    // 상위 3개 데이터만 보여줌
                    const list = currentPreviewData[letter].slice(0, 3).map(v => `<div>${v || '(빈 값)'}</div>`).join('');
                    const more = currentPreviewData[letter].length > 3 ? '<div class="text-muted">...</div>' : '';
                    previewEl.innerHTML = `<strong>[미리보기]</strong>${list}${more}`;
                    previewEl.style.display = 'block';
                } else {
                    previewEl.innerHTML = '';
                    previewEl.style.display = 'none';
                }
            }
        });

        // 폼 제출 (업로드 시작)
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            // 가로형 모드가 아닐 때 필수값 체크
            // (브라우저 required 속성이 hidden 요소에는 작동 안 할 수 있음)
            
            if (!confirm('선택한 설정으로 업로드를 시작하시겠습니까?')) return;

            const formData = new FormData(form);
            
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 처리 중...';
            }

            try {
                // 1단계: 데이터 검증 API 호출
                const verifyResp = await fetch('/api/verify_excel', {
                    method: 'POST',
                    headers: { 'X-CSRFToken': Flowork.getCsrfToken() },
                    body: formData
                });
                const verifyResult = await verifyResp.json();

                if (verifyResult.status !== 'success') throw new Error(verifyResult.message);

                // 검증 결과에 의심 행이 있으면 모달 띄우기
                if (verifyResult.suspicious_rows && verifyResult.suspicious_rows.length > 0) {
                    this.showVerificationModal(
                        verifyResult.suspicious_rows, 
                        formData, 
                        () => this.startUpload(form.action, formData, progressBar, progressStatus, submitButton)
                    );
                } else {
                    // 문제 없으면 바로 업로드 시작
                    this.startUpload(form.action, formData, progressBar, progressStatus, submitButton);
                }

            } catch (error) {
                alert(`오류: ${error.message}`);
                if (submitButton) {
                    submitButton.disabled = false;
                    submitButton.innerHTML = '<i class="bi bi-upload"></i> 업로드 시작'; // 원래 텍스트로 복구
                }
            }
        });
    }

    // 검증 모달 표시
    showVerificationModal(rows, formData, confirmCallback) {
        const modalEl = document.getElementById('verification-modal');
        
        // 모달 요소가 없으면 그냥 확인 창 띄우고 진행
        if (!modalEl || typeof bootstrap === 'undefined') {
            if(confirm(`검증 경고: ${rows.length}개의 의심스러운 행(데이터 누락 등)이 발견되었습니다.\n그래도 진행하시겠습니까?`)) {
                confirmCallback();
            }
            return;
        }
        
        const modal = new bootstrap.Modal(modalEl);
        const tbody = document.getElementById('suspicious-rows-tbody');
        const countSpan = document.getElementById('suspicious-count');
        if(countSpan) countSpan.textContent = rows.length;
        
        if(tbody) {
            tbody.innerHTML = rows.map(r => `
                <tr data-row-index="${r.row_index}">
                    <td class="text-center">${r.row_index}</td>
                    <td>${r.preview}</td>
                    <td class="text-danger small">${r.reasons}</td>
                    <td class="text-center">
                        <button type="button" class="btn btn-outline-danger btn-sm py-0 px-2 btn-exclude rounded-0">제외</button>
                    </td>
                </tr>
            `).join('');

            tbody.onclick = (e) => {
                const btn = e.target.closest('.btn-exclude');
                if (btn) {
                    const tr = btn.closest('tr');
                    tr.classList.toggle('table-danger'); // 제외 표시 스타일
                    tr.classList.toggle('text-decoration-line-through');
                    tr.classList.toggle('excluded');
                    btn.classList.toggle('active');
                    btn.textContent = btn.classList.contains('active') ? '복구' : '제외';
                }
            };
        }

        const btnConfirm = document.getElementById('btn-confirm-upload');
        // 이벤트 리스너 중복 방지를 위해 노드 복제
        const newBtn = btnConfirm.cloneNode(true);
        btnConfirm.parentNode.replaceChild(newBtn, btnConfirm);
        
        newBtn.onclick = () => {
            // 제외된 행 인덱스 수집
            const excluded = Array.from(tbody.querySelectorAll('tr.excluded')).map(tr => tr.dataset.rowIndex);
            formData.append('excluded_row_indices', excluded.join(','));
            
            modal.hide();
            confirmCallback();
        };

        modal.show();
    }

    // 실제 업로드(Celery Task 시작)
    async startUpload(url, formData, progressBar, progressStatus, submitButton) {
        if(submitButton) submitButton.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 업로드 중...';
        if(document.querySelector('.progress-wrapper')) {
            // 현재 폼 안의 progress wrapper 찾기
            const wrapper = submitButton.closest('form').querySelector('.progress-wrapper');
            if(wrapper) wrapper.style.display = 'block';
        }

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'X-CSRFToken': Flowork.getCsrfToken() },
                body: formData
            });
            const data = await response.json();

            if(data.status === 'success') {
                if(data.task_id) {
                    // 비동기 작업 폴링 시작
                    this.pollTask(data.task_id, progressBar, progressStatus);
                } else {
                    // 즉시 완료된 경우
                    alert(data.message);
                    window.location.reload();
                }
            } else {
                throw new Error(data.message);
            }
        } catch(e) {
            alert(`업로드 실패: ${e.message}`);
            if(submitButton) {
                submitButton.disabled = false;
                submitButton.innerHTML = '재시도';
            }
        }
    }

    // Celery 작업 상태 폴링
    pollTask(taskId, progressBar, progressStatus) {
        if (this.pollingInterval) clearInterval(this.pollingInterval);
        
        this.pollingInterval = setInterval(async () => {
            try {
                const task = await Flowork.get(`/api/task_status/${taskId}`);
                
                if(task.status === 'processing') {
                    const pct = task.percent || 0;
                    if(progressBar) { 
                        progressBar.style.width = `${pct}%`; 
                        progressBar.textContent = `${pct}%`; 
                    }
                    if(progressStatus) {
                        progressStatus.textContent = `처리 중... (${task.current}/${task.total})`;
                    }
                } else {
                    clearInterval(this.pollingInterval);
                    this.pollingInterval = null;
                    
                    if(task.status === 'completed') {
                        if(progressBar) { 
                            progressBar.className = 'progress-bar bg-success progress-bar-striped'; 
                            progressBar.textContent = '완료!'; 
                        }
                        setTimeout(() => {
                            alert(task.result.message || '작업이 완료되었습니다.');
                            window.location.reload();
                        }, 500);
                    } else {
                        if(progressBar) {
                            progressBar.className = 'progress-bar bg-danger';
                            progressBar.textContent = '에러';
                        }
                        alert(`작업 오류: ${task.message}`);
                    }
                }
            } catch(e) { 
                console.error("Polling error", e);
                // 네트워크 오류 등으로 폴링 실패 시에도 일단 계속 시도하거나 멈춤
            }
        }, 1000);
    }
}

// 앱 초기화 (Turbo Load 지원)
document.addEventListener('turbo:load', () => {
    // .update-stock-form 클래스를 가진 폼이 하나라도 있으면 초기화
    if (document.querySelector('.update-stock-form')) {
        if (currentStockApp) {
            currentStockApp.destroy();
        }
        currentStockApp = new StockApp();
    }
});

document.addEventListener('turbo:before-cache', () => {
    if (currentStockApp) {
        currentStockApp.destroy();
        currentStockApp = null;
    }
});