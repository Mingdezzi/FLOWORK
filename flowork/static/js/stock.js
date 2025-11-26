let currentStockApp = null;

class StockApp {
    constructor() {
        this.dom = {
            analyzeExcelUrl: document.body.dataset.analyzeExcelUrl,
            horizontalSwitches: document.querySelectorAll('.horizontal-mode-switch')
        };
        
        this.pollingInterval = null;
        console.log("[StockApp] Initialized. Analyze URL:", this.dom.analyzeExcelUrl);
        
        this.init();
    }

    init() {
        // 3가지 업로드 폼에 대한 설정
        const configs = [
            {
                id: 'store',
                fileInputId: 'store_stock_excel_file',
                formId: 'form-update-store',
                wrapperId: 'wrapper-store-file',
                statusId: 'status-store-file',
                gridId: 'grid-update-store',
            },
            {
                id: 'hq',
                fileInputId: 'hq_stock_excel_file_full',
                formId: 'form-update-hq-full',
                wrapperId: 'wrapper-hq-file-full',
                statusId: 'status-hq-file-full',
                gridId: 'grid-update-hq-full',
            },
            {
                id: 'db',
                fileInputId: 'db_excel_file',
                formId: 'form-import-db',
                wrapperId: 'wrapper-db-file',
                statusId: 'status-db-file',
                gridId: 'grid-import-db',
            }
        ];

        configs.forEach(config => this.setupExcelAnalyzer(config));

        // 가로형/세로형 스위치 초기화
        if (this.dom.horizontalSwitches.length > 0) {
            this.dom.horizontalSwitches.forEach(sw => {
                sw.addEventListener('change', (e) => this.toggleHorizontalMode(e.target));
                this.toggleHorizontalMode(sw); // 초기 상태 적용
            });
        }
    }

