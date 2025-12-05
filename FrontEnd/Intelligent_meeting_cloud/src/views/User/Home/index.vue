<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue';
import { useUserStore } from '@/stores/userStore';
import dayjs from 'dayjs';
import 'dayjs/locale/zh-cn';
import qrCodeImg from '@/assets/imgs/qr.png'; 

dayjs.locale('zh-cn');

const userStore = useUserStore();
const userInfo = userStore.userInfo || { username: 'Admin', role: '研发部' };

const now = ref(new Date());
let timer = null;

const timeData = computed(() => ({
  time: dayjs(now.value).format('HH:mm'),
  date: dayjs(now.value).format('MM月DD日'),
  weekday: dayjs(now.value).format('dddd')
}));

const greeting = computed(() => {
  const h = now.value.getHours();
  return h >= 5 && h < 12 ? '上午好' : (h >= 18 || h < 5) ? '晚上好' : '下午好';
});

const nextMeeting = ref({
  title: 'Q4 产品迭代复盘会',
  room: '305 会议室',
  timeRange: '14:30 - 16:00',
  host: '张总',
  minutesLeft: 15, 
  status: 'upcoming'
});

const notices = ref([
  { id: 1, type: 'urgent', icon: 'fa-fire-extinguisher', title: '消防演习通知', date: '10:00', content: '下午14:00进行全员演习，请走楼梯。' },
  { id: 2, type: 'maintenance', icon: 'fa-screwdriver-wrench', title: '设备维护', date: '昨天', content: '305会议室投影仪维修中，暂不可用。' },
  { id: 3, type: 'info', icon: 'fa-file-lines', title: '新规发布', date: '11-20', content: '《会议室使用规范 v2.0》已更新。' },
  { id: 4, type: 'info', icon: 'fa-snowflake', title: '行政通知', date: '11-15', content: '气温骤降，空调已开启制热模式。' },
]);

// --- 公告弹窗逻辑 ---
const showNoticeModal = ref(false);
const openNotices = () => showNoticeModal.value = true;
const closeNotices = () => showNoticeModal.value = false;

// --- 签到二维码弹窗逻辑 ---
const showQrModal = ref(false);
const openCheckIn = () => showQrModal.value = true;
const closeCheckIn = () => showQrModal.value = false;

onMounted(() => {
  timer = setInterval(() => { now.value = new Date() }, 1000);
});
onUnmounted(() => {
  if (timer) clearInterval(timer);
});
</script>

