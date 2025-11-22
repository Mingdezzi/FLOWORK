document.addEventListener('DOMContentLoaded', async () => {
    
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

    const calendarEl = document.getElementById('calendar');
    const eventModalEl = document.getElementById('event-modal');
    if (!calendarEl || !eventModalEl) {
        console.error("필수 요소(calendar, event-modal)가 없습니다.");
        return;
    }

    const eventModal = new bootstrap.Modal(eventModalEl);
    const bodyData = document.body.dataset;

    const apiUrls = {
        fetch: bodyData.apiScheduleEventsUrl,
        add: bodyData.apiScheduleAddUrl,
        updatePrefix: bodyData.apiScheduleUpdateUrlPrefix,
        deletePrefix: bodyData.apiScheduleDeleteUrlPrefix
    };

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

    let HOLIDAYS = {};
    try {
        const response = await fetch('/api/holidays');
        if (response.ok) {
            HOLIDAYS = await response.json();
        } else {
            console.warn('Failed to fetch holidays');
        }
    } catch (error) {
        console.error('Error fetching holidays:', error);
    }

    const calendar = new FullCalendar.Calendar(calendarEl, {
        locale: 'ko', 
        initialView: 'dayGridMonth', 
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek'
        },
        buttonText: {
             today: '오늘',
             month: '월',
             week: '주',
        },
        editable: true,
        selectable: true,
        
        events: apiUrls.fetch,

        dayCellDidMount: function(info) {
            const dateStr = info.date.toISOString().split('T')[0];
            const dayOfWeek = info.date.getDay(); 
            const holidayName = HOLIDAYS[dateStr];
            
            const dayNumberEl = info.el.querySelector('.fc-daygrid-day-number');
            
            if (dayOfWeek === 0 || dayOfWeek === 6 || holidayName) {
                if (dayNumberEl) {
                    dayNumberEl.style.color = '#dc3545'; 
                    dayNumberEl.style.fontWeight = 'bold';
                }
            }

            if (holidayName) {
                const holidayEl = document.createElement('div');
                holidayEl.textContent = holidayName;
                holidayEl.style.fontSize = '0.75em';
                holidayEl.style.color = '#dc3545';
                holidayEl.style.textAlign = 'left';
                holidayEl.style.paddingLeft = '4px';
                
                const topEl = info.el.querySelector('.fc-daygrid-day-top');
                if (topEl) {
                    topEl.appendChild(holidayEl);
                }
            }
        },

        dateClick: (info) => {
            resetModal();
            modalTitle.textContent = '새 일정 등록';
            eventStartDateInput.value = info.dateStr;
            eventAllDaySwitch.checked = true;
            toggleAllDayFields();
            eventModal.show();
        },
        
        eventClick: (info) => {
            resetModal();
            modalTitle.textContent = '일정 수정';
            
            const event = info.event;
            const props = event.extendedProps;
            
            eventIdInput.value = event.id;
            eventTitleInput.value = props.raw_title;
            eventStartDateInput.value = event.startStr.split('T')[0];
            eventAllDaySwitch.checked = event.allDay;
            
            if (event.end) {
                if (event.allDay) {
                    let endDate = new Date(event.endStr);
                    endDate.setDate(endDate.getDate() - 1);
                    eventEndDateInput.value = endDate.toISOString().split('T')[0];
                } else {
                    eventEndDateInput.value = event.endStr.split('T')[0];
                }
            }

            eventStaffSelect.value = props.staff_id || "0";
            eventTypeSelect.value = props.event_type || "일정";
            
            deleteButton.style.display = 'block';
            toggleAllDayFields();

            eventModal.show();
        }
    });

    calendar.render();

    eventAllDaySwitch.addEventListener('change', toggleAllDayFields);

    function toggleAllDayFields() {
        if (eventAllDaySwitch.checked) {
            eventEndDateWrapper.style.display = 'block';
        } else {
            eventEndDateWrapper.style.display = 'none';
            eventEndDateInput.value = '';
        }
    }

    eventTypeSelect.addEventListener('change', () => {
        const selectedOption = eventTypeSelect.options[eventTypeSelect.selectedIndex];
        const eventType = selectedOption.value;
        
        if (eventType !== '일정') {
            eventTitleInput.value = eventType;
        } else {
            if (['휴무', '연차', '반차', '병가'].includes(eventTitleInput.value)) {
                eventTitleInput.value = '';
            }
        }
    });

    saveButton.addEventListener('click', async () => {
        if (!eventStartDateInput.value || !eventTitleInput.value || !eventTypeSelect.value) {
            showModalStatus('시작 날짜, 일정 종류, 일정 제목은 필수입니다.', 'danger');
            return;
        }

        const selectedOption = eventTypeSelect.options[eventTypeSelect.selectedIndex];
        const eventColor = selectedOption.dataset.color || '#0d6efd';

        const eventData = {
            id: eventIdInput.value || null,
            staff_id: eventStaffSelect.value,
            event_type: eventTypeSelect.value,
            title: eventTitleInput.value.trim(),
            start_time: eventStartDateInput.value,
            all_day: eventAllDaySwitch.checked,
            end_time: eventEndDateInput.value || null,
            color: eventColor
        };
        
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
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(eventData)
            });
            const data = await response.json();
            
            if (!response.ok) throw new Error(data.message || '저장 실패');

            showModalStatus(data.message, 'success');
            calendar.refetchEvents();
            
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
                    'X-CSRFToken': csrfToken
                }
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.message || '삭제 실패');

            showModalStatus(data.message, 'success');
            calendar.refetchEvents();
            
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

    function resetModal() {
        modalForm.reset();
        eventIdInput.value = '';
        eventStaffSelect.value = "0";
        eventTypeSelect.value = "일정";
        eventAllDaySwitch.checked = true;
        toggleAllDayFields();
        deleteButton.style.display = 'none';
        modalStatus.innerHTML = '';
        setModalLoading(false);
    }

    function showModalStatus(message, type = 'info') {
        modalStatus.innerHTML = `<div class="alert alert-${type} mb-0">${message}</div>`;
    }

    function setModalLoading(isLoading) {
        saveButton.disabled = isLoading;
        deleteButton.disabled = isLoading;
        if (isLoading) {
            saveButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 저장 중...';
        } else {
            saveButton.innerHTML = '저장';
        }
    }

    eventModalEl.addEventListener('hidden.bs.modal', resetModal);
});