<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import dayjs from 'dayjs';
import { getStatistics } from '@/apis/statistics';
import { getAdminReservationPage } from '@/apis/reservation';

const router = useRouter();

const loading = ref(true);
const stats = ref([
  { title: '会议室使用次数', value: 0, unit: '次', color: '#3b82f6', icon: 'fa-calendar-check' },
  { title: '故障反馈总数', value: 0, unit: '条', color: '#ef4444', icon: 'fa-triangle-exclamation' },
  { title: '会议室总数', value: 0, unit: '间', color: '#10b981', icon: 'fa-door-open' },
  { title: '累计使用时长', value: 0, unit: '分钟', color: '#f59e0b', icon: 'fa-clock' },
]);

const recentReservations = ref([]);
const pendingList = ref([]);

const initDashboard = async () => {
  loading.value = true;
  try {
    const resStats = await getStatistics();
    const statData = resStats.data;

    if (statData) {
      stats.value[0].value = statData.totalUsageCount || 0;
      stats.value[1].value = statData.totalFaultCount || 0;
      stats.value[2].value = statData.totalRoomCount || 0;
      stats.value[3].value = (statData.dailyData || []).reduce(
        (acc, cur) => acc + Number(cur.totalUsageMinutes || 0),
        0
      );
    }

    const resReservations = await getAdminReservationPage({ page: 1, pageSize: 20 });
    const reservationList = resReservations.data?.records || [];

    recentReservations.value = reservationList.slice(0, 6).map((item) => ({
      id: item.id,
      topic: item.meetingTopic || '未命名会议',
      date: dayjs(item.startTime).format('YYYY-MM-DD HH:mm'),
      status: item.status,
    }));

    pendingList.value = reservationList
      .filter((item) => item.status === 0)
      .slice(0, 5)
      .map((item) => ({
        id: item.id,
        content: `${item.meetingTopic || '未命名会议'} · 房间 #${item.roomId}`,
        time: dayjs(item.startTime).format('MM-DD HH:mm'),
      }));
  } catch (error) {
    console.error(error);
  } finally {
    loading.value = false;
  }
};

const navigateTo = (path) => {
  router.push(path);
};

const handleAudit = () => {
  router.push('/manager/reservations');
};

const getStatusBadge = (status) => {
  const map = {
    0: { text: '待审核', cls: 'warning' },
    1: { text: '已通过', cls: 'success' },
    '-1': { text: '已取消', cls: 'danger' },
    2: { text: '已结束', cls: 'gray' },
  };

  return map[status] || { text: '未知', cls: 'gray' };
};

onMounted(initDashboard);
</script>

<template>
  <div class="home-container">
    <div class="header-section">
      <div class="welcome-text">
        <h2>欢迎回来，管理员</h2>
        <p class="subtitle">这里是今天的运营概览</p>
      </div>
      <div class="date-badge">{{ dayjs().format('YYYY年MM月DD日 dddd') }}</div>
    </div>

    <div class="stats-grid">
      <div v-for="(item, index) in stats" :key="index" class="card stat-card">
        <div class="stat-icon" :style="{ background: item.color + '20', color: item.color }">
          <i class="fas" :class="item.icon"></i>
        </div>
        <div class="stat-info">
          <span class="stat-title">{{ item.title }}</span>
          <div class="stat-number">
            {{ item.value }} <span class="stat-unit">{{ item.unit }}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="main-content">
      <div class="card section-left">
        <div class="card-header">
          <h3><i class="fas fa-list-alt"></i> 最新预约动态</h3>
          <button class="btn-link" @click="navigateTo('/manager/reservations')">查看全部</button>
        </div>

        <div v-if="loading" class="text-center py-4">加载中...</div>

        <table v-else class="simple-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>会议主题</th>
              <th>日期</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="res in recentReservations" :key="res.id">
              <td>#{{ res.id }}</td>
              <td>{{ res.topic }}</td>
              <td>{{ res.date }}</td>
              <td>
                <span class="badge" :class="getStatusBadge(res.status).cls">
                  {{ getStatusBadge(res.status).text }}
                </span>
              </td>
            </tr>
            <tr v-if="recentReservations.length === 0">
              <td colspan="4" class="text-center text-gray">暂无数据</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="section-right">
        <div class="card todo-card">
          <div class="card-header">
            <h3><i class="fas fa-bell"></i> 待审核事项</h3>
          </div>
          <ul class="todo-list">
            <li v-for="todo in pendingList" :key="todo.id" class="todo-item">
              <div class="todo-content">
                <span class="tag audit">审核</span>
                <div class="todo-text">
                  <div class="todo-title">{{ todo.content }}</div>
                  <div class="todo-time">{{ todo.time }}</div>
                </div>
              </div>
              <button class="btn-mini" @click="handleAudit(todo.id)">去处理</button>
            </li>
            <li v-if="pendingList.length === 0" class="empty-todo">
              暂无待办事项
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home-container {
  padding: 24px;
  background-color: #f8fafc;
  min-height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  color: #334155;
}

