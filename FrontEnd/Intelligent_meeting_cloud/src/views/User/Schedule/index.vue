<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import dayjs from 'dayjs';
import 'dayjs/locale/zh-cn';
dayjs.locale('zh-cn');

const STORAGE_KEY = 'schedule_events_data';

const DEFAULT_EVENTS = [
  { id: 1, title: 'Q4 研发例会', start: '2025-11-24 10:00', end: '11:30', room: '305 会议室', type: 'dept', host: '李经理', desc: '讨论 Q4 季度研发目标完成情况及下季度规划。' },
  { id: 2, title: '产品验收评审', start: '2025-11-24 14:00', end: '16:00', room: '401 洽谈室', type: 'important', host: '张总', desc: 'V2.0 版本上线验收。' },
];

const currentMonth = ref(dayjs());
const selectedDate = ref(dayjs());
const showModal = ref(false);
const currentEvent = ref(null);
const editForm = ref({});
const isEditMode = ref(false);
const allEvents = ref([]);


// 防误触关闭逻辑
const isPressedOnOverlay = ref(false)

const handleOverlayMouseDown = (e) => {
  // 只有直接按在遮罩层上，才标记为 true
  if (e.target === e.currentTarget) {
    isPressedOnOverlay.value = true
  } else {
    isPressedOnOverlay.value = false
  }
}

const handleOverlayMouseUp = (e) => {
  // 起点和终点都在遮罩层，才执行关闭
  if (isPressedOnOverlay.value && e.target === e.currentTarget) {
    closeModal() // 调用你原有的关闭方法
  }
  isPressedOnOverlay.value = false
}

onMounted(() => {
  const storedData = localStorage.getItem(STORAGE_KEY);
  if (storedData) {
    try {
      allEvents.value = JSON.parse(storedData);
    } catch (e) {
      console.error('读取日程数据失败', e);
      allEvents.value = DEFAULT_EVENTS;
    }
  } else {
    allEvents.value = DEFAULT_EVENTS;
  }
});

watch(allEvents, (newVal) => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(newVal));
}, { deep: true });

const daysInMonth = computed(() => currentMonth.value.daysInMonth());

const firstDayOfWeek = computed(() => {
  const day = currentMonth.value.startOf('month').day();
  return day === 0 ? 6 : day - 1; 
});

const calendarGrid = computed(() => {
  const grid = [];
  for (let i = 0; i < firstDayOfWeek.value; i++) {
    grid.push({ day: '', isPadding: true });
  }
  for (let i = 1; i <= daysInMonth.value; i++) {
    const dateStr = currentMonth.value.date(i).format('YYYY-MM-DD');
    const hasEvent = allEvents.value.some(e => e.start.startsWith(dateStr));
    
    grid.push({
      day: i,
      fullDate: dateStr,
      isPadding: false,
      hasEvent: hasEvent,
      isToday: dateStr === dayjs().format('YYYY-MM-DD'),
      isSelected: dateStr === selectedDate.value.format('YYYY-MM-DD')
    });
  }
  return grid;
});

const selectedDateEvents = computed(() => {
  const targetStr = selectedDate.value.format('YYYY-MM-DD');
  return allEvents.value
    .filter(e => e.start.startsWith(targetStr))
    .sort((a, b) => dayjs(a.start).diff(dayjs(b.start)));
});

const prevMonth = () => {
  currentMonth.value = currentMonth.value.subtract(1, 'month');
};

const nextMonth = () => {
  currentMonth.value = currentMonth.value.add(1, 'month');
};

const jumpToToday = () => {
  const today = dayjs();
  currentMonth.value = today;
  selectedDate.value = today;
};

const selectDay = (item) => {
  if (item.isPadding) return;
  selectedDate.value = dayjs(item.fullDate);
};

const openDetail = (event) => {
  currentEvent.value = event;
  isEditMode.value = false;
  showModal.value = true;
};

