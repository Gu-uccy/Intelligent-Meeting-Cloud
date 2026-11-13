<script setup>
import { ref, watch, onMounted } from 'vue';
import dayjs from 'dayjs';
import { getUserRoomPage } from "@/apis/room";
import { addReservation } from "@/apis/reservation";
import { toast } from '@/utils/message'
import '@/styles/el-message.css' 
import roomImg from "@/assets/imgs/room.png";
import RoomDetailPanel from './RoomDetail.vue';

const searchQuery = ref('');
const searchDate = ref(dayjs().format('YYYY-MM-DD'));
const roomList = ref([]);
const loadingRooms = ref(false);
const showModal = ref(false);
const selectedRoom = ref(null);
const pagination = ref({ current: 1, size: 4, total: 0 });
const bookingForm = ref({ title: '', date: '', startTime: '', endTime: '', desc: '' });
const submitting = ref(false);
const showDetail = ref(false);
const detailRoomId = ref(null);

const fetchRooms = async () => {
  loadingRooms.value = true;
  try {
    const res = await getUserRoomPage({
      page: pagination.value.current,
      pageSize: pagination.value.size,
      roomCode: searchQuery.value || undefined
    });
    if (res.data && res.data.records) {
      roomList.value = res.data.records.map(item => ({
        id: item.id,
        name: `${item.roomCode} ${item.location || ''}`,
        capacity: item.capacity,
        tags: item.equipment ? item.equipment.split(',') : [],
        image: item.image || roomImg,
        status: item.isActive ? 'available' : 'maintenance'
      }));
      pagination.value.total = Number(res.data.total);
    }
  } catch (e) { console.error(e); } 
  finally { loadingRooms.value = false; }
};

const changePage = (page) => {
  pagination.value.current = page;
  fetchRooms();
};

const submitBooking = async () => {
  if(!bookingForm.value.title || !bookingForm.value.startTime || !bookingForm.value.endTime) {
    return toast.warning('请填写完整信息');
  }
  if (bookingForm.value.startTime >= bookingForm.value.endTime) {
    return toast.warning('结束时间必须晚于开始时间');
  }
  const payload = {
    roomId: selectedRoom.value.id,
    meetingTopic: bookingForm.value.title,
    startTime: `${bookingForm.value.date} ${bookingForm.value.startTime}:00`,
    endTime: `${bookingForm.value.date} ${bookingForm.value.endTime}:00`,
    remark: bookingForm.value.desc,
    participantNum: selectedRoom.value.capacity
  };
  try {
    submitting.value = true;
    const res = await addReservation(payload);
    console.log("res =", res);
    if (res.code === 0) {
      toast.error('预约失败：' + (res.msg || '系统错误'));
      return;
    }
    toast.success('预约申请已提交，等待管理员审核');
    showModal.value = false;
  } catch (e) {
    console.log("ERROR =>", e);
    toast.error('预约失败：' + (e.message || '系统错误'));
  }finally {
    submitting.value = false;
  }
};

const goToDetail = (id) => {
  detailRoomId.value = id;
  showDetail.value = true;
}
const backToList = () => {
  showDetail.value = false;
  detailRoomId.value = null;
  fetchRooms();
}

watch(searchQuery, () => { pagination.value.current = 1; fetchRooms(); });
onMounted(fetchRooms);
</script>