<template>
  <div class="home-container">
    <header class="home-header">
      <div>
        <h2 class="welcome-text">
          {{ greeting }}，{{ userInfo.username }} <span class="wave-hand">👋</span>
        </h2>
        <p class="sub-text">
          <i class="fa-solid fa-location-arrow"></i> {{ userInfo.role }} · 祝你工作愉快
        </p>
      </div>
      <div class="header-time">
        <span class="big-clock">{{ timeData.time }}</span>
        <span class="date-info">{{ timeData.date }} {{ timeData.weekday }}</span>
      </div>
    </header>

    <div class="dashboard-content">

      <section class="left-section">
        <div class="card status-card">
          <div class="card-header">
            <h3><i class="fa-solid fa-hourglass-half"></i> 下一场会议</h3>
            <span v-if="nextMeeting" class="tag-status">即将开始</span>
          </div>

          <div v-if="nextMeeting" class="meeting-details">
            <h1 class="meeting-title">{{ nextMeeting.title }}</h1>
            
            <div class="meeting-meta">
              <div class="meta-item">
                <i class="fa-solid fa-clock"></i>
                <span>{{ nextMeeting.timeRange }}</span>
              </div>
              <div class="meta-item">
                <i class="fa-solid fa-map-location-dot"></i>
                <span>{{ nextMeeting.room }}</span>
              </div>
              <div class="meta-item">
                <i class="fa-solid fa-user-tie"></i>
                <span>主持人：{{ nextMeeting.host }}</span>
              </div>
            </div>

            <div class="action-area">
              <button class="btn-checkin" @click="openCheckIn">
                <i class="fa-solid fa-qrcode"></i> 立即签到
              </button>
            </div>
          </div>

          <div v-else class="empty-state">
            <i class="fa-solid fa-mug-hot"></i>
            <p>今天暂时没有会议安排</p>
            <span class="sub-empty">去左侧导航栏预约一个吧</span>
          </div>
        </div>
      </section>

      <!-- 右侧：公告通知 -->
      <section class="right-section">
        <div class="card notice-card">
          <div class="card-header border-b">
            <h3><i class="fa-solid fa-bullhorn" style="color: #fb923c;"></i> 公告栏</h3>
            <span class="more-link" @click="openNotices">全部 <i class="fa-solid fa-angle-right"></i></span>
          </div>
          
          <div class="notice-list-wrapper">
            <ul class="notice-list">
              <li v-for="item in notices.slice(0, 5)" :key="item.id" class="notice-item">
                <div class="notice-icon" :class="item.type">
                  <i class="fa-solid" :class="item.icon"></i>
                </div>
                <div class="notice-info">
                  <div class="notice-top">
                    <span class="notice-title">{{ item.title }}</span>
                    <span class="notice-time">{{ item.date }}</span>
                  </div>
                  <p class="notice-desc">{{ item.content }}</p>
                </div>
              </li>
            </ul>
          </div>
        </div>
      </section>

    </div>

    <!-- 弹窗容器 -->
    <Teleport to="body">
      
      <!-- 公告弹窗 -->
      <Transition name="fade">
        <div v-if="showNoticeModal" class="modal-overlay" @click.self="closeNotices">
          <div class="modal-container">
            <div class="modal-header">
              <h3><i class="fa-solid fa-bullhorn"></i> 公告中心</h3>
              <button class="close-btn" @click="closeNotices">
                <i class="fa-solid fa-xmark"></i>
              </button>
            </div>
            
            <div class="modal-body custom-scrollbar">
              <div v-for="item in notices" :key="item.id" class="modal-notice-item">
                <div class="modal-notice-left">
                  <div class="notice-icon" :class="item.type">
                    <i class="fa-solid" :class="item.icon"></i>
                  </div>
                </div>
                <div class="modal-notice-content">
                   <div class="modal-notice-head">
                     <span class="modal-title">{{ item.title }}</span>
                     <span class="tag-type" :class="item.type">
                        {{ item.type === 'urgent' ? '紧急' : item.type === 'maintenance' ? '维护' : '通知' }}
                     </span>
                     <span class="modal-time">{{ item.date }}</span>
                   </div>
                   <p class="modal-text">{{ item.content }}</p>
                </div>
              </div>
            </div>

            <div class="modal-footer">
              <span>共 {{ notices.length }} 条公告</span>
            </div>
          </div>
        </div>
      </Transition>

      <!-- 二维码签到弹窗 -->
      <Transition name="zoom">
        <div v-if="showQrModal" class="modal-overlay" @click.self="closeCheckIn">
          <div class="qr-modal-card">
            <button class="qr-close-btn" @click="closeCheckIn">
              <i class="fa-solid fa-xmark"></i>
            </button>
            <h3 class="qr-title">扫码签到</h3>
            <p class="qr-desc">请使用手机扫描下方二维码完成会议签到</p>
            
            <div class="qr-box">
              <img :src="qrCodeImg" alt="Check-in QR Code" class="qr-img" />
              <!-- 扫描线动画 -->
              <div class="scan-line"></div>
            </div>
            
            <div class="qr-footer">
              <i class="fa-solid fa-rotate-right"></i> 二维码每 60 秒自动刷新
            </div>
          </div>
        </div>
      </Transition>

    </Teleport>

  </div>
</template>

<style scoped>

:root {
  --bg-dark: #1e293b;       
  --bg-hover: #334155;      
  --text-primary: #f8fafc;  
  --text-secondary: #94a3b8;
  --accent-color: #0f766e;  
  --border-color: #334155;
}

* { user-select: none; }

