<script setup>
import { ref, reactive, onMounted, watch } from 'vue' // 引入 watch
import dayjs from 'dayjs'
import ModalDialog from '@/components/ModalDialog.vue'
import { getFaultPage, handleFault } from '@/apis/fault'
import { toast } from "@/utils/message";

// 状态定义
const loading = ref(false)
const list = ref([])
const pagination = reactive({
  current: 1,
  size: 10,
  total: 0
})

// [新增] 筛选状态：null=全部, 0=待处理, 1=处理中, 2=已修复
const currentStatus = ref('') 
const searchFaultNo = ref('')

// 弹窗控制
const dialog = ref(false)
const currentItem = ref(null) 
const handleForm = reactive({
  status: 1, 
})

// 状态字典
const statusMap = {
  0: { text: '待处理', class: 'status-pending' },
  1: { text: '处理中', class: 'status-processing' },
  2: { text: '已修复', class: 'status-fixed' }
}

// --- 方法 ---

const fetchData = async () => {
  loading.value = true
  try {
    const res = await getFaultPage({
      page: pagination.current,
      pageSize: pagination.size,
      status: currentStatus.value === '' ? undefined : currentStatus.value,
      faultNo: searchFaultNo.value || undefined
    })
    
    if (res.data?.records) {
      list.value = res.data.records
      pagination.total = Number(res.data.total)
    } else {
      list.value = []
      pagination.total = 0
    }
  } catch (error) {
    console.error('加载反馈失败', error)
    toast.error('加载反馈失败');
  } finally {
    loading.value = false
  }
}

const handlePageChange = (newPage) => {
  pagination.current = newPage
  fetchData()
}

// [新增] 监听筛选变化，重置页码并刷新
watch(currentStatus, () => {
  pagination.current = 1
  fetchData()
})

// 打开处理弹窗
const openHandle = (row) => {
  currentItem.value = row
  // 默认选中当前状态的下一个状态，或者保持当前
  handleForm.status = row.status === 0 ? 1 : row.status
  dialog.value = true
}

// 提交处理结果
const submitHandle = async () => {
  if (!currentItem.value) return

  try {
    await handleFault({
      faultNo: currentItem.value.faultNo, // 使用 faultNo
      status: handleForm.status
    })
    
    toast.success('处理成功')
    dialog.value = false
    fetchData() 
  } catch (error) {
    toast.error('操作失败：' + (error.message || '系统错误'))
  }
}

// 格式化时间
const formatTime = (t) => t ? dayjs(t).format('YYYY-MM-DD HH:mm') : '-'

onMounted(fetchData)
</script>

<template>
  <div class="page">
    <header class="page-header">
      <h2>反馈处理</h2>

      <div class="header-actions">
        <!-- [新增] 搜索框 -->
        <div class="search-box">
          <i class="fas fa-search search-icon"></i>
          <input 
            type="text" 
            v-model="searchFaultNo" 
            placeholder="搜索反馈编号..." 
            @keyup.enter="handlePageChange(1)"
          />
        </div>
      
        <!-- 状态筛选按钮组 -->
        <div class="filter-group">
          <button 
            class="filter-btn" 
            :class="{ active: currentStatus === '' }" 
            @click="currentStatus = ''"
          >全部</button>
          <button 
            class="filter-btn" 
            :class="{ active: currentStatus === 0 }" 
            @click="currentStatus = 0"
          >待处理</button>
          <button 
            class="filter-btn" 
            :class="{ active: currentStatus === 1 }" 
            @click="currentStatus = 1"
          >处理中</button>
          <button 
            class="filter-btn" 
            :class="{ active: currentStatus === 2 }" 
            @click="currentStatus = 2"
          >已修复</button>
        </div>
      </div>
    </header>

    <div v-if="loading" class="loading-state">
      <i class="fas fa-spinner fa-spin"></i> 加载中...
    </div>

    <div v-else>
      <table class="data-table">
        <thead>
          <tr>
            <th>故障编号</th>
            <th>设备名称</th>
            <th>所属房间</th>
            <th>故障描述</th>
            <th>上报时间</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in list" :key="row.id">
            <td class="font-mono">{{ row.faultNo }}</td>
            <td class="font-bold">{{ row.deviceName }}</td>
            <td>{{ row.roomId ? `房间 #${row.roomId}` : '公共区域' }}</td>
            <!-- 增加 title 属性，鼠标悬停显示完整描述 -->
            <td class="desc-cell" :title="row.faultDesc">{{ row.faultDesc }}</td>
            <td>{{ formatTime(row.createTime) }}</td>
            <td>
              <span class="status-badge" :class="statusMap[row.status]?.class || 'status-pending'">
                {{ statusMap[row.status]?.text || '未知' }}
              </span>
            </td>
            <td class="actions">
              <button v-if="row.status !== 2" class="btn-handle" @click="openHandle(row)">
                <i class="fas fa-tools"></i> 处理
              </button>
              <span v-else class="text-gray">无需操作</span>
            </td>
          </tr>
          <tr v-if="list.length === 0">
            <td colspan="7" class="empty-text">暂无反馈记录</td>
          </tr>
        </tbody>
      </table>

      <!-- 分页 -->
      <div class="pagination" v-if="pagination.total > 0">
        <button :disabled="pagination.current === 1" @click="handlePageChange(pagination.current - 1)">上一页</button>
        <span>第 {{ pagination.current }} 页 / 共 {{ Math.ceil(pagination.total / pagination.size) }} 页</span>
        <button :disabled="pagination.current * pagination.size >= pagination.total" @click="handlePageChange(pagination.current + 1)">下一页</button>
      </div>
    </div>

    <!-- 处理弹窗 -->
    <ModalDialog
      :show="dialog"
      title="更新处理进度"
      @close="dialog = false"
      @submit="submitHandle"
    >
      <div class="info-row" v-if="currentItem">
        <label>设备：</label> <span>{{ currentItem.deviceName }}</span>
      </div>
      <div class="info-row" v-if="currentItem">
        <label>描述：</label> <span>{{ currentItem.faultDesc }}</span>
      </div>

      <label class="form-label">
        更改状态
        <select v-model="handleForm.status">
          <option :value="0">待处理 (Pending)</option>
          <option :value="1">处理中 (Processing)</option>
          <option :value="2">已修复 (Fixed)</option>
        </select>
      </label>

      <div class="tip-box">
        <i class="fas fa-check-circle"></i> 选择“已修复”后，该记录将归档。
      </div>
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

