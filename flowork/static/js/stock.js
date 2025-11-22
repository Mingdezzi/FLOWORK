document.addEventListener('DOMContentLoaded', () => {
    
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    const analyzeExcelUrl = document.body.dataset.analyzeExcelUrl;
    
    function setupExcelAnalyzer(config) {
        const { fileInputId, formId, wrapperId, statusId, gridId } = config;

        const fileInput = document.getElementById(fileInputId);
        const form = document.getElementById(formId);
        const wrapper = document.getElementById(wrapperId);
        const statusText = document.getElementById(statusId);
        const grid = document.getElementById(gridId);
        const submitButton = form?.querySelector('button[type="submit"]');
        const progressBar = form?.querySelector('.progress-bar');
        const progressWrapper = form?.querySelector('.progress-wrapper');
        const progressStatus = form?.querySelector('.progress-status');

        if (!fileInput || !form || !grid) return;

        const selects = grid.querySelectorAll('select');
        const previews = grid.querySelectorAll('.col-preview');

        let currentPreviewData = {};
        let currentColumnLetters = [];

        function resetUi() {
            wrapper.classList.remove('success', 'error', 'loading');
            statusText.textContent = '엑셀 파일을 선택하세요.';
            grid.style.display = 'none';
            if (submitButton) submitButton.style.display = 'none';
            if (progressWrapper) progressWrapper.style.display = 'none';
            currentPreviewData = {};
            currentColumnLetters = [];
            disableSelects();
            fileInput.value = ''; 
        }

        function disableSelects() {
             selects.forEach(select => {
                const defaultOptionText = select.querySelector('option:first-child')?.textContent || '-- 열 선택 --';
                select.innerHTML = `<option value="">${defaultOptionText}</option>`;
                select.disabled = true;
            });
            previews.forEach(preview => {
                preview.innerHTML = '';
            });
        }

        function populateSelects() {
            selects.forEach(select => {
                const defaultOptionText = select.querySelector('option:first-child')?.textContent || '-- 열 선택 --';
                select.innerHTML = `<option value="">${defaultOptionText}</option>`;
                
                currentColumnLetters.forEach(letter => {
                    const option = document.createElement('option');
                    option.value = letter;
                    option.textContent = letter;
                    select.appendChild(option);
                });
                select.disabled = false;
            });
            
            previews.forEach(preview => {
                preview.innerHTML = '';
            });
        }
        
        fileInput.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) {
                resetUi();
                return;
            }

            wrapper.classList.remove('success', 'error');
            wrapper.classList.add('loading');
            statusText.textContent = '파일 분석 중... (로딩...)';
            grid.style.display = 'none';
            if (submitButton) submitButton.style.display = 'none';
            if (progressWrapper) progressWrapper.style.display = 'none';
            disableSelects();

            const formData = new FormData();
            formData.append('excel_file', file);

            try {
                const response = await fetch(analyzeExcelUrl, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrfToken
                    },
                    body: formData
                });
                const data = await response.json();

                if (!response.ok || data.status === 'error') {
                    throw new Error(data.message || '알 수 없는 오류');
                }
                
                currentPreviewData = data.preview_data;
                currentColumnLetters = data.column_letters;
                
                populateSelects();

                wrapper.classList.remove('loading');
                wrapper.classList.add('success');
                statusText.textContent = `분석 완료: ${file.name} (총 ${currentColumnLetters.length}개 열)`;
                grid.style.display = 'grid';
                if (submitButton) submitButton.style.display = 'block';

            } catch (error) {
                console.error('Excel Analyze Error:', error);
                resetUi();
                wrapper.classList.remove('loading');
                wrapper.classList.add('error');
                statusText.textContent = `분석 실패: ${error.message}`;
                alert(`[엑셀 분석 오류]\n${error.message}\n\n파일을 다시 선택해주세요.`);
            }
        });

        grid.addEventListener('change', (e) => {
            if (e.target.tagName !== 'SELECT') return;

            const selectedLetter = e.target.value;
            const mappingItem = e.target.closest('.mapping-item');
            const previewEl = mappingItem ? mappingItem.querySelector('.col-preview') : null;

            if (!previewEl) return;

            if (selectedLetter && currentPreviewData[selectedLetter]) {
                const previewHtml = currentPreviewData[selectedLetter]
                    .map(item => `<li>${item || '(빈 값)'}</li>`)
                    .join('');
                previewEl.innerHTML = `<ul>${previewHtml}</ul>`;
            } else {
                previewEl.innerHTML = '';
            }
        });

        if (form) {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const msg = '엑셀 파일 검증을 시작합니다.\n검증 후 문제가 없는 행만 업로드됩니다.\n계속하시겠습니까?';
                if (!confirm(msg)) return;

                const formData = new FormData(form);
                
                if (submitButton) {
                    submitButton.disabled = true;
                    submitButton.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 데이터 검증 중...';
                }

                try {
                    const verifyResp = await fetch('/api/verify_excel', {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': csrfToken
                        },
                        body: formData
                    });

                    const contentType = verifyResp.headers.get("content-type");
                    if (!verifyResp.ok || !contentType || !contentType.includes("application/json")) {
                        const text = await verifyResp.text();
                        throw new Error(`서버 오류 (${verifyResp.status}): ${text.substring(0, 100)}...`);
                    }

                    const verifyResult = await verifyResp.json();

                    if (verifyResult.status !== 'success') {
                        throw new Error(verifyResult.message);
                    }

                    const suspiciousRows = verifyResult.suspicious_rows || [];
                    
                    if (suspiciousRows.length > 0) {
                        showVerificationModal(suspiciousRows, formData);
                    } else {
                        startUploadProcess(formData);
                    }

                } catch (error) {
                    console.error('Verification Error:', error);
                    alert(`검증 중 오류 발생:\n${error.message}\n\n(로그인이 만료되었거나 서버에 문제가 있을 수 있습니다.)`);
                    resetSubmitButton();
                }
            });
        }

        function showVerificationModal(suspiciousRows, originalFormData) {
            const modalEl = document.getElementById('verification-modal');
            if (!modalEl || typeof bootstrap === 'undefined') {
                if(confirm(`검증 결과 ${suspiciousRows.length}개의 의심 행이 발견되었습니다.\n(모달을 띄울 수 없어 바로 진행합니다.)\n\n그대로 진행하시겠습니까?`)) {
                    startUploadProcess(originalFormData);
                } else {
                    resetSubmitButton();
                }
                return;
            }

            const modal = new bootstrap.Modal(modalEl);
            const tbody = document.getElementById('suspicious-rows-tbody');
            const countSpan = document.getElementById('suspicious-count');
            const confirmBtn = document.getElementById('btn-confirm-upload');
            const cancelBtn = document.getElementById('btn-cancel-verification');
            
            countSpan.textContent = suspiciousRows.length;
            tbody.innerHTML = '';
            
            suspiciousRows.forEach(row => {
                const tr = document.createElement('tr');
                tr.dataset.rowIndex = row.row_index;
                tr.innerHTML = `
                    <td class="text-center">${row.row_index}</td>
                    <td>${row.preview}</td>
                    <td class="text-danger small">${row.reasons}</td>
                    <td class="text-center">
                        <button type="button" class="btn btn-outline-danger btn-sm py-0 px-1 btn-exclude-row" title="제외하기">
                            <i class="bi bi-x-lg"></i>
                        </button>
                    </td>
                `;
                tbody.appendChild(tr);
            });

            tbody.onclick = (e) => {
                const btn = e.target.closest('.btn-exclude-row');
                if (btn) {
                    const tr = btn.closest('tr');
                    if (tr.classList.contains('excluded')) {
                        tr.classList.remove('table-danger', 'text-decoration-line-through', 'excluded');
                        btn.classList.remove('active');
                    } else {
                        tr.classList.add('table-danger', 'text-decoration-line-through', 'excluded');
                        btn.classList.add('active');
                    }
                }
            };

            confirmBtn.onclick = () => {
                const excludedIndices = [];
                tbody.querySelectorAll('tr.excluded').forEach(tr => {
                    excludedIndices.push(tr.dataset.rowIndex);
                });
                
                originalFormData.append('excluded_row_indices', excludedIndices.join(','));
                
                modal.hide();
                startUploadProcess(originalFormData);
            };
            
            cancelBtn.onclick = () => {
                resetSubmitButton();
            };

            modal.show();
        }

        async function startUploadProcess(formData) {
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 작업 시작...';
            }
            if (progressWrapper) progressWrapper.style.display = 'block';
            if (progressBar) {
                progressBar.style.width = '0%';
                progressBar.textContent = '0%';
                progressBar.classList.add('progress-bar-animated');
                progressBar.classList.remove('bg-success', 'bg-danger');
            }
            if (progressStatus) progressStatus.textContent = '서버에 데이터 전송 중...';

            try {
                const actionUrl = form.action; 
                const response = await fetch(actionUrl, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrfToken
                    },
                    body: formData
                });
                const data = await response.json();

                if (data.status === 'success' && data.task_id) {
                    pollTaskStatus(data.task_id);
                } else if (data.status === 'success') {
                    finishProgress();
                    alert(data.message);
                    window.location.reload();
                } else {
                    throw new Error(data.message || '작업 시작 실패');
                }
            } catch (error) {
                console.error('Upload Error:', error);
                alert(`업로드 오류: ${error.message}`);
                resetSubmitButton();
                if (progressWrapper) progressWrapper.style.display = 'none';
            }
        }

        function pollTaskStatus(taskId) {
            const intervalId = setInterval(async () => {
                try {
                    const res = await fetch(`/api/task_status/${taskId}`);
                    if (!res.ok) throw new Error("Status check failed");
                    
                    const task = await res.json();

                    if (task.status === 'processing') {
                        const percent = task.percent || 0;
                        if (progressBar) {
                            progressBar.style.width = `${percent}%`;
                            progressBar.textContent = `${percent}%`;
                        }
                        if (progressStatus) {
                            progressStatus.textContent = `처리 중... (${task.current} / ${task.total})`;
                        }
                    } else if (task.status === 'completed') {
                        clearInterval(intervalId);
                        finishProgress();
                        alert(task.result.message);
                        window.location.reload();
                    } else if (task.status === 'error') {
                        clearInterval(intervalId);
                        if (progressBar) progressBar.classList.add('bg-danger');
                        if (progressStatus) progressStatus.textContent = '오류 발생';
                        alert(`작업 중 오류 발생: ${task.message}`);
                        resetSubmitButton();
                    } else if (task.status === 'not_found') {
                        clearInterval(intervalId);
                        alert('작업 상태를 찾을 수 없습니다.');
                        resetSubmitButton();
                    }

                } catch (err) {
                    console.error('Polling error:', err);
                }
            }, 1000);
        }
        
        function finishProgress() {
            if (progressBar) {
                progressBar.style.width = '100%';
                progressBar.textContent = '100%';
                progressBar.classList.remove('progress-bar-animated');
                progressBar.classList.add('bg-success');
            }
            if (progressStatus) progressStatus.textContent = '완료!';
        }

        function resetSubmitButton() {
            if (submitButton) {
                submitButton.disabled = false;
                submitButton.innerHTML = '<i class="bi bi-arrow-clockwise me-1"></i> 검토 및 업로드';
            }
        }
    }
    
    function initModeSwitches() {
        const switches = document.querySelectorAll('.horizontal-mode-switch');
        switches.forEach(sw => {
            sw.addEventListener('change', (e) => {
                const form = e.target.closest('form');
                const isHorizontal = e.target.checked;
                const conditionalFields = form.querySelectorAll('.conditional-field[data-show-if="vertical"]');
                
                conditionalFields.forEach(wrapper => {
                    if (isHorizontal) {
                        wrapper.style.display = 'none';
                    } else {
                        wrapper.style.display = 'block';
                    }
                });
            });
            
            const form = sw.closest('form');
            const conditionalFields = form.querySelectorAll('.conditional-field[data-show-if="vertical"]');
            if (sw.checked) {
                conditionalFields.forEach(w => w.style.display = 'none');
            } else {
                conditionalFields.forEach(w => w.style.display = 'block');
            }
        });
    }
    initModeSwitches();

    const storeConfig = {
        fileInputId: 'store_stock_excel_file',
        formId: 'form-update-store',
        wrapperId: 'wrapper-store-file',
        statusId: 'status-store-file',
        gridId: 'grid-update-store',
    };
    if (document.getElementById(storeConfig.formId)) {
        setupExcelAnalyzer(storeConfig);
    }
    
    const hqConfigFull = {
        fileInputId: 'hq_stock_excel_file_full',
        formId: 'form-update-hq-full',
        wrapperId: 'wrapper-hq-file-full',
        statusId: 'status-hq-file-full',
        gridId: 'grid-update-hq-full',
    };
    if (document.getElementById(hqConfigFull.formId)) {
        setupExcelAnalyzer(hqConfigFull);
    }

    const dbImportConfig = {
        fileInputId: 'db_excel_file',
        formId: 'form-import-db',
        wrapperId: 'wrapper-db-file',
        statusId: 'status-db-file',
        gridId: 'grid-import-db',
    };
    if (document.getElementById(dbImportConfig.formId)) {
        setupExcelAnalyzer(dbImportConfig);
    }
});