const startCreate = () => {
  currentEvent.value = null;
  editForm.value = {
    title: '',
    date: selectedDate.value.format('YYYY-MM-DD'),
    startTime: '09:00',
    endTime: '10:00',
    type: 'normal',
    room: '',
    host: '',
    desc: ''
  };
  isEditMode.value = true;
  showModal.value = true;
};

const startEdit = () => {
  const [dateStr, timeStr] = currentEvent.value.start.split(' ');
  editForm.value = {
    ...currentEvent.value,
    date: dateStr,
    startTime: timeStr,
    endTime: currentEvent.value.end
  };
  isEditMode.value = true;
};

const cancelEdit = () => {
  if (currentEvent.value) {
    isEditMode.value = false;
    editForm.value = {};
  } else {
    closeModal();
  }
};

const saveEvent = () => {
  if (!editForm.value.title || !editForm.value.date || !editForm.value.startTime) {
    alert('请补全必要信息');
    return;
  }

  const newStart = `${editForm.value.date} ${editForm.value.startTime}`;
  
  // 构造事件对象
  const eventData = {
    ...editForm.value,
    start: newStart,
    end: editForm.value.endTime
  };

  if (editForm.value.id) {
    // === 更新模式 ===
    const index = allEvents.value.findIndex(e => e.id === editForm.value.id);
    if (index !== -1) {
      allEvents.value[index] = eventData;
      currentEvent.value = eventData;
    }
  } else {
    // === 新建模式 ===
    eventData.id = Date.now();
    allEvents.value.push(eventData);
  }

  selectedDate.value = dayjs(editForm.value.date);
  
  isEditMode.value = false;
  if (!currentEvent.value) closeModal();
};

const deleteEvent = () => {
  const targetId = currentEvent.value?.id || editForm.value?.id;
  if (!targetId) return;

  if (confirm('确定要删除这个日程安排吗？')) {
    allEvents.value = allEvents.value.filter(e => e.id !== targetId);
    closeModal();
  }
};

const closeModal = () => {
  showModal.value = false;
  setTimeout(() => {
    currentEvent.value = null;
    isEditMode.value = false;
    editForm.value = {};
  }, 300);
};

const getEventTypeClass = (type) => {
  switch (type) {
    case 'important': return 'border-red-500 bg-red-50 text-red-600';
    case 'dept': return 'border-blue-500 bg-blue-50 text-blue-600';
    case 'system': return 'border-gray-500 bg-gray-50 text-gray-600';
    default: return 'border-teal-500 bg-teal-50 text-teal-600';
  }
};

const getModalHeaderClass = (type) => {
  switch (type) {
    case 'important': return 'bg-red-500';
    case 'dept': return 'bg-blue-500';
    case 'system': return 'bg-gray-600';
    default: return 'bg-teal-500';
  }
};
</script>

