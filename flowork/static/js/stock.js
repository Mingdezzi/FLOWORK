/**
 * Stock Management Logic
 * Refactored to use Class-based structure and Common Utilities
 */

class StockApp {
    constructor() {
        this.dom = {
            analyzeExcelUrl: document.body.dataset.analyzeExcelUrl,
            horizontalSwitches: document.querySelectorAll('.horizontal-mode-switch')
        };
        
        this.init();
    }

    init() {
        // 1. 엑셀 분석기 초기화
        this.setupExcelAnalyzer({
            fileInputId: 'store_stock_excel_file',
            formId: 'form-update-store',
            wrapperId: 'wrapper-store-file',
            statusId: 'status-store-file',
            gridId: 'grid-update-store',
        });
        
        this.setupExcelAnalyzer({
            fileInputId: 'hq_stock_excel_file_full',
            formId: 'form-update-hq-full',
            wrapperId: 'wrapper-hq-file-full',
            statusId: 'status-hq-file-full',
            gridId: 'grid-update-hq-full',
        });

        this.setupExcelAnalyzer({
            fileInputId: 'db_excel_file',
            formId: 'form-import-db',
            wrapperId: 'wrapper-db-file',
            statusId: 'status-db-file',
            gridId: 'grid-import-db',
        });

        // 2. 가로/세로 모드 스위치 초기화
        this.dom.horizontalSwitches.forEach(sw => {
            sw.addEventListener('change', (e) => this.toggleHorizontalMode(e.target));
            // 초기 상태 반영
            this.toggleHorizontalMode(sw);
        });
    }

    toggleHorizontalMode(switchEl) {
        const form = switchEl.closest('form');
        const isHorizontal = switchEl.checked;
        const conditionalFields = form.querySelectorAll('.conditional-field[data-show-if="vertical"]');
        
        conditionalFields.forEach(wrapper => {
            wrapper.style.display = isHorizontal ? 'none' : 'block';
        });
    }

