let currentOperationsApp = null;

class OperationsApp {
    constructor() {
        this.csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        this.today = new Date().toISOString().split('T')[0];

        this.dom = {
            attTbody: document.getElementById('att-tbody'),
            salesTbody: document.getElementById('sales-tbody'),
            
            attDateInput: document.getElementById('work-date'),
            btnAttLoad: document.getElementById('btn-load'),
            btnAttSave: document.getElementById('btn-save'),
            
            salesDateInput: document.getElementById('sale-date'),
            btnSalesLoad: document.getElementById('btn-load-sales'),
            btnSalesSave: document.getElementById('btn-save-sales'),
            brandList: document.getElementById('brand-list'),
            btnAddBrand: document.getElementById('btn-add-brand'),
            newBrandInput: document.getElementById('new-brand-name')
        };

        this.urls = {
            attGet: document.body.dataset.apiGet,
            attSave: document.body.dataset.apiSave,
            brand: document.body.dataset.apiBrand,
            sales: document.body.dataset.apiSales
        };

        this.boundHandleSalesInput = this.handleSalesInput.bind(this);
        this.boundHandleBrandListClick = this.handleBrandListClick.bind(this);

        this.init();
    }

    init() {
        if (this.dom.attTbody) {
            this.dom.attDateInput.value = this.today;
            this.dom.btnAttLoad.addEventListener('click', () => this.loadAttendance());
            this.dom.btnAttSave.addEventListener('click', () => this.saveAttendance());
            this.loadAttendance();
        }

        if (this.dom.salesTbody) {
            this.dom.salesDateInput.value = this.today;
            this.dom.btnSalesLoad.addEventListener('click', () => this.loadSales());
            this.dom.btnSalesSave.addEventListener('click', () => this.saveSales());
            this.dom.btnAddBrand.addEventListener('click', () => this.addBrand());
            
            this.dom.salesTbody.addEventListener('input', this.boundHandleSalesInput);
            this.dom.brandList.addEventListener('click', this.boundHandleBrandListClick);

            this.loadSales();
            this.loadBrands();
        }
    }

    destroy() {
        if (this.dom.salesTbody) {
            this.dom.salesTbody.removeEventListener('input', this.boundHandleSalesInput);
            this.dom.brandList.removeEventListener('click', this.boundHandleBrandListClick);
        }
    }

    loadAttendance() {
        const date = this.dom.attDateInput.value;
        fetch(`${this.urls.attGet}?date=${date}`)
            .then(r => r.json())
            .then(data => {
                this.dom.attTbody.innerHTML = '';
                if (data.data.length === 0) {
                    this.dom.attTbody.innerHTML = '<tr><td colspan="6" class="p-4 text-center">등록된 직원이 없습니다.</td></tr>';
                    return;
                }
                data.data.forEach(r => {
                    const tr = document.createElement('tr');
                    tr.dataset.staffId = r.staff_id;
                    tr.innerHTML = `
                        <td class="fw-bold">${r.name}</td>
                        <td>${r.position || '-'}</td>
                        <td>
                            <select class="form-select form-select-sm status-sel">
                                ${['출근', '결근', '휴가', '반차', '병가', '지각', '조퇴', '휴무'].map(s => 
                                    `<option value="${s}" ${r.status === s ? 'selected' : ''}>${s}</option>`
                                ).join('')}
                            </select>
                        </td>
                        <td><input type="time" class="form-control form-control-sm in-time" value="${r.check_in}"></td>
                        <td><input type="time" class="form-control form-control-sm out-time" value="${r.check_out}"></td>
                        <td><input type="text" class="form-control form-control-sm memo" value="${r.memo}"></td>
                    `;
                    this.dom.attTbody.appendChild(tr);
                });
            });
    }

