let currentCrmApp = null;

class CrmApp {
    constructor() {
        this.csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        this.dom = {
            custTbody: document.getElementById('customer-tbody'),
            searchInput: document.getElementById('search-query'),
            btnSearch: document.getElementById('btn-search'),
            formAdd: document.getElementById('form-add-customer'),
            
            repModalEl: document.getElementById('repairModal'),
            btnSaveRepair: document.getElementById('btn-save-repair'),
            repDateInput: document.getElementById('rep-date'),
            
            repName: document.getElementById('rep-name'),
            repPhone: document.getElementById('rep-phone'),
            repCode: document.getElementById('rep-code'),
            repProd: document.getElementById('rep-prod'),
            repColor: document.getElementById('rep-color'),
            repSize: document.getElementById('rep-size'),
            repDesc: document.getElementById('rep-desc')
        };
        
        this.urls = {
            list: document.body.dataset.apiListUrl,
            add: document.body.dataset.apiAddUrl,
            statusBase: document.body.dataset.apiStatusUrl
        };

        this.boundHandleSearchKeydown = this.handleSearchKeydown.bind(this);
        this.boundHandleAddSubmit = this.handleAddSubmit.bind(this);
        this.boundHandleSaveRepair = this.handleSaveRepair.bind(this);
        this.boundHandleStatusChange = this.handleStatusChange.bind(this);

        this.init();
    }

    init() {
        if (this.dom.custTbody) {
            this.dom.btnSearch.addEventListener('click', () => this.loadCustomers(1));
            this.dom.searchInput.addEventListener('keydown', this.boundHandleSearchKeydown);
            this.dom.formAdd.addEventListener('submit', this.boundHandleAddSubmit);
            this.loadCustomers();
        }

        if (this.dom.repModalEl) {
            const today = new Date().toISOString().split('T')[0];
            if(this.dom.repDateInput) this.dom.repDateInput.value = today;
            
            this.dom.btnSaveRepair.addEventListener('click', this.boundHandleSaveRepair);
            document.body.addEventListener('change', this.boundHandleStatusChange);
        }
    }

    destroy() {
        if (this.dom.custTbody) {
            this.dom.searchInput.removeEventListener('keydown', this.boundHandleSearchKeydown);
            this.dom.formAdd.removeEventListener('submit', this.boundHandleAddSubmit);
        }
        if (this.dom.repModalEl) {
            this.dom.btnSaveRepair.removeEventListener('click', this.boundHandleSaveRepair);
            document.body.removeEventListener('change', this.boundHandleStatusChange);
        }
    }

    handleSearchKeydown(e) {
        if (e.key === 'Enter') this.loadCustomers(1);
    }

    loadCustomers(page = 1) {
        const query = this.dom.searchInput.value.trim();
        fetch(`${this.urls.list}?page=${page}&query=${encodeURIComponent(query)}`)
            .then(r => r.json())
            .then(data => {
                this.dom.custTbody.innerHTML = '';
                if (data.customers.length === 0) {
                    this.dom.custTbody.innerHTML = '<tr><td colspan="5" class="p-4 text-muted">등록된 고객이 없습니다.</td></tr>';
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
                    this.dom.custTbody.appendChild(tr);
                });
            });
    }

    handleAddSubmit(e) {
        e.preventDefault();
        const payload = {
            name: document.getElementById('new-name').value,
            phone: document.getElementById('new-phone').value,
            address: document.getElementById('new-address').value
        };
        
        fetch(this.urls.add, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': this.csrfToken },
            body: JSON.stringify(payload)
        }).then(r => r.json()).then(data => {
            if (data.status === 'success') {
                alert(data.message);
                this.dom.formAdd.reset();
                this.loadCustomers(1);
            } else {
                alert(data.message);
            }
        });
    }

    handleSaveRepair() {
        const payload = {
            date: this.dom.repDateInput.value,
            customer_name: this.dom.repName.value,
            customer_phone: this.dom.repPhone.value,
            product_code: this.dom.repCode.value,
            product_info: this.dom.repProd.value,
            color: this.dom.repColor.value,
            size: this.dom.repSize.value,
            description: this.dom.repDesc.value
        };
        
        if(!payload.customer_name || !payload.customer_phone || !payload.description) {
            alert('고객명, 연락처, 수선 내용은 필수입니다.'); return;
        }
        
        fetch('/api/repairs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': this.csrfToken },
            body: JSON.stringify(payload)
        }).then(r => r.json()).then(data => {
            if (data.status === 'success') {
                alert(data.message);
                window.location.reload();
            } else {
                alert(data.message);
            }
        });
    }

    handleStatusChange(e) {
        if (e.target.classList.contains('status-select')) {
            const id = e.target.dataset.id;
            const newStatus = e.target.value;
            
            fetch(`${this.urls.statusBase}/${id}/status`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': this.csrfToken },
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
    }
}

document.addEventListener('turbo:load', () => {
    if (document.getElementById('customer-tbody') || document.getElementById('repairModal')) {
        if (currentCrmApp) {
            currentCrmApp.destroy();
        }
        currentCrmApp = new CrmApp();
    }
});

document.addEventListener('turbo:before-cache', () => {
    if (currentCrmApp) {
        currentCrmApp.destroy();
        currentCrmApp = null;
    }
});