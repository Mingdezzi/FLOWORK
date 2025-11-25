// 이미지 폴백 함수 (전역)
if (!window.imgFallback) {
    window.imgFallback = function(img) {
        const src = img.src;
        if (src.includes('_DF_01.jpg')) {
            img.src = src.replace('_DF_01.jpg', '_DM_01.jpg');
        } else if (src.includes('_DM_01.jpg')) {
            img.src = src.replace('_DM_01.jpg', '_DG_01.jpg');
        } else {
            img.style.visibility = 'hidden';
        }
    };
}

class IndexApp {
    constructor() {
        this.csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        this.liveSearchUrl = document.body.dataset.liveSearchUrl;
        this.debounceTimer = null;
        this.isKorShiftActive = false;

        this.korKeyMap = {
            'ㅂ': 'ㅃ', 'ㅈ': 'ㅉ', 'ㄷ': 'ㄸ', 'ㄱ': 'ㄲ', 'ㅅ': 'ㅆ',
            'ㅐ': 'ㅒ', 'ㅔ': 'ㅖ'
        };
        this.korReverseKeyMap = {
            'ㅃ': 'ㅂ', 'ㅉ': 'ㅈ', 'ㄸ': 'ㄷ', 'ㄲ': 'ㄱ', 'ㅆ': 'ㅅ',
            'ㅒ': 'ㅐ', 'ㅖ': 'ㅔ'
        };

        // DOM 요소 캐싱을 init 시점으로 지연시킴
        this.dom = {}; 
        
        this.init();
    }

    init() {
        // DOM 요소 가져오기
        this.dom = {
            searchInput: document.getElementById('search-query-input'),
            clearTopBtn: document.getElementById('keypad-clear-top'),
            categoryBar: document.getElementById('category-bar'),
            categoryButtons: document.querySelectorAll('.category-btn'),
            hiddenCategoryInput: document.getElementById('selected-category'),
            keypadContainer: document.getElementById('keypad-container'),
            keypadNum: document.getElementById('keypad-num'),
            keypadKor: document.getElementById('keypad-kor'),
            keypadEng: document.getElementById('keypad-eng'),
            productListUl: document.getElementById('product-list-ul'),
            listContainer: document.getElementById('product-list-view'),
            detailContainer: document.getElementById('product-detail-view'),
            detailIframe: document.getElementById('product-detail-iframe'),
            backButton: document.getElementById('btn-back-to-list'),
            productListHeader: document.getElementById('product-list-header'),
            paginationUL: document.getElementById('search-pagination'),
            searchForm: document.getElementById('search-form'),
            korShiftBtn: document.querySelector('[data-key="shift-kor"]') // 셀렉터 수정
        };

        if (!this.dom.searchInput) return; // 검색 페이지가 아니면 종료

        this.checkMobile();
        this.bindEvents();
        this.showKeypad('num'); // 초기 키패드 설정
        
        const currentCategory = this.dom.hiddenCategoryInput ? this.dom.hiddenCategoryInput.value : '전체';
        if(this.dom.categoryButtons) {
            this.dom.categoryButtons.forEach(btn => {
                if (btn.dataset.category === currentCategory) {
                    btn.classList.add('active');
                    btn.classList.remove('btn-outline-secondary');
                    btn.classList.add('btn-primary');
                }
            });
        }
        
        // 초기 로드 시 검색 실행 (필요한 경우)
        // this.performSearch(1); 
    }

    checkMobile() {
        const isMobile = /Mobi|Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
        if (isMobile && this.dom.searchInput) {
            this.dom.searchInput.setAttribute('readonly', true);
            this.dom.searchInput.setAttribute('inputmode', 'none');
        }
    }

