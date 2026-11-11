<script setup>
import { ref, onMounted, defineProps, defineEmits } from 'vue';
import dayjs from 'dayjs';
import { toast } from '@/utils/message';
import roomImg from "@/assets/imgs/room.png";

// API
import { getUserRoomPage } from "@/apis/room"; 
import { getTimeSlots } from "@/apis/room";
import { addReservation } from "@/apis/reservation"; 
import { useUserStore } from '@/stores/userStore';

const props = defineProps({
  roomId: { type: Number, required: true }
});

const emit = defineEmits(['back']);
const userStore = useUserStore();

const roomInfo = ref({});
const timeSlotList = ref([]); // [修改] 存放后端返回的时间片数组
const selectedDate = ref(dayjs().format('YYYY-MM-DD'));
const loading = ref(false);
const slotsLoading = ref(false); // [新增] 专门用于时间片的 loading

// 预约弹窗相关
const showBookingModal = ref(false);
const submitting = ref(false);
const bookingForm = ref({
  date: selectedDate.value,
  startTime: '',
  endTime: '',
  theme: '',
  remark: ''
});

const isHalfHourStep = (timeStr) => {
  if (!timeStr) return false;
  const minute = parseInt(timeStr.split(':')[1], 10);
  return minute === 0 || minute === 30;
};


onMounted(async () => {
  await fetchRoomInfo();
  await fetchOccupancy();
});

// 1. 获取房间详情 (保持不变)
const fetchRoomInfo = async () => {
  loading.value = true;
  try {
    const res = await getUserRoomPage({ page: 1, pageSize: 10, id: props.roomId }); 
    if (res.data?.records?.length > 0) {
      const target = res.data.records.find(r => r.id == props.roomId);
      if(target) {
        roomInfo.value = { 
          ...target, 
          image: target.image || roomImg,
          equipment: target.equipment ? target.equipment.split(',') : []
        };
      }
    }
  } catch(e) {
    toast.error('加载房间信息失败');
  } finally {
    loading.value = false;
  }
};

// 2. [重构] 获取占用情况 (适配新接口格式)
const fetchOccupancy = async () => {
  slotsLoading.value = true;
  try {
    const res = await getTimeSlots({
      date: selectedDate.value,
      roomId: props.roomId
    });
    
    // 后端返回格式: [{displayTime: "08:00-08:30", startTime: "08:00:00", status: 2}, ...]
    if (res.code === 1) { // 兼容不同的成功码
      timeSlotList.value = res.data || [];
    } else {
      timeSlotList.value = [];
      toast.error('获取时间段失败');
    }
  } catch(e) {
    console.error(e);
    timeSlotList.value = [];
  } finally {
    slotsLoading.value = false;
  }
};

// [新增] 点击时间片
const handleSlotClick = (slot) => {
  // 状态校验：只有 status === 0 (绿色/空闲) 可点击
  if (slot.status !== 0) return;

  // 自动填充表单
  bookingForm.value.date = selectedDate.value;
  // 截取前5位 "09:00:00" -> "09:00" 适配 input type="time"
  const startStr = slot.startTime.substring(0, 5); 
  bookingForm.value.startTime = startStr;
  
  // 自动计算结束时间 (默认 +30分钟)
  // 注意：这里需要结合具体日期，否则跨天会有问题，但在会议室场景通常是当天的
  const startObj = dayjs(`${selectedDate.value} ${startStr}`);
  const endObj = startObj.add(30, 'minute');
  bookingForm.value.endTime = endObj.format('HH:mm');

  bookingForm.value.theme = '';
  bookingForm.value.remark = '';
  
  showBookingModal.value = true;
};

// 手动点击"立即预约"按钮 (不选时间片，默认空)
const openManualBooking = () => {
  if (!roomInfo.value.isActive) return toast.warning('会议室维护中，无法预约');
  bookingForm.value = {
    date: selectedDate.value,
    startTime: '09:00',
    endTime: '10:00',
    theme: '',
    remark: ''
  };
  showBookingModal.value = true;
};

