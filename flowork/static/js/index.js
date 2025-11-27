/**
 * Dashboard & Search Logic (Refactored for SPA & Data-Centric)
 */

class DashboardApp {
    constructor() {
        this.container = null;
        this.debounceTimer = null;
        this.isKorShiftActive = false;
        this.csrfToken = null;
        this.liveSearchUrl = null;
        
        this.korKeyMap = { 'ㅂ': 'ㅃ', 'ㅈ': 'ㅉ', 'ㄷ': 'ㄸ', 'ㄱ': 'ㄲ', 'ㅅ': 'ㅆ', 'ㅐ': 'ㅒ', 'ㅔ': 'ㅖ' };
        this.korReverseKeyMap = { 'ㅃ': 'ㅂ', 'ㅉ': 'ㅈ', 'ㄸ': 'ㄷ', 'ㄲ': 'ㄱ', 'ㅆ': 'ㅅ', 'ㅒ': 'ㅐ', 'ㅖ': 'ㅔ' };
        
        this.handlers = {
            productListClick: (e) => this.handleProductListClick(e),
            backButtonClick: () => this.handleBackButtonClick(),
            keypadClick: (e) => this.handleKeypadClick(e),
            categoryClick: (e) => this.handleCategoryClick(e),
            clearTopClick: () => this.handleClearTopClick(),
            searchInput: (e) => this.handleSearchInput(e),
            searchKeydown: (e) => this.handleSearchKeydown(e),
            searchSubmit: (e) => { e.preventDefault(); clearTimeout(this.debounceTimer); this.performSearch(1); }
        };
    }

    init(container) {
        this.container = container;
        this.csrfToken = Flowork.getCsrfToken();
        const dataset = Object.assign({}, document.body.dataset, container.dataset);
        this.liveSearchUrl = dataset.liveSearchUrl;

        this.dom = {
            searchInput: container.querySelector('#search-query-input'),
            clearTopBtn: container.querySelector('#keypad-clear-top'),
            categoryBar: container.querySelector('#category-bar'),
            hiddenCategoryInput: container.querySelector('#selected-category'),
            keypadContainer: container.querySelector('#keypad-container'),
            keypadNum: container.querySelector('#keypad-num'),
            keypadKor: container.querySelector('#keypad-kor'),
            keypadEng: container.querySelector('#keypad-eng'),
            korShiftBtn: container.querySelector('#keypad-kor [data-key="shift-kor"]'),
            
            productListUl: container.querySelector('#product-list-ul'),
            listContainer: container.querySelector('#product-list-view'),
            detailContainer: container.querySelector('#product-detail-view'),
            detailIframe: container.querySelector('#product-detail-iframe'),
            backButton: container.querySelector('#btn-back-to-list'),
            productListHeader: container.querySelector('#product-list-header'),
            paginationUL: container.querySelector('#search-pagination'),
            searchForm: container.querySelector('#search-form'),

            // Dashboard specific elements
            announcementList: container.querySelector('#announcement-list'),
            orderList: container.querySelector('#pending-order-list'),
            scheduleList: container.querySelector('#weekly-schedule-list'),
            loadingAnnouncements: container.querySelector('#loading-announcements'),
            loadingOrders: container.querySelector('#loading-orders'),
            loadingSchedules: container.querySelector('#loading-schedules'),
            emptyOrders: container.querySelector('#empty-orders'),
            emptySchedules: container.querySelector('#empty-schedules')
        };

        if (/Mobi|Android|iPhone|iPad|iPod/i.test(navigator.userAgent)) {
            if (this.dom.searchInput) {
                this.dom.searchInput.setAttribute('readonly', true);
                this.dom.searchInput.setAttribute('inputmode', 'none');
            }
        }

        this.bindEvents();
        
        // 검색 페이지 초기화
        if(this.dom.keypadContainer) this.showKeypad('num');
        if (this.dom.hiddenCategoryInput && this.dom.categoryBar) {
            const currentCategory = this.dom.hiddenCategoryInput.value || '전체';
            const btns = this.dom.categoryBar.querySelectorAll('.category-btn');
            btns.forEach(btn => {
                if (btn.dataset.category === currentCategory) btn.classList.add('active');
            });
        }
        if (this.dom.productListUl) {
            this.performSearch(1);
        }

        // [신규] 대시보드 데이터 로드 (대시보드 요소가 있을 때만)
        if (this.dom.announcementList) {
            this.loadDashboardStats();
        }
    }

