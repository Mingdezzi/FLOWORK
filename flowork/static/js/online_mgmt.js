document.addEventListener('DOMContentLoaded', () => {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    
    const btnStart = document.getElementById('btn-start-process');
    const btnReset = document.getElementById('btn-reset-selection');
    const btnClearBatch = document.getElementById('btn-clear-current-batch');
    
    const btnSearchExec = document.getElementById('btn-search-exec');
    const btnSearchReset = document.getElementById('btn-search-reset');
    const searchMultiCodes = document.getElementById('search-multi-codes');
    const searchName = document.getElementById('search-name');
    const searchYear = document.getElementById('search-year');
    const searchCategory = document.getElementById('search-category');
    
    const btnUploadLogo = document.getElementById('btn-upload-logo');
    const inputLogoFile = document.getElementById('logo-file');

    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    const progressContainer = document.getElementById('progress-container');

    const imgModalEl = document.getElementById('imagePreviewModal');
    const imgModal = new bootstrap.Modal(imgModalEl);
    const folderModalEl = document.getElementById('folderViewModal');
    const folderModal = new bootstrap.Modal(folderModalEl);
    
    const bodyData = document.body.dataset;
    const API_LIST = bodyData.apiList;
    const API_PROCESS = bodyData.apiProcess;
    const API_OPTIONS = bodyData.apiOptions;
    const API_TASK_STATUS = bodyData.apiTaskStatusPrefix;
    const API_FOLDER = bodyData.apiFolderPrefix;
    const API_LOGO_UPLOAD = bodyData.apiLogoUpload;
    const API_DOWNLOAD = "/api/product/download/";
    const API_DELETE = "/api/product/delete_image_data";

    let isProcessing = false;
    let pollingInterval = null;
    
    const paginationState = {
        'tab-current-ready': 1, 
        'tab-current-processing': 1, 
        'tab-current-completed': 1, 
        'tab-current-failed': 1,
        'tab-hist-all': 1, 
        'tab-hist-completed': 1, 
        'tab-hist-failed': 1
    };

    let currentBatchCodes = JSON.parse(sessionStorage.getItem('currentBatchCodes') || '[]');

    loadUserOptions();
    initEventListeners();
    
    const activeTabs = document.querySelectorAll('.nav-link.active');
    activeTabs.forEach(tab => loadTabContent(tab));

    async function loadUserOptions() {
        try {
            const res = await fetch(API_OPTIONS);
            const json = await res.json();
            if (json.status === 'success' && json.options) {
                const opts = json.options;
                if(opts.padding) document.getElementById('opt-padding').value = opts.padding;
                if(opts.direction) document.getElementById('opt-direction').value = opts.direction;
                if(opts.bg_color) {
                    document.getElementById('opt-bgcolor-text').value = opts.bg_color;
                    document.getElementById('opt-bgcolor-picker').value = opts.bg_color;
                }
                if(opts.logo_align) document.getElementById('opt-logo-align').value = opts.logo_align;
            }
        } catch (e) { 
            console.error("옵션 로드 실패:", e); 
        }
    }

    function initEventListeners() {
        document.querySelectorAll('button[data-bs-toggle="tab"]').forEach(tab => {
            tab.addEventListener('shown.bs.tab', (e) => loadTabContent(e.target));
        });

        if (btnSearchExec) btnSearchExec.addEventListener('click', performSearch);
        if (btnSearchReset) btnSearchReset.addEventListener('click', resetSearchForm);

        const colorPicker = document.getElementById('opt-bgcolor-picker');
        const colorText = document.getElementById('opt-bgcolor-text');
        if (colorPicker && colorText) {
            colorPicker.addEventListener('input', (e) => { colorText.value = e.target.value.toUpperCase(); });
            colorText.addEventListener('input', (e) => { if(/^#[0-9A-F]{6}$/i.test(e.target.value)) colorPicker.value = e.target.value; });
        }

        if (btnUploadLogo) btnUploadLogo.addEventListener('click', uploadLogo);

        if (btnStart) btnStart.addEventListener('click', startProcess);
        if (btnReset) btnReset.addEventListener('click', resetSelectionStatus);

        if (currentBatchCodes.length > 0) btnClearBatch.style.display = 'block';
        if (btnClearBatch) {
            btnClearBatch.addEventListener('click', () => {
                if(confirm('현재 작업 목록 리스트를 비우시겠습니까?\n(실제 데이터는 삭제되지 않으며, 목록에서만 제거됩니다)')) {
                    currentBatchCodes = [];
                    sessionStorage.setItem('currentBatchCodes', '[]');
                    btnClearBatch.style.display = 'none';
                    refreshActiveTab('current');
                }
            });
        }

        document.body.addEventListener('change', (e) => {
            if (e.target.classList.contains('check-all')) {
                const table = e.target.closest('table');
                table.querySelectorAll('.item-check:not(:disabled)').forEach(cb => cb.checked = e.target.checked);
                updateButtonState();
            }
            if (e.target.classList.contains('item-check')) updateButtonState();
        });
    }

    async function uploadLogo() {
        const file = inputLogoFile.files[0];
        if (!file) return alert('파일을 선택해주세요.');

        const formData = new FormData();
        formData.append('logo_file', file);

        try {
            btnUploadLogo.disabled = true;
            btnUploadLogo.textContent = '업로드 중...';
            
            const res = await fetch(API_LOGO_UPLOAD, {
                method: 'POST',
                headers: { 'X-CSRFToken': csrfToken },
                body: formData
            });
            const json = await res.json();
            if (json.status === 'success') {
                alert('로고가 성공적으로 업로드되었습니다.');
                inputLogoFile.value = '';
            } else {
                alert('업로드 실패: ' + json.message);
            }
        } catch (e) {
            alert('서버 오류 발생');
        } finally {
            btnUploadLogo.disabled = false;
            btnUploadLogo.textContent = '업로드';
        }
    }

    function loadTabContent(tabElement) {
        const targetId = tabElement.dataset.bsTarget.substring(1); 
        const tabType = tabElement.dataset.tabType;
        const scope = tabElement.dataset.scope;
        const page = paginationState[targetId] || 1;
        loadData(targetId, tabType, scope, page);
    }

    function refreshActiveTab(scopeFilter = null) {
        const selector = scopeFilter ? `.nav-link.active[data-scope="${scopeFilter}"]` : '.nav-link.active';
        const activeLink = document.querySelector(selector);
        if (activeLink) loadTabContent(activeLink);
    }

    async function loadData(targetId, tabType, scope, page) {
        const container = document.querySelector(`#${targetId} .table-responsive`);
        if (!container) return;

        if (scope === 'current' && currentBatchCodes.length === 0) {
            container.innerHTML = `<div class="text-center p-5 text-muted">현재 진행 중인 작업이 없습니다.</div>`;
            const badge = document.querySelector(`#${targetId.replace('tab-', 'cnt-')}`);
            if (badge) badge.textContent = '0';
            return;
        }

        container.innerHTML = `<div class="text-center p-5"><div class="spinner-border text-secondary"></div><div class="mt-2">로딩 중...</div></div>`;

        try {
            const params = new URLSearchParams({ page, limit: 20, tab: tabType });

            if (scope === 'history') {
                const multiCodes = searchMultiCodes ? searchMultiCodes.value.trim() : '';
                if (multiCodes) params.append('multi_codes', multiCodes); 
                
                const sName = searchName ? searchName.value.trim() : '';
                if (sName) params.append('product_name', sName);
                
                const sYear = searchYear ? searchYear.value.trim() : '';
                if (sYear) params.append('release_year', sYear);
                
                const sCat = searchCategory ? searchCategory.value.trim() : '';
                if (sCat) params.append('item_category', sCat);
            }

            if (scope === 'current') {
                params.append('batch_codes', currentBatchCodes.join(','));
            }

            const res = await fetch(`${API_LIST}?${params.toString()}`);
            const json = await res.json();

            if (json.status === 'success') {
                renderTable(targetId, json.data);
                renderPagination(targetId, json.pagination);
                const badge = document.getElementById(targetId.replace('tab-', 'cnt-'));
                if (badge) badge.textContent = json.pagination.total_items;
            } else {
                container.innerHTML = `<div class="text-danger p-5">${json.message}</div>`;
            }
        } catch (e) {
            console.error("Data Load Error:", e);
            container.innerHTML = `<div class="text-danger p-5">데이터 로드 중 오류가 발생했습니다.</div>`;
        }
    }

    function renderTable(targetId, items) {
        const container = document.querySelector(`#${targetId} .table-responsive`);
        const template = document.getElementById('table-template');
        
        if (!items || items.length === 0) {
            container.innerHTML = `<div class="text-center p-5 text-muted">데이터가 없습니다.</div>`;
            return;
        }

        const tableClone = template.content.cloneNode(true);
        const tbody = tableClone.querySelector('tbody');

        items.forEach(item => {
            const tr = document.createElement('tr');
            let statusBadge = `<span class="badge bg-secondary status-badge">대기</span>`;
            let disabled = '';

            if (item.status === 'PROCESSING') {
                statusBadge = `<span class="badge bg-primary status-badge">진행중</span>`;
                disabled = 'disabled';
            } else if (item.status === 'COMPLETED') {
                statusBadge = `<span class="badge bg-success status-badge">완료</span>`;
            } else if (item.status === 'FAILED') {
                statusBadge = `<span class="badge bg-danger status-badge" title="${item.message}">실패</span>`;
            }

            const thumbHtml = item.thumbnail ? `<img src="${item.thumbnail}" class="img-preview" onclick="showImageModal('${item.thumbnail}')">` : `<div class="img-placeholder"><i class="bi bi-image"></i></div>`;
            const detailHtml = item.detail ? `<img src="${item.detail}" class="img-preview" onclick="showImageModal('${item.detail}')">` : `<span class="text-muted">-</span>`;
            const folderBtn = `<button class="btn btn-sm btn-outline-info" onclick="showFolderModal('${item.style_code}')"><i class="bi bi-folder"></i></button>`;
            
            const downloadBtn = item.status === 'COMPLETED' ? `<button class="btn btn-sm btn-outline-dark" onclick="downloadImages('${item.style_code}')"><i class="bi bi-download"></i></button>` : `<button class="btn btn-sm btn-outline-secondary" disabled><i class="bi bi-download"></i></button>`;
            const deleteBtn = `<button class="btn btn-sm btn-outline-danger" onclick="deleteImages('${item.style_code}')"><i class="bi bi-trash"></i></button>`;

            tr.innerHTML = `
                <td><input type="checkbox" class="form-check-input item-check" value="${item.style_code}" ${disabled}></td>
                <td class="fw-bold">${item.style_code}</td>
                <td class="text-start text-truncate" style="max-width: 150px;" title="${item.product_name}">${item.product_name}</td>
                <td>${item.total_colors}</td>
                <td>${thumbHtml}</td>
                <td>${detailHtml}</td>
                <td>${folderBtn}</td>
                <td>${statusBadge}</td>
                <td><div class="btn-group">${downloadBtn}${deleteBtn}</div></td>
            `;
            tbody.appendChild(tr);
        });

        container.innerHTML = '';
        container.appendChild(tableClone);
        updateButtonState();
    }

    function renderPagination(targetId, pagination) {
        const pageId = targetId.replace('tab-', 'page-'); 
        const container = document.getElementById(pageId);
        if (!container) return;
        container.innerHTML = '';

        if (pagination.total_pages <= 1) return;

        const ul = document.createElement('ul');
        ul.className = 'pagination pagination-sm mb-0';

        const createLink = (pageNum, text, active=false, disabled=false) => {
            const li = document.createElement('li');
            li.className = `page-item ${active ? 'active' : ''} ${disabled ? 'disabled' : ''}`;
            li.innerHTML = `<a class="page-link" href="#">${text}</a>`;
            if(!disabled && !active) {
                li.onclick = (e) => {
                    e.preventDefault();
                    paginationState[targetId] = pageNum;
                    loadTabContent(document.querySelector(`button[data-bs-target="#${targetId}"]`));
                };
            }
            return li;
        };

        ul.appendChild(createLink(pagination.current_page - 1, '&laquo;', false, !pagination.has_prev));
        
        let start = Math.max(1, pagination.current_page - 2);
        let end = Math.min(pagination.total_pages, start + 4);
        if(end - start < 4) start = Math.max(1, end - 4);

        for(let i=start; i<=end; i++) ul.appendChild(createLink(i, i, i===pagination.current_page));
        
        ul.appendChild(createLink(pagination.current_page + 1, '&raquo;', false, !pagination.has_next));
        container.appendChild(ul);
    }

    function performSearch() {
        const histAllTab = document.querySelector('button[data-bs-target="#tab-hist-all"]');
        if (histAllTab) {
            new bootstrap.Tab(histAllTab).show();
            paginationState['tab-hist-all'] = 1;
            loadTabContent(histAllTab);
        }
    }

    function resetSearchForm() {
        if(searchMultiCodes) searchMultiCodes.value = '';
        if(searchName) searchName.value = '';
        if(searchYear) searchYear.value = '';
        if(searchCategory) searchCategory.value = '';
        performSearch();
    }

    function updateButtonState() {
        const checked = document.querySelectorAll('.item-check:checked').length;
        if (btnStart) {
            btnStart.disabled = checked === 0;
            btnStart.innerHTML = checked > 0 ? `<i class="bi bi-play-fill me-1"></i> ${checked}건 처리 시작` : `<i class="bi bi-play-fill me-1"></i> 처리 시작`;
        }
        if (btnReset) {
            btnReset.disabled = checked === 0;
        }
    }

    async function startProcess() {
        const checked = document.querySelectorAll('.item-check:checked');
        const styleCodes = Array.from(checked).map(cb => cb.value);
        if (styleCodes.length === 0) return;

        const options = {
            padding: document.getElementById('opt-padding').value,
            direction: document.getElementById('opt-direction').value,
            bg_color: document.getElementById('opt-bgcolor-text').value,
            logo_align: document.getElementById('opt-logo-align').value
        };

        if (!confirm(`${styleCodes.length}건의 이미지 처리를 시작하시겠습니까?`)) return;

        btnStart.disabled = true;
        try {
            const res = await fetch(API_PROCESS, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                body: JSON.stringify({ style_codes: styleCodes, options })
            });
            const json = await res.json();
            if (json.status === 'success') {
                const newSet = new Set([...currentBatchCodes, ...styleCodes]);
                currentBatchCodes = Array.from(newSet);
                sessionStorage.setItem('currentBatchCodes', JSON.stringify(currentBatchCodes));
                
                if(btnClearBatch) btnClearBatch.style.display = 'block';
                startProgressPolling(json.task_id);
                
                const processingTab = document.querySelector('button[data-bs-target="#tab-current-processing"]');
                new bootstrap.Tab(processingTab).show();
                loadTabContent(processingTab);
            } else {
                alert(json.message);
                btnStart.disabled = false;
            }
        } catch (e) {
            alert('작업 요청 중 오류가 발생했습니다.');
            btnStart.disabled = false;
        }
    }

    function startProgressPolling(taskId) {
        if (pollingInterval) clearInterval(pollingInterval);
        progressContainer.style.display = 'block';
        isProcessing = true;

        pollingInterval = setInterval(async () => {
            try {
                const res = await fetch(`${API_TASK_STATUS}${taskId}`);
                const task = await res.json();

                if (task.status === 'processing') {
                    const pct = task.percent || 0;
                    progressBar.style.width = `${pct}%`;
                    progressText.textContent = `${pct}% (${task.current}/${task.total})`;
                } else if (task.status === 'completed' || task.status === 'error') {
                    clearInterval(pollingInterval);
                    isProcessing = false;
                    progressBar.style.width = '100%';
                    progressBar.classList.remove('progress-bar-animated');
                    
                    if (task.status === 'completed') {
                        progressBar.classList.add('bg-success');
                        progressText.textContent = '완료!';
                    } else {
                        progressBar.classList.add('bg-danger');
                        progressText.textContent = '오류 발생';
                        alert('작업 중 오류가 발생했습니다: ' + task.message);
                    }
                    
                    setTimeout(() => {
                        progressContainer.style.display = 'none';
                        progressBar.style.width = '0%';
                        progressBar.classList.remove('bg-success', 'bg-danger');
                        progressBar.classList.add('progress-bar-animated');
                        refreshActiveTab();
                    }, 2000);
                }
            } catch (e) { console.error("Polling Error:", e); }
        }, 1000);
    }

    async function resetSelectionStatus() {
        const checked = document.querySelectorAll('.item-check:checked');
        const styleCodes = Array.from(checked).map(cb => cb.value);
        if (styleCodes.length === 0) return;
        if (!confirm('선택된 항목을 대기 상태로 초기화하시겠습니까?')) return;

        try {
            const res = await fetch(bodyData.apiReset, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                body: JSON.stringify({ style_codes: styleCodes })
            });
            const json = await res.json();
            alert(json.message);
            refreshActiveTab();
        } catch (e) { alert('오류 발생'); }
    }
    
    window.showImageModal = (src) => {
        document.getElementById('preview-image-target').src = src;
        imgModal.show();
    };

    window.showFolderModal = async (styleCode) => {
        const container = document.querySelector('#folderViewModal .modal-body .list-group');
        container.innerHTML = '<div class="text-center"><div class="spinner-border"></div></div>';
        folderModal.show();

        try {
            const res = await fetch(`${API_FOLDER}${styleCode}`);
            const json = await res.json();
            if (json.status === 'success') {
                if (json.images.length === 0) container.innerHTML = '<div class="text-center p-3 text-muted">폴더가 비어있거나 존재하지 않습니다.</div>';
                else {
                    let html = '';
                    json.images.forEach(img => {
                        let iconClass = 'bi-file-earmark';
                        if (img.type === 'dir') iconClass = 'bi-folder-fill text-warning';
                        else if (img.file_type === 'processed') iconClass = 'bi-magic text-primary';
                        else if (img.file_type === 'original') iconClass = 'bi-image text-secondary';

                        html += `
                            <a href="${img.url}" target="_blank" class="list-group-item list-group-item-action d-flex align-items-center folder-item">
                                <i class="bi ${iconClass} me-3 fs-5"></i>
                                <div>
                                    <div class="fw-bold">${img.name}</div>
                                </div>
                            </a>`;
                    });
                    container.innerHTML = html;
                }
            } else {
                container.innerHTML = `<div class="alert alert-danger">${json.message}</div>`;
            }
        } catch (e) { container.innerHTML = `<div class="alert alert-danger">오류 발생</div>`; }
    };

    window.downloadImages = (styleCode) => { window.location.href = `${API_DOWNLOAD}${styleCode}`; };

    window.deleteImages = async (styleCode) => {
        if (!confirm(`[${styleCode}]의 이미지 데이터와 파일을 모두 삭제하시겠습니까?`)) return;
        try {
            const res = await fetch(API_DELETE, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                body: JSON.stringify({ style_codes: [styleCode] })
            });
            const json = await res.json();
            alert(json.message);
            refreshActiveTab();
        } catch (e) { alert('삭제 중 오류가 발생했습니다.'); }
    };
});