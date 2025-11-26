/**
 * FLOWORK Common Utilities
 * - API 통신 래퍼 (CSRF 자동 처리)
 * - 포맷팅 함수 (금액, 날짜)
 */

const Flowork = {
    // CSRF 토큰 가져오기
    getCsrfToken: () => {
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    },

    // API 요청 래퍼 (fetch)
    api: async (url, options = {}) => {
        const defaults = {
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': Flowork.getCsrfToken()
            }
        };
        
        // 옵션 병합
        const settings = { ...defaults, ...options };
        if (options.headers) {
            settings.headers = { ...defaults.headers, ...options.headers };
        }

        try {
            const response = await fetch(url, settings);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.message || `Server Error: ${response.status}`);
            }
            return data;
        } catch (error) {
            console.error("API Error:", error);
            throw error;
        }
    },

    // GET 요청 단축
    get: async (url) => {
        return await Flowork.api(url, { method: 'GET' });
    },

    // POST 요청 단축
    post: async (url, body) => {
        return await Flowork.api(url, {
            method: 'POST',
            body: JSON.stringify(body)
        });
    },

    // 숫자 포맷 (3자리 콤마)
    fmtNum: (num) => {
        return (num || 0).toLocaleString();
    },

    // 날짜 포맷 (YYYY-MM-DD)
    fmtDate: (dateObj) => {
        if (!dateObj) dateObj = new Date();
        if (typeof dateObj === 'string') dateObj = new Date(dateObj);
        
        const year = dateObj.getFullYear();
        const month = String(dateObj.getMonth() + 1).padStart(2, '0');
        const day = String(dateObj.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }
};

// 전역에서 사용 가능하도록 설정
window.Flowork = Flowork;