    destroy() {
        if (this.dom.productListUl) this.dom.productListUl.removeEventListener('click', this.handlers.productListClick);
        if (this.dom.backButton) this.dom.backButton.removeEventListener('click', this.handlers.backButtonClick);
        if (this.dom.keypadContainer) this.dom.keypadContainer.removeEventListener('click', this.handlers.keypadClick);
        if (this.dom.categoryBar) this.dom.categoryBar.removeEventListener('click', this.handlers.categoryClick);
        if (this.dom.clearTopBtn) this.dom.clearTopBtn.removeEventListener('click', this.handlers.clearTopClick);
        if (this.dom.searchInput) {
            this.dom.searchInput.removeEventListener('input', this.handlers.searchInput);
            this.dom.searchInput.removeEventListener('keydown', this.handlers.searchKeydown);
        }
        if (this.dom.searchForm) this.dom.searchForm.removeEventListener('submit', this.handlers.searchSubmit);

        clearTimeout(this.debounceTimer);
        this.container = null;
        this.dom = {};
    }

    bindEvents() {
        if (this.dom.productListUl) this.dom.productListUl.addEventListener('click', this.handlers.productListClick);
        if (this.dom.backButton) this.dom.backButton.addEventListener('click', this.handlers.backButtonClick);
        if (this.dom.keypadContainer) this.dom.keypadContainer.addEventListener('click', this.handlers.keypadClick);
        if (this.dom.categoryBar) this.dom.categoryBar.addEventListener('click', this.handlers.categoryClick);
        if (this.dom.clearTopBtn) this.dom.clearTopBtn.addEventListener('click', this.handlers.clearTopClick);
        if (this.dom.searchInput) {
            this.dom.searchInput.addEventListener('input', this.handlers.searchInput);
            this.dom.searchInput.addEventListener('keydown', this.handlers.searchKeydown);
        }
        if (this.dom.searchForm) this.dom.searchForm.addEventListener('submit', this.handlers.searchSubmit);
    }

    // --- Dashboard Logic ---

