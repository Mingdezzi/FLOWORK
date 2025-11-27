class ListApp {
    constructor() {
        this.container = null;
        this.handlers = {};
    }

    init(container) {
        this.container = container;
        
        this.dom = {
            form: container.querySelector('#advanced-search-form'),
            pagination: container.querySelector('ul.pagination')
        };

        // 1. 검색 폼 제출 가로채기
        if (this.dom.form) {
            this.handlers.submit = (e) => this.handleSubmit(e);
            this.dom.form.addEventListener('submit', this.handlers.submit);
        }

        // 2. 페이지네이션 링크 가로채기 (TabManager 전역 처리와 별개로 안전장치)
        if (this.dom.pagination) {
            this.handlers.pageClick = (e) => this.handlePageClick(e);
            this.dom.pagination.addEventListener('click', this.handlers.pageClick);
        }
    }

    destroy() {
        if (this.dom.form) this.dom.form.removeEventListener('submit', this.handlers.submit);
        if (this.dom.pagination) this.dom.pagination.removeEventListener('click', this.handlers.pageClick);
        this.container = null;
        this.dom = {};
        this.handlers = {};
    }

    handleSubmit(e) {
        e.preventDefault();
        
        // 폼 데이터를 쿼리 스트링으로 변환
        const formData = new FormData(this.dom.form);
        const params = new URLSearchParams(formData);
        
        // 현재 탭의 URL (action 속성) + 쿼리 스트링
        const url = `${this.dom.form.getAttribute('action')}?${params.toString()}`;
        
        // 현재 활성화된 탭 ID를 찾아 내용 리로드
        if (TabManager.activeTabId) {
            TabManager.loadContent(TabManager.activeTabId, url);
        }
    }

    handlePageClick(e) {
        const link = e.target.closest('a.page-link');
        if (link && !link.parentElement.classList.contains('disabled')) {
            e.preventDefault();
            const url = link.href;
            if (TabManager.activeTabId) {
                TabManager.loadContent(TabManager.activeTabId, url);
            }
        }
    }
}

// 모듈 등록
window.PageRegistry = window.PageRegistry || {};
window.PageRegistry['list'] = new ListApp();