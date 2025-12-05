<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import ModalDialog from '@/components/ModalDialog.vue'
import { toast } from "@/utils/message";

// API
import { 
  getUserPage, 
  addUser, 
  updateUser, 
  deleteUsers,
  setUserActive 
} from '@/apis/user-manage'

const loading = ref(false)
const list = ref([])
const pagination = reactive({
  current: 1,
  size: 10,
  total: 0
})

// 搜索
const searchUsername = ref('')

// 弹窗
const dialog = ref(false)
const isEdit = ref(false)
const editId = ref(null)

const form = reactive({
  username: '',
  loginAccount: '',
  password: '', // 仅新增时必填，编辑时留空表示不改
  email: '',
  phone: '',
  gender: 0, // 0未知 1男 2女
  isActive: 1 // 1启用 0禁用
})

const selectedIds = ref([]) // 存储选中的ID

// 计算属性：判断是否全选
const isAllSelected = computed(() => {
  if (list.value.length === 0) return false
  // 检查当前页的所有ID是否都在 selectedIds 中
  return list.value.every(item => selectedIds.value.includes(item.id))
})

// 全选/取消全选
const toggleSelectAll = () => {
  if (isAllSelected.value) {
    // 如果已经是全选，则清空当前页的选中项
    const currentPageIds = list.value.map(item => item.id)
    selectedIds.value = selectedIds.value.filter(id => !currentPageIds.includes(id))
  } else {
    // 否则将当前页所有未选中的ID加进去
    const currentPageIds = list.value.map(item => item.id)
    // 使用 Set 去重，防止重复添加
    const newSet = new Set([...selectedIds.value, ...currentPageIds])
    selectedIds.value = Array.from(newSet)
  }
}

// 批量删除方法
const handleBatchDelete = async () => {
  if (selectedIds.value.length === 0) return toast.warning('请先选择要删除的用户')
  
  if (!confirm(`确定要删除选中的 ${selectedIds.value.length} 个用户吗？`)) return

  try {
    loading.value = true
    await deleteUsers(selectedIds.value) // 传入 ID 数组
    toast.success('批量删除成功')
    selectedIds.value = [] // 清空选中状态
    fetchData() // 刷新列表
  } catch (error) {
    toast.error('删除失败')
  } finally {
    loading.value = false
  }
}

const fetchData = async () => {
  loading.value = true
  try {
    const res = await getUserPage({
      page: pagination.current,
      pageSize: pagination.size,
      username: searchUsername.value || undefined
    })
    
    if (res.data?.records) {
      list.value = res.data.records
      pagination.total = Number(res.data.total)
    } else {
      list.value = []
      pagination.total = 0
    }
  } catch (error) {
    console.error(error)
    toast.error('加载用户失败');
  } finally {
    loading.value = false
  }
}

const handlePageChange = (newPage) => {
  pagination.current = newPage
  fetchData()
}

const openAdd = () => {
  isEdit.value = false
  editId.value = null
  Object.assign(form, { 
    username: '', loginAccount: '', password: '', 
    email: '', phone: '', gender: 0, isActive: 1 
  })
  dialog.value = true
}

const openEdit = (row) => {
  isEdit.value = true
  editId.value = row.id
  Object.assign(form, {
    username: row.username,
    loginAccount: row.loginAccount,
    password: '', // 编辑时不回显密码
    email: row.email,
    phone: row.phone,
    gender: row.gender,
    isActive: row.isActive
  })
  dialog.value = true
}

const submit = async () => {
  if (!form.username || !form.loginAccount) return toast.warning('用户名和账号必填')
  
  // 新增时密码必填
  if (!isEdit.value && !form.password) return toast.warning('初始密码必填')

  const payload = { ...form }

  try {
    if (isEdit.value) {
      // 编辑时如果密码为空，不传密码字段，避免覆盖为空
      if (!payload.password) delete payload.password
      const res = await updateUser({ id: editId.value, ...payload })
      if (res.code === 1) {
        toast.success('更新成功')
      } else {
        toast.error(res.msg || '更新失败');
        throw new Error(res.msg || '更新失败');
      }
    } else {
      const res = await addUser(payload)
      if (res.code === 1) {
        toast.success('更新成功')
      } else {
        toast.error(res.msg || '更新失败');
        throw new Error(res.msg || '更新失败');
      }
    }
    dialog.value = false
    fetchData()
  } catch (error) {
    toast.error('操作失败：' + (error.message || '未知错误'))
  }
}