    async loadDashboardStats() {
        try {
            const response = await fetch('/api/dashboard/stats', {
                method: 'GET',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': this.csrfToken }
            });
            const res = await response.json();
            
            if (res.status === 'success') {
                const data = res.data;
                
                // 1. 공지사항 렌더링
                if (this.dom.loadingAnnouncements) this.dom.loadingAnnouncements.style.display = 'none';
                
                if (data.announcements.length > 0) {
                    this.dom.announcementList.innerHTML = data.announcements.map(item => `
                        <li class="list-group-item d-flex justify-content-between align-items-center announcement-list-item">
                            <a href="#" onclick="TabManager.open('공지사항', '/announcement/${item.id}', 'announcements'); return false;" class="text-decoration-none text-dark text-truncate" style="max-width: 70%;">
                                ${item.title}
                            </a>
                            <small class="text-muted">${item.date}</small>
                        </li>
                    `).join('');
                } else {
                    this.dom.announcementList.innerHTML = '<li class="list-group-item text-center text-muted">등록된 공지사항이 없습니다.</li>';
                }

                // 2. 주문 현황 렌더링 (매장 전용)
                if (this.dom.loadingOrders) this.dom.loadingOrders.style.display = 'none';
                
                if (data.pending_orders.length > 0) {
                    this.dom.orderList.innerHTML = data.pending_orders.map(order => `
                        <tr onclick="TabManager.open('주문상세', '/order/${order.id}', 'order');" style="cursor: pointer;">
                            <td>${order.customer_name}</td>
                            <td class="text-start text-truncate" style="max-width: 120px;">${order.product_name}</td>
                            <td><span class="badge bg-info text-dark">${order.status}</span></td>
                            <td>${order.date}</td>
                        </tr>
                    `).join('');
                    if(this.dom.emptyOrders) this.dom.emptyOrders.style.display = 'none';
                } else {
                    if(this.dom.emptyOrders) this.dom.emptyOrders.style.display = 'block';
                }

                // 3. 주간 일정 렌더링 (매장 전용)
                if (this.dom.loadingSchedules) this.dom.loadingSchedules.style.display = 'none';
                
                if (data.weekly_schedules.length > 0) {
                    this.dom.scheduleList.innerHTML = data.weekly_schedules.map(event => `
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            <div class="text-truncate">
                                <span class="badge me-2" style="background-color: ${event.color};">${event.type}</span>
                                <strong>${event.title}</strong>
                                <small class="text-muted ms-1">(${event.staff_name})</small>
                            </div>
                            <small class="text-muted flex-shrink-0 ms-2">${event.date_str}</small>
                        </li>
                    `).join('');
                    if(this.dom.emptySchedules) this.dom.emptySchedules.style.display = 'none';
                } else {
                    if(this.dom.emptySchedules) this.dom.emptySchedules.style.display = 'block';
                }
            }
        } catch (e) {
            console.error("Dashboard load error:", e);
            // 에러 시 로딩 스피너 숨김 처리 등 예외처리
            if (this.dom.loadingAnnouncements) this.dom.loadingAnnouncements.style.display = 'none';
            if (this.dom.loadingOrders) this.dom.loadingOrders.style.display = 'none';
            if (this.dom.loadingSchedules) this.dom.loadingSchedules.style.display = 'none';
        }
    }

    // --- Search & Keypad Handlers (기존 유지) ---

    handleProductListClick(e) {
        const link = e.target.closest('a.product-item');
        if (link) {
            e.preventDefault();
            const url = link.getAttribute('href'); // /product/123
            
            if (window.innerWidth >= 992) {
                // 데스크탑: 우측 프레임
                const detailUrl = url + (url.includes('?') ? '&' : '?') + 'partial=1';
                if (this.dom.detailIframe) this.dom.detailIframe.src = detailUrl;
                if (this.dom.listContainer && this.dom.detailContainer) {
                    this.dom.listContainer.style.display = 'none';
                    this.dom.detailContainer.style.display = 'flex';
                }
            } else {
                // 모바일: 새 탭
                TabManager.open('상품상세', url, 'product_detail_' + url.split('/').pop());
            }
        }
    }

    handleBackButtonClick() {
        if (this.dom.listContainer && this.dom.detailContainer) {
            this.dom.listContainer.style.display = 'flex';
            this.dom.detailContainer.style.display = 'none';
        }
        if (this.dom.detailIframe) {
            this.dom.detailIframe.src = 'about:blank';
        }
    }

    handleKeypadClick(e) {
        const key = e.target.closest('.keypad-btn, .qwerty-key');
        if (!key) return;

        const dataKey = key.dataset.key;
        if (!dataKey) return;

        const input = this.dom.searchInput;

        if (dataKey === 'backspace') {
            let currentValue = input.value;
            if (currentValue.length > 0) {
                input.value = currentValue.slice(0, -1);
            }
            this.triggerSearch();
        } 
        else if (dataKey === 'mode-kor') { this.showKeypad('kor'); } 
        else if (dataKey === 'mode-eng') { 
            this.showKeypad('eng'); 
            if (this.isKorShiftActive) { this.isKorShiftActive = false; this.updateKorKeypadVisuals(); }
        } 
        else if (dataKey === 'mode-num') { 
            this.showKeypad('num'); 
            if (this.isKorShiftActive) { this.isKorShiftActive = false; this.updateKorKeypadVisuals(); }
        }
        else if (dataKey === 'shift-kor') {
            this.isKorShiftActive = !this.isKorShiftActive;
            this.updateKorKeypadVisuals();
        }
        else if (dataKey === ' ') {
            input.value += ' ';
            this.triggerSearch();
        }
        else {
            input.value = Hangul.assemble(input.value + dataKey);
            this.triggerSearch();
        }
        
        input.focus();
    }

