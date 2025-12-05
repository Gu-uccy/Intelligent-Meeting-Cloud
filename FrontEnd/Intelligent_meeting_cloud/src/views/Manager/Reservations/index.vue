<script setup>
import { ref, reactive, onMounted } from 'vue'
import dayjs from 'dayjs'
import ModalDialog from '@/components/ModalDialog.vue'
import { toast } from "@/utils/message";

// API 引入
import { 
  getAdminReservationPage, 
  addReservation, 
  updateReservation, 
  cancelReservation 
} from '@/apis/reservation'
import { getAdminRoomPage } from '@/apis/room'
import { getUserPage } from '@/apis/user-manage' 
import { auditReservation } from '@/apis/reservation'

// --- 状态定义 ---
const loading = ref(false)
const list = ref([])
const pagination = reactive({
  current: 1,
  size: 10,
  total: 0
})

const searchQuery = ref('')

// 字典映射 (ID -> Name)
const roomDict = ref({})
const userDict = ref({})
// 下拉框选项
const roomOptions = ref([])
const userOptions = ref([])

// 弹窗表单状态
const dialog = ref(false)
const isEdit = ref(false)
const editId = ref(null)

const form = reactive({
  userId: '',
  roomId: '',
  meetingTopic: '',
  startTime: '',
  endTime: ''
})

const initDicts = async () => {
  // 1. 获取所有房间
  try {
    const roomRes = await getAdminRoomPage({ page: 1, pageSize: 10 });
    if(roomRes.data?.records) {
      roomOptions.value = roomRes.data.records.map(r => ({ id: r.id, name: r.roomCode }));
      roomRes.data.records.forEach(r => roomDict.value[r.id] = r.roomCode);
    }
  } catch(e) {
    toast.error('加载会议室列表失败');
  }

  // 2. 获取所有用户
  try {
    const userRes = await getUserPage({ page: 1, pageSize: 10 });
    if(userRes.data?.records) {
      userOptions.value = userRes.data.records.map(u => ({ id: u.id, name: u.username }));
      userRes.data.records.forEach(u => userDict.value[u.id] = u.username);
    }
  } catch(e) {
    toast.error('加载用户列表失败');
  }
}

// --- 核心方法：获取预订列表 ---
const fetchData = async () => {
  loading.value = true
  try {
    const res = await getAdminReservationPage({
      page: pagination.current,
      pageSize: pagination.size,
      reservationNo: searchQuery.value || undefined
    })
    
    if (res.data?.records) {
      list.value = res.data.records
      pagination.total = Number(res.data.total)
    } else {
      list.value = []
      pagination.total = 0
    }
  } catch (error) {
    console.error('加载失败', error)
    toast.error('加载预订列表失败');
  } finally {
    loading.value = false
  }
}

// 分页切换
const handlePageChange = (newPage) => {
  pagination.current = newPage
  fetchData()
}

// --- 表单操作 ---
const openAdd = () => {
  isEdit.value = false
  editId.value = null
  // 重置表单
  Object.assign(form, { userId: '', roomId: '', meetingTopic: '', startTime: '', endTime: '' })
  dialog.value = true
}

const openEdit = (row) => {
  isEdit.value = true
  editId.value = row.id
  // 填充表单 (注意时间格式转换：后端 "2023-01-01 12:00:00" -> input "2023-01-01T12:00")
  Object.assign(form, {
    userId: row.userId,
    roomId: row.roomId,
    meetingTopic: row.meetingTopic,
    startTime: row.startTime ? row.startTime.replace(' ', 'T').slice(0, 16) : '',
    endTime: row.endTime ? row.endTime.replace(' ', 'T').slice(0, 16) : ''
  })
  dialog.value = true
}

const submit = async () => {
  if (!form.userId || !form.roomId || !form.startTime || !form.endTime) {
    return toast.warning('请填写完整信息')
  }
  if (form.startTime >= form.endTime) {
    return toast.warning('结束时间必须晚于开始时间')
  }

  // 格式化数据：input "T" -> 后端 " " + ":00"
  const payload = {
    userId: form.userId,
    roomId: form.roomId,
    meetingTopic: form.meetingTopic,
    startTime: form.startTime.replace('T', ' ') + ':00',
    endTime: form.endTime.replace('T', ' ') + ':00'
  }

  try {
    if (isEdit.value) {
      const res = await updateReservation({ ...payload, id: editId.value })
      if (res.code === 1) {
        toast.success('更新成功')
      } else {
        toast.error(res.msg || '更新失败');
        throw new Error(res.msg || '更新失败');
      }      
    } else {
      // 管理员帮用户预约，通常需要 user_id
      const res = await addReservation({ ...payload, participantNum: 1 }) 
      if (res.code === 1) {
        toast.success('更新成功')
      } else {
        toast.error(res.msg || '更新失败');
        throw new Error(res.msg || '更新失败');
      }      
    }
    dialog.value = false
    fetchData() // 刷新列表
  } catch (error) {
    toast.error('操作失败：' + (error.message || '系统错误'))
  }
}

