let currentOnlineManager = null;

class OnlineManager {
    constructor() {
        const ds = document.body.dataset;
        this.urls = {
            list: ds.apiList,
            process: ds.apiProcess,
            options: ds.apiOptions,
            taskStatus: ds.apiTaskStatusPrefix,
            folder: ds.apiFolderPrefix,
            logoUpload: ds.apiLogoUpload,
            download: '/api/product/download/',
            delete: '/api/product/delete_image_data'
        };

        this.pagination = {};
        this.currentBatch = JSON.parse(sessionStorage.getItem('currentBatchCodes') || '[]');
        this.pollingInterval = null;
        this.isProcessing = false;

        this.dom = this.cacheDom();
        
        this.boundHandleBodyChange = this.handleBodyChange.bind(this);
        
        this.init();
    }

    cacheDom() {
        return {
            btnStart: document.getElementById('btn-start-process'),
            btnReset: document.getElementById('btn-reset-selection'),
            btnClear: document.getElementById('btn-clear-current-batch'),
            btnSearch: document.getElementById('btn-search-exec'),
            btnSearchReset: document.getElementById('btn-search-reset'),
            searchMulti: document.getElementById('search-multi-codes'),
            searchName: document.getElementById('search-name'),
            searchYear: document.getElementById('search-year'),
            searchCat: document.getElementById('search-category'),
            btnLogo: document.getElementById('btn-upload-logo'),
            inputLogo: document.getElementById('logo-file'),
            progBar: document.getElementById('progress-bar'),
            progText: document.getElementById('progress-text'),
            progContainer: document.getElementById('progress-container'),
            imgModal: new bootstrap.Modal(document.getElementById('imagePreviewModal')),
            folderModal: new bootstrap.Modal(document.getElementById('folderViewModal')),
            tabs: document.querySelectorAll('button[data-bs-toggle="tab"]')
        };
    }

    init() {
        this.loadUserOptions();
        
        this.dom.tabs.forEach(tab => {
            tab.addEventListener('shown.bs.tab', (e) => this.loadTabContent(e.target));
        });

        this.dom.btnSearch.onclick = () => this.search();
        this.dom.btnSearchReset.onclick = () => this.resetSearch();
        this.dom.btnLogo.onclick = () => this.uploadLogo();
        this.dom.btnStart.onclick = () => this.startProcess();
        this.dom.btnReset.onclick = () => this.resetSelection();
        
        if(this.dom.btnClear) {
            if(this.currentBatch.length > 0) this.dom.btnClear.style.display = 'block';
            this.dom.btnClear.onclick = () => {
                if(confirm('현재 작업 목록을 비우시겠습니까?')) {
                    this.currentBatch = [];
                    sessionStorage.setItem('currentBatchCodes', '[]');
                    this.dom.btnClear.style.display = 'none';
                    this.refreshActiveTab('current');
                }
            };
        }

        document.body.addEventListener('change', this.boundHandleBodyChange);

        document.querySelectorAll('.nav-link.active').forEach(tab => this.loadTabContent(tab));
        
        window.showImageModal = (src) => { document.getElementById('preview-image-target').src = src; this.dom.imgModal.show(); };
        window.downloadImages = (code) => { window.location.href = `${this.urls.download}${code}`; };
        window.deleteImages = (code) => this.deleteImages(code);
        window.showFolderModal = (code) => this.showFolder(code);
    }

