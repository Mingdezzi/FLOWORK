document.addEventListener('DOMContentLoaded', () => {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    
    const custTbody = document.getElementById('customer-tbody');
    if (custTbody) {
        const listUrl = document.body.dataset.apiListUrl;
        const addUrl = document.body.dataset.apiAddUrl;
        const searchInput = document.getElementById('search-query');
        const btnSearch = document.getElementById('btn-search');
        const formAdd = document.getElementById('form-add-customer');

        function loadCustomers(page=1) {
            const query = searchInput.value.trim();
            fetch(`${listUrl}?page=${page}&query=${encodeURIComponent(query)}`)
                .then(r => r.json())
                .then(data => {
                    custTbody.innerHTML = '';
                    if (data.customers.length === 0) {
                        custTbody.innerHTML = '<tr><td colspan="5" class="p-4 text-muted">등록된 고객이 없습니다.</td></tr>';
                        return;
                    }
                    data.customers.forEach(c => {
                        const tr = document.createElement('tr');
                        tr.innerHTML = `
                            <td>${c.code}</td>
                            <td class="fw-bold">${c.name}</td>
                            <td>${c.phone}</td>
                            <td>${c.address}</td>
                            <td>${c.created_at}</td>
                        `;
                        custTbody.appendChild(tr);
                    });
                });
        }

        btnSearch.addEventListener('click', () => loadCustomers(1));
        searchInput.addEventListener('keydown', (e) => { if(e.key==='Enter') loadCustomers(1); });

        formAdd.addEventListener('submit', (e) => {
            e.preventDefault();
            const payload = {
                name: document.getElementById('new-name').value,
                phone: document.getElementById('new-phone').value,
                address: document.getElementById('new-address').value
            };
            
            fetch(addUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                body: JSON.stringify(payload)
            }).then(r => r.json()).then(data => {
                if (data.status === 'success') {
                    alert(data.message);
                    formAdd.reset();
                    loadCustomers(1);
                } else {
                    alert(data.message);
                }
            });
        });

        loadCustomers();
    }

    const repModalEl = document.getElementById('repairModal');
    if (repModalEl) {
        const repModal = new bootstrap.Modal(repModalEl);
        const btnSave = document.getElementById('btn-save-repair');
        const today = new Date().toISOString().split('T')[0];
        document.getElementById('rep-date').value = today;
        
        btnSave.addEventListener('click', () => {
            const payload = {
                date: document.getElementById('rep-date').value,
                customer_name: document.getElementById('rep-name').value,
                customer_phone: document.getElementById('rep-phone').value,
                product_code: document.getElementById('rep-code').value,
                product_info: document.getElementById('rep-prod').value,
                color: document.getElementById('rep-color').value,
                size: document.getElementById('rep-size').value,
                description: document.getElementById('rep-desc').value
            };
            
            if(!payload.customer_name || !payload.customer_phone || !payload.description) {
                alert('고객명, 연락처, 수선 내용은 필수입니다.'); return;
            }
            
            fetch('/api/repairs', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                body: JSON.stringify(payload)
            }).then(r => r.json()).then(data => {
                if (data.status === 'success') {
                    alert(data.message);
                    window.location.reload();
                } else {
                    alert(data.message);
                }
            });
        });

        document.body.addEventListener('change', (e) => {
            if (e.target.classList.contains('status-select')) {
                const id = e.target.dataset.id;
                const newStatus = e.target.value;
                const statusUrl = document.body.dataset.apiStatusUrl; 
                
                fetch(`${statusUrl}/${id}/status`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                    body: JSON.stringify({ status: newStatus })
                }).then(r => r.json()).then(data => {
                    if (data.status === 'success') {
                        const row = e.target.closest('tr');
                        const badge = row.querySelector('.status-badge');
                        if(badge) badge.textContent = newStatus;
                    } else {
                        alert(data.message);
                    }
                });
            }
        });
    }
});