document.addEventListener('DOMContentLoaded', () => {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

    // 1. 건의사항 작성
    const suggForm = document.getElementById('suggestion-form');
    if (suggForm) {
        suggForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const url = document.body.dataset.apiCreateUrl;
            const payload = {
                title: document.getElementById('title').value,
                content: document.getElementById('content').value,
                is_private: document.getElementById('is_private')?.checked || false
            };
            
            fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                body: JSON.stringify(payload)
            }).then(r => r.json()).then(data => {
                if(data.status === 'success') {
                    alert(data.message);
                    window.location.href = '/network/suggestions';
                } else {
                    alert(data.message);
                }
            });
        });
    }

    // 2. 건의사항 댓글
    const btnComment = document.getElementById('btn-save-comment');
    if (btnComment) {
        btnComment.addEventListener('click', () => {
            const id = btnComment.dataset.id;
            const content = document.getElementById('comment-content').value;
            if (!content) return;
            
            fetch(`/api/suggestions/${id}/comment`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                body: JSON.stringify({ content })
            }).then(r => r.json()).then(data => {
                if(data.status === 'success') window.location.reload();
                else alert(data.message);
            });
        });
    }

    // 3. 건의사항 삭제
    const btnDelSugg = document.querySelector('.btn-delete-sugg');
    if (btnDelSugg) {
        btnDelSugg.addEventListener('click', () => {
            if (!confirm('정말 삭제하시겠습니까?')) return;
            const id = btnDelSugg.dataset.id;
            fetch(`/api/suggestions/${id}`, {
                method: 'DELETE',
                headers: { 'X-CSRFToken': csrfToken }
            }).then(r => r.json()).then(data => {
                if(data.status === 'success') window.location.href = '/network/suggestions';
                else alert(data.message);
            });
        });
    }

    // 4. 메일 발송
    const mailForm = document.getElementById('mail-form');
    if (mailForm) {
        mailForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const url = document.body.dataset.apiSendUrl;
            const payload = {
                target_store_id: document.getElementById('receiver').value,
                title: document.getElementById('title').value,
                content: document.getElementById('content').value
            };
            
            if (!payload.target_store_id) {
                alert('받는 사람을 선택하세요.'); return;
            }
            
            fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                body: JSON.stringify(payload)
            }).then(r => r.json()).then(data => {
                if(data.status === 'success') {
                    alert(data.message);
                    window.location.href = '/network/mail?type=sent';
                } else {
                    alert(data.message);
                }
            });
        });
    }

    // 5. 메일 삭제
    const btnDelMail = document.querySelector('.btn-delete-mail');
    if (btnDelMail) {
        btnDelMail.addEventListener('click', () => {
            if (!confirm('정말 삭제하시겠습니까?')) return;
            const id = btnDelMail.dataset.id;
            fetch(`/api/mails/${id}`, {
                method: 'DELETE',
                headers: { 'X-CSRFToken': csrfToken }
            }).then(r => r.json()).then(data => {
                if(data.status === 'success') window.location.href = '/network/mail';
                else alert(data.message);
            });
        });
    }
});