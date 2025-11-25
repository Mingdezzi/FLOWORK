document.addEventListener('turbo:load', () => {
    const updateStatusUrl = document.body.dataset.updateStatusUrl;
    if (!updateStatusUrl) return;

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

    document.body.addEventListener('click', async (e) => {
        const targetButton = e.target.closest('.status-btn');
        
        if (!targetButton || targetButton.classList.contains('active')) {
            return;
        }

        const orderId = targetButton.dataset.orderId;
        const newStatus = targetButton.dataset.newStatus;
        
        if (!orderId || !newStatus) {
            return;
        }

        if (confirm(`주문(ID: ${orderId})의 상태를 [${newStatus}](으)로 변경하시겠습니까?`)) {
            try {
                const response = await fetch(updateStatusUrl, {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken 
                    },
                    body: JSON.stringify({
                        order_id: orderId,
                        new_status: newStatus
                    })
                });

                const data = await response.json();

                if (response.ok && data.status === 'success') {
                    alert('상태가 변경되었습니다.');
                    window.location.reload(); 
                } else {
                    throw new Error(data.message || '상태 변경에 실패했습니다.');
                }
            } catch (error) {
                console.error('Order status update error:', error);
                alert(`오류: ${error.message}`);
            }
        }
    });
});