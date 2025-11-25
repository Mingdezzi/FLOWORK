window.Flowork = {
    getCsrfToken: () => {
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    },
    api: async (url, options = {}) => {
        const defaults = {
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': window.Flowork.getCsrfToken()
            }
        };
        
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

    get: async (url) => {
        return await window.Flowork.api(url, { method: 'GET' });
    },

    post: async (url, body) => {
        return await window.Flowork.api(url, {
            method: 'POST',
            body: JSON.stringify(body)
        });
    },

    fmtNum: (num) => {
        return (num || 0).toLocaleString();
    },

    fmtDate: (dateObj) => {
        if (!dateObj) dateObj = new Date();
        if (typeof dateObj === 'string') dateObj = new Date(dateObj);
        
        const year = dateObj.getFullYear();
        const month = String(dateObj.getMonth() + 1).padStart(2, '0');
        const day = String(dateObj.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }
};