const submitBooking = async () => {
  if (!bookingForm.value.startTime || !bookingForm.value.endTime || !bookingForm.value.theme) {
    return toast.warning('请填写完整信息');
  }
  if (!isHalfHourStep(bookingForm.value.startTime) || !isHalfHourStep(bookingForm.value.endTime)) {
    return toast.warning('预约时间必须是整点或半点（如 09:00, 09:30）');
  }
  if (bookingForm.value.startTime >= bookingForm.value.endTime) {
    return toast.warning('结束时间必须晚于开始时间');
  }

  const payload = {
    userId: userStore.userInfo?.id,
    roomId: props.roomId,
    meetingTopic: bookingForm.value.theme,
    startTime: `${bookingForm.value.date} ${bookingForm.value.startTime}:00`,
    endTime: `${bookingForm.value.date} ${bookingForm.value.endTime}:00`,
    remark: bookingForm.value.remark,
    participantNum: roomInfo.value.capacity
  };

  try {
    submitting.value = true;
    const result = await addReservation(payload);
    if (result?.code !== 1) {
      toast.error('预约失败：' + (result?.msg || '系统错误'));
      return;
    }
    toast.success('预约申请已提交，等待管理员审核');
    showBookingModal.value = false;
    fetchOccupancy(); // 刷新状态
  } catch (e) {
    toast.error('预约失败：' + (e.message || '系统错误'));
  } finally {
    submitting.value = false;
  }
};
</script>