const handleRemove = async (id) => {
  if (!confirm('确定删除该用户？此操作不可恢复。')) return
  try {
    await deleteUsers([id])
    toast.success('已删除')
    selectedIds.value = selectedIds.value.filter(item => item !== id)
    fetchData()
  } catch (error) {
    toast.error('删除失败')
  }
}

const toggleActive = async (row) => {
  try {
    // 接口是 setUserActive(status, id)，status: 1启用 0禁用
    // 注意：假设 row.isActive 是 1 或 0
    const newStatus = row.isActive === 1 ? 0 : 1
    await setUserActive(newStatus, row.id)
    row.isActive = newStatus // 本地更新
  } catch (error) {
    toast.error('状态切换失败')
  }
}

// 辅助
const genderMap = { 0: '未知', 1: '男', 2: '女' }

onMounted(fetchData)
</script>

<template>
  <div class="page">
    <header class="page-header">
      <h2>用户管理</h2>
      
      <!-- [修改] 统一头部操作区 -->
      <div class="header-actions">
        <button 
          v-if="selectedIds.length > 0"
          class="batch-del-btn" 
          @click="handleBatchDelete"
        >
          <i class="fas fa-trash"></i> 批量删除 ({{ selectedIds.length }})
        </button>
        <div class="search-box">
          <i class="fas fa-search search-icon"></i>
          <input 
            type="text" 
            v-model="searchUsername" 
            placeholder="搜索用户名..." 
            @keyup.enter="handlePageChange(1)" 
          />
        </div>
        <button class="add-btn" @click="openAdd">
          <i class="fas fa-plus"></i> 添加用户
        </button>
      </div>
    </header>

    <div v-if="loading" class="loading-state">
      <i class="fas fa-spinner fa-spin"></i> 加载中...
    </div>

    <div v-else>
      <table class="data-table">
        <thead>
          <tr>
            <th style="width: 40px; text-align: center;">
              <input 
                type="checkbox" 
                :checked="isAllSelected" 
                @change="toggleSelectAll" 
              />
            </th>
            <th>ID</th>
            <th>登录账号</th>
            <th>用户名</th>
            <th>联系方式</th>
            <th>性别</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in list" :key="row.id">
            <td style="text-align: center;">
              <input 
                type="checkbox" 
                :value="row.id" 
                v-model="selectedIds" 
              />
            </td>            
            <td class="font-mono">#{{ row.id }}</td>
            <td class="font-bold">{{ row.loginAccount }}</td>
            <td>{{ row.username }}</td>
            <td>
              <div class="contact-info">
                <div v-if="row.email"><i class="fas fa-envelope"></i> {{ row.email }}</div>
                <div v-if="row.phone"><i class="fas fa-phone"></i> {{ row.phone }}</div>
              </div>
            </td>
            <td>{{ genderMap[row.gender] }}</td>
            <td>
              <span 
                class="status-badge" 
                :class="row.isActive === 1 ? 'status-active' : 'status-disabled'"
                @click="toggleActive(row)"
                title="点击切换状态"
                style="cursor: pointer"
              >
                {{ row.isActive === 1 ? '正常' : '禁用' }}
              </span>
            </td>
            <td class="actions">
              <button class="edit" @click="openEdit(row)">
                <i class="fas fa-pen"></i> 编辑
              </button>
              <button class="del" @click="handleRemove(row.id)">
                <i class="fas fa-trash"></i> 删除
              </button>
            </td>
          </tr>
          <tr v-if="list.length === 0">
            <td colspan="7" class="empty-text">暂无数据</td>
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

    <!-- 弹窗 -->
    <ModalDialog
      :show="dialog"
      :title="isEdit ? '编辑用户' : '添加用户'"
      @close="dialog = false"
      @submit="submit"
    >
      <label>
        登录账号 (唯一)
        <input v-model="form.loginAccount" :disabled="isEdit" placeholder="例如：admin001" required />
      </label>
      
      <label>
        用户名 (昵称)
        <input v-model="form.username" placeholder="例如：张三" required />
      </label>

      <label>
        {{ isEdit ? '重置密码 (留空则不修改)' : '初始密码' }}
        <input type="password" v-model="form.password" placeholder="******" />
      </label>

      <div class="form-row">
        <label>
          性别
          <select v-model="form.gender">
            <option :value="0">未知</option>
            <option :value="1">男</option>
            <option :value="2">女</option>
          </select>
        </label>
        <label>
          状态
          <select v-model="form.isActive">
            <option :value="1">启用</option>
            <option :value="0">禁用</option>
          </select>
        </label>
      </div>

      <label>
        邮箱
        <input type="email" v-model="form.email" />
      </label>
      
      <label>
        手机号
        <input type="tel" v-model="form.phone" />
      </label>

    </ModalDialog>
  </div>
