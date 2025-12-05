<script setup>
import { ref, reactive, onMounted,computed } from 'vue'
import ModalDialog from '@/components/ModalDialog.vue'
import { toast } from "@/utils/message";

// API
import { 
  getAdminRoomPage,
  addRoom, 
  updateRoom, 
  deleteRooms,
  setRoomActive
} from '@/apis/room'
import { uploadFile } from '@/apis/common'

// 状态定义
const loading = ref(false)
const list = ref([])
const pagination = reactive({
  current: 1,
  size: 10,
  total: 0
})

// 搜索条件
const searchCode = ref('')
const roomFileRef = ref(null)

const dialog = ref(false)
const isEdit = ref(false)
const editId = ref(null)

const form = reactive({
  roomCode: '',
  capacity: '',
  location: '',
  equipment: '', // 后端是字符串，逗号分隔
  image: '',
  isActive: true // 默认启用
})

// 图片裁剪相关
const showRoomCropper = ref(false)
const roomCropperRef = ref(null)
const roomUploadLoading = ref(false)
const roomCropperOption = reactive({
  img: '',             
  outputSize: 1,       
  outputType: 'png',   
  info: true,          
  canScale: true,      
  autoCrop: true,
  fixed: true,         
  fixedNumber: [16, 9], 
  full: true,          
  fixedBox: false,     
  canMoveBox: true,    
  original: false,     
  centerBox: true,     
  high: true,          
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
    await deleteRooms(selectedIds.value) // 传入 ID 数组
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
    const res = await getAdminRoomPage({
      page: pagination.current,
      pageSize: pagination.size,
      roomCode: searchCode.value || undefined
    })
    
    if (res.data?.records) {
      list.value = res.data.records
      pagination.total = Number(res.data.total)
    } else {
      list.value = []
      pagination.total = 0
    }
  } catch (error) {
    toast.error('加载会议室失败');
    console.error('加载会议室失败', error);
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
    roomCode: '', 
    capacity: '', 
    location: '', 
    equipment: '', 
    image: '',
    isActive: true 
  })
  dialog.value = true
}

const openEdit = (row) => {
  isEdit.value = true
  editId.value = row.id
  Object.assign(form, {
    roomCode: row.roomCode,
    capacity: row.capacity,
    location: row.location,
    equipment: row.equipment,
    image: row.image,
    isActive: row.isActive
  })
  dialog.value = true
}

const triggerRoomUpload = () => roomFileRef.value.click();

const handleRoomImage = (e) => {
  const file = e.target.files[0];
  if (!file) return;
  if (file.size > 5 * 1024 * 1024) return toast.warning('原始图片不能超过 5MB');
  const reader = new FileReader();
  reader.onload = (evt) => {
    roomCropperOption.img = evt.target.result;
    showRoomCropper.value = true;
  }
  reader.readAsDataURL(file);
  e.target.value = '';
}

const handleRoomCropConfirm = () => {
  roomUploadLoading.value = true;
  roomCropperRef.value.getCropBlob(async (blob) => {
    try {
      const file = new File([blob], "room-cover.png", { type: "image/png" });
      const res = await uploadFile(file);
      const url = res.data;
      form.image = url;
      if (isEdit.value && editId.value) {
        localStorage.setItem(`room_img_${editId.value}`, url);
      } else {
        localStorage.setItem('temp_room_new_img', url);
      }
      toast.success('上传成功');
      showRoomCropper.value = false;
    } catch(err) { 
      console.error(err);
      toast.error('上传失败'); 
    } finally {
      roomUploadLoading.value = false;
    }
  })
}