const handleCancel = async (id) => {
  if (!confirm('确定取消该预订？此操作不可恢复。')) return
  try {
    await cancelReservation(id) // 注意：这里调用的是取消接口，有些系统可能是 DELETE
    toast.success('已取消')
    fetchData()
  } catch (error) {
    toast.error('取消失败')
  }
}

// --- 辅助显示 ---
const formatTime = (t) => t ? dayjs(t).format('YYYY-MM-DD HH:mm') : '-'
const getRoomName = (id) => roomDict.value[id] || `ID:${id}`
const getUserName = (id) => userDict.value[id] || `ID:${id}`
// 状态显示
const getStatusLabel = (status) => {
  const map = { 0: '待审核', 1: '已预约', 2: '已结束', '-1': '已取消' } // 根据实际后端枚举调整
  return map[status] || status
}

const handleAudit = async (row, newStatus) => {
  const actionName = newStatus === 1 ? '通过' : '驳回';
  if(!confirm(`确定要${actionName}该预约吗？`)) return;

  try {
    await auditReservation({
      id: row.id,
      status: newStatus,
      remark: newStatus === 1 ? '管理员通过' : '管理员驳回' // 可选
    });
    alert('操作成功');
    fetchData(); // 刷新列表
  } catch (e) {
    alert('操作失败');
  }
}

onMounted(async () => {
  await initDicts()
  fetchData()
})
</script>

<template>
  <div class="page">
    <header class="page-header">
      <h2>预订管理</h2>
      <div class="header-actions">
        <div class="search-box">
          <i class="fas fa-search search-icon"></i>
          <input 
            type="text" 
            v-model="searchQuery" 
            placeholder="搜索预订编号..." 
            @keyup.enter="handlePageChange(1)"
          />
        </div>
        <button class="add-btn" @click="openAdd">
          <i class="fas fa-plus"></i> 添加预订
        </button>
      </div>
    </header>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <i class="fas fa-spinner fa-spin"></i> 加载中...
    </div>

    <div v-else>
      <table class="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>预订人</th>
            <th>会议主题</th>
            <th>会议室</th>
            <th>开始时间</th>
            <th>结束时间</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in list" :key="row.id">
            <td>#{{ row.id }}</td>
            <td>{{ getUserName(row.username) }}</td>
            <td>{{ row.meetingTopic || '-' }}</td>
            <td>{{ getRoomName(row.roomId) }}</td>
            <td>{{ formatTime(row.startTime) }}</td>
            <td>{{ formatTime(row.endTime) }}</td>
            <td>
              <span class="status-badge" :class="`status-${row.status}`">
                {{ getStatusLabel(row.status) }}
              </span>
            </td>
            <td class="actions">
              <template v-if="row.status === 0">
                <button class="btn-pass" @click="handleAudit(row, 1)">
                  <i class="fas fa-check"></i> 通过
                </button>
                <button class="btn-reject" @click="handleAudit(row, -1)">
                  <i class="fas fa-times"></i> 驳回
                </button>
              </template>
              <template v-else>
                <button class="edit" @click="openEdit(row)">
                  <i class="fas fa-pen"></i> 编辑
                </button>
                <button class="del" @click="handleCancel(row.id)">
                  <i class="fas fa-ban"></i> 取消
                </button>
              </template>
            </td>
          </tr>
          <tr v-if="list.length === 0">
            <td colspan="8" style="text-align: center; color: #999; padding: 2rem;">暂无数据</td>
          </tr>
        </tbody>
      </table>

      <!-- 分页器 -->
      <div class="pagination" v-if="pagination.total > 0">
        <button :disabled="pagination.current === 1" @click="handlePageChange(pagination.current - 1)">上一页</button>
        <span>第 {{ pagination.current }} 页 / 共 {{ Math.ceil(pagination.total / pagination.size) }} 页</span>
        <button :disabled="pagination.current * pagination.size >= pagination.total" @click="handlePageChange(pagination.current + 1)">下一页</button>
      </div>
    </div>

    <!-- 弹窗 -->
    <ModalDialog
      :show="dialog"
      :title="isEdit ? '编辑预订信息' : '添加新的预订'"
      @close="dialog = false"
      @submit="submit"
    >
      <label>
        预订用户
        <select v-model="form.userId" required>
          <option value="" disabled>请选择用户</option>
          <option v-for="u in userOptions" :key="u.id" :value="u.id">{{ u.name }}</option>
        </select>
      </label>
      
      <label>
        会议室
        <select v-model="form.roomId" required>
          <option value="" disabled>请选择会议室</option>
          <option v-for="r in roomOptions" :key="r.id" :value="r.id">{{ r.name }}</option>
        </select>
      </label>

      <label>
        会议主题
        <input v-model="form.meetingTopic" placeholder="例如：Q4 总结会" required />
      </label>

      <label>
        开始时间
        <input type="datetime-local" v-model="form.startTime" required />
      </label>
      
      <label>
        结束时间
        <input type="datetime-local" v-model="form.endTime" required />
      </label>
    </ModalDialog>
  </div>
