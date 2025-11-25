class LogManager {
    constructor() {
        this.tbody = document.getElementById('log-list-tbody');
        this.btnAuto = document.getElementById('btn-auto-log');
        
        this.loadLogs();

        if(this.btnAuto) {
            this.btnAuto.addEventListener('click', () => this.createAutoLog());
        }
    }

    async loadLogs() {
        try {
            const res = await Flowork.get('/api/system/logs');
            this.tbody.innerHTML = '';
            
            if(res.logs.length === 0) {
                this.tbody.innerHTML = '<tr><td colspan="4" class="text-center p-5 text-muted">기록된 업데이트 로그가 없습니다.</td></tr>';
                return;
            }
            
            res.logs.forEach(log => {
                // 줄바꿈 문자를 <br>로 변환하여 줄바꿈 처리
                const contentHtml = log.content ? log.content.replace(/\n/g, '<br>') : '';
                
                const row = `
                    <tr>
                        <td class="text-center"><span class="badge bg-primary fs-6">${log.version}</span></td>
                        <td class="p-3">
                            <div class="fw-bold mb-1 text-dark" style="font-size: 1.05rem;">${log.title}</div>
                            <div class="text-secondary" style="font-size: 0.9rem; line-height: 1.5;">${contentHtml}</div>
                        </td>
                        <td class="text-center text-muted small">${log.date}</td>
                        <td class="text-center"><span class="badge bg-light text-dark border">${log.admin}</span></td>
                    </tr>
                `;
                this.tbody.insertAdjacentHTML('beforeend', row);
            });
        } catch(e) {
            console.error(e);
            this.tbody.innerHTML = '<tr><td colspan="4" class="text-center p-5 text-danger"><i class="bi bi-exclamation-triangle me-2"></i>로그를 불러오지 못했습니다.</td></tr>';
        }
    }

    async createAutoLog() {
        if(!confirm('Git 커밋 기록을 기반으로 새 버전을 생성하고 로그를 남기시겠습니까?')) return;
        
        try {
            this.btnAuto.disabled = true;
            this.btnAuto.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 처리 중...';
            
            const res = await Flowork.post('/api/system/logs/auto', {});
            
            if(res.status === 'success') {
                alert(res.message);
                this.loadLogs();
            } else if(res.status === 'info') {
                alert(res.message);
            } else {
                alert(res.message);
            }
        } catch(e) {
            alert('오류가 발생했습니다.');
        } finally {
            this.btnAuto.disabled = false;
            this.btnAuto.innerHTML = '<i class="bi bi-magic me-1"></i> 최신 변경사항 자동 기록';
        }
    }
}

document.addEventListener('turbo:load', () => {
    if(document.getElementById('log-list-tbody')) {
        new LogManager();
    }
});