    destroy() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
    }

    toggleHorizontalMode(switchEl) {
        const form = switchEl.closest('form');
        if (!form) return;
        
        const isHorizontal = switchEl.checked;
        // 'vertical'일 때만 보여야 하는 필드(사이즈, 재고 등) 찾기
        const conditionalFields = form.querySelectorAll('.conditional-field[data-show-if="vertical"]');
        
        conditionalFields.forEach(wrapper => {
            wrapper.style.display = isHorizontal ? 'none' : 'block';
            const select = wrapper.querySelector('select');
            if (select) {
                select.disabled = isHorizontal; // 값 전송 방지
                if (isHorizontal) select.removeAttribute('required'); // 필수 체크 해제
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
        
        // 요소가 하나라도 없으면 (권한 부족 등으로 렌더링 안 된 경우) 스킵
        if (!fileInput || !form || !grid) {
            return;
        }

        const submitButton = form.querySelector('button[type="submit"]');
        const progressBar = form.querySelector('.progress-bar');
        const selects = grid.querySelectorAll('select');
        
        let currentPreviewData = {};
        let currentColumnLetters = [];

        // UI 초기화 (리셋)
        const resetUi = () => {
            if(wrapper) {
                wrapper.classList.remove('border-success', 'border-danger', 'bg-success-subtle', 'bg-danger-subtle', 'bg-warning-subtle');
                wrapper.classList.add('bg-light');
            }
            if(statusText) statusText.textContent = '엑셀 파일을 선택하세요.';
            
            grid.style.display = 'none';
            if(submitButton) submitButton.style.display = 'none';
            
            currentPreviewData = {};
            currentColumnLetters = [];
            
            selects.forEach(sel => { 
                sel.innerHTML = '<option value="">-- 열 선택 --</option>'; 
                sel.disabled = true; 
            });
            
            // 미리보기 텍스트 초기화
            grid.querySelectorAll('.col-preview').forEach(pre => pre.innerHTML = '');
            
            fileInput.value = ''; // 파일 입력값 초기화 (같은 파일 다시 선택 가능하도록)
        };

        // [핵심] 파일 선택 이벤트
        fileInput.addEventListener('change', async (e) => {
            console.log(`[StockApp] File selected: ${fileInputId}`);
            const file = e.target.files[0];
            if (!file) { 
                resetUi(); 
                return; 
            }

            // 로딩 표시
            if(wrapper) {
                wrapper.classList.remove('bg-light', 'border-danger', 'bg-success-subtle');
                wrapper.classList.add('bg-warning-subtle');
            }
            if(statusText) statusText.textContent = '파일 분석 중... 잠시만 기다려주세요.';
            
            grid.style.display = 'none';
            if(submitButton) submitButton.style.display = 'none';

            const formData = new FormData();
            formData.append('excel_file', file);

            try {
                if (!this.dom.analyzeExcelUrl) throw new Error("분석 API URL 설정을 찾을 수 없습니다.");

                const response = await fetch(this.dom.analyzeExcelUrl, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': Flowork.getCsrfToken() },
                    body: formData
                });
                
                const data = await response.json();

                if (data.status !== 'success') {
                    throw new Error(data.message || "분석 실패");
                }

                // 분석 성공
                currentPreviewData = data.preview_data;
                currentColumnLetters = data.column_letters;
                
                // 드롭다운 채우기
                selects.forEach(select => {
                    const defaultText = select.querySelector('option:first-child')?.textContent || '-- 열 선택 --';
                    select.innerHTML = `<option value="">${defaultText}</option>`;
                    currentColumnLetters.forEach(letter => {
                        const opt = document.createElement('option');
                        opt.value = letter;
                        opt.textContent = letter;
                        select.appendChild(opt);
                    });
                    select.disabled = false;
                });

                // UI 성공 상태로 변경
                if(wrapper) {
                    wrapper.classList.remove('bg-warning-subtle');
                    wrapper.classList.add('border-success', 'bg-success-subtle');
                }
                if(statusText) statusText.textContent = `분석 완료: ${file.name} (${currentColumnLetters.length}개 열)`;
                
                grid.style.display = 'grid';
                if(submitButton) submitButton.style.display = 'block';

            } catch (error) {
                console.error("[StockApp] Analyze Error:", error);
                resetUi();
                
                if(wrapper) {
                    wrapper.classList.remove('bg-warning-subtle');
                    wrapper.classList.add('border-danger', 'bg-danger-subtle');
                }
                if(statusText) statusText.textContent = '분석 실패';
                
                alert(`[오류] 엑셀 분석 중 문제가 발생했습니다.\n${error.message}`);
            }
        });

        // 컬럼 선택 시 데이터 미리보기
        grid.addEventListener('change', (e) => {
            if (e.target.tagName !== 'SELECT') return;
            
            const letter = e.target.value;
            const previewEl = e.target.closest('.mapping-item-wrapper')?.querySelector('.col-preview');
            
            if (previewEl) {
                if (letter && currentPreviewData[letter]) {
                    const items = currentPreviewData[letter].slice(0,3).map(v => `<div>${v||'(빈 값)'}</div>`).join('');
                    const more = currentPreviewData[letter].length > 3 ? '<div class="text-muted small">...</div>' : '';
                    previewEl.innerHTML = `<div class="small mt-1 border-top pt-1">${items}${more}</div>`;
                } else {
                    previewEl.innerHTML = '';
                }
            }
        });

        // 폼 제출 (업로드 시작)
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            if(!confirm('선택한 설정으로 업로드를 시작하시겠습니까?')) return;

            const formData = new FormData(form);
            
            if(submitButton) {
                submitButton.disabled = true;
                submitButton.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 처리 중...';
            }

            try {
                // 1단계: 검증
                const verifyResp = await fetch('/api/verify_excel', {
                    method: 'POST',
                    headers: { 'X-CSRFToken': Flowork.getCsrfToken() },
                    body: formData
                });
                const vData = await verifyResp.json();
                
                if(vData.status !== 'success') throw new Error(vData.message);

                // 2단계: (필요시) 모달 확인 후 업로드
                if (vData.suspicious_rows && vData.suspicious_rows.length > 0) {
                    this.showVerificationModal(
                        vData.suspicious_rows, 
                        formData, 
                        () => this.startUpload(form.action, formData, progressBar, submitButton)
                    );
                } else {
                    await this.startUpload(form.action, formData, progressBar, submitButton);
                }

            } catch(error) {
                alert(`오류: ${error.message}`);
                if(submitButton) {
                    submitButton.disabled = false;
                    submitButton.innerHTML = '<i class="bi bi-upload"></i> 업로드 시작';
                }
            }
        });
    }

    async startUpload(url, formData, progressBar, submitButton) {
        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'X-CSRFToken': Flowork.getCsrfToken() },
                body: formData
            });
            const data = await response.json();

            if(data.status === 'success') {
                if(data.task_id) {
                    this.pollTask(data.task_id, progressBar);
                } else {
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

    pollTask(taskId, progressBar) {
        if(this.pollingInterval) clearInterval(this.pollingInterval);
        
        // 진행률 바 표시
        if(progressBar) {
            const wrapper = progressBar.closest('.progress-wrapper');
            if(wrapper) wrapper.style.display = 'block';
        }

        this.pollingInterval = setInterval(async () => {
            try {
                const res = await fetch(`/api/task_status/${taskId}`);
                const task = await res.json();
                
                if(task.status === 'processing') {
                    if(progressBar) {
                        progressBar.style.width = `${task.percent}%`;
                        progressBar.textContent = `${task.percent}%`;
                    }
                } else {
                    clearInterval(this.pollingInterval);
                    if(task.status === 'completed') {
                        if(progressBar) { 
                            progressBar.className = 'progress-bar bg-success'; 
                            progressBar.textContent = '완료!'; 
                        }
                        setTimeout(() => {
                            alert(task.result.message);
                            window.location.reload();
                        }, 500);
                    } else {
                        if(progressBar) {
                            progressBar.className = 'progress-bar bg-danger';
                            progressBar.textContent = '에러';
                        }
                        alert(`작업 실패: ${task.message}`);
                    }
                }
            } catch(e) {
                // 폴링 에러는 무시하고 계속 시도 (네트워크 일시 장애 등)
                console.warn("Polling error:", e);
            }
        }, 1000);
    }

    showVerificationModal(rows, formData, confirmCallback) {
        const modalEl = document.getElementById('verification-modal');
        
        if (!modalEl || typeof bootstrap === 'undefined') {
            if(confirm(`검증 경고: ${rows.length}개의 의심스러운 행이 발견되었습니다.\n그래도 진행하시겠습니까?`)) {
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
                    tr.classList.toggle('table-danger');
                    tr.classList.toggle('text-decoration-line-through');
                    tr.classList.toggle('excluded');
                    btn.classList.toggle('active');
                    btn.textContent = btn.classList.contains('active') ? '복구' : '제외';
                }
            };
        }

        const btnConfirm = document.getElementById('btn-confirm-upload');
        const newBtn = btnConfirm.cloneNode(true);
        btnConfirm.parentNode.replaceChild(newBtn, btnConfirm);
        
        newBtn.onclick = () => {
            const excluded = Array.from(tbody.querySelectorAll('tr.excluded')).map(tr => tr.dataset.rowIndex);
            formData.append('excluded_row_indices', excluded.join(','));
            
            modal.hide();
            confirmCallback();
        };

        modal.show();
    }
}

// 페이지 로드 시 초기화 (Turbo 및 일반 로드 호환)
document.addEventListener('turbo:load', () => {
    if (document.querySelector('.update-stock-form')) {
        if (currentStockApp) currentStockApp.destroy();
        currentStockApp = new StockApp();
    }
});