const submit = async () => {
  if (!form.roomCode || !form.capacity) return toast.warning('名称和容量必填')

  const payload = { ...form }
  payload.capacity = Number(payload.capacity)

  try {
    if (isEdit.value) {
      const res = await updateRoom({ id: editId.value, ...payload });
      if (res.code === 1) {
        toast.success('更新成功')
      } else {
        toast.error(res.msg || '更新失败');
        throw new Error(res.msg || '更新失败');
      }
    } else {
      const res = await addRoom(payload)
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
  if (!confirm('确定删除该会议室？')) return
  try {
    await deleteRooms([id])
    toast.success('已删除')
    selectedIds.value = selectedIds.value.filter(item => item !== id)
    fetchData()
  } catch (error) {
    toast.error('删除失败')
  }
}

// 快捷切换状态
const toggleStatus = async (row) => {
  try {
    const newStatus = !row.isActive
    await setRoomActive(row.id, newStatus) 
    row.isActive = newStatus
  } catch (error) {
    toast.error('状态切换失败')
  }
}

onMounted(fetchData)
</script>

<template>
  <div class="page">
    <header class="page-header">
      <h2>会议室管理</h2>
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
            v-model="searchCode" 
            placeholder="搜索会议室编号..." 
            @keyup.enter="handlePageChange(1)"
          />
        </div>
      <button class="add-btn" @click="openAdd">
        <i class="fas fa-plus"></i> 添加会议室
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
            <th>预览</th>
            <th>会议室名称 (编号)</th>
            <th>位置</th>
            <th>容量</th>
            <th>设备标签</th>
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
            <td>
              <img v-if="row.image" :src="row.image" class="thumb-img" />
              <div v-else class="thumb-placeholder"><i class="fas fa-image"></i></div>
            </td>
            <td class="font-medium">{{ row.roomCode }}</td>
            <td>{{ row.location || '-' }}</td>
            <td>{{ row.capacity }} 人</td>
            <td>
              <div class="tag-list">
                <span v-for="tag in (row.equipment ? row.equipment.split(',') : [])" :key="tag" class="tag">
                  {{ tag }}
                </span>
              </div>
            </td>
            <td>
              <span 
                class="status-badge" 
                :class="row.isActive ? 'status-active' : 'status-disabled'"
                @click="toggleStatus(row)"
                style="cursor: pointer"
                title="点击切换状态"
              >
                {{ row.isActive ? '使用中' : '已禁用' }}
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
            <td colspan="6" style="text-align: center; color: #999; padding: 2rem;">暂无数据</td>
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
      :title="isEdit ? '编辑会议室' : '添加会议室'"
      @close="dialog = false"
      @submit="submit"
    >
      <div class="upload-area" @click="triggerRoomUpload">
        <img v-if="form.image" :src="form.image" class="preview-img" />
        <div v-else class="upload-placeholder">
          <i class="fas fa-cloud-upload-alt"></i> 点击上传封面图
        </div>
        <input type="file" ref="roomFileRef" hidden @change="handleRoomImage" />
      </div>
      <label>
        会议室名称 / 编号
        <input v-model="form.roomCode" placeholder="如：Meeting-A 或 305室" required />
      </label>
      <label>
        位置
        <input v-model="form.location" placeholder="如：3楼东侧" />
      </label>
      <label>
        容量（人）
        <input type="number" v-model="form.capacity" min="1" placeholder="10" required />
      </label>
      <label>
        设备设施 (逗号分隔)
        <input v-model="form.equipment" placeholder="如：投影仪,白板,音响" />
      </label>
      <label>
        初始状态
        <select v-model="form.isActive">
          <option :value="true">启用 (可预订)</option>
          <option :value="false">禁用 (维护中)</option>
        </select>
      </label>
    </ModalDialog>
    <!-- 图片裁剪模态框 -->
    <div v-if="showRoomCropper" class="cropper-modal">
      <div class="cropper-card glass-card">
        <h3 class="cropper-title">裁剪封面图</h3>
        <div class="cropper-content">
          <VueCropper
            ref="roomCropperRef"
            :img="roomCropperOption.img"
            :outputSize="roomCropperOption.outputSize"
            :outputType="roomCropperOption.outputType"
            :info="roomCropperOption.info"
            :canScale="roomCropperOption.canScale"
            :autoCrop="roomCropperOption.autoCrop"
            :fixed="roomCropperOption.fixed"
            :fixedNumber="roomCropperOption.fixedNumber"
            :full="roomCropperOption.full"
            :fixedBox="roomCropperOption.fixedBox"
            :canMoveBox="roomCropperOption.canMoveBox"
            :original="roomCropperOption.original"
            :centerBox="roomCropperOption.centerBox"
            :high="roomCropperOption.high"
          ></VueCropper>
        </div>
        <div class="cropper-actions">
          <button class="cancel-btn" @click="showRoomCropper = false">取消</button>
          <button class="confirm-btn" @click="handleRoomCropConfirm" :disabled="roomUploadLoading">
            <i class="fa-solid fa-spinner fa-spin" v-if="roomUploadLoading"></i>
            {{ roomUploadLoading ? '上传中...' : '确认裁剪' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 绿色主题统一 */
.page-header { 
  display: flex; justify-content: space-between; align-items: center; 
  margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 1px solid #e2e8f0;
}
.page-header h2 { margin: 0; font-size: 1.5rem; font-weight: 600; color: #1e293b; }
.page-header { 
  display: flex; 
  justify-content: space-between; 
  align-items: center; 
  margin-bottom: 1.5rem; 
  padding-bottom: 1rem; 
  border-bottom: 1px solid #e2e8f0;
}

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
  background: #20ae7c; 
  color: #fff; 
  border: none; 
  border-radius: 8px;
  padding: 0.6rem 1.2rem; 
  cursor: pointer; 
  font-weight: 500;
  display: flex; 
  align-items: center; 
  gap: 0.5rem; 
  transition: all 0.2s;
  white-space: nowrap; /* 防止按钮换行 */
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
.font-medium { font-weight: 600; }

/* 标签样式 */
.tag-list { display: flex; gap: 4px; flex-wrap: wrap; }
.tag {
  background: #f1f5f9; color: #64748b; padding: 2px 6px; 
  border-radius: 4px; font-size: 0.75rem;
}

/* 状态徽章 */
.status-badge { 
  padding: 4px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 600; user-select: none;
}
.status-active { background: rgba(32, 174, 124, 0.15); color: #20ae7c; }
.status-disabled { background: #f1f5f9; color: #94a3b8; }

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

label { display: block; margin-bottom: 1rem; font-size: 0.95rem; font-weight: 500; color: #374151; }
label input, label select {
  width: 100%; padding: 0.7rem; margin-top: 0.4rem;
  border: 1px solid #cbd5e1; border-radius: 8px; background: #fff;
  font-size: 0.95rem; transition: border-color 0.2s;
}
label input:focus, label select:focus { outline: none; border-color: #20ae7c; box-shadow: 0 0 0 3px rgba(32, 174, 124, 0.1); }
.thumb-img { width: 50px; height: 36px; object-fit: cover; border-radius: 4px; border: 1px solid #e2e8f0; }
.thumb-placeholder { width: 50px; height: 36px; background: #f1f5f9; border-radius: 4px; display: flex; align-items: center; justify-content: center; color: #cbd5e1; }

.upload-area {
  width: 100%; height: 140px; border: 2px dashed #cbd5e1; border-radius: 8px;
  margin-bottom: 1rem; cursor: pointer; overflow: hidden; background: #f8fafc;
  display: flex; align-items: center; justify-content: center; position: relative;
}
.upload-area:hover { border-color: #20ae7c; background: #f0fdf4; }
.preview-img { width: 100%; height: 100%; object-fit: cover; }
.upload-placeholder { color: #94a3b8; display: flex; flex-direction: column; align-items: center; gap: 8px; }
.upload-placeholder i { font-size: 2rem; }
/* 裁剪弹窗样式 */
.cropper-modal {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(5px);
  z-index: 9999;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
}

.cropper-card {
  width: 600px;
  max-width: 95vw;
  height: 500px;
  display: flex;
  flex-direction: column;
  padding: 20px;
  background: #1e293b;
}

.cropper-title {
  color: #fff;
  margin-bottom: 15px;
  font-size: 1.2rem;
  text-align: center;
}

.cropper-content {
  flex: 1;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 20px;
  position: relative;
}

.cropper-actions {
  display: flex;
  justify-content: flex-end;
  gap: 15px;
}

.cancel-btn {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  border: 1px solid rgba(255, 255, 255, 0.2);
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s;
}
.cancel-btn:hover {
  background: rgba(255, 255, 255, 0.2);
}

.confirm-btn {
  background: #20ae7c;
  color: #fff;
  border: none;
  padding: 10px 25px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: bold;
  transition: all 0.3s;
}
.confirm-btn:hover {
  filter: brightness(1.1);
}
.confirm-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}
</style>