    bindEvents() {
        // 1. 상품 리스트 클릭
        if (this.dom.productListUl) {
            this.dom.productListUl.addEventListener('click', (e) => {
                const link = e.target.closest('a.product-item');
                if (link && window.innerWidth >= 992) {
                    e.preventDefault();
                    const targetUrl = link.getAttribute('href');
                    const detailUrl = targetUrl + (targetUrl.includes('?') ? '&' : '?') + 'partial=1';
                    
                    if (this.dom.detailIframe) this.dom.detailIframe.src = detailUrl;
                    
                    if (this.dom.listContainer) this.dom.listContainer.style.display = 'none';
                    if (this.dom.detailContainer) this.dom.detailContainer.style.display = 'flex';
                }
            });
        }

        // 2. 뒤로가기 버튼
        if (this.dom.backButton) {
            this.dom.backButton.addEventListener('click', () => {
                if (this.dom.listContainer) this.dom.listContainer.style.display = 'flex';
                if (this.dom.detailContainer) this.dom.detailContainer.style.display = 'none';
                if (this.dom.detailIframe) this.dom.detailIframe.src = 'about:blank';
            });
        }

        // 3. 키패드 클릭 (이벤트 위임)
        if (this.dom.keypadContainer) {
            this.dom.keypadContainer.addEventListener('click', (e) => this.handleKeypadClick(e));
            
            // 모바일 터치 지연 방지
            this.dom.keypadContainer.addEventListener('touchstart', (e) => {
                // 필요한 경우 preventDefault 처리 등을 추가
            }, {passive: true});
        }

        // 4. 카테고리 버튼
        if (this.dom.categoryBar) {
            this.dom.categoryBar.addEventListener('click', (e) => {
                const target = e.target.closest('.category-btn');
                if (!target) return;
                
                this.dom.categoryButtons.forEach(btn => {
                    btn.classList.remove('active', 'btn-primary');
                    btn.classList.add('btn-outline-secondary');
                });
                target.classList.add('active', 'btn-primary');
                target.classList.remove('btn-outline-secondary');
                
                if(this.dom.hiddenCategoryInput) {
                    this.dom.hiddenCategoryInput.value = target.dataset.category;
                    this.performSearch(1);
                }
            });
        }

        // 5. 상단 Clear 버튼
        if (this.dom.clearTopBtn) {
            this.dom.clearTopBtn.addEventListener('click', () => {
                this.dom.searchInput.value = '';
                this.performSearch(1);
                this.dom.searchInput.focus();
            });
        }

        // 6. 검색 인풋
        if (this.dom.searchInput) {
            this.dom.searchInput.addEventListener('input', (e) => {
                if (e.isTrusted && !e.target.readOnly) this.triggerSearch();
            });
            this.dom.searchInput.addEventListener('keydown', (e) => {
                if (!e.target.readOnly && e.key === 'Enter') {
                    clearTimeout(this.debounceTimer);
                    this.performSearch(1);
                }
            });
        }

        // 7. 폼 제출 (엔터키 등 방지 및 처리)
        if (this.dom.searchForm) {
            this.dom.searchForm.addEventListener('submit', (e) => {
                e.preventDefault();
                clearTimeout(this.debounceTimer);
                this.performSearch(1);
            });
        }
    }

    showKeypad(mode) {
        if(this.dom.keypadNum) this.dom.keypadNum.classList.add('keypad-hidden');
        if(this.dom.keypadKor) this.dom.keypadKor.classList.add('keypad-hidden');
        if(this.dom.keypadEng) this.dom.keypadEng.classList.add('keypad-hidden');

        if (mode === 'kor') {
            if(this.dom.keypadKor) this.dom.keypadKor.classList.remove('keypad-hidden');
            document.body.dataset.inputMode = 'kor';
        } else if (mode === 'eng') {
            if(this.dom.keypadEng) this.dom.keypadEng.classList.remove('keypad-hidden');
            document.body.dataset.inputMode = 'eng';
        } else {
            if(this.dom.keypadNum) this.dom.keypadNum.classList.remove('keypad-hidden');
            document.body.dataset.inputMode = 'num';
        }
    }