<template>
  <div class="h-full">
    
    <!-- 模式 1: 会议室列表 -->
    <div v-if="!showDetail" class="flex flex-col h-full">
      <!-- 搜索栏 -->
      <div class="filter-bar">
        <div class="search-input">
          <i class="fa-solid fa-magnifying-glass"></i>
          <input type="text" v-model="searchQuery" placeholder="搜索会议室名称..." />
        </div>
        <div class="date-picker-wrapper">
          <i class="fa-regular fa-calendar icon-date"></i>
          <input type="date" class="real-date-input" v-model="searchDate" />
        </div>
      </div>

      <!-- 列表内容 -->
      <div v-if="loadingRooms" class="text-center text-gray-400 py-4 flex-1">
        <i class="fa-solid fa-spinner fa-spin"></i> 加载中...
      </div>
      <div v-else class="flex-1">
        <div class="rooms-grid">
          <div v-for="room in roomList" :key="room.id" class="room-card group">
            <div class="room-img-box" @click="goToDetail(room.id)">
              <img :src="room.image" alt="Meeting Room" />
              <div class="status-overlay" :class="room.status === 'available' ? 'bg-green' : 'bg-red'">
                {{ room.status === 'available' ? '空闲' : '维护中' }}
              </div>
              <div class="hover-overlay">
                <span>查看详情</span>
              </div>
            </div>
            
            <div class="room-info">
              <div class="flex justify-between items-start">
                <h3 class="font-bold text-lg text-white">{{ room.name }}</h3>
                <span class="text-sm text-gray-400">{{ room.capacity }}人</span>
              </div>
              <div class="tags">
                <span v-for="tag in room.tags" :key="tag" class="tag">{{ tag }}</span>
              </div>
              
              <!-- 按钮 -->
              <button 
                class="btn-book" 
                :disabled="room.status !== 'available'" 
                @click="goToDetail(room.id)"
              >
                {{ room.status === 'available' ? '立即预约' : '维护中' }}
              </button>
            </div>
          </div>
        </div>
        
        <div v-if="roomList.length === 0" class="no-results">
          <i class="fa-solid fa-inbox"></i> <p>未找到匹配的会议室</p>
        </div>
      </div>

      <!-- 分页 -->
      <div class="pagination-bar" v-if="pagination.total > 0">
        <span class="page-info">共 {{ pagination.total }} 个会议室</span>
        <div class="page-controls">
          <button class="btn-page" :disabled="pagination.current === 1" @click="changePage(pagination.current - 1)">
            <i class="fa-solid fa-chevron-left"></i>
          </button>
          <span class="current-page">{{ pagination.current }}</span>
          <button class="btn-page" :disabled="pagination.current * pagination.size >= pagination.total" @click="changePage(pagination.current + 1)">
            <i class="fa-solid fa-chevron-right"></i>
          </button>
        </div>
      </div>

      <!-- 列表页的快速预约弹窗 (Teleport) -->
      <Teleport to="body">
        <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
          <div class="modal-card">
            <div class="modal-header">
              <h3 class="text-white">预约 {{ selectedRoom?.name }}</h3>
              <button @click="showModal = false" class="btn-close"><i class="fa-solid fa-xmark"></i></button>
            </div>
            <div class="modal-body">
              <div class="form-group"><label>主题</label><input type="text" v-model="bookingForm.title" placeholder="例如：Q4 产品研讨会"></div>
              <div class="form-group"><label>日期</label><input type="date" v-model="bookingForm.date"></div>
              <div class="form-row">
                <div class="form-group"><label>开始</label><input type="time" v-model="bookingForm.startTime"></div>
                <div class="form-group"><label>结束</label><input type="time" v-model="bookingForm.endTime"></div>
              </div>
              <div class="form-group"><label>备注</label><input type="text" v-model="bookingForm.desc" placeholder="需求..."></div>
              <button class="btn-primary-block" @click="submitBooking">提交预约申请</button>
            </div>
          </div>
        </div>
      </Teleport>
    </div>

    <!-- 模式 2: 详情详情组件 -->
    <RoomDetailPanel 
      v-else 
      :room-id="detailRoomId" 
      @back="backToList" 
    />

  </div>
</template>