    destroy() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
        }
        document.body.removeEventListener('change', this.boundHandleBodyChange);
        
        window.showImageModal = null;
        window.downloadImages = null;
        window.deleteImages = null;
        window.showFolderModal = null;
    }

    handleBodyChange(e) {
        if(e.target.classList.contains('check-all')) {
            const table = e.target.closest('table');
            table.querySelectorAll('.item-check:not(:disabled)').forEach(cb => cb.checked = e.target.checked);
            this.updateBtnState();
        }
        if(e.target.classList.contains('item-check')) this.updateBtnState();
    }

    async loadUserOptions() {
        try {
            const data = await Flowork.get(this.urls.options);
            if (data.status === 'success' && data.options) {
                const o = data.options;
                if(o.padding) document.getElementById('opt-padding').value = o.padding;
                if(o.direction) document.getElementById('opt-direction').value = o.direction;
                if(o.logo_align) document.getElementById('opt-logo-align').value = o.logo_align;
                if(o.bg_color) {
                    document.getElementById('opt-bgcolor-text').value = o.bg_color;
                    document.getElementById('opt-bgcolor-picker').value = o.bg_color;
                }
            }
        } catch (e) {}
    }

    async uploadLogo() {
        const file = this.dom.inputLogo.files[0];
        if(!file) return alert('파일 선택 필수');
        
        const formData = new FormData();
        formData.append('logo_file', file);
        
        try {
            this.dom.btnLogo.disabled = true;
            await fetch(this.urls.logoUpload, {
                method: 'POST',
                headers: { 'X-CSRFToken': Flowork.getCsrfToken() },
                body: formData
            });
            alert('로고 업로드 성공');
            this.dom.inputLogo.value = '';
        } catch (e) { alert('업로드 실패'); }
        finally { this.dom.btnLogo.disabled = false; }
    }

    loadTabContent(tab) {
        const targetId = tab.dataset.bsTarget.substring(1);
        const type = tab.dataset.tabType;
        const scope = tab.dataset.scope;
        const page = this.pagination[targetId] || 1;
        this.loadData(targetId, type, scope, page);
    }

    refreshActiveTab(scope = null) {
        const sel = scope ? `.nav-link.active[data-scope="${scope}"]` : '.nav-link.active';
        const active = document.querySelector(sel);
        if(active) this.loadTabContent(active);
    }

    async loadData(targetId, type, scope, page) {
        const container = document.querySelector(`#${targetId} .table-responsive`);
        if(!container) return;

        if (scope === 'current' && this.currentBatch.length === 0) {
            container.innerHTML = '<div class="text-center p-5 text-muted">작업 목록 없음</div>';
            const badge = document.querySelector(`#${targetId.replace('tab-', 'cnt-')}`);
            if(badge) badge.textContent = '0';
            return;
        }

        container.innerHTML = '<div class="text-center p-5">로딩 중...</div>';

        const params = new URLSearchParams({ page, limit: 20, tab: type });
        if (scope === 'history') {
            if(this.dom.searchMulti.value) params.append('multi_codes', this.dom.searchMulti.value);
            if(this.dom.searchName.value) params.append('product_name', this.dom.searchName.value);
            if(this.dom.searchYear.value) params.append('release_year', this.dom.searchYear.value);
            if(this.dom.searchCat.value) params.append('item_category', this.dom.searchCat.value);
        } else {
            params.append('batch_codes', this.currentBatch.join(','));
        }

        try {
            const data = await Flowork.get(`${this.urls.list}?${params.toString()}`);
            if(data.status === 'success') {
                this.renderTable(targetId, data.data);
                this.renderPagination(targetId, data.pagination);
                const badge = document.getElementById(targetId.replace('tab-', 'cnt-'));
                if(badge) badge.textContent = data.pagination.total_items;
            } else {
                container.innerHTML = `<div class="text-danger p-5">${data.message}</div>`;
            }
        } catch (e) { container.innerHTML = '<div class="text-danger p-5">오류 발생</div>'; }
    }

    renderTable(targetId, items) {
        const container = document.querySelector(`#${targetId} .table-responsive`);
        const template = document.getElementById('table-template');
        
        if(!items || items.length === 0) {
            container.innerHTML = '<div class="text-center p-5 text-muted">데이터 없음</div>';
            return;
        }

        const clone = template.content.cloneNode(true);
        const tbody = clone.querySelector('tbody');

        items.forEach(i => {
            const tr = document.createElement('tr');
            let statusHtml = `<span class="badge bg-secondary">대기</span>`;
            let disabled = '';
            if (i.status === 'PROCESSING') { statusHtml = `<span class="badge bg-primary">진행</span>`; disabled='disabled'; }
            else if (i.status === 'COMPLETED') statusHtml = `<span class="badge bg-success">완료</span>`;
            else if (i.status === 'FAILED') statusHtml = `<span class="badge bg-danger">실패</span>`;

            const thumb = i.thumbnail ? `<img src="${i.thumbnail}" class="img-preview" onclick="showImageModal('${i.thumbnail}')">` : `<div class="img-placeholder">-</div>`;
            const detail = i.detail ? `<img src="${i.detail}" class="img-preview" onclick="showImageModal('${i.detail}')">` : `-`;
            const dlBtn = i.status === 'COMPLETED' ? `<button class="btn btn-sm btn-outline-dark" onclick="downloadImages('${i.style_code}')"><i class="bi bi-download"></i></button>` : '';
            
            tr.innerHTML = `
                <td><input type="checkbox" class="item-check form-check-input" value="${i.style_code}" ${disabled}></td>
                <td class="fw-bold">${i.style_code}</td>
                <td class="text-truncate" style="max-width:150px;">${i.product_name}</td>
                <td>${i.total_colors}</td>
                <td>${thumb}</td>
                <td>${detail}</td>
                <td><button class="btn btn-sm btn-outline-info" onclick="showFolderModal('${i.style_code}')"><i class="bi bi-folder"></i></button></td>
                <td>${statusHtml}</td>
                <td><div class="btn-group">${dlBtn}<button class="btn btn-sm btn-outline-danger" onclick="deleteImages('${i.style_code}')"><i class="bi bi-trash"></i></button></div></td>
            `;
            tbody.appendChild(tr);
        });
        container.innerHTML = '';
        container.appendChild(clone);
        this.updateBtnState();
    }

    renderPagination(targetId, pg) {
        const container = document.getElementById(targetId.replace('tab-', 'page-'));
        if(!container || pg.total_pages <= 1) { if(container) container.innerHTML=''; return; }
        
        let html = '<ul class="pagination pagination-sm mb-0">';
        const addPage = (p, txt, cls='') => {
            html += `<li class="page-item ${cls}"><a class="page-link" href="#" data-page="${p}">${txt}</a></li>`;
        };
        
        addPage(pg.current_page - 1, '«', pg.has_prev ? '' : 'disabled');
        let start = Math.max(1, pg.current_page - 2);
        let end = Math.min(pg.total_pages, start + 4);
        for(let i=start; i<=end; i++) addPage(i, i, i===pg.current_page ? 'active' : '');
        addPage(pg.current_page + 1, '»', pg.has_next ? '' : 'disabled');
        
        container.innerHTML = html + '</ul>';
        container.querySelectorAll('a').forEach(a => {
            a.onclick = (e) => {
                e.preventDefault();
                if(!a.parentElement.classList.contains('disabled')) {
                    this.pagination[targetId] = parseInt(a.dataset.page);
                    this.loadTabContent(document.querySelector(`button[data-bs-target="#${targetId}"]`));
                }
            }
        });
    }

    updateBtnState() {
        const cnt = document.querySelectorAll('.item-check:checked').length;
        this.dom.btnStart.disabled = cnt === 0;
        this.dom.btnStart.innerHTML = cnt > 0 ? `<i class="bi bi-play-fill"></i> ${cnt}건 시작` : `<i class="bi bi-play-fill"></i> 시작`;
        this.dom.btnReset.disabled = cnt === 0;
    }

    async startProcess() {
        const codes = Array.from(document.querySelectorAll('.item-check:checked')).map(c => c.value);
        if(codes.length === 0) return;
        
        const options = {
            padding: document.getElementById('opt-padding').value,
            direction: document.getElementById('opt-direction').value,
            bg_color: document.getElementById('opt-bgcolor-text').value,
            logo_align: document.getElementById('opt-logo-align').value
        };

        if(!confirm(`${codes.length}건 처리 시작?`)) return;
        
        this.dom.btnStart.disabled = true;
        try {
            const res = await Flowork.post(this.urls.process, { style_codes: codes, options });
            if(res.status === 'success') {
                const newBatch = new Set([...this.currentBatch, ...codes]);
                this.currentBatch = Array.from(newBatch);
                sessionStorage.setItem('currentBatchCodes', JSON.stringify(this.currentBatch));
                if(this.dom.btnClear) this.dom.btnClear.style.display = 'block';
                
                this.pollTask(res.task_id);
                
                const tab = document.querySelector('button[data-bs-target="#tab-current-processing"]');
                new bootstrap.Tab(tab).show();
                this.loadTabContent(tab);
            } else alert(res.message);
        } catch(e) { alert('요청 실패'); }
        finally { this.dom.btnStart.disabled = false; }
    }

    pollTask(taskId) {
        if(this.pollingInterval) clearInterval(this.pollingInterval);
        this.dom.progContainer.style.display = 'block';
        this.isProcessing = true;

        this.pollingInterval = setInterval(async () => {
            try {
                const task = await Flowork.get(`${this.urls.taskStatus}${taskId}`);
                if(task.status === 'processing') {
                    const pct = task.percent || 0;
                    this.dom.progBar.style.width = `${pct}%`;
                    this.dom.progText.textContent = `${pct}%`;
                } else {
                    clearInterval(this.pollingInterval);
                    this.pollingInterval = null;
                    this.isProcessing = false;
                    this.dom.progBar.style.width = '100%';
                    this.dom.progText.textContent = task.status === 'completed' ? '완료' : '오류';
                    setTimeout(() => {
                        this.dom.progContainer.style.display = 'none';
                        this.dom.progBar.style.width = '0%';
                        this.refreshActiveTab();
                    }, 2000);
                }
            } catch(e) { 
                if (this.pollingInterval) {
                    clearInterval(this.pollingInterval);
                    this.pollingInterval = null;
                }
            }
        }, 1000);
    }

    async resetSelection() {
        const codes = Array.from(document.querySelectorAll('.item-check:checked')).map(c => c.value);
        if(codes.length === 0) return;
        if(!confirm('선택 항목 초기화?')) return;
        
        try {
            await Flowork.post(document.body.dataset.apiReset || '/api/product/images/reset', { style_codes: codes });
            alert('초기화 완료');
            this.refreshActiveTab();
        } catch(e) { alert('오류'); }
    }

    async deleteImages(code) {
        if(!confirm('삭제하시겠습니까?')) return;
        try {
            await Flowork.post(this.urls.delete, { style_codes: [code] });
            alert('삭제 완료');
            this.refreshActiveTab();
        } catch(e) { alert('삭제 실패'); }
    }

    async showFolder(code) {
        const list = document.getElementById('folder-list-container');
        list.innerHTML = '로딩중...';
        this.dom.folderModal.show();
        
        try {
            const data = await Flowork.get(`${this.urls.folder}${code}`);
            if(data.status === 'success' && data.items.length > 0) {
                list.innerHTML = data.items.map(i => `
                    <a href="${i.url}" target="_blank" class="list-group-item list-group-item-action">
                        <i class="bi ${i.type === 'dir' ? 'bi-folder' : 'bi-file-earmark'} me-2"></i> ${i.name}
                    </a>
                `).join('');
            } else {
                list.innerHTML = '<div class="p-3 text-center">파일 없음</div>';
            }
        } catch(e) { list.innerHTML = '오류'; }
    }

    search() {
        const tab = document.querySelector('button[data-bs-target="#tab-hist-all"]');
        new bootstrap.Tab(tab).show();
        this.pagination['tab-hist-all'] = 1;
        this.loadTabContent(tab);
    }

    resetSearch() {
        this.dom.searchMulti.value = '';
        this.dom.searchName.value = '';
        this.dom.searchYear.value = '';
        this.dom.searchCat.value = '';
        this.search();
    }
}

document.addEventListener('turbo:load', () => {
    if (document.querySelector('.options-panel')) {
        if (currentOnlineManager) {
            currentOnlineManager.destroy();
        }
        currentOnlineManager = new OnlineManager();
    }
});

document.addEventListener('turbo:before-cache', () => {
    if (currentOnlineManager) {
        currentOnlineManager.destroy();
        currentOnlineManager = null;
    }
});