    updateKorKeypadVisuals() {
        if(!this.dom.keypadKor) return;
        
        if (this.isKorShiftActive) {
            if(this.dom.korShiftBtn) {
                this.dom.korShiftBtn.classList.add('active');
                this.dom.korShiftBtn.style.backgroundColor = '#e2e6ea';
            }
            for (const [base, shifted] of Object.entries(this.korKeyMap)) {
                const keyEl = this.dom.keypadKor.querySelector(`[data-key="${base}"]`);
                if (keyEl) {
                    keyEl.dataset.originalKey = base; // 원래 키 저장
                    keyEl.dataset.key = shifted;
                    keyEl.textContent = shifted;
                }
            }
        } else {
            if(this.dom.korShiftBtn) {
                this.dom.korShiftBtn.classList.remove('active');
                this.dom.korShiftBtn.style.backgroundColor = '';
            }
            // 모든 키를 원래대로 복구 (ReverseMap 사용보다 안전)
            const changedKeys = this.dom.keypadKor.querySelectorAll('[data-original-key]');
            changedKeys.forEach(keyEl => {
                const original = keyEl.dataset.originalKey;
                if(original) {
                    keyEl.dataset.key = original;
                    keyEl.textContent = original;
                    delete keyEl.dataset.originalKey;
                }
            });
        }
    }

    handleKeypadClick(e) {
        // 버튼이나, 버튼 내부 아이콘 클릭 시 처리
        const keyBtn = e.target.closest('button');
        if (!keyBtn) return;

        const dataKey = keyBtn.dataset.key;
        if (!dataKey) return;

        e.preventDefault(); // 포커스 잃는 것 방지

        if (dataKey === 'backspace') {
            let val = this.dom.searchInput.value;
            if (val.length > 0) {
                // 한글 라이브러리가 있고 한글이 포함된 경우 자모 분리 후 삭제 시도
                if (window.Hangul && Hangul.isComplete(val.slice(-1))) {
                     let disassembled = Hangul.disassemble(val);
                     disassembled.pop();
                     this.dom.searchInput.value = Hangul.assemble(disassembled);
                } else {
                    this.dom.searchInput.value = val.slice(0, -1);
                }
            }
            this.triggerSearch();
        } else if (dataKey === 'mode-kor') {
            this.showKeypad('kor');
        } else if (dataKey === 'mode-eng') {
            this.showKeypad('eng');
            this.isKorShiftActive = false;
            this.updateKorKeypadVisuals();
        } else if (dataKey === 'mode-num') {
            this.showKeypad('num');
            this.isKorShiftActive = false;
            this.updateKorKeypadVisuals();
        } else if (dataKey === 'shift-kor') {
            this.isKorShiftActive = !this.isKorShiftActive;
            this.updateKorKeypadVisuals();
        } else if (dataKey === 'shift-eng') {
            // 영어 Shift (대문자 토글) - 필요 시 구현
        } else {
            // 일반 문자 입력
            let char = dataKey;
            
            if (window.Hangul) {
                // 기존 값 + 입력 값 합쳐서 조립
                this.dom.searchInput.value = Hangul.assemble(this.dom.searchInput.value + char);
            } else {
                this.dom.searchInput.value += char;
            }
            this.triggerSearch();
        }
    }

    triggerSearch() {
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(() => { this.performSearch(1); }, 300);
    }