    setupExcelAnalyzer(config) {
        const { fileInputId, formId, wrapperId, statusId, gridId } = config;
        const fileInput = document.getElementById(fileInputId);
        const form = document.getElementById(formId);
        const wrapper = document.getElementById(wrapperId);
        const statusText = document.getElementById(statusId);
        const grid = document.getElementById(gridId);
        
        if (!fileInput || !form || !grid) return;

        const submitButton = form.querySelector('button[type="submit"]');
        const progressBar = form.querySelector('.progress-bar');
        const progressWrapper = form.querySelector('.progress-wrapper');
        const progressStatus = form.querySelector('.progress-status');
        const selects = grid.querySelectorAll('select');
        const previews = grid.querySelectorAll('.col-preview');

        let currentPreviewData = {};
        let currentColumnLetters = [];

        const resetUi = () => {
            wrapper.classList.remove('success', 'error', 'loading');
            statusText.textContent = '엑셀 파일을 선택하세요.';
            grid.style.display = 'none';
            if (submitButton) submitButton.style.display = 'none';
            if (progressWrapper) progressWrapper.style.display = 'none';
            currentPreviewData = {};
            currentColumnLetters = [];
            selects.forEach(sel => { sel.innerHTML = '<option value="">-- 열 선택 --</option>'; sel.disabled = true; });
            previews.forEach(pre => pre.innerHTML = '');
            fileInput.value = ''; 
        };

        const populateSelects = () => {
            selects.forEach(select => {
                const defaultText = select.querySelector('option:first-child')?.textContent || '-- 열 선택 --';
                select.innerHTML = `<option value="">${defaultText}</option>`;
                currentColumnLetters.forEach(letter => {
                    const option = document.createElement('option');
                    option.value = letter;
                    option.textContent = letter;
                    select.appendChild(option);
                });
                select.disabled = false;
            });
            previews.forEach(pre => pre.innerHTML = '');
        };

        // 파일 선택 이벤트
        fileInput.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return resetUi();

            wrapper.classList.remove('success', 'error');
            wrapper.classList.add('loading');
            statusText.textContent = '분석 중...';
            grid.style.display = 'none';
            if (submitButton) submitButton.style.display = 'none';

            const formData = new FormData();
            formData.append('excel_file', file);

            try {
                // [변경] fetch -> Flowork.api (FormData는 body에 직접 전달, Content-Type 헤더 자동생성 방지를 위해 옵션 조정 필요하지만, 
                // Flowork.api는 JSON을 기본으로 하므로 여기서는 예외적으로 fetch 사용하거나, Flowork.api를 확장해야 함.
                // 편의상 여기서는 직접 fetch를 사용하되 에러 핸들링 통일)
                
                const response = await fetch(this.dom.analyzeExcelUrl, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': Flowork.getCsrfToken() }, // Content-Type은 FormData가 자동 설정
                    body: formData
                });
                const data = await response.json();

                if (data.status !== 'success') throw new Error(data.message);

                currentPreviewData = data.preview_data;
                currentColumnLetters = data.column_letters;
                
                populateSelects();

                wrapper.classList.remove('loading');
                wrapper.classList.add('success');
                statusText.textContent = `완료: ${file.name} (${currentColumnLetters.length}열)`;
                grid.style.display = 'grid';
                if (submitButton) submitButton.style.display = 'block';

            } catch (error) {
                console.error('Analyze Error:', error);
                resetUi();
                wrapper.classList.remove('loading');
                wrapper.classList.add('error');
                statusText.textContent = '분석 실패';
                alert(`[오류] ${error.message}`);
            }
        });

        // 열 선택 시 미리보기
        grid.addEventListener('change', (e) => {
            if (e.target.tagName !== 'SELECT') return;
            const letter = e.target.value;
            const previewEl = e.target.closest('.mapping-item-wrapper')?.querySelector('.col-preview');
            
            if (previewEl) {
                if (letter && currentPreviewData[letter]) {
                    const list = currentPreviewData[letter].map(v => `<li>${v || '(빈 값)'}</li>`).join('');
                    previewEl.innerHTML = `<ul>${list}</ul>`;
                } else {
                    previewEl.innerHTML = '';
                }
            }
        });

        // 폼 제출 (업로드)
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!confirm('엑셀 파일 검증 및 업로드를 시작하시겠습니까?')) return;

            const formData = new FormData(form);
            
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 검증 중...';
            }

            try {
                // 1. 검증
                const verifyResp = await fetch('/api/verify_excel', {
                    method: 'POST',
                    headers: { 'X-CSRFToken': Flowork.getCsrfToken() },
                    body: formData
                });
                const verifyResult = await verifyResp.json();

                if (verifyResult.status !== 'success') throw new Error(verifyResult.message);

                if (verifyResult.suspicious_rows && verifyResult.suspicious_rows.length > 0) {
                    this.showVerificationModal(verifyResult.suspicious_rows, formData, () => this.startUpload(form.action, formData, progressBar, progressStatus, submitButton));
                } else {
                    this.startUpload(form.action, formData, progressBar, progressStatus, submitButton);
                }

            } catch (error) {
                alert(`오류: ${error.message}`);
                if (submitButton) {
                    submitButton.disabled = false;
                    submitButton.innerHTML = '<i class="bi bi-arrow-clockwise me-1"></i> 재시도';
                }
            }
        });
    }

    showVerificationModal(rows, formData, confirmCallback) {
        const modalEl = document.getElementById('verification-modal');
        if (!modalEl || typeof bootstrap === 'undefined') {
            if(confirm(`검증 경고: ${rows.length}개의 의심 행이 있습니다. 진행하시겠습니까?`)) confirmCallback();
            return;
        }
        
        const modal = new bootstrap.Modal(modalEl);
        const tbody = document.getElementById('suspicious-rows-tbody');
        document.getElementById('suspicious-count').textContent = rows.length;
        
        tbody.innerHTML = rows.map(r => `
            <tr data-row-index="${r.row_index}">
                <td class="text-center">${r.row_index}</td>
                <td>${r.preview}</td>
                <td class="text-danger small">${r.reasons}</td>
                <td class="text-center"><button type="button" class="btn btn-outline-danger btn-sm py-0 px-1 btn-exclude"><i class="bi bi-x-lg"></i></button></td>
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
            }
        };

        const btnConfirm = document.getElementById('btn-confirm-upload');
        // 기존 리스너 제거를 위해 cloneNode 사용
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

    async startUpload(url, formData, progressBar, progressStatus, submitButton) {
        if(submitButton) submitButton.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 업로드 중...';
        if(document.querySelector('.progress-wrapper')) document.querySelector('.progress-wrapper').style.display = 'block';

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'X-CSRFToken': Flowork.getCsrfToken() },
                body: formData
            });
            const data = await response.json();

            if(data.status === 'success') {
                if(data.task_id) {
                    this.pollTask(data.task_id, progressBar, progressStatus);
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

    pollTask(taskId, progressBar, progressStatus) {
        const interval = setInterval(async () => {
            try {
                const task = await Flowork.get(`/api/task_status/${taskId}`);
                if(task.status === 'processing') {
                    const pct = task.percent || 0;
                    if(progressBar) { progressBar.style.width = `${pct}%`; progressBar.textContent = `${pct}%`; }
                    if(progressStatus) progressStatus.textContent = `처리 중... (${task.current}/${task.total})`;
                } else {
                    clearInterval(interval);
                    if(task.status === 'completed') {
                        if(progressBar) { progressBar.className = 'progress-bar bg-success'; progressBar.textContent = '완료'; }
                        alert(task.result.message);
                        window.location.reload();
                    } else {
                        if(progressBar) progressBar.className = 'progress-bar bg-danger';
                        alert(`작업 오류: ${task.message}`);
                    }
                }
            } catch(e) { clearInterval(interval); }
        }, 1000);
    }
}

document.addEventListener('DOMContentLoaded', () => new StockApp());