<template>
  <div class="schedule-wrapper">
    <div class="main-card">
      
      <!-- 顶部工具栏 -->
      <div class="toolbar">
        <h2 class="page-title"><i class="fa-solid fa-calendar-check text-primary"></i> 日程管理</h2>
        <div class="controls">
          <button class="btn-today" @click="jumpToToday">回到今天</button>
          <div class="month-switcher">
            <button class="btn-icon" @click="prevMonth"><i class="fa-solid fa-chevron-left"></i></button>
            <span class="current-month-text">{{ currentMonth.format('YYYY年 MMMM') }}</span>
            <button class="btn-icon" @click="nextMonth"><i class="fa-solid fa-chevron-right"></i></button>
          </div>
        </div>
      </div>

      <!-- 内容双栏布局 -->
      <div class="schedule-content">
        
        <!-- 左侧日历 -->
        <div class="calendar-section">
          <div class="week-header">
            <span v-for="w in ['一', '二', '三', '四', '五', '六', '日']" :key="w">{{ w }}</span>
          </div>
          
          <div class="days-grid">
            <div 
              v-for="(item, index) in calendarGrid" 
              :key="index"
              class="day-cell"
              :class="{
                'is-padding': item.isPadding,
                'is-today': item.isToday,
                'is-selected': item.isSelected,
                'has-event': item.hasEvent
              }"
              @click="selectDay(item)"
            >
              <span v-if="!item.isPadding">{{ item.day }}</span>
              <div v-if="item.hasEvent" class="event-dot"></div>
            </div>
          </div>
        </div>

        <!-- 右侧日程列表 -->
        <div class="agenda-section">
          <div class="agenda-header">
            <div>
              <div class="date-big">{{ selectedDate.format('MM月DD日') }}</div>
              <div class="weekday-small">{{ selectedDate.format('dddd') }}</div>
            </div>
            <!-- 新建按钮 -->
            <button class="btn-add" @click="startCreate">
              <i class="fa-solid fa-plus"></i> 新建日程
            </button>
          </div>

          <div class="timeline-container custom-scrollbar">
            <div v-if="selectedDateEvents.length > 0" class="timeline-list">
              <div v-for="event in selectedDateEvents" :key="event.id" class="timeline-item">
                <div class="time-col">
                  <span class="start-time">{{ event.start.split(' ')[1] }}</span>
                  <span class="end-time">{{ event.end }}</span>
                </div>
                <div class="content-col card-event" :class="getEventTypeClass(event.type)">
                  <h4 class="event-title">{{ event.title }}</h4>
                  <div class="event-meta">
                    <span><i class="fa-solid fa-location-dot"></i> {{ event.room }}</span>
                    <span><i class="fa-solid fa-user"></i> {{ event.host }}</span>
                  </div>
                  <button class="btn-detail" @click="openDetail(event)">查看详情</button>
                </div>
              </div>
            </div>

            <div v-else class="empty-state">
              <div class="empty-icon-box">
                <i class="fa-solid fa-mug-hot"></i>
              </div>
              <p>这一天没有任何安排</p>
              <button class="btn-create-empty" @click="startCreate">添加一个安排</button>
            </div>

          </div>
        </div>
      </div>
    </div>

    <!-- 详情/编辑 弹窗 -->
    <Transition name="modal-fade">
      <div 
        v-if="showModal" 
        class="modal-overlay" 
        @mousedown="handleOverlayMouseDown" 
        @mouseup="handleOverlayMouseUp"
      >
        <div class="modal-card">
          
          <!-- 弹窗头部 -->
          <div class="modal-header" :class="isEditMode ? 'bg-indigo-500' : getModalHeaderClass(currentEvent?.type)">
            <h3 class="modal-title">
              {{ isEditMode ? (currentEvent ? '编辑日程' : '新建日程') : currentEvent?.title }}
            </h3>
            <button class="btn-close" @click="closeModal">
              <i class="fa-solid fa-xmark"></i>
            </button>
          </div>
          
          <!-- 查看模式 -->
          <div v-if="!isEditMode && currentEvent" class="modal-body view-mode">
            <div class="info-row">
              <div class="info-icon"><i class="fa-regular fa-clock"></i></div>
              <div class="info-content">
                <span class="label">时间</span>
                <span class="value">{{ currentEvent.start }} - {{ currentEvent.end }}</span>
              </div>
            </div>

            <div class="info-row">
              <div class="info-icon"><i class="fa-solid fa-location-dot"></i></div>
              <div class="info-content">
                <span class="label">地点</span>
                <span class="value">{{ currentEvent.room || '未指定' }}</span>
              </div>
            </div>

            <div class="info-row">
              <div class="info-icon"><i class="fa-solid fa-user-tie"></i></div>
              <div class="info-content">
                <span class="label">主持人</span>
                <span class="value">{{ currentEvent.host || '暂无' }}</span>
              </div>
            </div>

            <hr class="divider"/>

            <div class="desc-section">
              <span class="label block mb-2">备注 / 描述</span>
              <p class="desc-text">
                {{ currentEvent.desc || '暂无详细描述' }}
              </p>
            </div>
          </div>

          <!-- 编辑/新建模式 -->
          <div v-else class="modal-body edit-mode custom-scrollbar">
            <div class="form-group">
              <label>日程标题</label>
              <input type="text" v-model="editForm.title" class="form-input" placeholder="请输入标题" />
            </div>

            <div class="form-row">
              <div class="form-group half">
                <label>日期</label>
                <input type="date" v-model="editForm.date" class="form-input" />
              </div>
              <div class="form-group half">
                <label>类型</label>
                <select v-model="editForm.type" class="form-input">
                  <option value="normal">普通会议</option>
                  <option value="dept">部门会议</option>
                  <option value="important">重要会议</option>
                  <option value="system">系统通知</option>
                </select>
              </div>
            </div>

            <div class="form-row">
              <div class="form-group half">
                <label>开始时间</label>
                <input type="time" v-model="editForm.startTime" class="form-input" />
              </div>
              <div class="form-group half">
                <label>结束时间</label>
                <input type="time" v-model="editForm.endTime" class="form-input" placeholder="例: 12:00" />
              </div>
            </div>

            <div class="form-row">
              <div class="form-group half">
                <label>地点</label>
                <input type="text" v-model="editForm.room" class="form-input" />
              </div>
              <div class="form-group half">
                <label>主持人</label>
                <input type="text" v-model="editForm.host" class="form-input" />
              </div>
            </div>

            <div class="form-group">
              <label>备注描述</label>
              <textarea v-model="editForm.desc" class="form-input textarea" rows="3"></textarea>
            </div>
          </div>

          <!-- 弹窗底部 -->
          <div class="modal-footer">
            
            <!-- 查看模式底部 -->
            <template v-if="!isEditMode">
              <!-- 删除按钮 -->
              <button class="btn-danger mr-auto" @click="deleteEvent">删除</button>
              <button class="btn-secondary" @click="closeModal">关闭</button>
              <button class="btn-primary" @click="startEdit">编辑</button>
            </template>

            <!-- 编辑/新建模式底部 -->
            <template v-else>
              <button v-if="editForm.id" class="btn-danger mr-auto" @click="deleteEvent">删除</button>
              <div v-else class="mr-auto"></div>

              <button class="btn-secondary" @click="cancelEdit">取消</button>
              <button class="btn-primary" @click="saveEvent">
                {{ editForm.id ? '保存修改' : '立即创建' }}
              </button>
            </template>

          </div>

        </div>
      </div>
    </Transition>

  </div>