</template>

<style scoped>
.page-header { 
  display: flex; justify-content: space-between; align-items: center; 
  margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 1px solid #e2e8f0;
}
.page-header h2 { margin: 0; font-size: 1.5rem; font-weight: 600; color: #1e293b; }
.header-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.search-box {
  position: relative;
  width: 240px;
}
.search-box input {
  width: 100%;
  padding: 0.6rem 1rem 0.6rem 2.2rem;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 0.9rem;
  outline: none;
  transition: all 0.2s;
}
.search-box input:focus {
  border-color: #20ae7c;
  box-shadow: 0 0 0 3px rgba(32, 174, 124, 0.1);
}
.search-icon {
  position: absolute;
  left: 0.8rem;
  top: 50%;
  transform: translateY(-50%);
  color: #94a3b8;
  font-size: 0.9rem;
  pointer-events: none;
}

.add-btn {
  background: #20ae7c;
  color: #fff; border: none; border-radius: 8px;
  padding: 0.6rem 1.2rem; cursor: pointer; font-weight: 500;
  display: flex; align-items: center; gap: 0.5rem; transition: all 0.2s;
}
.add-btn:hover { background: #189e6e; transform: translateY(-1px); }

.loading-state { text-align: center; padding: 2rem; color: #64748b; font-size: 1.1rem; }

.data-table {
  width: 100%; border-collapse: separate; border-spacing: 0;
  background: #fff; border-radius: 12px; overflow: hidden;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05); border: 1px solid #e2e8f0;
}
.data-table th {
  background: #f8fafc; text-align: left; padding: 1rem;
  font-weight: 600; color: #475569; font-size: 0.85rem; text-transform: uppercase;
  border-bottom: 1px solid #e2e8f0;
}
.data-table td { padding: 1rem; border-bottom: 1px solid #f1f5f9; font-size: 0.95rem; color: #334155; }
.data-table tr:last-child td { border-bottom: none; }

.status-badge { padding: 4px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 600; }
.status-1 { background: rgba(32, 174, 124, 0.15); color: #20ae7c; } /* 已预约 */
.status-2 { background: #f1f5f9; color: #64748b; } /* 已结束 */
.status--1 { background: #fee2e2; color: #ef4444; } /* 已取消 */

.actions button {
  margin-right: 0.5rem; padding: 0.4rem 0.8rem; border: none; border-radius: 6px;
  cursor: pointer; font-size: 0.85rem; font-weight: 500; transition: all 0.15s;
  display: inline-flex; align-items: center; gap: 4px;
}
.edit { background: rgba(32, 174, 124, 0.1); color: #20ae7c; }
.edit:hover { background: rgba(32, 174, 124, 0.2); }
.del { background: #fee2e2; color: #ef4444; }
.del:hover { background: #fecaca; }

/* 分页 */
.pagination { display: flex; justify-content: flex-end; align-items: center; margin-top: 1.5rem; gap: 1rem; }
.pagination button {
  padding: 0.5rem 1rem; border: 1px solid #e2e8f0; background: white; border-radius: 6px; cursor: pointer; color: #475569;
}
.pagination button:disabled { opacity: 0.5; cursor: not-allowed; }
.pagination button:hover:not(:disabled) { 
  border-color: #20ae7c; 
  color: #20ae7c; 
}
/* 表单 */
label { display: block; margin-bottom: 1rem; font-size: 0.95rem; font-weight: 500; color: #374151; }
label input, label select {
  width: 100%; padding: 0.7rem; margin-top: 0.4rem;
  border: 1px solid #cbd5e1; border-radius: 8px; background: #fff;
  font-size: 0.95rem; transition: border-color 0.2s;
}
label input:focus, label select:focus { 
  outline: none; 
  border-color: #20ae7c; 
  box-shadow: 0 0 0 3px rgba(32, 174, 124, 0.1); 
}
.btn-pass { 
  background: #dcfce7; color: #166534; border: none; padding: 0.4rem 0.8rem; 
  border-radius: 6px; cursor: pointer; font-size: 0.85rem; margin-right: 0.5rem; 
}
.btn-pass:hover { background: #bbf7d0; }

.btn-reject { 
  background: #fee2e2; color: #991b1b; border: none; padding: 0.4rem 0.8rem; 
  border-radius: 6px; cursor: pointer; font-size: 0.85rem; 
}
.btn-reject:hover { background: #fecaca; }
</style>