    handleCategoryClick(e) {
        const target = e.target.closest('.category-btn');
        if (!target) return;

        const btns = this.dom.categoryBar.querySelectorAll('.category-btn');
        btns.forEach(btn => btn.classList.remove('active'));
        target.classList.add('active');
        this.dom.hiddenCategoryInput.value = target.dataset.category;
        this.performSearch(1);
        this.dom.searchInput.focus();
    }

    handleClearTopClick() {
        this.dom.searchInput.value = '';
        this.performSearch(1);
        this.dom.searchInput.focus();
    }

    handleSearchInput(e) {
        if (e.isTrusted && !e.target.readOnly) { 
            this.triggerSearch();
        }
    }

    handleSearchKeydown(e) {
        if (e.target.readOnly) return;
        if (e.key === 'Enter') {
            clearTimeout(this.debounceTimer);
            this.performSearch(1);
        }
    }

    updateKorKeypadVisuals() {
        const shiftBtn = this.dom.korShiftBtn; 
        if(!shiftBtn) return;

        if (this.isKorShiftActive) {
            shiftBtn.classList.add('active', 'btn-primary');
            shiftBtn.classList.remove('btn-outline-secondary');
            for (const [base, shifted] of Object.entries(this.korKeyMap)) {
                const keyEl = this.dom.keypadKor.querySelector(`[data-key="${base}"]`);
                if (keyEl) { keyEl.dataset.key = shifted; keyEl.textContent = shifted; }
            }
        } else {
            shiftBtn.classList.remove('active', 'btn-primary');
            shiftBtn.classList.add('btn-outline-secondary');
            for (const [shifted, base] of Object.entries(this.korReverseKeyMap)) {
                const keyEl = this.dom.keypadKor.querySelector(`[data-key="${shifted}"]`);
                if (keyEl) { keyEl.dataset.key = base; keyEl.textContent = base; }
            }
        }
    }

    showKeypad(mode) {
        this.dom.keypadNum.classList.add('keypad-hidden');
        this.dom.keypadKor.classList.add('keypad-hidden');
        this.dom.keypadEng.classList.add('keypad-hidden');

        if (mode === 'kor') {
            this.dom.keypadKor.classList.remove('keypad-hidden');
        } else if (mode === 'eng') {
            this.dom.keypadEng.classList.remove('keypad-hidden');
        } else {
            this.dom.keypadNum.classList.remove('keypad-hidden');
        }
    }

    triggerSearch() {
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(() => { this.performSearch(1); }, 300);
    }

    async performSearch(page = 1) {
        if(!this.dom.productListUl) return;

        const query = this.dom.searchInput.value;
        const category = this.dom.hiddenCategoryInput ? this.dom.hiddenCategoryInput.value : '전체';
        const perPage = 10;

        this.dom.productListUl.innerHTML = '<li class="list-group-item text-center text-muted p-4">검색 중...</li>';
        this.dom.paginationUL.innerHTML = '';

        try {
            const response = await fetch(this.liveSearchUrl, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({ query, category, page, per_page: perPage })
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                if (this.dom.listContainer && this.dom.detailContainer) {
                    this.dom.listContainer.style.display = 'flex';
                    this.dom.detailContainer.style.display = 'none';
                }
                if (this.dom.detailIframe) this.dom.detailIframe.src = 'about:blank';

                this.renderResults(data.products, data.showing_favorites, data.selected_category);
                this.renderPagination(data.total_pages, data.current_page);
            } else { 
                throw new Error(data.message || 'API error'); 
            }
        } catch (error) {
            console.error('Search error:', error);
            this.dom.productListUl.innerHTML = '<li class="list-group-item text-center text-danger p-4">오류가 발생했습니다.</li>';
        }
    }