.header-section {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 24px;
}

.header-section h2 {
  margin: 0;
  font-size: 1.5rem;
  color: #1e293b;
}

.subtitle {
  color: #64748b;
  margin: 4px 0 0;
  font-size: 0.95rem;
}

.date-badge {
  background: white;
  padding: 8px 16px;
  border-radius: 20px;
  color: #64748b;
  font-size: 0.9rem;
  font-weight: 500;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  border: 1px solid #e2e8f0;
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f1f5f9;
}

.card-header h3 {
  margin: 0;
  font-size: 1rem;
  color: #334155;
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-header i {
  color: #20ae7c;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 20px;
  margin-bottom: 24px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 0;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
}

.stat-title {
  color: #64748b;
  font-size: 0.85rem;
  font-weight: 500;
}

.stat-number {
  font-size: 1.5rem;
  font-weight: 700;
  color: #1e293b;
  line-height: 1.2;
}

.stat-unit {
  font-size: 0.85rem;
  color: #94a3b8;
  font-weight: normal;
  margin-left: 4px;
}

.main-content {
  display: flex;
  gap: 24px;
}

.section-left {
  flex: 2;
}

.section-right {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.simple-table {
  width: 100%;
  border-collapse: collapse;
}

.simple-table th {
  text-align: left;
  padding: 12px;
  color: #64748b;
  font-weight: 600;
  font-size: 0.85rem;
  background: #f8fafc;
  border-radius: 6px;
}

.simple-table td {
  padding: 12px;
  border-bottom: 1px solid #f1f5f9;
  font-size: 0.95rem;
}

.simple-table tr:last-child td {
  border-bottom: none;
}

.text-center {
  text-align: center;
}

.text-gray {
  color: #94a3b8;
}

.badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
}

.badge.success {
  background: #d1fae5;
  color: #059669;
}

.badge.warning {
  background: #fef3c7;
  color: #d97706;
}

.badge.danger {
  background: #fee2e2;
  color: #dc2626;
}

.badge.gray {
  background: #f1f5f9;
  color: #94a3b8;
}

.todo-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.todo-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px dashed #e2e8f0;
}

.todo-item:last-child {
  border-bottom: none;
}

.todo-content {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.todo-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.todo-title {
  font-size: 0.9rem;
  color: #334155;
}

.todo-time {
  font-size: 0.75rem;
  color: #94a3b8;
}

.tag.audit {
  background: #fef3c7;
  color: #d97706;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: 600;
  height: fit-content;
  margin-top: 2px;
}

.empty-todo {
  text-align: center;
  color: #94a3b8;
  padding: 20px;
  font-size: 0.9rem;
}

.btn-link {
  background: none;
  border: none;
  color: #20ae7c;
  cursor: pointer;
  font-size: 0.9rem;
}

.btn-link:hover {
  text-decoration: underline;
}

.btn-mini {
  padding: 4px 10px;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.8rem;
  color: #64748b;
  transition: all 0.2s;
}

.btn-mini:hover {
  border-color: #20ae7c;
  color: #20ae7c;
  background: #f0fdf4;
}

@media (max-width: 1024px) {
  .main-content {
    flex-direction: column;
  }
}
</style>
