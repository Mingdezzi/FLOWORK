function imgFallback(img) {
    const src = img.src;
    if (src.includes('_DF_01.jpg')) {
        img.src = src.replace('_DF_01.jpg', '_DM_01.jpg');
    } else if (src.includes('_DM_01.jpg')) {
        img.src = src.replace('_DM_01.jpg', '_DG_01.jpg');
    } else {
        img.style.visibility = 'hidden';
    }
}

(function() {
    function isMobile() {
        const ua = navigator.userAgent;
        return /Mobi|Android|iPhone|iPad|iPod/i.test(ua);
    }
    if (isMobile()) {
        const searchInput = document.getElementById('search-query-input');
        if (searchInput) {
            searchInput.setAttribute('readonly', true);
            searchInput.setAttribute('inputmode', 'none');
        }
    }
})();

document.addEventListener('DOMContentLoaded', (event) => {
    
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

    const searchInput = document.getElementById('search-query-input');
    const clearTopBtn = document.getElementById('keypad-clear-top');
    
    const categoryBar = document.getElementById('category-bar');
    const categoryButtons = categoryBar.querySelectorAll('.category-btn');
    const hiddenCategoryInput = document.getElementById('selected-category');

    const keypadContainer = document.getElementById('keypad-container');
    const keypadNum = document.getElementById('keypad-num');
    const keypadKor = document.getElementById('keypad-kor');
    const keypadEng = document.getElementById('keypad-eng');

    // [수정] 상세 뷰 제어를 위한 요소 가져오기
    const productListUl = document.getElementById('product-list-ul');
    const listContainer = document.getElementById('product-list-view');
    const detailContainer = document.getElementById('product-detail-view');
    const detailIframe = document.getElementById('product-detail-iframe');
    const backButton = document.getElementById('btn-back-to-list');

    // [수정] 1. 상품 클릭 이벤트 위임 (productListUl에 리스너 등록)
    if (productListUl) {
        productListUl.addEventListener('click', (e) => {
            // 링크(.product-item) 또는 그 내부 요소를 클릭했는지 확인
            const link = e.target.closest('a.product-item');
            if (link) {
                // PC 화면일 때만 Iframe으로 보여주기 (992px 기준)
                if (window.innerWidth >= 992) {
                    e.preventDefault(); // 기본 이동(페이지 전환) 막기
                    
                    const targetUrl = link.getAttribute('href');
                    // partial=1 파라미터 추가 (헤더/네비게이션 숨김)
                    const detailUrl = targetUrl + (targetUrl.includes('?') ? '&' : '?') + 'partial=1';
                    
                    if (detailIframe) {
                        detailIframe.src = detailUrl;
                    }
                    
                    if (listContainer && detailContainer) {
                        listContainer.style.display = 'none';
                        detailContainer.style.display = 'flex'; // flex로 해야 내부 flex layout 적용됨
                    }
                }
                // 모바일이면 기본 동작(href 이동) 유지
            }
        });
    }

    // [수정] 2. 뒤로가기 버튼 이벤트
    if (backButton) {
        backButton.addEventListener('click', () => {
            if (listContainer && detailContainer) {
                listContainer.style.display = 'flex';
                detailContainer.style.display = 'none';
            }
            if (detailIframe) {
                detailIframe.src = 'about:blank'; // 리소스 해제
            }
        });
    }

    let isKorShiftActive = false;
    
    const korKeyMap = {
        'ㅂ': 'ㅃ', 'ㅈ': 'ㅉ', 'ㄷ': 'ㄸ', 'ㄱ': 'ㄲ', 'ㅅ': 'ㅆ',
        'ㅐ': 'ㅒ', 'ㅔ': 'ㅖ'
    };
    const korReverseKeyMap = {
        'ㅃ': 'ㅂ', 'ㅉ': 'ㅈ', 'ㄸ': 'ㄷ', 'ㄲ': 'ㄱ', 'ㅆ': 'ㅅ',
        'ㅒ': 'ㅐ', 'ㅖ': 'ㅔ'
    };
    const korShiftBtn = document.querySelector('#keypad-kor [data-key="shift-kor"]');

    function updateKorKeypadVisuals() {
        if (isKorShiftActive) {
            korShiftBtn.classList.add('active', 'btn-primary');
            korShiftBtn.classList.remove('btn-outline-secondary');
            for (const [base, shifted] of Object.entries(korKeyMap)) {
                const keyEl = document.querySelector(`#keypad-kor [data-key="${base}"]`);
                if (keyEl) {
                    keyEl.dataset.key = shifted;
                    keyEl.textContent = shifted;
                }
            }
        } else {
            korShiftBtn.classList.remove('active', 'btn-primary');
            korShiftBtn.classList.add('btn-outline-secondary');
            for (const [shifted, base] of Object.entries(korReverseKeyMap)) {
                const keyEl = document.querySelector(`#keypad-kor [data-key="${shifted}"]`);
                if (keyEl) {
                    keyEl.dataset.key = base;
                    keyEl.textContent = base;
                }
            }
        }
    }

    function showKeypad(mode) {
        keypadNum.classList.add('keypad-hidden');
        keypadKor.classList.add('keypad-hidden');
        keypadEng.classList.add('keypad-hidden');

        if (mode === 'kor') {
            keypadKor.classList.remove('keypad-hidden');
            document.body.dataset.inputMode = 'kor';
        } else if (mode === 'eng') {
            keypadEng.classList.remove('keypad-hidden');
            document.body.dataset.inputMode = 'eng';
        } else {
            keypadNum.classList.remove('keypad-hidden');
            document.body.dataset.inputMode = 'num';
        }
    }
    
    if (keypadContainer) {
        keypadContainer.addEventListener('click', (e) => {
            const key = e.target.closest('.keypad-btn, .qwerty-key');
            if (!key) return;

            const dataKey = key.dataset.key;
            if (!dataKey) return;


            if (dataKey === 'backspace') {
                let currentValue = searchInput.value;
                if (currentValue.length > 0) {
                    searchInput.value = currentValue.slice(0, -1);
                }
                triggerSearch(); 
            } 
            else if (dataKey === 'mode-kor') {
                showKeypad('kor');
            } 
            else if (dataKey === 'mode-eng') {
                showKeypad('eng');
                if (isKorShiftActive) {
                    isKorShiftActive = false;
                    updateKorKeypadVisuals();
                }
            } 
            else if (dataKey === 'mode-num') {
                showKeypad('num');
                if (isKorShiftActive) {
                    isKorShiftActive = false;
                    updateKorKeypadVisuals();
                }
            }
            else if (dataKey === 'shift-kor') {
                isKorShiftActive = !isKorShiftActive;
                updateKorKeypadVisuals();
            }
            else if (dataKey === 'shift-eng') {
            }
            else if (dataKey === ' ') {
                searchInput.value += ' ';
                triggerSearch(); 
            }
            else {
                searchInput.value = Hangul.assemble(searchInput.value + dataKey);
                triggerSearch(); 
            }
            
            searchInput.focus();
        });
    }


    const productListHeader = document.getElementById('product-list-header');
    const paginationUL = document.getElementById('search-pagination');
    
    const liveSearchUrl = document.body.dataset.liveSearchUrl;
    const imageURLPrefix = document.body.dataset.imageUrlPrefix;

    let debounceTimer;

    function triggerSearch() {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => { performSearch(1); }, 300);
    }

    const performSearch = async (page = 1) => {
        const query = searchInput.value;
        const category = hiddenCategoryInput.value;
        const perPage = 10;

        productListUl.innerHTML = '<li class="list-group-item text-center text-muted p-4">검색 중...</li>';
        paginationUL.innerHTML = '';

        try {
            const response = await fetch(liveSearchUrl, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
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
                renderResults(data.products, data.showing_favorites, data.selected_category);
                renderPagination(data.total_pages, data.current_page);
            } else { 
                throw new Error(data.message || 'API error'); 
            }
        } catch (error) {
            console.error('실시간 검색 오류:', error);
            productListUl.innerHTML = '<li class="list-group-item text-center text-danger p-4">검색 중 오류가 발생했습니다.</li>';
        }
    };
    
    const renderResults = (products, showingFavorites, selectedCategory) => {
         if (showingFavorites) {
            productListHeader.innerHTML = '<i class="bi bi-star-fill me-2 text-warning"></i>즐겨찾기 목록';
        } else {
            let categoryBadge = '';
            if (selectedCategory && selectedCategory !== '전체') {
                categoryBadge = `<span class="badge bg-success ms-2">${selectedCategory}</span>`;
            }
            productListHeader.innerHTML = `<i class="bi bi-card-list me-2"></i>상품 검색 결과 ${categoryBadge}`;
        }
        productListUl.innerHTML = '';
        if (products.length === 0) {
            const message = showingFavorites ? '즐겨찾기 상품 없음.' : '검색된 상품 없음.';
            productListUl.innerHTML = `<li class="list-group-item text-center text-muted p-4">${message}</li>`;
            return;
        }
        products.forEach(product => {
            const productHtml = `
                <li class="list-group-item">
                    <a href="/product/${product.product_id}" class="product-item d-flex align-items-center text-decoration-none text-body">
                        <img src="${imageURLPrefix}${product.image_pn}.jpg" alt="${product.product_name}" class="item-image rounded border flex-shrink-0" onerror="imgFallback(this)">
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
            productListUl.insertAdjacentHTML('beforeend', productHtml);
        });
    };

    const renderPagination = (totalPages, currentPage) => {
        paginationUL.innerHTML = '';
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
                    performSearch(pageNum);
                });
            }
            
            li.appendChild(a);
            return li;
        };

        paginationUL.appendChild(createPageItem(currentPage - 1, '«', false, currentPage === 1));

        let startPage = Math.max(1, currentPage - 2);
        let endPage = Math.min(totalPages, currentPage + 2);

        if (endPage - startPage < 4) {
            if (startPage === 1) endPage = Math.min(totalPages, startPage + 4);
            else if (endPage === totalPages) startPage = Math.max(1, endPage - 4);
        }

        for (let i = startPage; i <= endPage; i++) {
            paginationUL.appendChild(createPageItem(i, i, i === currentPage));
        }

        paginationUL.appendChild(createPageItem(currentPage + 1, '»', false, currentPage === totalPages));
    };

    if (categoryBar) {
        categoryBar.addEventListener('click', (e) => {
            const target = e.target.closest('.category-btn');
            if (!target) return;

            categoryButtons.forEach(btn => btn.classList.remove('active'));
            target.classList.add('active');
            hiddenCategoryInput.value = target.dataset.category;
            performSearch(1); 
            searchInput.focus();
        });
    }

    if (clearTopBtn) {
        clearTopBtn.addEventListener('click', () => {
            searchInput.value = '';
            performSearch(1);
            searchInput.focus();
        });
    }
    
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            if (e.isTrusted && !e.target.readOnly) { 
                triggerSearch();
            }
        });
        
         searchInput.addEventListener('keydown', (e) => {
             if (e.target.readOnly) return;
             
            if (e.key === 'Backspace') {
            } else if (e.key === 'Enter') {
                 clearTimeout(debounceTimer);
                 performSearch(1);
             }
        });
    }
    
    const searchForm = document.getElementById('search-form');
    if (searchForm) {
        searchForm.addEventListener('submit', (e) => {
            e.preventDefault();
            clearTimeout(debounceTimer);
            performSearch(1);
        });
    }
    
    showKeypad('num');
    
    const currentCategory = hiddenCategoryInput.value || '전체';
    categoryButtons.forEach(btn => {
        if (btn.dataset.category === currentCategory) {
            btn.classList.add('active');
        }
    });
    
    performSearch(1);

});