<style scoped>
/* --- 通用辅助类 --- */
.h-full { height: 100%; }
.flex { display: flex; }
.flex-col { flex-direction: column; }
.flex-1 { flex: 1; }
.text-center { text-align: center; }
.text-gray-400 { color: #94a3b8; }
.text-white { color: #fff; }
.truncate { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.shrink-0 { flex-shrink: 0; }
.cursor-pointer { cursor: pointer; }
.py-4 { padding-top: 1rem; padding-bottom: 1rem; }

/* 搜索栏 */
.filter-bar { display: flex; justify-content: space-between; margin-bottom: 1.5rem; }
.search-input { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); padding: 0 1rem; border-radius: 8px; display: flex; align-items: center; gap: 10px; color: #94a3b8; width: 300px; height: 42px; }
.search-input input { border: none; background: transparent; outline: none; width: 100%; color: #fff; height: 100%; font-size: 0.95rem; }
.date-picker-wrapper { position: relative; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; display: flex; align-items: center; width: 180px; height: 42px; overflow: hidden; }
.icon-date { position: absolute; left: 1rem; color: #94a3b8; pointer-events: none; z-index: 1; }
.real-date-input { border: none; background: transparent; outline: none; width: 100%; height: 100%; padding-left: 2.5rem; padding-right: 1rem; color: #fff; cursor: pointer; color-scheme: dark; }

/* 卡片网格 */
.rooms-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 2rem; }
.room-card { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05); border-radius: 12px; overflow: hidden; transition: transform 0.2s, box-shadow 0.2s; }
.room-card:hover { transform: translateY(-4px); box-shadow: 0 10px 15px -3px rgba(0,0,0,0.3); background: rgba(255,255,255,0.05); }

.room-img-box { height: 160px; background: #1e293b; position: relative; display: flex; align-items: center; justify-content: center; overflow: hidden; }
.room-img-box img { width: 100%; height: 100%; object-fit: cover; transition: transform 0.3s; }
.room-card:hover .room-img-box img { transform: scale(1.05); }

/* 图片悬停效果 */
.hover-overlay {
  position: absolute; top: 0; left: 0; width: 100%; height: 100%;
  background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center;
  opacity: 0; transition: opacity 0.3s;
}
.room-img-box:hover .hover-overlay { opacity: 1; }
.hover-overlay span { border: 1px solid white; color: white; padding: 6px 12px; border-radius: 20px; font-size: 0.85rem; }

.status-overlay { position: absolute; top: 10px; right: 10px; color: white; padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; backdrop-filter: blur(4px); }
.bg-green { background: rgba(16, 185, 129, 0.9); }
.bg-red { background: rgba(239, 68, 68, 0.9); }

.room-info { padding: 1.5rem; }
.tags { margin: 0.8rem 0; display: flex; gap: 6px; flex-wrap: wrap; height: 24px; overflow: hidden; } /* 限制标签高度防止抖动 */
.tag { background: rgba(255,255,255,0.1); color: #cbd5e1; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; }

.btn-book {
  width: 100%; padding: 0.75rem;
  background: rgba(32, 174, 124, 0.1); 
  color: #20ae7c;
  border: 1px solid rgba(32, 174, 124, 0.2); 
  border-radius: 8px; 
  cursor: pointer; 
  font-weight: 600; 
  margin-top: 0.5rem; 
  transition: all 0.3s;
}
.btn-book:hover:not(:disabled) { background: #20ae7c; color: white; }
.btn-book:disabled { background: rgba(255,255,255,0.05); color: #64748b; border-color: transparent; cursor: not-allowed; }

.no-results { grid-column: 1 / -1; text-align: center; padding: 3rem; color: #94a3b8; }
.no-results i { font-size: 3rem; margin-bottom: 1rem; opacity: 0.5; }

.pagination-bar { display: flex; justify-content: space-between; align-items: center; padding-top: 1.5rem; margin-top: auto; border-top: 1px solid rgba(255,255,255,0.1); }
.page-info { font-size: 0.85rem; color: #94a3b8; }
.page-controls { display: flex; align-items: center; gap: 1rem; }
.btn-page { width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; border-radius: 6px; border: 1px solid rgba(255,255,255,0.1); background: rgba(255,255,255,0.05); color: #fff; cursor: pointer; }
.btn-page:hover:not(:disabled) { background: #20ae7c; border-color: #20ae7c; }
.btn-page:disabled { opacity: 0.5; cursor: not-allowed; background: transparent; }
.current-page { font-weight: 600; color: #fff; font-size: 0.9rem; min-width: 40px; text-align: center; }
</style>
