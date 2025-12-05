<script setup>
import { ref, computed, onMounted } from 'vue';
import dayjs from 'dayjs';
import { getMyReservations, cancelReservation } from "@/apis/reservation";
import { getUserRoomPage } from "@/apis/room";
import { toast } from '@/utils/message'
import '@/styles/el-message.css' 

const allBookings = ref([]);
const loading = ref(false);
const pagination = ref({ current: 1, size: 6, total: 0 });
const roomDict = ref({});

const fetchRoomDict = async () => {
  try {
    const res = await getUserRoomPage({ page: 1, pageSize: 100 });
    if(res.data && res.data.records) {
      res.data.records.forEach(r => {
        roomDict.value[r.id] = `${r.roomCode} ${r.location || ''}`;
      });
    }
  } catch(e) {}
};

const fetchRecords = async () => {
  loading.value = true;
  try {
    const res = await getMyReservations();
    if (res.data) {
      const mapped = res.data.map(item => {
        const start = dayjs(item.startTime);
        const end = dayjs(item.endTime);
        let status = 'upcoming';
        if (item.status === -1) status = 'cancelled';
        else if (end.isBefore(dayjs())) status = 'finished';

        return {
          id: item.id,
          title: item.meetingTopic,
          room: roomDict.value[item.roomId] || `会议室 #${item.roomId}`,
          date: start.format('YYYY-MM-DD'),
          time: `${start.format('HH:mm')}-${end.format('HH:mm')}`,
          status
        };
      });
      mapped.sort((a, b) => dayjs(b.date).valueOf() - dayjs(a.date).valueOf());
      allBookings.value = mapped;
      pagination.value.total = mapped.length;
    }
  } catch (e) { console.error(e); } 
  finally { loading.value = false; }
};

const paginatedList = computed(() => {
  const start = (pagination.value.current - 1) * pagination.value.size;
  return allBookings.value.slice(start, start + pagination.value.size);
});

const changePage = (page) => pagination.value.current = page;

const handleCancel = async (id) => {
  if(!confirm('确定取消？')) return;
  try {
    await cancelReservation(id);
    toast.success('已取消');
    fetchRecords();
  } catch (e) { toast.error('取消失败'); }
};

const getBadge = (status) => {
  const map = {
    upcoming: { text: '即将开始', cls: 'badge-blue' },
    finished: { text: '已结束', cls: 'badge-gray' },
    cancelled: { text: '已取消', cls: 'badge-red' },
    pending: { text: '审核中', cls: 'badge-orange' }
  };
  return map[status] || { text: status, cls: '' };
};

onMounted(async () => {
  await fetchRoomDict();
  await fetchRecords();
});
</script>

<template>
  <div class="h-full flex flex-col">
    <div v-if="loading" class="text-center py-4"><i class="fa-solid fa-spinner fa-spin"></i> 加载中...</div>
    <div v-else class="flex-1">
      <table class="data-table">
        <thead>
          <tr>
            <th>会议主题</th><th>会议室</th><th>时间</th><th>状态</th><th class="text-right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in paginatedList" :key="item.id">
            <td class="font-bold">{{ item.title }}</td>
            <td>{{ item.room }}</td>
            <td class="text-sm text-gray-400"><div>{{ item.date }}</div><div>{{ item.time }}</div></td>
            <td><span class="badge" :class="getBadge(item.status).cls">{{ getBadge(item.status).text }}</span></td>
            <td class="actions">
              <button v-if="item.status === 'upcoming'" class="btn-text text-red" title="取消" @click="handleCancel(item.id)">
                <i class="fa-solid fa-ban"></i>
              </button>
            </td>
          </tr>
          <tr v-if="paginatedList.length === 0"><td colspan="5" class="text-center py-8">暂无记录</td></tr>
        </tbody>
      </table>
    </div>
    
    <!-- 分页 -->
    <div class="pagination-bar" v-if="pagination.total > 0">
      <span class="page-info">共 {{ pagination.total }} 条</span>
      <div class="page-controls">
        <button class="btn-page" :disabled="pagination.current === 1" @click="changePage(pagination.current - 1)">
          <i class="fa-solid fa-chevron-left"></i>
        </button>
        <span class="current-page">{{ pagination.current }} / {{ Math.ceil(pagination.total/pagination.size)||1 }}</span>
        <button class="btn-page" :disabled="pagination.current * pagination.size >= pagination.total" @click="changePage(pagination.current + 1)">
          <i class="fa-solid fa-chevron-right"></i>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* --- 通用辅助类 --- */
.h-full { height: 100%; }
.flex { display: flex; }
.flex-col { flex-direction: column; }
.flex-1 { flex: 1; }
.text-center { text-align: center; }
.text-right { text-align: right; }
.py-4 { padding-top: 1rem; padding-bottom: 1rem; }
.py-8 { padding-top: 2rem; padding-bottom: 2rem; }
.font-bold { font-weight: 700; }
.text-sm { font-size: 0.875rem; }
.text-gray-400 { color: #94a3b8; }

/* --- 表格样式 --- */
.data-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
}
.data-table th { 
  text-align: left; padding: 1rem; 
  border-bottom: 1px solid rgba(255, 255, 255, 0.1); 
  color: #94a3b8; font-size: 0.9rem; 
}
.data-table td { 
  padding: 1.2rem 1rem; 
  border-bottom: 1px solid rgba(255, 255, 255, 0.05); 
  color: #e2e8f0; 
}

/* --- 状态徽章 --- */
.badge { padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
.badge-blue { background: rgba(37, 99, 235, 0.15); color: #60a5fa; }
.badge-gray { background: rgba(148, 163, 184, 0.15); color: #94a3b8; }
.badge-orange { background: rgba(249, 115, 22, 0.15); color: #fb923c; }
.badge-red { background: rgba(239, 68, 68, 0.15); color: #f87171; }

/* --- 操作按钮 --- */
.actions { text-align: right; }
.btn-text { 
  background: none; border: none; cursor: pointer; font-size: 1.1rem; 
  margin-left: 0.8rem; padding: 4px; border-radius: 4px; transition: background 0.2s; 
}
.btn-text:hover { background: rgba(255, 255, 255, 0.1); }
.text-blue { color: #60a5fa; }
.text-red { color: #f87171; }
.text-gray { color: #94a3b8; }

/* --- 分页条 --- */
.pagination-bar {
  display: flex; justify-content: space-between; align-items: center;
  padding-top: 1.5rem; margin-top: auto; border-top: 1px solid rgba(255, 255, 255, 0.1);
}
.page-info { font-size: 0.85rem; color: #94a3b8; }
.page-controls { display: flex; align-items: center; gap: 1rem; }
.btn-page {
  width: 32px; height: 32px; display: flex; align-items: center; justify-content: center;
  border-radius: 6px; border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05); color: #fff; cursor: pointer;
}
.btn-page:hover:not(:disabled) { background: #2563eb; border-color: #2563eb; }
.btn-page:disabled { opacity: 0.5; cursor: not-allowed; background: transparent; }
.current-page { font-weight: 600; color: #fff; font-size: 0.9rem; min-width: 40px; text-align: center; }
</style>