    saveAttendance() {
        const records = [];
        this.dom.attTbody.querySelectorAll('tr').forEach(tr => {
            records.push({
                staff_id: tr.dataset.staffId,
                status: tr.querySelector('.status-sel').value,
                check_in: tr.querySelector('.in-time').value,
                check_out: tr.querySelector('.out-time').value,
                memo: tr.querySelector('.memo').value
            });
        });
        
        fetch(this.urls.attSave, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': this.csrfToken },
            body: JSON.stringify({ date: this.dom.attDateInput.value, records: records })
        }).then(r => r.json()).then(d => {
            alert(d.message);
            if(d.status==='success') this.loadAttendance();
        });
    }

    loadSales() {
        const date = this.dom.salesDateInput.value;
        fetch(`${this.urls.sales}?date=${date}`)
            .then(r => r.json())
            .then(data => {
                this.dom.salesTbody.innerHTML = '';
                if (data.data.length === 0) {
                    this.dom.salesTbody.innerHTML = '<tr><td colspan="6" class="p-4 text-center">등록된 경쟁사 브랜드가 없습니다. [브랜드 관리] 탭에서 추가해주세요.</td></tr>';
                    return;
                }
                data.data.forEach(r => {
                    const total = r.off_norm + r.off_evt + r.on_norm + r.on_evt;
                    const tr = document.createElement('tr');
                    tr.dataset.brandId = r.brand_id;
                    tr.innerHTML = `
                        <td class="fw-bold bg-light">${r.brand_name}</td>
                        <td><input type="number" class="form-control form-control-sm text-end off-norm" value="${r.off_norm}"></td>
                        <td><input type="number" class="form-control form-control-sm text-end off-evt" value="${r.off_evt}"></td>
                        <td><input type="number" class="form-control form-control-sm text-end on-norm" value="${r.on_norm}"></td>
                        <td><input type="number" class="form-control form-control-sm text-end on-evt" value="${r.on_evt}"></td>
                        <td class="fw-bold total-cell">${total.toLocaleString()}</td>
                    `;
                    this.dom.salesTbody.appendChild(tr);
                });
            });
    }

    loadBrands() {
        fetch(this.urls.brand)
            .then(r => r.json())
            .then(data => {
                this.dom.brandList.innerHTML = '';
                data.brands.forEach(b => {
                    const li = document.createElement('li');
                    li.className = 'list-group-item d-flex justify-content-between align-items-center';
                    li.innerHTML = `
                        ${b.name}
                        <button class="btn btn-sm btn-outline-danger btn-del-brand" data-id="${b.id}">&times;</button>
                    `;
                    this.dom.brandList.appendChild(li);
                });
            });
    }

    handleSalesInput(e) {
        if (e.target.tagName === 'INPUT' && e.target.type === 'number') {
            const tr = e.target.closest('tr');
            if (tr) {
                const v = cls => parseInt(tr.querySelector('.'+cls).value) || 0;
                const sum = v('off-norm') + v('off-evt') + v('on-norm') + v('on-evt');
                tr.querySelector('.total-cell').textContent = sum.toLocaleString();
            }
        }
    }

    saveSales() {
        const records = [];
        this.dom.salesTbody.querySelectorAll('tr').forEach(tr => {
            records.push({
                brand_id: tr.dataset.brandId,
                off_norm: tr.querySelector('.off-norm').value,
                off_evt: tr.querySelector('.off-evt').value,
                on_norm: tr.querySelector('.on-norm').value,
                on_evt: tr.querySelector('.on-evt').value
            });
        });
        
        fetch(this.urls.sales, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': this.csrfToken },
            body: JSON.stringify({ date: this.dom.salesDateInput.value, records: records })
        }).then(r => r.json()).then(d => {
            alert(d.message);
        });
    }

    addBrand() {
        const name = this.dom.newBrandInput.value.trim();
        if (!name) return;
        
        fetch(this.urls.brand, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': this.csrfToken },
            body: JSON.stringify({ name: name })
        }).then(r => r.json()).then(d => {
            if (d.status === 'success') {
                this.dom.newBrandInput.value = '';
                this.loadBrands();
                this.loadSales(); 
            } else {
                alert(d.message);
            }
        });
    }

    handleBrandListClick(e) {
        if (e.target.classList.contains('btn-del-brand')) {
            if (!confirm('정말 삭제하시겠습니까? (기존 매출 기록은 유지됩니다)')) return;
            const id = e.target.dataset.id;
            fetch(`${this.urls.brand}/${id}`, {
                method: 'DELETE',
                headers: { 'X-CSRFToken': this.csrfToken }
            }).then(() => {
                this.loadBrands();
                this.loadSales();
            });
        }
    }
}

document.addEventListener('turbo:load', () => {
    if (document.getElementById('att-tbody') || document.getElementById('sales-tbody')) {
        if (currentOperationsApp) {
            currentOperationsApp.destroy();
        }
        currentOperationsApp = new OperationsApp();
    }
});

document.addEventListener('turbo:before-cache', () => {
    if (currentOperationsApp) {
        currentOperationsApp.destroy();
        currentOperationsApp = null;
    }
});