    async performSearch(page = 1) {
        const query = this.dom.searchInput.value;
        const category = this.dom.hiddenCategoryInput ? this.dom.hiddenCategoryInput.value : '전체';
        const perPage = 10;

        if(this.dom.productListUl) {
            this.dom.productListUl.innerHTML = '<li class="list-group-item text-center text-muted p-4">검색 중...</li>';
        }
        if(this.dom.paginationUL) {
            this.dom.paginationUL.innerHTML = '';
        }

        try {
            const response = await fetch(this.liveSearchUrl, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({ 
                    query: query, 
                    category: category,
                    page: page,
                    per_page: perPage
                })
            });
            
            if (!response.ok) throw new Error('Network response was not ok');
            const data = await response.json();
            
            if (data.status === 'success') {
                if (this.dom.listContainer && this.dom.detailContainer) {
                    this.dom.listContainer.style.display = 'flex';
                    this.dom.detailContainer.style.display = 'none';
                }
                if (this.dom.detailIframe) {
                    this.dom.detailIframe.src = 'about:blank';
                }

                this.renderResults(data.products, data.showing_favorites, data.selected_category);
                this.renderPagination(data.total_pages, data.current_page);
            } else { 
                throw new Error(data.message || 'API error'); 
            }
        } catch (error) {
            console.error('Search Error:', error);
            if(this.dom.productListUl) {
                this.dom.productListUl.innerHTML = '<li class="list-group-item text-center text-danger p-4">오류가 발생했습니다.</li>';
            }
        }
    }

    renderResults(products, showingFavorites, selectedCategory) {
        if(!this.dom.productListHeader || !this.dom.productListUl) return;

        if (showingFavorites) {
            this.dom.productListHeader.innerHTML = '<i class="bi bi-star-fill me-2 text-warning"></i>즐겨찾기 목록';
        } else {
            let categoryBadge = '';
            if (selectedCategory && selectedCategory !== '전체') {
                categoryBadge = `<span class="badge bg-success ms-2">${selectedCategory}</span>`;
            }
            this.dom.productListHeader.innerHTML = `<i class="bi bi-card-list me-2"></i>상품 검색 결과 ${categoryBadge}`;
        }
        
        this.dom.productListUl.innerHTML = '';
        
        if (!products || products.length === 0) {
            const message = showingFavorites ? '즐겨찾기 상품 없음.' : '검색된 상품 없음.';
            this.dom.productListUl.innerHTML = `<li class="list-group-item text-center text-muted p-4">${message}</li>`;
            return;
        }
        
        products.forEach(product => {
            const salePrice = product.sale_price || '0';
            const productHtml = `
                <li class="list-group-item">
                    <a href="/product/${product.product_id}" class="product-item d-flex align-items-center text-decoration-none text-body">
                        <img src="${product.image_url}" alt="${product.product_name}" class="item-image rounded border flex-shrink-0" style="width:60px; height:60px; object-fit:contain; background:#fff;" onerror="imgFallback(this)">
                        <div class="item-details flex-grow-1 ms-3">
                            <div class="product-name fw-bold text-dark">${product.product_name}</div>
                            <div class="product-meta small text-muted mt-1">
                                <span class="meta-item me-2 badge bg-light text-dark border">${product.product_number}</span>
                                ${product.colors ? `<span class="meta-item d-inline-block me-2 text-secondary"><i class="bi bi-palette"></i> ${product.colors}</span>` : ''}
                                <span class="meta-item me-2 fw-bold text-primary">${salePrice}</span>
                                <span class="meta-item discount small ${product.original_price > 0 ? 'text-danger' : 'text-secondary'}">${product.discount}</span>
                            </div>
                        </div>
                    </a>
                </li>
            `;
            this.dom.productListUl.insertAdjacentHTML('beforeend', productHtml);
        });
    }

    renderPagination(totalPages, currentPage) {
        if(!this.dom.paginationUL) return;
        
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

// Turbo Load 이벤트 또는 DOMContentLoaded
function initIndex() {
    if (document.getElementById('search-query-input')) {
        // 기존 인스턴스 정리 (필요하다면)
        window.currentIndexApp = new IndexApp();
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initIndex);
} else {
    initIndex();
}

// Turbo 사용하는 경우를 위한 리스너
document.addEventListener('turbo:load', initIndex);