<template>
  <div class="detail-panel custom-scrollbar">
    <!-- 顶部导航 -->
    <div class="nav-bar">
      <button class="back-btn" @click="emit('back')">
        <i class="fas fa-arrow-left"></i> 返回列表
      </button>
    </div>

    <div v-if="loading" class="text-center py-4 text-gray-400">
      <i class="fas fa-spinner fa-spin"></i> 加载中...
    </div>

    <div v-else class="content-wrapper">
      <!-- 左侧：房间信息 -->
      <div class="room-info-card">
        <div class="img-wrapper">
          <img :src="roomInfo.image" class="room-img" />
          <div class="status-tag" :class="roomInfo.isActive ? 'active' : 'maintenance'">
            {{ roomInfo.isActive ? '可预订' : '维护中' }}
          </div>
        </div>
        
        <div class="info-body">
          <h1 class="room-title">{{ roomInfo.roomCode }}</h1>
          <p class="room-loc"><i class="fas fa-map-marker-alt"></i> {{ roomInfo.location || '位置未知' }}</p>
          
          <div class="spec-grid">
            <div class="spec-item">
              <span class="label">容量</span>
              <span class="val">{{ roomInfo.capacity }}人</span>
            </div>
            <div class="spec-item">
              <span class="label">设备</span>
              <div class="tags">
                <span v-for="tag in roomInfo.equipment" :key="tag" class="tag">{{ tag }}</span>
              </div>
            </div>
          </div>

          <div class="desc-box">
            <h3>会议室简介</h3>
            <p>{{ roomInfo.remark || '暂无详细描述。' }}</p>
          </div>

          <button class="btn-book-large" :disabled="!roomInfo.isActive" @click="openManualBooking">
            {{ roomInfo.isActive ? '自定义时间预约' : '暂停使用' }}
          </button>
        </div>
      </div>

      <!-- 右侧：时间片网格 (全新 UI) -->
      <div class="slots-card">
        <div class="slots-header">
          <h3><i class="fas fa-clock"></i> 预约时间段</h3>
          <!-- 日期选择 -->
          <div class="date-ctrl">
            <input type="date" v-model="selectedDate" @change="fetchOccupancy" class="date-picker" />
          </div>
        </div>

        <!-- 状态图例 -->
        <div class="status-legend">
          <span class="legend-item"><span class="dot available"></span> 可预约</span>
          <span class="legend-item"><span class="dot booked"></span> 已被订</span>
          <span class="legend-item"><span class="dot expired"></span> 已过期</span>
        </div>

        <div v-if="slotsLoading" class="text-center py-8 text-gray-400">
          <i class="fas fa-spinner fa-spin"></i> 刷新时间表中...
        </div>

        <div v-else class="slots-grid">
          <div 
            v-for="(slot, index) in timeSlotList" 
            :key="index"
            class="time-slot"
            :class="`status-${slot.status}`"
            @click="handleSlotClick(slot)"
          >
            <span class="slot-time">{{ slot.displayTime }}</span>
            <span class="slot-label">
              {{ slot.status === 0 ? '空闲' : (slot.status === 1 ? '已订' : '过期') }}
            </span>
          </div>
          
          <div v-if="timeSlotList.length === 0" class="no-slots">
            暂无时间段数据
          </div>
        </div>
      </div>
    </div>

    <!-- 预约弹窗 -->
    <Teleport to="body">
      <div v-if="showBookingModal" class="modal-overlay" @click.self="showBookingModal = false">
        <div class="modal-card">
          <div class="modal-header">
            <h3>预约 {{ roomInfo.roomCode }}</h3>
            <button class="btn-close" @click="showBookingModal = false"><i class="fas fa-times"></i></button>
          </div>
          <div class="modal-body">
            <div class="form-group"><label>日期</label><input type="date" v-model="bookingForm.date" disabled></div>
            <div class="form-row">
              <div class="form-group"><label>开始时间</label><input type="time" step="1800" v-model="bookingForm.startTime"></div>
              <div class="form-group"><label>结束时间</label><input type="time" step="1800" v-model="bookingForm.endTime"></div>
            </div>
            <div class="form-group"><label>会议主题</label><input type="text" v-model="bookingForm.theme" placeholder="请输入会议主题"></div>
            <div class="form-group"><label>备注</label><input type="text" v-model="bookingForm.remark" placeholder="如：需投影仪"></div>
            
            <button class="btn-primary-block" @click="submitBooking" :disabled="submitting">
              <i class="fas fa-spinner fa-spin" v-if="submitting"></i>
              {{ submitting ? '提交中...' : '提交预约申请' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
/* 继承之前的通用样式 */
.detail-panel { height: 100%; overflow-y: auto; color: #fff; animation: fadeIn 0.3s ease; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

.nav-bar { margin-bottom: 1.5rem; }
.back-btn { background: transparent; border: 1px solid rgba(255,255,255,0.2); color: #cbd5e1; padding: 0.5rem 1rem; border-radius: 8px; cursor: pointer; transition: all 0.2s; display: flex; align-items: center; gap: 8px; }
.back-btn:hover { border-color: #20ae7c; color: #20ae7c; }

.content-wrapper { display: grid; grid-template-columns: 350px 1fr; gap: 2rem; }

/* 左侧信息卡片 (保持不变) */
.room-info-card { background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(255,255,255,0.1); border-radius: 16px; overflow: hidden; backdrop-filter: blur(10px); }
.img-wrapper { position: relative; height: 200px; }
.room-img { width: 100%; height: 100%; object-fit: cover; }
.status-tag { position: absolute; top: 10px; right: 10px; padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
.status-tag.active { background: rgba(32, 174, 124, 0.9); color: white; }
.status-tag.maintenance { background: rgba(239, 68, 68, 0.9); color: white; }
.info-body { padding: 1.5rem; }
.room-title { margin: 0; font-size: 1.8rem; font-weight: 700; color: #f1f5f9; }
.room-loc { color: #94a3b8; margin: 0.5rem 0 1.5rem 0; font-size: 0.9rem; }
.spec-grid { margin-bottom: 1.5rem; }
.spec-item { display: flex; margin-bottom: 0.8rem; }
.spec-item .label { width: 60px; color: #64748b; font-size: 0.9rem; }
.spec-item .val { color: #e2e8f0; font-weight: 500; }
.tags { display: flex; flex-wrap: wrap; gap: 6px; }
.tag { background: rgba(255,255,255,0.1); padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; color: #cbd5e1; }
.desc-box h3 { font-size: 1rem; color: #e2e8f0; margin-bottom: 0.5rem; border-left: 3px solid #20ae7c; padding-left: 8px; }
.desc-box p { font-size: 0.9rem; color: #94a3b8; line-height: 1.5; margin-bottom: 2rem; }
.btn-book-large { width: 100%; padding: 1rem; background: #20ae7c; color: white; border: none; border-radius: 8px; font-size: 1rem; font-weight: 600; cursor: pointer; transition: all 0.2s; }
.btn-book-large:hover:not(:disabled) { background: #189e6e; transform: translateY(-2px); }
.btn-book-large:disabled { background: #334155; color: #64748b; cursor: not-allowed; }

/* 右侧：时间片网格样式 */
.slots-card {
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 16px;
  padding: 1.5rem;
  display: flex; flex-direction: column;
}
.slots-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
.slots-header h3 { margin: 0; color: #e2e8f0; font-size: 1.1rem; display: flex; align-items: center; gap: 8px; }
.date-picker { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); color: #fff; padding: 6px 12px; border-radius: 6px; outline: none; color-scheme: dark; cursor: pointer; }

.status-legend { display: flex; gap: 1.5rem; margin-bottom: 1.5rem; font-size: 0.9rem; color: #94a3b8; }
.legend-item { display: flex; align-items: center; gap: 6px; }
.dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
.dot.available { background: #10b981; box-shadow: 0 0 5px rgba(16, 185, 129, 0.5); }
.dot.booked { background: #ef4444; }
.dot.expired { background: #64748b; }

.slots-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); /* 自适应列宽 */
  gap: 1rem;
}

.time-slot {
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.03);
  border-radius: 8px;
  padding: 1rem 0.5rem;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  display: flex; flex-direction: column; gap: 4px;
}

.slot-time { font-size: 1rem; font-weight: 600; color: #f1f5f9; }
.slot-label { font-size: 0.8rem; font-weight: 500; }

/* 状态样式 */
.time-slot.status-0 { /* 可预约 */
  border-color: rgba(16, 185, 129, 0.3);
}
.time-slot.status-0:hover {
  background: rgba(16, 185, 129, 0.2);
  border-color: #10b981;
  transform: translateY(-2px);
}
.time-slot.status-0 .slot-label { color: #10b981; }

.time-slot.status-1 { /* 已订 */
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.2);
  cursor: not-allowed; opacity: 0.8;
}
.time-slot.status-1 .slot-time { color: #fca5a5; text-decoration: line-through; }
.time-slot.status-1 .slot-label { color: #ef4444; }

.time-slot.status-2 { /* 过期 */
  background: rgba(100, 116, 139, 0.1);
  border-color: rgba(100, 116, 139, 0.2);
  cursor: not-allowed; opacity: 0.6;
}
.time-slot.status-2 .slot-time { color: #94a3b8; }
.time-slot.status-2 .slot-label { color: #64748b; }

.no-slots { grid-column: 1 / -1; text-align: center; color: #64748b; padding: 2rem; }

/* 弹窗样式 (复用) */
.modal-overlay { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.6); backdrop-filter: blur(4px); z-index: 999; display: flex; align-items: center; justify-content: center; }
.modal-card { background: #1e293b; width: 400px; padding: 2rem; border-radius: 16px; border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 20px 25px rgba(0,0,0,0.3); }
.modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
.btn-close { background: none; border: none; color: #94a3b8; cursor: pointer; font-size: 1.2rem; }
.form-group { margin-bottom: 1rem; }
.form-group label { display: block; color: #cbd5e1; font-size: 0.9rem; margin-bottom: 0.5rem; }
.form-group input { width: 100%; padding: 0.8rem; background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; color: white; box-sizing: border-box; }
.form-group input:focus { border-color: #20ae7c; outline: none; }
.form-row { display: flex; gap: 1rem; }
.btn-primary-block { width: 100%; padding: 0.8rem; background: #20ae7c; color: white; border: none; border-radius: 8px; margin-top: 1rem; cursor: pointer; font-weight: 600; }
.btn-primary-block:hover { background: #189e6e; }
.btn-primary-block:disabled { opacity: 0.7; cursor: not-allowed; }

@media (max-width: 900px) { .content-wrapper { grid-template-columns: 1fr; } }
</style>
