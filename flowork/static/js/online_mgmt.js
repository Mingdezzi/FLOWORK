document.addEventListener('DOMContentLoaded', () => {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    
    // UI 요소 참조
    const btnStart = document.getElementById('btn-start-process');
    const btnReset = document.getElementById('btn-reset-selection');
    const btnClearBatch = document.getElementById('btn-clear-current-batch');
    const btnSearch = document.getElementById('btn-search');
    const searchInput = document.getElementById('search-input');
    
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    const progressContainer = document.getElementById('progress-container');

    // 모달 요소 참조
    const imgModalEl = document.getElementById('imagePreviewModal');
    const imgModal = new bootstrap.Modal(imgModalEl);
    const folderModalEl = document.getElementById('folderViewModal');
    const folderModal = new bootstrap.Modal(folderModalEl);
    
    // API URL
    const bodyData = document.body.dataset;
    const API_LIST = bodyData.apiList;
    const API_PROCESS = bodyData.apiProcess;
    const API_OPTIONS = bodyData.apiOptions;
    const API_TASK_STATUS = bodyData.apiTaskStatusPrefix;
    const API_FOLDER = bodyData.apiFolderPrefix;
    const API_DOWNLOAD = "/api/product/download/";
    const API_DELETE = "/api/product/delete_image_data";

    // 상태 변수
    let isProcessing = false;
    let pollingInterval = null;
    
    // 탭별 페이지네이션 상태
    const paginationState = {
        // 상단 탭 (Current Batch)
        'tab-current-ready': 1,
        'tab-current-processing': 1,
        'tab-current-completed': 1,
        'tab-current-failed': 1,
        // 하단 탭 (History)
        'tab-hist-all': 1,
        'tab-hist-completed': 1,
        'tab-hist-failed': 1
    };

    // 현재 작업 중인 품번 목록 (세션 스토리지 사용)
    let currentBatchCodes = JSON.parse(sessionStorage.getItem('currentBatchCodes') || '[]');

    // --- 1. 초기화 및 옵션 로드 ---
    loadUserOptions();
    initEventListeners();
    
    // 초기 로드: 활성화된 탭의 데이터 로드
    const activeTabs = document.querySelectorAll('.nav-link.active');
    activeTabs.forEach(tab => loadTabContent(tab));

    // --- 2. 사용자 옵션 로드 함수 ---
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

    // --- 3. 이벤트 리스너 설정 ---
    function initEventListeners() {
        // 탭 전환 이벤트
        document.querySelectorAll('button[data-bs-toggle="tab"]').forEach(tab => {
            tab.addEventListener('shown.bs.tab', (e) => {
                loadTabContent(e.target);
            });
        });

        // 검색 이벤트
        btnSearch.addEventListener('click', () => performSearch());
        searchInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') performSearch(); });

        // 옵션 UI 동기화
        const colorPicker = document.getElementById('opt-bgcolor-picker');
        const colorText = document.getElementById('opt-bgcolor-text');
        colorPicker.addEventListener('input', (e) => { colorText.value = e.target.value.toUpperCase(); });
        colorText.addEventListener('input', (e) => { if(/^#[0-9A-F]{6}$/i.test(e.target.value)) colorPicker.value = e.target.value; });

        // 작업 시작 버튼
        btnStart.addEventListener('click', startProcess);
        
        // 선택 초기화 버튼
        btnReset.addEventListener('click', resetSelectionStatus);

        // 현재 작업 목록 비우기
        if (currentBatchCodes.length > 0) btnClearBatch.style.display = 'block';
        btnClearBatch.addEventListener('click', () => {
            if(confirm('현재 작업 목록 리스트를 비우시겠습니까?\n(실제 데이터는 삭제되지 않습니다)')) {
                currentBatchCodes = [];
                sessionStorage.setItem('currentBatchCodes', '[]');
                btnClearBatch.style.display = 'none';
                refreshActiveTab('current');
            }
        });

        // 전체 선택 체크박스
        document.body.addEventListener('change', (e) => {
            if (e.target.classList.contains('check-all')) {
                const table = e.target.closest('table');
                const checkboxes = table.querySelectorAll('.item-check:not(:disabled)');
                checkboxes.forEach(cb => cb.checked = e.target.checked);
                updateButtonState();
            }
            if (e.target.classList.contains('item-check')) {
                updateButtonState();
            }
        });
    }

    // --- 4. 데이터 로드 및 렌더링 ---
    function loadTabContent(tabElement) {
        const targetId = tabElement.dataset.bsTarget.substring(1); // # 제거
        const tabType = tabElement.dataset.tabType; // ready, processing, ...
        const scope = tabElement.dataset.scope; // current, history
        const page = paginationState[targetId] || 1;

        loadData(targetId, tabType, scope, page);
    }

    function refreshActiveTab(scopeFilter = null) {
        const activeLink = document.querySelector(`.nav-link.active[data-scope="${scopeFilter}"]`) || document.querySelector('.nav-link.active');
        if (activeLink) loadTabContent(activeLink);
    }

    async function loadData(targetId, tabType, scope, page) {
        const container = document.querySelector(`#${targetId} .table-responsive`);
        if (!container) return;

        // 현재 작업 목록이 비어있는데 상단 탭을 조회하는 경우
        if (scope === 'current' && currentBatchCodes.length === 0) {
            container.innerHTML = `<div class="text-center p-5 text-muted">현재 진행 중인 작업이 없습니다.<br>하단 검색에서 품번을 선택하여 작업을 시작하세요.</div>`;
            document.querySelector(`#${targetId.replace('tab-', 'cnt-')}`).textContent = '0';
            return;
        }

        container.innerHTML = `<div class="text-center p-5"><div class="spinner-border text-secondary" role="status"></div><div class="mt-2 text-muted">데이터 로딩 중...</div></div>`;

        try {
            const params = new URLSearchParams({
                page: page,
                limit: 20,
                tab: tabType
            });

            // 검색어 (하단 탭만 적용)
            if (scope === 'history') {
                const query = searchInput.value.trim();
                if (query) params.append('query', query);
            }

            // 배치 필터 (상단 탭만 적용)
            if (scope === 'current') {
                params.append('batch_codes', currentBatchCodes.join(','));
            }

            const res = await fetch(`${API_LIST}?${params.toString()}`);
            const json = await res.json();

            if (json.status === 'success') {
                renderTable(targetId, json.data, scope);
                renderPagination(targetId, json.pagination);
                
                // 카운트 배지 업데이트
                const badgeId = targetId.replace('tab-', 'cnt-');
                const badge = document.getElementById(badgeId);
                if (badge) badge.textContent = json.pagination.total_items;
            } else {
                container.innerHTML = `<div class="text-center p-5 text-danger">${json.message}</div>`;
            }
        } catch (e) {
            console.error(e);
            container.innerHTML = `<div class="text-center p-5 text-danger">데이터 로드 중 오류가 발생했습니다.</div>`;
        }
    }

    function renderTable(targetId, items, scope) {
        const container = document.querySelector(`#${targetId} .table-responsive`);
        const template = document.getElementById('table-template');
        
        if (!items || items.length === 0) {
            container.innerHTML = `<div class="text-center p-5 text-muted">데이터가 없습니다.</div>`;
            return;
        }

        // 템플릿 복제
        const tableClone = template.content.cloneNode(true);
        const tbody = tableClone.querySelector('tbody');

        items.forEach(item => {
            const tr = document.createElement('tr');
            
            let statusBadge = '';
            let disabled = '';
            
            if (item.status === 'PROCESSING') {
                statusBadge = `<span class="badge bg-primary status-badge">진행중</span>`;
                disabled = 'disabled';
            } else if (item.status === 'COMPLETED') {
                statusBadge = `<span class="badge bg-success status-badge">완료</span>`;
            } else if (item.status === 'FAILED') {
                statusBadge = `<span class="badge bg-danger status-badge" title="${item.message}">실패</span>`;
            } else {
                statusBadge = `<span class="badge bg-secondary status-badge">대기</span>`;
            }

            // 이미지 미리보기 핸들러
            const thumbHtml = item.thumbnail 
                ? `<img src="${item.thumbnail}" class="img-preview" onclick="showImageModal('${item.thumbnail}')">`
                : `<div class="img-placeholder"><i class="bi bi-image"></i></div>`;
                
            const detailHtml = item.detail
                ? `<img src="${item.detail}" class="img-preview" onclick="showImageModal('${item.detail}')">`
                : `<span class="text-muted">-</span>`;

            const folderBtn = `<button class="btn btn-sm btn-outline-info" onclick="showFolderModal('${item.style_code}')"><i class="bi bi-folder"></i></button>`;
            
            const downloadBtn = item.status === 'COMPLETED'
                ? `<button class="btn btn-sm btn-outline-dark" onclick="downloadImages('${item.style_code}')"><i class="bi bi-download"></i></button>`
                : `<button class="btn btn-sm btn-outline-secondary" disabled><i class="bi bi-download"></i></button>`;
            
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
        // (기존 코드와 동일한 페이지네이션 로직)
        // targetId에 맞는 pagination container 찾기 (예: #table-hist-all -> #page-hist-all)
        // 구조상 table-responsive 뒤에 div id="page-..." 가 있음.
        // 그러나 HTML 구조상 id 매핑이 복잡하므로, parent의 querySelector로 찾음.
        
        // Tab Pane ID를 기반으로 Pagination ID 유추
        // 예: tab-hist-all -> page-hist-all (HTML 구조에 맞춤)
        const pageId = targetId.replace('tab-', 'page-'); 
        const container = document.getElementById(pageId);
        
        if (!container) return;
        container.innerHTML = '';

        if (pagination.total_pages <= 1) return;

        const ul = document.createElement('ul');
        ul.className = 'pagination pagination-sm mb-0';

        const createPageLink = (pageNum, text, active = false, disabled = false) => {
            const li = document.createElement('li');
            li.className = `page-item ${active ? 'active' : ''} ${disabled ? 'disabled' : ''}`;
            li.innerHTML = `<a class="page-link" href="#">${text}</a>`;
            if (!disabled && !active) {
                li.onclick = (e) => {
                    e.preventDefault();
                    paginationState[targetId] = pageNum;
                    const tabEl = document.querySelector(`button[data-bs-target="#${targetId}"]`);
                    loadTabContent(tabEl);
                };
            }
            return li;
        };

        ul.appendChild(createPageLink(pagination.current_page - 1, '&laquo;', false, !pagination.has_prev));

        let start = Math.max(1, pagination.current_page - 2);
        let end = Math.min(pagination.total_pages, start + 4);
        if (end - start < 4) start = Math.max(1, end - 4);

        for (let i = start; i <= end; i++) {
            ul.appendChild(createPageLink(i, i, i === pagination.current_page));
        }

        ul.appendChild(createPageLink(pagination.current_page + 1, '&raquo;', false, !pagination.has_next));
        container.appendChild(ul);
    }

    // --- 5. 액션 핸들러 ---

    function updateButtonState() {
        const checked = document.querySelectorAll('.item-check:checked').length;
        btnStart.disabled = checked === 0;
        btnStart.innerHTML = checked > 0 ? `<i class="bi bi-play-fill me-1"></i> ${checked}건 처리 시작` : `<i class="bi bi-play-fill me-1"></i> 처리 시작`;
        
        btnReset.disabled = checked === 0;
    }

    function performSearch() {
        // 검색은 항상 '전체 이력' 탭에서 수행된다고 가정 (또는 현재 활성 탭)
        // 여기서는 '전체 이력 -> 전체 목록' 탭을 활성화하고 검색
        const histAllTab = document.querySelector('button[data-bs-target="#tab-hist-all"]');
        if (histAllTab) {
            new bootstrap.Tab(histAllTab).show();
            paginationState['tab-hist-all'] = 1;
            loadTabContent(histAllTab);
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
        btnStart.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 요청 중...';

        try {
            const res = await fetch(API_PROCESS, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                body: JSON.stringify({ style_codes: styleCodes, options: options })
            });
            const json = await res.json();

            if (json.status === 'success') {
                // 현재 작업 목록에 추가 (중복 제거)
                const newSet = new Set([...currentBatchCodes, ...styleCodes]);
                currentBatchCodes = Array.from(newSet);
                sessionStorage.setItem('currentBatchCodes', JSON.stringify(currentBatchCodes));
                
                btnClearBatch.style.display = 'block';
                
                // 프로그레스 바 시작
                startProgressPolling(json.task_id);
                
                // 상단 탭(진행중)으로 이동
                const processingTab = document.querySelector('button[data-bs-target="#tab-current-processing"]');
                new bootstrap.Tab(processingTab).show();
                loadTabContent(processingTab);
                
            } else {
                alert(json.message);
                btnStart.disabled = false;
            }
        } catch (e) {
            console.error(e);
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
                        alert(task.result.message);
                    } else {
                        progressBar.classList.add('bg-danger');
                        progressText.textContent = '오류 발생';
                        alert('작업 중 오류가 발생했습니다: ' + task.message);
                    }
                    
                    // 잠시 후 프로그레스바 숨김 및 목록 갱신
                    setTimeout(() => {
                        progressContainer.style.display = 'none';
                        progressBar.style.width = '0%';
                        progressBar.classList.remove('bg-success', 'bg-danger');
                        progressBar.classList.add('progress-bar-animated');
                        refreshActiveTab();
                    }, 2000);
                }
            } catch (e) {
                console.error("Polling Error:", e);
            }
        }, 1000); // 1초마다 갱신
    }

    async function resetSelectionStatus() {
        const checked = document.querySelectorAll('.item-check:checked');
        const styleCodes = Array.from(checked).map(cb => cb.value);
        
        if (styleCodes.length === 0) return;
        if (!confirm(`${styleCodes.length}건의 상태를 '대기'로 초기화하시겠습니까?`)) return;

        try {
            const res = await fetch(bodyData.apiReset, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                body: JSON.stringify({ style_codes: styleCodes })
            });
            const json = await res.json();
            alert(json.message);
            refreshActiveTab();
        } catch (e) {
            alert('오류가 발생했습니다.');
        }
    }

    // 전역 함수로 등록 (HTML onclick에서 호출)
    window.showImageModal = function(src) {
        const img = document.getElementById('preview-image-target');
        img.src = src;
        imgModal.show();
    };

    window.showFolderModal = async function(styleCode) {
        const container = document.querySelector('#folderViewModal .modal-body');
        container.innerHTML = '<div class="text-center"><div class="spinner-border"></div></div>';
        folderModal.show();

        try {
            const res = await fetch(`${API_FOLDER}${styleCode}`);
            const json = await res.json();
            
            if (json.status === 'success') {
                if (json.images.length === 0) {
                    container.innerHTML = '<div class="text-center text-muted p-3">저장된 이미지가 없습니다.</div>';
                } else {
                    let html = `<div class="list-group list-group-flush">`;
                    json.images.forEach(img => {
                        let icon = img.type === 'processed' ? '<i class="bi bi-magic text-primary me-2"></i>' : '<i class="bi bi-image me-2"></i>';
                        html += `<a href="${img.path}" target="_blank" class="list-group-item list-group-item-action d-flex align-items-center">
                            ${icon} ${img.name}
                        </a>`;
                    });
                    html += '</div>';
                    container.innerHTML = html;
                }
            } else {
                container.innerHTML = `<div class="alert alert-danger">${json.message}</div>`;
            }
        } catch (e) {
            container.innerHTML = `<div class="alert alert-danger">오류 발생</div>`;
        }
    };

    window.downloadImages = function(styleCode) {
        window.location.href = `${API_DOWNLOAD}${styleCode}`;
    };

    window.deleteImages = async function(styleCode) {
        if (!confirm(`[${styleCode}]의 모든 이미지 데이터와 파일을 삭제하시겠습니까?`)) return;
        try {
            const res = await fetch(API_DELETE, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                body: JSON.stringify({ style_codes: [styleCode] })
            });
            const json = await res.json();
            alert(json.message);
            refreshActiveTab();
        } catch (e) {
            alert('삭제 중 오류가 발생했습니다.');
        }
    };
});