.home-container { width: 100%; height: 100%; padding: 1.5rem; box-sizing: border-box; color: #fff; display: flex; flex-direction: column; gap: 2rem; }
.home-header { display: flex; justify-content: space-between; align-items: flex-end; }
.welcome-text { font-size: 1.8rem; font-weight: 700; margin: 0; color: #f1f5f9; }
.wave-hand { display: inline-block; animation: wave 2s infinite; transform-origin: 70% 70%; }
.sub-text { color: #94a3b8; margin-top: 0.5rem; font-size: 0.9rem; }
.header-time { text-align: right; display: flex; flex-direction: column; }
.big-clock { font-size: 2.5rem; font-weight: 700; font-family: monospace; line-height: 1; color: #f1f5f9; }
.date-info { color: #94a3b8; font-size: 0.9rem; margin-top: 4px; }
.dashboard-content { flex: 1; display: grid; grid-template-columns: 3fr 2fr; gap: 1.5rem; min-height: 0; }
.card { min-height: 500px; max-height: 500px; background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; backdrop-filter: blur(10px); display: flex; flex-direction: column; height: 100%; overflow: hidden; }
.card-header { padding: 1.25rem; display: flex; justify-content: space-between; align-items: center; }
.card-header h3 { margin: 0; font-size: 1.1rem; display: flex; align-items: center; gap: 8px; color: #e2e8f0; }
.border-b { border-bottom: 1px solid rgba(255, 255, 255, 0.05); }
.meeting-details { padding: 0 2rem 2rem 2rem; display: flex; flex-direction: column; justify-content: center; flex: 1; }
.tag-status { background: rgba(45, 212, 191, 0.15); color: #2dd4bf; padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
.meeting-title { font-size: 2rem; margin: 0 0 1.5rem 0; line-height: 1.2; }
.meeting-meta { display: flex; gap: 2rem; margin-bottom: 2rem; flex-wrap: wrap; }
.meta-item { display: flex; align-items: center; gap: 8px; color: #94a3b8; font-size: 0.95rem; }
.meta-item i { color: #2dd4bf; }
.btn-checkin { background: linear-gradient(135deg, #0f766e 0%, #115e59 100%); color: white; border: none; padding: 12px 32px; border-radius: 8px; font-size: 1rem; cursor: pointer; transition: all 0.2s; display: inline-flex; align-items: center; gap: 8px; box-shadow: 0 4px 12px rgba(15, 118, 110, 0.3); }
.btn-checkin:hover { transform: translateY(-2px); box-shadow: 0 6px 16px rgba(15, 118, 110, 0.4); }
.empty-state { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #64748b; gap: 1rem; }
.empty-state i { font-size: 3rem; opacity: 0.5; }
.sub-empty { font-size: 0.8rem; opacity: 0.7; }
.more-link { font-size: 0.8rem; color: #64748b; cursor: pointer; }
.more-link:hover { color: #fff; }
.notice-list-wrapper { flex: 1; overflow-y: auto; padding: 0 1rem 1rem 1rem; }
.notice-list { list-style: none; padding: 0; margin: 0; }
.notice-item { display: flex; gap: 1rem; padding: 1rem; border-radius: 12px; transition: background 0.2s; cursor: pointer; border-bottom: 1px solid rgba(255,255,255,0.03); }
.notice-item:hover { background: rgba(255, 255, 255, 0.1); }
.notice-item:last-child { border-bottom: none; }
.notice-icon { width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.notice-icon.urgent { background: rgba(239, 68, 68, 0.15); color: #ef4444; }
.notice-icon.maintenance { background: rgba(249, 115, 22, 0.15); color: #f97316; }
.notice-icon.info { background: rgba(59, 130, 246, 0.15); color: #3b82f6; }
.notice-info { flex: 1; min-width: 0; }
.notice-top { display: flex; justify-content: space-between; margin-bottom: 4px; }
.notice-title { font-weight: 600; font-size: 0.95rem; color: #e2e8f0; }
.notice-time { font-size: 0.75rem; color: #64748b; }
.notice-desc { margin: 0; font-size: 0.85rem; color: #94a3b8; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.custom-scrollbar::-webkit-scrollbar { width: 6px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.15); border-radius: 3px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.3); cursor: pointer; }

/* 公告弹窗样式 */
.modal-overlay { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0, 0, 0, 0.7); backdrop-filter: blur(5px); z-index: 9999; display: flex; justify-content: center; align-items: center; }
.modal-container { background: #1e293b; width: 90%; max-width: 700px; height: 80vh; border-radius: 16px; border: 1px solid rgba(255, 255, 255, 0.1); box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5); display: flex; flex-direction: column; overflow: hidden; }
.modal-header { padding: 1.5rem; border-bottom: 1px solid rgba(255, 255, 255, 0.1); display: flex; justify-content: space-between; align-items: center; background: rgba(30, 41, 59, 0.9); }
.modal-header h3 { margin: 0; color: #f1f5f9; display: flex; align-items: center; gap: 10px; }
.close-btn { background: transparent; border: none; color: #94a3b8; font-size: 1.2rem; cursor: pointer; padding: 5px; transition: color 0.2s; }
.close-btn:hover { color: #fff; }
.modal-body { flex: 1; padding: 1.5rem; overflow-y: auto; }
.modal-notice-item { display: flex; gap: 1.2rem; padding: 1.25rem; border-bottom: 1px solid rgba(255, 255, 255, 0.05); transition: background 0.2s; }
.modal-notice-item:last-child { border-bottom: none; }
.modal-notice-item:hover { background: rgba(255, 255, 255, 0.03); }
.modal-notice-left { flex-shrink: 0; }
.modal-notice-content { flex: 1; }
.modal-notice-head { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; flex-wrap: wrap; }
.modal-title { font-size: 1.1rem; font-weight: 600; color: #f1f5f9; }
.tag-type { font-size: 0.75rem; padding: 2px 8px; border-radius: 4px; font-weight: 500; }
.tag-type.urgent { background: rgba(239, 68, 68, 0.15); color: #ef4444; }
.tag-type.maintenance { background: rgba(249, 115, 22, 0.15); color: #f97316; }
.tag-type.info { background: rgba(59, 130, 246, 0.15); color: #3b82f6; }
.modal-time { margin-left: auto; font-size: 0.85rem; color: #64748b; }
.modal-text { margin: 0; color: #cbd5e1; line-height: 1.6; font-size: 0.95rem; }
.modal-footer { padding: 1rem 1.5rem; border-top: 1px solid rgba(255, 255, 255, 0.1); text-align: right; color: #64748b; font-size: 0.85rem; background: rgba(30, 41, 59, 0.9); }

.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

@keyframes wave { 0%, 100% { transform: rotate(0deg); } 25% { transform: rotate(20deg); } 75% { transform: rotate(-15deg); } }

/* --- 二维码弹窗样式 --- */
.qr-modal-card {
  background: white;
  width: 340px;
  border-radius: 20px;
  padding: 2.5rem 2rem;
  text-align: center;
  position: relative;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
  animation: zoomIn 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.qr-close-btn {
  position: absolute;
  top: 15px;
  right: 15px;
  background: #f1f5f9;
  border: none;
  width: 32px; height: 32px;
  border-radius: 50%;
  color: #64748b;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.2s;
}
.qr-close-btn:hover { background: #e2e8f0; color: #334155; }

.qr-title {
  color: #1e293b;
  font-size: 1.5rem;
  margin: 0 0 0.5rem 0;
}
.qr-desc {
  color: #64748b;
  font-size: 0.9rem;
  margin: 0 0 1.5rem 0;
}

.qr-box {
  width: 220px;
  height: 220px;
  margin: 0 auto 1.5rem auto;
  position: relative;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 10px;
  overflow: hidden;
}

.qr-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

/* 扫描线动画 */
.scan-line {
  position: absolute;
  top: 0; left: 0; width: 100%; height: 2px;
  background: #0f766e;
  box-shadow: 0 0 4px #0f766e;
  animation: scan 2s linear infinite;
}

.qr-footer {
  color: #94a3b8;
  font-size: 0.8rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}
.qr-footer i { animation: spin 4s linear infinite; }

@keyframes scan {
  0% { top: 0; opacity: 0; }
  10% { opacity: 1; }
  90% { opacity: 1; }
  100% { top: 100%; opacity: 0; }
}
@keyframes spin { 100% { transform: rotate(360deg); } }
@keyframes zoomIn {
  from { transform: scale(0.8); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}

/* Zoom Transition */
.zoom-enter-active, .zoom-leave-active { transition: all 0.2s ease; }
.zoom-enter-from, .zoom-leave-to { opacity: 0; transform: scale(0.9); }
</style>