/**
 * List Page Logic (Data-Centric Refactoring)
 */
class ListApp {
    constructor() {
        this.container = null;
        this.csrfToken = null;
        this.handlers = {};
        this.dom = {};
        this.currentParams = {}; // 현재 검색 조건 저장 (페이지 이동용)
        this.fallbackRules = [];
    }

    init(container) {
        this.container = container;
        this.csrfToken = Flowork.getCsrfToken();
        const dataset = Object.assign({}, document.body.dataset, container.dataset);
        
        // [신규] 이미지 폴백 규칙 로드
        try {
            const rules = dataset.fallbackRules;
            if (rules) this.fallbackRules = JSON.parse(rules);
        } catch(e) {
            console.error("Failed to parse fallback rules", e);
        }
        
        // [신규] 전역 폴백 함수 정의 (onerror에서 호출됨)
        // SPA에서는 전역 오염을 피해야 하지만, onclick/onerror 등 인라인 핸들러를 위해선 필요함.
        window.imgFallback = (img) => {
            const src = img.src;
            
            if (!this.fallbackRules || this.fallbackRules.length === 0) {
                img.style.visibility = 'hidden';
                return;
            }

            let foundMatch = false;
            for (const rule of this.fallbackRules) {
                // rule.from -> rule.to (예: "_DF_01.jpg" -> "_DM_01.jpg")
                if (src.includes(rule.from)) {
                    img.src = src.replace(rule.from, rule.to);
                    foundMatch = true;
                    break; // 한번만 교체하고 브라우저가 다시 로드 시도하게 함
                }
            }
            
            // 규칙에 매칭되지 않거나 이미 대체된 경우 숨김
            if (!foundMatch) {
                img.style.visibility = 'hidden';
            }
        };

        this.dom = {
            form: container.querySelector('#advanced-search-form'),
            listContainer: container.querySelector('#search-results-container'),
            paginationUl: container.querySelector('#search-pagination'),
            paginationWrapper: container.querySelector('#pagination-wrapper'),
            countBadge: container.querySelector('#search-result-count'),
            loadingDiv: container.querySelector('#search-loading'),
            initialGuide: container.querySelector('#initial-guide'),
            btnSubmit: container.querySelector('#btn-exec-search')
        };

        if (this.dom.form) {
            this.handlers.submit = (e) => {
                e.preventDefault();
                this.performSearch(1);
            };
            this.dom.form.addEventListener('submit', this.handlers.submit);
        }
    }

    destroy() {
        if (this.dom.form) this.dom.form.removeEventListener('submit', this.handlers.submit);
        // 전역 함수는 덮어쓰기 방식이라 null 처리하면 다른 탭에 영향 줄 수 있어 유지
        this.container = null;
        this.dom = {};
        this.handlers = {};
    }

    async performSearch(page = 1) {
        // 폼 데이터 수집
        const formData = new FormData(this.dom.form);
        const params = {};
        formData.forEach((value, key) => {
            if(value.trim()) params[key] = value.trim();
        });
        
        this.currentParams = params; // 저장

        // UI 업데이트: 로딩 표시
        this.dom.listContainer.innerHTML = '';
        if(this.dom.initialGuide) this.dom.initialGuide.style.display = 'none';
        this.dom.loadingDiv.style.display = 'block';
        this.dom.paginationWrapper.style.display = 'none';
        this.dom.btnSubmit.disabled = true;

        try {
            const response = await fetch('/api/products/advanced_search', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({ 
                    params: params,
                    page: page,
                    per_page: 20
                })
            });

            const data = await response.json();

            if (data.status === 'success') {
                this.renderProducts(data.data);
                this.renderPagination(data.pagination);
                if(this.dom.countBadge) this.dom.countBadge.textContent = data.pagination.total;
            } else {
                this.dom.listContainer.innerHTML = `<li class="list-group-item text-center text-danger p-4">오류: ${data.message}</li>`;
            }

        } catch (error) {
            console.error('Search API error:', error);
            this.dom.listContainer.innerHTML = '<li class="list-group-item text-center text-danger p-4">서버 통신 중 오류가 발생했습니다.</li>';
        } finally {
            this.dom.loadingDiv.style.display = 'none';
            this.dom.btnSubmit.disabled = false;
        }
    }

    renderProducts(items) {
        if (!items || items.length === 0) {
            this.dom.listContainer.innerHTML = '<li class="list-group-item text-center text-muted p-5">조건에 맞는 상품이 없습니다.</li>';
            return;
        }

        let html = '';
        items.forEach(p => {
            const discountHtml = p.discount_rate > 0
                ? `<span class="meta-item discount text-danger">${p.discount_rate}%</span>`
                : `<span class="meta-item discount text-secondary">0%</span>`;
                
            const colorsHtml = p.colors 
                ? `<span class="meta-item d-block d-sm-inline me-2"><i class="bi bi-palette"></i> ${p.colors}</span>` 
                : '';

            html += `
                <li class="list-group-item">
                    <a href="#" onclick="TabManager.open('상품상세', '/product/${p.id}', 'product_detail'); return false;" class="product-item d-flex align-items-center text-decoration-none text-body">
                        <img src="${p.image_url}" alt="${p.product_name}" class="item-image rounded border flex-shrink-0" onerror="imgFallback(this)">
                        <div class="item-details flex-grow-1 ms-3">
                            <div class="product-name fw-bold">${p.product_name}</div>
                            <div class="product-meta small text-muted">
                                <span class="meta-item me-2">${p.product_number}</span>
                                ${colorsHtml}
                                <span class="meta-item me-2 fw-bold text-dark">${p.sale_price}원</span>
                                ${discountHtml}
                            </div>
                        </div>
                    </a>
                </li>
            `;
        });
        this.dom.listContainer.innerHTML = html;
    }

    renderPagination(pg) {
        if (pg.total === 0) {
            this.dom.paginationWrapper.style.display = 'none';
            return;
        }
        
        this.dom.paginationWrapper.style.display = 'flex';
        this.dom.paginationUl.innerHTML = '';

        const createItem = (p, text, cls='') => {
            const li = document.createElement('li');
            li.className = `page-item ${cls}`;
            const a = document.createElement('a');
            a.className = 'page-link';
            a.href = '#';
            a.textContent = text;
            if (!cls.includes('disabled') && !cls.includes('active')) {
                a.onclick = (e) => {
                    e.preventDefault();
                    this.performSearch(p);
                };
            }
            li.appendChild(a);
            return li;
        };

        // Prev
        this.dom.paginationUl.appendChild(createItem(pg.current_page - 1, '«', pg.has_prev ? '' : 'disabled'));

        // Pages (Simple range logic)
        let start = Math.max(1, pg.current_page - 2);
        let end = Math.min(pg.pages, start + 4);
        if(end - start < 4 && pg.pages > 4) start = Math.max(1, end - 4);

        for(let i=start; i<=end; i++) {
            this.dom.paginationUl.appendChild(createItem(i, i, i === pg.current_page ? 'active' : ''));
        }

        // Next
        this.dom.paginationUl.appendChild(createItem(pg.current_page + 1, '»', pg.has_next ? '' : 'disabled'));
    }
}

window.PageRegistry = window.PageRegistry || {};
window.PageRegistry['list'] = new ListApp();