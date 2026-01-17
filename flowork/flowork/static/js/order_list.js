document.addEventListener('DOMContentLoaded', () => {
    
    // (신규) API URL 가져오기
    const updateStatusUrl = document.body.dataset.updateStatusUrl;

    // (신규) 이벤트 위임을 사용하여 두 목록(진행 중, 월별)의 버튼 클릭을 모두 처리
    document.body.addEventListener('click', async (e) => {
        // 클릭된 요소가 .status-btn 인지 확인
        const targetButton = e.target.closest('.status-btn');
        
        // .status-btn이 아니거나, 이미 active 상태이면 아무것도 안 함
        if (!targetButton || targetButton.classList.contains('active')) {
            return;
        }

        const orderId = targetButton.dataset.orderId;
        const newStatus = targetButton.dataset.newStatus;
        
        if (!orderId || !newStatus || !updateStatusUrl) {
            return;
        }

        // (신규) 사용자 확인
        if (confirm(`주문(ID: ${orderId})의 상태를 [${newStatus}](으)로 변경하시겠습니까?`)) {
            try {
                // (신규) API 서버로 Fetch 요청
                const response = await fetch(updateStatusUrl, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        order_id: orderId,
                        new_status: newStatus
                    })
                });

                const data = await response.json();

                if (response.ok && data.status === 'success') {
                    // (신규) 성공 시, 페이지를 새로고침하여 변경사항(목록 이동 등)을 반영
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