    renderResults(products, showingFavorites, selectedCategory) {
        if (this.dom.productListHeader) {
            if (showingFavorites) {
                this.dom.productListHeader.innerHTML = '<i class="bi bi-star-fill me-2 text-warning"></i>즐겨찾기 목록';
            } else {
                let categoryBadge = '';
                if (selectedCategory && selectedCategory !== '전체') {
                    categoryBadge = `<span class="badge bg-success ms-2">${selectedCategory}</span>`;
                }
                this.dom.productListHeader.innerHTML = `<i class="bi bi-card-list me-2"></i>상품 검색 결과 ${categoryBadge}`;
            }
        }

        this.dom.productListUl.innerHTML = '';
        if (products.length === 0) {
            const message = showingFavorites ? '즐겨찾기 상품 없음.' : '검색된 상품 없음.';
            this.dom.productListUl.innerHTML = `<li class="list-group-item text-center text-muted p-4">${message}</li>`;
            return;
        }

        products.forEach(product => {
            const productHtml = `
                <li class="list-group-item">
                    <a href="#" onclick="TabManager.open('상품상세', '/product/${product.product_id}', 'product_detail'); return false;" class="product-item d-flex align-items-center text-decoration-none text-body">
                        <img src="${product.image_url}" alt="${product.product_name}" class="item-image rounded border flex-shrink-0" onerror="imgFallback(this)">
                        <div class="item-details flex-grow-1 ms-3">
                            <div class="product-name fw-bold">${product.product_name}</div>
                            <div class="product-meta small text-muted">
                                <span class="meta-item me-2">${product.product_number}</span>
                                ${product.colors ? `<span class="meta-item d-block d-sm-inline me-2"><i class="bi bi-palette"></i> ${product.colors}</span>` : ''}
                                <span class="meta-item me-2 fw-bold text-dark">${product.sale_price}</span>
                                <span class="meta-item discount ${product.original_price > 0 ? 'text-danger' : 'text-secondary'}">${product.discount}</span>
                            </div>
                        </div>
                    </a>
                </li>
            `;
            this.dom.productListUl.insertAdjacentHTML('beforeend', productHtml);
        });
    }

    renderPagination(totalPages, currentPage) {
        this.dom.paginationUL.innerHTML = '';
        if (totalPages <= 1) return;

        const createPageItem = (pageNum, text, isActive = false, isDisabled = false) => {
            const li = document.createElement('li');
            li.className = `page-item ${isActive ? 'active' : ''} ${isDisabled ? 'disabled' : ''}`;
            
            const a = document.createElement('a');
            a.className = 'page-link';
            a.href = '#';
            a.textContent = text;
            
            if (!isDisabled && !isActive) {
                a.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.performSearch(pageNum);
                });
            }
            li.appendChild(a);
            return li;
        };

        this.dom.paginationUL.appendChild(createPageItem(currentPage - 1, '«', false, currentPage === 1));

        let startPage = Math.max(1, currentPage - 2);
        let endPage = Math.min(totalPages, currentPage + 2);

        if (endPage - startPage < 4) {
            if (startPage === 1) endPage = Math.min(totalPages, startPage + 4);
            else if (endPage === totalPages) startPage = Math.max(1, endPage - 4);
        }

        for (let i = startPage; i <= endPage; i++) {
            this.dom.paginationUL.appendChild(createPageItem(i, i, i === currentPage));
        }

        this.dom.paginationUL.appendChild(createPageItem(currentPage + 1, '»', false, currentPage === totalPages));
    }
}

const dashboardApp = new DashboardApp();
window.PageRegistry = window.PageRegistry || {};
window.PageRegistry['home'] = dashboardApp;
window.PageRegistry['search'] = dashboardApp;