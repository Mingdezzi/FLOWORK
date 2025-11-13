document.addEventListener('DOMContentLoaded', () => {
    
    // [수정] CSRF 토큰 가져오기
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

    // --- 1. DOM 요소 및 API URL 가져오기 ---
    const calendarEl = document.getElementById('calendar');
    const eventModalEl = document.getElementById('event-modal');
    if (!calendarEl || !eventModalEl) {
        console.error("필수 요소(calendar, event-modal)가 없습니다.");
        return;
    }

    const eventModal = new bootstrap.Modal(eventModalEl);
    const bodyData = document.body.dataset;

    // API URL
    const apiUrls = {
        fetch: bodyData.apiScheduleEventsUrl,
        add: bodyData.apiScheduleAddUrl,
        updatePrefix: bodyData.apiScheduleUpdateUrlPrefix,
        deletePrefix: bodyData.apiScheduleDeleteUrlPrefix
    };

    // 모달 내부 폼 요소
    const modalForm = document.getElementById('form-schedule-event');
    const modalTitle = document.getElementById('eventModalLabel');
    const eventIdInput = document.getElementById('event_id');
    const eventStaffSelect = document.getElementById('event_staff');
    const eventTypeSelect = document.getElementById('event_type');
    const eventTitleInput = document.getElementById('event_title');
    const eventStartDateInput = document.getElementById('event_start_date');
    const eventAllDaySwitch = document.getElementById('event_all_day');
    const eventEndDateWrapper = document.getElementById('event_end_date_wrapper');
    const eventEndDateInput = document.getElementById('event_end_date');
    const saveButton = document.getElementById('btn-save-event');
    const deleteButton = document.getElementById('btn-delete-event');
    const modalStatus = document.getElementById('event-modal-status');

    // --- 2. FullCalendar 초기화 ---
    const calendar = new FullCalendar.Calendar(calendarEl, {
        locale: 'ko', // 한국어
        initialView: 'dayGridMonth', // 월간 뷰
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek' // 월/주 보기
        },
        buttonText: {
             today: '오늘',
             month: '월',
             week: '주',
        },
        editable: true, // 드래그/리사이즈 (관리자만 가능하도록 API에서 막아야 함)
        selectable: true, // 날짜 선택 가능
        
        // (A) 이벤트 데이터 로드
        events: apiUrls.fetch,

        // (B) 날짜 클릭 시 (새 일정)
        dateClick: (info) => {
            resetModal();
            modalTitle.textContent = '새 일정 등록';
            eventStartDateInput.value = info.dateStr; // 클릭한 날짜
            eventAllDaySwitch.checked = true;
            toggleAllDayFields();
            
            eventModal.show();
        },
        
        // (C) 기존 일정 클릭 시 (수정/삭제)
        eventClick: (info) => {
            resetModal();
            modalTitle.textContent = '일정 수정';
            
            const event = info.event;
            const props = event.extendedProps;
            
            eventIdInput.value = event.id;
            eventTitleInput.value = props.raw_title;
            eventStartDateInput.value = event.startStr.split('T')[0];
            eventAllDaySwitch.checked = event.allDay;
            
            // end 날짜 처리 (allDay 이벤트는 +1일 된 상태이므로 -1일 필요)
            if (event.end) {
                if (event.allDay) {
                    let endDate = new Date(event.endStr);
                    endDate.setDate(endDate.getDate() - 1); // 하루 빼기
                    eventEndDateInput.value = endDate.toISOString().split('T')[0];
                } else {
                    eventEndDateInput.value = event.endStr.split('T')[0];
                }
            }

            eventStaffSelect.value = props.staff_id || "0";
            eventTypeSelect.value = props.event_type || "일정";
            
            deleteButton.style.display = 'block'; // 삭제 버튼 표시
            toggleAllDayFields();

            eventModal.show();
        }
    });

    calendar.render(); // 캘린더 그리기

    // --- 3. 모달 이벤트 핸들러 ---

    // '하루 종일' 스위치 변경 시
    eventAllDaySwitch.addEventListener('change', toggleAllDayFields);

    function toggleAllDayFields() {
        if (eventAllDaySwitch.checked) {
            // 하루 종일 (종료 날짜 필드 표시)
            eventEndDateWrapper.style.display = 'block';
        } else {
            // 하루 종일 아님 (종료 날짜 필드 숨기기 - 시간 미구현)
            eventEndDateWrapper.style.display = 'none';
            eventEndDateInput.value = ''; // 시간 입력 미구현으로 종료일 초기화
        }
    }

    // '일정 종류' 변경 시 (제목 자동완성 및 색상 저장)
    eventTypeSelect.addEventListener('change', () => {
        const selectedOption = eventTypeSelect.options[eventTypeSelect.selectedIndex];
        const eventType = selectedOption.value;
        
        // '일정'이 아닐 경우, 제목 자동 완성
        if (eventType !== '일정') {
            eventTitleInput.value = eventType;
        } else {
            if (eventTitleInput.value === "휴무" || eventTitleInput.value === "연차" || 
                eventTitleInput.value === "반차" || eventTitleInput.value === "병가") {
                eventTitleInput.value = ''; // 기본값으로 복귀 시 제목 비우기
            }
        }
    });

    // '저장' 버튼 클릭
    saveButton.addEventListener('click', async () => {
        // 유효성 검사
        if (!eventStartDateInput.value || !eventTitleInput.value || !eventTypeSelect.value) {
            showModalStatus('시작 날짜, 일정 종류, 일정 제목은 필수입니다.', 'danger');
            return;
        }

        const selectedOption = eventTypeSelect.options[eventTypeSelect.selectedIndex];
        const eventColor = selectedOption.dataset.color || '#0d6efd';

        // 서버로 보낼 데이터
        const eventData = {
            id: eventIdInput.value || null,
            staff_id: eventStaffSelect.value,
            event_type: eventTypeSelect.value,
            title: eventTitleInput.value.trim(),
            start_time: eventStartDateInput.value,
            all_day: eventAllDaySwitch.checked,
            end_time: eventEndDateInput.value || null, // 비어있으면 null
            color: eventColor
        };
        
        // all_day가 true이고 end_time이 있으면 +1일 처리 (DB 저장을 위해)
        if (eventData.all_day && eventData.end_time) {
             let endDate = new Date(eventData.end_time);
             endDate.setDate(endDate.getDate() + 1);
             eventData.end_time = endDate.toISOString().split('T')[0];
        }

        const isNew = !eventData.id;
        const url = isNew ? apiUrls.add : `${apiUrls.updatePrefix}${eventData.id}`;
        
        setModalLoading(true);

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken // [수정] 헤더 추가
                },
                body: JSON.stringify(eventData)
            });
            const data = await response.json();
            
            if (!response.ok) throw new Error(data.message || '저장 실패');

            showModalStatus(data.message, 'success');
            calendar.refetchEvents(); // 캘린더 새로고침
            
            setTimeout(() => {
                eventModal.hide();
                setModalLoading(false);
            }, 1000);

        } catch (error) {
            console.error('Save event error:', error);
            showModalStatus(`오류: ${error.message}`, 'danger');
            setModalLoading(false);
        }
    });

    // '삭제' 버튼 클릭
    deleteButton.addEventListener('click', async () => {
        const eventId = eventIdInput.value;
        if (!eventId) return;

        if (!confirm(`[${eventTitleInput.value}] 일정을 정말 삭제하시겠습니까?`)) {
            return;
        }
        
        setModalLoading(true);
        const url = `${apiUrls.deletePrefix}${eventId}`;

        try {
            const response = await fetch(url, { 
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': csrfToken // [수정] 헤더 추가
                }
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.message || '삭제 실패');

            showModalStatus(data.message, 'success');
            calendar.refetchEvents(); // 캘린더 새로고침
            
            setTimeout(() => {
                eventModal.hide();
                setModalLoading(false);
            }, 1000);

        } catch (error) {
            console.error('Delete event error:', error);
            showModalStatus(`오류: ${error.message}`, 'danger');
            setModalLoading(false);
        }
    });

    // --- 4. 유틸리티 함수 ---

    // 모달 폼 초기화
    function resetModal() {
        modalForm.reset();
        eventIdInput.value = '';
        eventStaffSelect.value = "0"; // '매장 전체'
        eventTypeSelect.value = "일정";
        eventAllDaySwitch.checked = true;
        toggleAllDayFields();
        deleteButton.style.display = 'none';
        modalStatus.innerHTML = '';
        setModalLoading(false);
    }

    // 모달 상태 메시지 표시
    function showModalStatus(message, type = 'info') {
        modalStatus.innerHTML = `<div class="alert alert-${type} mb-0">${message}</div>`;
    }

    // 모달 로딩 상태 (버튼 비활성화)
    function setModalLoading(isLoading) {
        saveButton.disabled = isLoading;
        deleteButton.disabled = isLoading;
        if (isLoading) {
            saveButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 저장 중...';
        } else {
            saveButton.innerHTML = '저장';
        }
    }

    // Bootstrap 모달이 닫힐 때 폼 초기화
    eventModalEl.addEventListener('hidden.bs.modal', resetModal);
});