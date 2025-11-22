document.addEventListener('DOMContentLoaded', () => {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    const today = new Date().toISOString().split('T')[0];

    const attTbody = document.getElementById('att-tbody');
    if (attTbody) {
        const dateInput = document.getElementById('work-date');
        const btnLoad = document.getElementById('btn-load');
        const btnSave = document.getElementById('btn-save');
        const urlGet = document.body.dataset.apiGet;
        const urlSave = document.body.dataset.apiSave;
        
        dateInput.value = today;

        function loadAttendance() {
            const date = dateInput.value;
            fetch(`${urlGet}?date=${date}`)
                .then(r => r.json())
                .then(data => {
                    attTbody.innerHTML = '';
                    if (data.data.length === 0) {
                        attTbody.innerHTML = '<tr><td colspan="6" class="p-4 text-center">등록된 직원이 없습니다.</td></tr>';
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
                        attTbody.appendChild(tr);
                    });
                });
        }

        btnLoad.addEventListener('click', loadAttendance);
        
        btnSave.addEventListener('click', () => {
            const records = [];
            attTbody.querySelectorAll('tr').forEach(tr => {
                records.push({
                    staff_id: tr.dataset.staffId,
                    status: tr.querySelector('.status-sel').value,
                    check_in: tr.querySelector('.in-time').value,
                    check_out: tr.querySelector('.out-time').value,
                    memo: tr.querySelector('.memo').value
                });
            });
            
            fetch(urlSave, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                body: JSON.stringify({ date: dateInput.value, records: records })
            }).then(r => r.json()).then(d => {
                alert(d.message);
                if(d.status==='success') loadAttendance();
            });
        });

        loadAttendance();
    }

    const salesTbody = document.getElementById('sales-tbody');
    if (salesTbody) {
        const dateInput = document.getElementById('sale-date');
        const btnLoad = document.getElementById('btn-load-sales');
        const btnSave = document.getElementById('btn-save-sales');
        const brandList = document.getElementById('brand-list');
        const btnAddBrand = document.getElementById('btn-add-brand');
        const newBrandInput = document.getElementById('new-brand-name');
        
        const urlBrand = document.body.dataset.apiBrand;
        const urlSales = document.body.dataset.apiSales;
        
        dateInput.value = today;

        function loadSales() {
            const date = dateInput.value;
            fetch(`${urlSales}?date=${date}`)
                .then(r => r.json())
                .then(data => {
                    salesTbody.innerHTML = '';
                    if (data.data.length === 0) {
                        salesTbody.innerHTML = '<tr><td colspan="6" class="p-4 text-center">등록된 경쟁사 브랜드가 없습니다. [브랜드 관리] 탭에서 추가해주세요.</td></tr>';
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
                        
                        tr.addEventListener('input', () => {
                            const v = cls => parseInt(tr.querySelector('.'+cls).value) || 0;
                            const sum = v('off-norm') + v('off-evt') + v('on-norm') + v('on-evt');
                            tr.querySelector('.total-cell').textContent = sum.toLocaleString();
                        });
                        
                        salesTbody.appendChild(tr);
                    });
                });
        }

        function loadBrands() {
            fetch(urlBrand)
                .then(r => r.json())
                .then(data => {
                    brandList.innerHTML = '';
                    data.brands.forEach(b => {
                        const li = document.createElement('li');
                        li.className = 'list-group-item d-flex justify-content-between align-items-center';
                        li.innerHTML = `
                            ${b.name}
                            <button class="btn btn-sm btn-outline-danger btn-del-brand" data-id="${b.id}">&times;</button>
                        `;
                        brandList.appendChild(li);
                    });
                });
        }

        btnLoad.addEventListener('click', loadSales);
        
        btnSave.addEventListener('click', () => {
            const records = [];
            salesTbody.querySelectorAll('tr').forEach(tr => {
                records.push({
                    brand_id: tr.dataset.brandId,
                    off_norm: tr.querySelector('.off-norm').value,
                    off_evt: tr.querySelector('.off-evt').value,
                    on_norm: tr.querySelector('.on-norm').value,
                    on_evt: tr.querySelector('.on-evt').value
                });
            });
            
            fetch(urlSales, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                body: JSON.stringify({ date: dateInput.value, records: records })
            }).then(r => r.json()).then(d => {
                alert(d.message);
            });
        });

        btnAddBrand.addEventListener('click', () => {
            const name = newBrandInput.value.trim();
            if (!name) return;
            
            fetch(urlBrand, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                body: JSON.stringify({ name: name })
            }).then(r => r.json()).then(d => {
                if (d.status === 'success') {
                    newBrandInput.value = '';
                    loadBrands();
                    loadSales(); 
                } else {
                    alert(d.message);
                }
            });
        });

        brandList.addEventListener('click', (e) => {
            if (e.target.classList.contains('btn-del-brand')) {
                if (!confirm('정말 삭제하시겠습니까? (기존 매출 기록은 유지됩니다)')) return;
                const id = e.target.dataset.id;
                fetch(`${urlBrand}/${id}`, {
                    method: 'DELETE',
                    headers: { 'X-CSRFToken': csrfToken }
                }).then(() => {
                    loadBrands();
                    loadSales();
                });
            }
        });

        loadSales();
        loadBrands();
    }
});