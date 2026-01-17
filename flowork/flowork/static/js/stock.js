document.addEventListener('DOMContentLoaded', () => {
    
    const analyzeExcelUrl = document.body.dataset.analyzeExcelUrl;

    function setupExcelAnalyzer(fileInputId, formId, wrapperId, statusId, gridId, analyzeUrl) {
        const fileInput = document.getElementById(fileInputId);
        const form = document.getElementById(formId);
        const wrapper = document.getElementById(wrapperId);
        const statusText = document.getElementById(statusId);
        const grid = document.getElementById(gridId);
        const submitButton = form.querySelector('button[type="submit"]');
        const selects = grid.querySelectorAll('select');
        const previews = grid.querySelectorAll('.col-preview');

        let currentPreviewData = {};
        let currentColumnLetters = [];

        if (!fileInput) return;

        fileInput.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) {
                resetUi();
                return;
            }

            wrapper.classList.remove('success', 'error');
            wrapper.classList.add('loading');
            statusText.textContent = '파일 분석 중... (로딩...)';
            grid.style.display = 'none';
            submitButton.style.display = 'none';
            disableSelects();

            const formData = new FormData();
            formData.append('excel_file', file);

            try {
                const response = await fetch(analyzeUrl, {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();

                if (!response.ok || data.status === 'error') {
                    throw new Error(data.message || '알 수 없는 오류');
                }
                
                currentPreviewData = data.preview_data;
                currentColumnLetters = data.column_letters;
                
                populateSelects();

                wrapper.classList.remove('loading');
                wrapper.classList.add('success');
                statusText.textContent = `분석 완료: ${file.name} (총 ${currentColumnLetters.length}개 열)`;
                grid.style.display = 'grid';
                submitButton.style.display = 'block';

            } catch (error) {
                console.error('Excel Analyze Error:', error);
                resetUi();
                wrapper.classList.remove('loading');
                wrapper.classList.add('error');
                statusText.textContent = `분석 실패: ${error.message}`;
                alert(`[엑셀 분석 오류]\n${error.message}\n\n파일을 다시 선택해주세요.`);
            }
        });

        function populateSelects() {
            selects.forEach(select => {
                select.innerHTML = '<option value="">-- 열 선택 --</option>';
                currentColumnLetters.forEach(letter => {
                    const option = document.createElement('option');
                    option.value = letter;
                    option.textContent = letter;
                    select.appendChild(option);
                });
                select.disabled = false;
            });
            
            previews.forEach(preview => {
                preview.innerHTML = '';
            });
        }
        
        grid.addEventListener('change', (e) => {
            if (e.target.tagName !== 'SELECT') return;

            const selectedLetter = e.target.value;
            const previewId = `preview_${e.target.id}`;
            const previewEl = document.getElementById(previewId);

            if (!previewEl) return;

            if (selectedLetter && currentPreviewData[selectedLetter]) {
                const previewHtml = currentPreviewData[selectedLetter]
                    .map(item => `<li>${item || '(빈 값)'}</li>`)
                    .join('');
                previewEl.innerHTML = `<ul>${previewHtml}</ul>`;
            } else {
                previewEl.innerHTML = '';
            }
        });

        function resetUi() {
            wrapper.classList.remove('success', 'error', 'loading');
            statusText.textContent = '엑셀 파일을 선택하세요.';
            grid.style.display = 'none';
            submitButton.style.display = 'none';
            currentPreviewData = {};
            currentColumnLetters = [];
            disableSelects();
            fileInput.value = ''; 
        }
        
        function disableSelects() {
             selects.forEach(select => {
                select.innerHTML = '<option value="">-- 열 선택 --</option>';
                select.disabled = true;
            });
            previews.forEach(preview => {
                preview.innerHTML = '';
            });
        }
    }

    setupExcelAnalyzer(
        'store_stock_excel_file',
        'form-update-store',
        'wrapper-store-file',
        'status-store-file',
        'grid-update-store',
        analyzeExcelUrl
    );

    setupExcelAnalyzer(
        'hq_stock_excel_file',
        'form-update-hq',
        'wrapper-hq-file',
        'status-hq-file',
        'grid-update-hq',
        analyzeExcelUrl
    );

});