</template>

<style scoped>
/* 绿色主题统一 */
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
.batch-del-btn {
  background-color: #ef4444;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  margin-right: 10px;
  display: flex;
  align-items: center;
  gap: 5px;
}
.batch-del-btn:hover {
  background-color: #dc2626;
}
.row-selected {
  background-color: #fef2f2;
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
  background: #20ae7c; color: #fff; border: none; border-radius: 8px;
  padding: 0.6rem 1.2rem; cursor: pointer; font-weight: 500;
  display: flex; align-items: center; gap: 0.5rem; transition: all 0.2s;
}
.add-btn:hover { background: #189e6e; transform: translateY(-1px); }

.loading-state { text-align: center; padding: 2rem; color: #64748b; }

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
.font-bold { font-weight: 600; color: #1e293b; }

.contact-info { font-size: 0.85rem; color: #64748b; display: flex; flex-direction: column; gap: 2px; }
.contact-info i { width: 16px; color: #94a3b8; }

.status-badge { padding: 4px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 600; user-select: none; }
.status-active { background: rgba(32, 174, 124, 0.15); color: #20ae7c; }
.status-disabled { background: #fee2e2; color: #ef4444; }

.actions button {
  margin-right: 0.5rem; padding: 0.4rem 0.8rem; border: none; border-radius: 6px;
  cursor: pointer; font-size: 0.85rem; font-weight: 500; transition: all 0.15s;
  display: inline-flex; align-items: center; gap: 4px;
}
.edit { background: rgba(32, 174, 124, 0.1); color: #20ae7c; }
.edit:hover { background: rgba(32, 174, 124, 0.2); }
.del { background: #fee2e2; color: #ef4444; }
.del:hover { background: #fecaca; }

.pagination { display: flex; justify-content: flex-end; align-items: center; margin-top: 1.5rem; gap: 1rem; }
.pagination button { padding: 0.5rem 1rem; border: 1px solid #e2e8f0; background: white; border-radius: 6px; cursor: pointer; color: #475569; }
.pagination button:disabled { opacity: 0.5; cursor: not-allowed; }
.pagination button:hover:not(:disabled) { border-color: #20ae7c; color: #20ae7c; }

/* 表单 */
label { display: block; margin-bottom: 1rem; font-size: 0.95rem; font-weight: 500; color: #374151; }
label input, label select {
  width: 100%; padding: 0.7rem; margin-top: 0.4rem;
  border: 1px solid #cbd5e1; border-radius: 8px; background: #fff;
  font-size: 0.95rem; transition: border-color 0.2s;
}
label input:focus, label select:focus { outline: none; border-color: #20ae7c; box-shadow: 0 0 0 3px rgba(32, 174, 124, 0.1); }
.form-row { display: flex; gap: 1rem; }
.form-row label { flex: 1; }
</style>