</template>

<style scoped>
input, textarea { user-select: auto; }
* { user-select: none; }
:root {
  --primary: #2563eb;
  --bg-dark: #1e293b;
  --text-main: #334155;
  --border-color: #e2e8f0;
}

.schedule-wrapper {
  width: 100%; height: 100%; padding: 1.5rem; box-sizing: border-box;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  overflow: hidden; position: relative;
}

.main-card {
  background: rgba(30, 41, 59, 0.4); border-radius: 16px; height: 100%;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); display: flex; flex-direction: column;
}

.toolbar {
  padding: 1.5rem 2rem; border-bottom: 1px solid var(--border-color);
  display: flex; justify-content: space-between; align-items: center; flex-shrink: 0;
}
.page-title { font-size: 1.25rem; color: #fff; display: flex; align-items: center; gap: 10px; margin: 0; }
.text-primary { color: #20ae7cf3; }
.controls { display: flex; align-items: center; gap: 1.5rem; }
.btn-today {
  padding: 6px 16px; background: #f1f5f9; color: #445369; border: none; border-radius: 6px;
  cursor: pointer; font-size: 0.9rem; transition: all 0.2s;
}
.btn-today:hover { background: #e2e8f0; color: #000000; }
.month-switcher { display: flex; align-items: center; gap: 1rem; }
.current-month-text { font-weight: 700; color: #fff; min-width: 120px; text-align: center; }
.btn-icon {
  background: none; border: 1px solid var(--border-color); width: 32px; height: 32px;
  border-radius: 50%; cursor: pointer; color: #64748b; display: flex; align-items: center;
  justify-content: center; transition: all 0.2s;
}
.btn-icon:hover { border-color: var(--primary); color: var(--primary); }
.schedule-content { flex: 1; display: flex; overflow: hidden; min-height: 0; }

.calendar-section {
  flex: 3; height: 600px; padding: 2rem; display: flex; flex-direction: column;
  border-right: 1px solid var(--border-color); overflow-y: auto;
}
.week-header {
  display: grid; grid-template-columns: repeat(7, 1fr); text-align: center; margin-bottom: 1rem;
  color: #c5cbd4; font-weight: 600; font-size: 0.9rem;
}
.days-grid { flex: 1; display: grid; grid-template-columns: repeat(7, 1fr); grid-auto-rows: 1fr; gap: 8px; min-height: 0; }
.day-cell {
  border-radius: 12px; cursor: pointer; display: flex; flex-direction: column;
  align-items: center; justify-content: center; position: relative; font-weight: 500;
  color: #20ae7cf3; transition: background 0.3s;
}
.day-cell:hover:not(.is-padding) { background: rgba(30, 41, 59, 0.4); }
.is-padding { cursor: default; }
.is-selected {
  background: #20ae7c1c !important; color: #20ae7cf3; font-weight: 700;
  box-shadow: inset 0 0 0 2px var(--primary); border: 1px solid; border-color: #20ae7c;
}
.is-today { color: #00ffa6; }
.is-today::after {
  content: '今'; position: absolute; top: 4px; right: 4px; font-size: 0.6rem; color: var(--primary);
}
.event-dot { width: 6px; height: 6px; background: #ef4444; border-radius: 50%; margin-top: 4px; }

.agenda-section {
  flex: 2; min-height: 600px; max-height: 600px; padding: 2rem; display: flex; flex-direction: column;
  background: rgba(30, 41, 59, 0.4); border-radius: 3%; height: 100%; overflow: hidden;
}
.agenda-header {
  margin-bottom: 2rem; padding-bottom: 1rem; border-bottom: 1px solid var(--border-color);
  flex-shrink: 0; display: flex; justify-content: space-between; align-items: center;
}
.date-big { font-size: 2rem; font-weight: 700; color: #fff; }
.weekday-small { font-size: 1rem; color: #ffffffd6; margin-top: 4px; }

.btn-add {
  background: #20ae7cf3; color: white; border: none; padding: 8px 16px; border-radius: 8px;
  cursor: pointer; display: flex; align-items: center; gap: 6px; font-weight: 600;
  transition: all 0.2s;
}
.btn-add:hover { background: #1a966a; transform: translateY(-2px); }

.timeline-container { flex: 1; overflow-y: auto; padding-right: 10px; padding-bottom: 20px; }
.timeline-item { display: flex; gap: 1.5rem; margin-bottom: 1.5rem; }
.time-col { display: flex; flex-direction: column; align-items: flex-end; min-width: 60px; padding-top: 4px; }
.start-time { font-weight: 700; font-size: 1.1rem; color: #fff; }
.end-time { font-size: 0.8rem; color: #94a3b8; }
.content-col {
  flex: 1; padding: 1rem; border-radius: 12px; border-right: 4px solid rgba(30, 41, 59, 0.4);
  position: relative; transition: transform 0.2s; background: rgba(30, 41, 59, 0.4);
}
.content-col:hover { transform: translateX(2%); transition: transform 0.3s; }
.event-title { margin: 0 0 0.5rem 0; font-size: 1rem; font-weight: 600; }
.event-meta { display: flex; gap: 1rem; font-size: 0.85rem; opacity: 0.8; margin-bottom: 1rem; }
.btn-detail {
  background: #fff; border: 1px solid rgba(0,0,0,0.1); padding: 4px 12px; border-radius: 4px;
  font-size: 0.75rem; cursor: pointer; color: #64748b; transition: 0.2s;
}
.btn-detail:hover { color: #000000; border-color: var(--primary); transform: scale(1.05); }

.empty-state { height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #94a3b8; }
.empty-icon-box {
  width: 80px; height: 80px; background: #f1f5f9; border-radius: 50%;
  display: flex; align-items: center; justify-content: center; font-size: 2rem; margin-bottom: 1rem;
}
.btn-create-empty {
  margin-top: 1rem; background: transparent; border: 1px dashed #64748b; color: #64748b;
  padding: 8px 16px; border-radius: 6px; cursor: pointer; transition: 0.2s;
}
.btn-create-empty:hover { border-color: #20ae7cf3; color: #20ae7cf3; }

.custom-scrollbar::-webkit-scrollbar { width: 6px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: #94a3b8; border-radius: 3px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #cbd5e1; cursor: pointer; }

/* ===== Overlay ===== */
.modal-overlay {
  position: fixed; 
  top: 0; left: 0; width: 100vw; height: 100vh;
  background: rgba(0, 0, 0, 0.6); 
  backdrop-filter: blur(4px);
  z-index: 100;
  display: flex; align-items: center; justify-content: center;
}

/* ===== Modal Card ===== */
.modal-card {
  width: 90%; max-width: 450px;
  background: #1e293bdd;
  border-radius: 16px;
  padding: 2rem;
  border: 1px solid rgba(255,255,255,0.1);
  box-shadow: 0 20px 25px -5px rgba(0,0,0,0.3);
  color: white;
}

/* ===== Header ===== */
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.modal-title {
  margin: 0;
  font-size: 1.3rem;
  font-weight: 600;
  color: white;
}

/* 关闭按钮 */
.btn-close {
  background: none;
  border: none;
  font-size: 1.2rem;
  cursor: pointer;
  color: #94a3b8;
}
.btn-close:hover {
  color: #fff;
}

/* ===== Form / Body ===== */
.modal-body {
  padding: 0;
  color: white;
}

/* label 与输入框统一深色风格 */
.form-group {
  margin-bottom: 1.2rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: #cbd5e1;
  font-size: 0.9rem;
}

/* 输入框深色半透明玻璃风 */
.form-input {
  width: 100%;
  padding: 0.8rem;
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  background: rgba(0,0,0,0.2);
  color: white;
  font-size: 0.95rem;
  box-sizing: border-box;
}

.form-input:focus {
  outline: none;
  border-color: #20ae7c;
}

/* 行内布局 */
.form-row {
  display: flex;
  gap: 1rem;
}

/* 文本域 */
.textarea {
  min-height: 80px;
  resize: vertical;
}

/* ===== Footer ===== */
.modal-footer {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid rgba(255,255,255,0.1);
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
}

/* 按钮：深色风格对齐 */
.btn-secondary {
  padding: 0.7rem 1.6rem;
  border: 1px solid rgba(255,255,255,0.15);
  background: rgba(255,255,255,0.05);
  color: #cbd5e1;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 500;
}
.btn-secondary:hover {
  background: rgba(255,255,255,0.15);
}

/* 主按钮统一绿色 */
.btn-primary {
  padding: 0.8rem 1.6rem;
  border: none;
  background: #20ae7c;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  color: white;
}
.btn-primary:hover {
  filter: brightness(1.1);
}

/* 危险按钮 */
.btn-danger {
  padding: 0.7rem 1.6rem;
  border: 1px solid #ef4444;
  background: transparent;
  border-radius: 8px;
  color: #ef4444;
  cursor: pointer;
  font-weight: 600;
}
.btn-danger:hover {
  background: #ef4444;
  color: white;
}

/* 动画保持不变 */
.modal-fade-enter-active, .modal-fade-leave-active {
  transition: opacity 0.3s ease;
}

.modal-fade-enter-from, .modal-fade-leave-to {
  opacity: 0;
}


@media (max-width: 1024px) {
  .schedule-content { flex-direction: column; overflow-y: auto; }
  .calendar-section { border-right: none; border-bottom: 1px solid var(--border-color); }
  .days-grid { min-height: 300px; }
}
</style>