/* 搜索框样式 */
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

/* 筛选按钮组样式 */
.filter-group { display: flex; gap: 0.5rem; background: #fff; padding: 4px; border-radius: 8px; border: 1px solid #e2e8f0; }
.filter-btn {
  border: none; background: transparent; padding: 6px 12px; border-radius: 6px;
  cursor: pointer; color: #64748b; font-size: 0.9rem; transition: all 0.2s;
}
.filter-btn:hover { background: #f1f5f9; }
.filter-btn.active { background: #20ae7c; color: white; font-weight: 500; }

.loading-state { text-align: center; padding: 2rem; color: #64748b; }

.data-table {
  width: 100%; border-collapse: separate; border-spacing: 0;
  background: #fff; border-radius: 12px; overflow: hidden;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05); border: 1px solid #e2e8f0;
  table-layout: fixed;
}
.data-table th {
  background: #f8fafc; text-align: left; padding: 1rem;
  font-weight: 600; color: #475569; font-size: 0.85rem; text-transform: uppercase;
  border-bottom: 1px solid #e2e8f0;
}
.data-table td { padding: 1rem; border-bottom: 1px solid #f1f5f9; font-size: 0.95rem; color: #334155; }
.data-table tr:last-child td { border-bottom: none; }

.font-mono { font-family: monospace; color: #64748b; font-size: 0.9em; }
.font-bold { font-weight: 600; color: #1e293b; }
.desc-cell { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 200px; color: #475569; }

.status-badge { padding: 4px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 600; }
.status-pending { background: #fee2e2; color: #ef4444; }
.status-processing { background: #fef3c7; color: #d97706; }
.status-fixed { background: #d1fae5; color: #059669; }

.btn-handle {
  padding: 0.4rem 0.8rem; border: none; border-radius: 6px;
  cursor: pointer; font-size: 0.85rem; font-weight: 500; transition: all 0.15s;
  background: rgba(32, 174, 124, 0.1); color: #20ae7c;
  display: inline-flex; align-items: center; gap: 4px;
}
.btn-handle:hover { background: rgba(32, 174, 124, 0.2); }
.text-gray { color: #94a3b8; font-size: 0.85rem; }

.empty-text { text-align: center; color: #94a3b8; padding: 2rem; }

.pagination { display: flex; justify-content: flex-end; align-items: center; margin-top: 1.5rem; gap: 1rem; }
.pagination button { padding: 0.5rem 1rem; border: 1px solid #e2e8f0; background: white; border-radius: 6px; cursor: pointer; color: #475569; }
.pagination button:disabled { opacity: 0.5; cursor: not-allowed; }
.pagination button:hover:not(:disabled) { border-color: #20ae7c; color: #20ae7c; }

.info-row { margin-bottom: 0.8rem; font-size: 0.95rem; }
.info-row label { color: #64748b; margin-right: 0.5rem; }
.info-row span { color: #1e293b; font-weight: 500; }

.form-label { display: block; margin-top: 1.5rem; font-size: 0.95rem; font-weight: 500; color: #374151; }
select {
  width: 100%; padding: 0.7rem; margin-top: 0.5rem;
  border: 1px solid #cbd5e1; border-radius: 8px; background: #fff;
  font-size: 0.95rem; outline: none;
}
select:focus { border-color: #20ae7c; box-shadow: 0 0 0 3px rgba(32, 174, 124, 0.1); }

.tip-box {
  margin-top: 1.5rem; padding: 0.8rem; background: #f0fdf4; border-radius: 8px;
  color: #166534; font-size: 0.85rem; display: flex; align-items: center; gap: 8px;
}
</style>