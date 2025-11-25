let currentNetworkApp = null;

class NetworkApp {
    constructor() {
        this.dom = {
            suggForm: document.getElementById('suggestion-form'),
            btnComment: document.getElementById('btn-save-comment'),
            btnDelSugg: document.querySelector('.btn-delete-sugg'),
            mailForm: document.getElementById('mail-form'),
            btnDelMail: document.querySelector('.btn-delete-mail'),
            
            suggTitle: document.getElementById('title'),
            suggContent: document.getElementById('content'),
            suggIsPrivate: document.getElementById('is_private'),
            commentContent: document.getElementById('comment-content'),
            
            mailReceiver: document.getElementById('receiver'),
            mailTitle: document.getElementById('title'),
            mailContent: document.getElementById('content')
        };

        this.urls = {
            suggCreate: document.body.dataset.apiCreateUrl,
            mailSend: document.body.dataset.apiSendUrl
        };

        this.boundHandleSuggestionSubmit = this.handleSuggestionSubmit.bind(this);
        this.boundHandleSaveComment = this.handleSaveComment.bind(this);
        this.boundHandleDeleteSuggestion = this.handleDeleteSuggestion.bind(this);
        this.boundHandleMailSubmit = this.handleMailSubmit.bind(this);
        this.boundHandleDeleteMail = this.handleDeleteMail.bind(this);

        this.init();
    }

    init() {
        if (this.dom.suggForm) {
            this.dom.suggForm.addEventListener('submit', this.boundHandleSuggestionSubmit);
        }

        if (this.dom.btnComment) {
            this.dom.btnComment.addEventListener('click', this.boundHandleSaveComment);
        }

        if (this.dom.btnDelSugg) {
            this.dom.btnDelSugg.addEventListener('click', this.boundHandleDeleteSuggestion);
        }

        if (this.dom.mailForm) {
            this.dom.mailForm.addEventListener('submit', this.boundHandleMailSubmit);
        }

        if (this.dom.btnDelMail) {
            this.dom.btnDelMail.addEventListener('click', this.boundHandleDeleteMail);
        }
    }

    destroy() {
        if (this.dom.suggForm) {
            this.dom.suggForm.removeEventListener('submit', this.boundHandleSuggestionSubmit);
        }
        if (this.dom.btnComment) {
            this.dom.btnComment.removeEventListener('click', this.boundHandleSaveComment);
        }
        if (this.dom.btnDelSugg) {
            this.dom.btnDelSugg.removeEventListener('click', this.boundHandleDeleteSuggestion);
        }
        if (this.dom.mailForm) {
            this.dom.mailForm.removeEventListener('submit', this.boundHandleMailSubmit);
        }
        if (this.dom.btnDelMail) {
            this.dom.btnDelMail.removeEventListener('click', this.boundHandleDeleteMail);
        }
    }

    async handleSuggestionSubmit(e) {
        e.preventDefault();
        const payload = {
            title: this.dom.suggTitle.value,
            content: this.dom.suggContent.value,
            is_private: this.dom.suggIsPrivate?.checked || false
        };
        
        try {
            const data = await Flowork.post(this.urls.suggCreate, payload);
            if(data.status === 'success') {
                alert(data.message);
                window.location.href = '/network/suggestions';
            } else {
                alert(data.message);
            }
        } catch(error) {
            alert('오류가 발생했습니다.');
        }
    }

    async handleSaveComment() {
        const id = this.dom.btnComment.dataset.id;
        const content = this.dom.commentContent.value;
        if (!content) return;
        
        try {
            const data = await Flowork.post(`/api/suggestions/${id}/comment`, { content });
            if(data.status === 'success') window.location.reload();
            else alert(data.message);
        } catch(error) {
            alert('오류가 발생했습니다.');
        }
    }

    async handleDeleteSuggestion() {
        if (!confirm('정말 삭제하시겠습니까?')) return;
        const id = this.dom.btnDelSugg.dataset.id;
        
        try {
            const data = await Flowork.api(`/api/suggestions/${id}`, { method: 'DELETE' });
            if(data.status === 'success') window.location.href = '/network/suggestions';
            else alert(data.message);
        } catch(error) {
            alert('오류가 발생했습니다.');
        }
    }

    async handleMailSubmit(e) {
        e.preventDefault();
        const payload = {
            target_store_id: this.dom.mailReceiver.value,
            title: this.dom.mailTitle.value,
            content: this.dom.mailContent.value
        };
        
        if (!payload.target_store_id) {
            alert('받는 사람을 선택하세요.'); return;
        }
        
        try {
            const data = await Flowork.post(this.urls.mailSend, payload);
            if(data.status === 'success') {
                alert(data.message);
                window.location.href = '/network/mail?type=sent';
            } else {
                alert(data.message);
            }
        } catch(error) {
            alert('오류가 발생했습니다.');
        }
    }

    async handleDeleteMail() {
        if (!confirm('정말 삭제하시겠습니까?')) return;
        const id = this.dom.btnDelMail.dataset.id;
        
        try {
            const data = await Flowork.api(`/api/mails/${id}`, { method: 'DELETE' });
            if(data.status === 'success') window.location.href = '/network/mail';
            else alert(data.message);
        } catch(error) {
            alert('오류가 발생했습니다.');
        }
    }
}

document.addEventListener('turbo:load', () => {
    if (document.getElementById('suggestion-form') || 
        document.getElementById('mail-form') || 
        document.querySelector('.btn-delete-mail')) {
        
        if (currentNetworkApp) {
            currentNetworkApp.destroy();
        }
        currentNetworkApp = new NetworkApp();
    }
});

document.addEventListener('turbo:before-cache', () => {
    if (currentNetworkApp) {
        currentNetworkApp.destroy();
        currentNetworkApp = null;
    }
});