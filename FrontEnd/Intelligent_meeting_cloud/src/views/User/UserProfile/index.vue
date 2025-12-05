<script setup>
import { ref, reactive, onMounted } from 'vue';
import { useUserStore } from '@/stores/userStore';
import { updateUser, getByIdAPI } from '@/apis/user-manage'; 
import { uploadFile } from '@/apis/common';
import defaultAvatar from "@/assets/imgs/avatar.svg";
import { toast } from '@/utils/message'
import '@/styles/el-message.css' 

const userStore = useUserStore();
const isLoading = ref(false);
const fileInputRef = ref(null);
const currentAvatar = ref(defaultAvatar);

// 图片裁剪相关
const showCropper = ref(false)
const cropperRef = ref(null)  
const cropperLoading = ref(false) 
const option = reactive({
  img: '', 
  outputSize: 1,      
  outputType: 'png',  
  info: true,         
  canScale: true,     
  autoCrop: true,     
  autoCropWidth: 200, 
  autoCropHeight: 200,
  fixed: true, 
  fixedNumber: [1, 1],
  full: true,  
  fixedBox: false,    
  canMoveBox: true,   
  original: false,    
  centerBox: true,    
  high: true,         
})

const form = reactive({
  id: null,
  username: '',
  loginAccount: '',
  email: '',
  phone: '',
  gender: 0,
  remark: '',
  image: ''
});

const displayJoinDate = ref('2023-01-01');

const fetchLatestUserInfo = async () => {
  const storeUser = userStore.userInfo.user || {};
  const userId = storeUser.id;

  if (!userId) {
    toast.error('无法获取用户信息，请重新登录');
    return;
  }

  try {
    isLoading.value = true;
    const res = await getByIdAPI(userId);
    const data = res.data;

    form.id = data.id;
    form.username = data.username || '';
    form.loginAccount = data.loginAccount || storeUser.loginAccount;
    form.email = data.email || '';
    form.phone = data.phone || '';
    form.remark = data.remark || ''; 
    form.gender = data.gender || 0;
    form.image = data.image || storeUser.image;

    if (data.createTime) {
      displayJoinDate.value = data.createTime.substring(0, 10);
    }

    if (data.image) {
      currentAvatar.value = data.image;
    }
  } catch (error) {
    console.error(error);
    toast.error('获取用户详情失败');
  } finally {
    isLoading.value = false;
  }
};

onMounted(() => {
  fetchLatestUserInfo();
  const user = userStore.userInfo || {};

  form.id = user.id;
  form.loginAccount = user.loginAccount || '';
  form.username = user.username || '';
  form.email = user.email || '';
  form.phone = user.phone || '';
  form.remark = user.remark || '';
  form.gender = user.gender || 0;
  form.image = user.image || '';

  if (user.createTime) {
    form.joinDate = user.createTime.substring(0, 10);
  } else {
    form.joinDate = '2023-01-01';
  }

  if (user.image) {
    currentAvatar.value = user.image;
  } else if (user.avatar) {
    currentAvatar.value = user.avatar;
  }
});

const triggerUpload = () => {
  fileInputRef.value.click();
};

const handleFileChange = (event) => {
  const file = event.target.files[0];
  if (!file) return;
  if (file.size > 5 * 1024 * 1024) return toast.warning('原始图片不能超过 5MB');
  const reader = new FileReader();
  reader.onload = (e) => {
    option.img = e.target.result;
    showCropper.value = true;
  }
  reader.readAsDataURL(file);
  event.target.value = '';
};

const handleCropConfirm = () => {
  cropperLoading.value = true;
  cropperRef.value.getCropBlob(async (blob) => {
    try {
      const file = new File([blob], "avatar.png", { type: "image/png" });
      const res = await uploadFile(file);
      const url = res.data; 
      currentAvatar.value = url;
      form.avatar = url;
      toast.success('头像裁剪上传成功，记得保存哦！');
      showCropper.value = false;
    } catch (error) {
      toast.error('上传失败');
      console.error(error);
    } finally {
      cropperLoading.value = false
    }
  })
}

const handleSave = async () => {
  if (!form.id) return;
  isLoading.value = true;
  
  const updatePayload = {
    id: form.id,
    loginAccount: form.loginAccount,
    username: form.username,
    email: form.email,
    phone: form.phone,
    remark: form.remark,
    gender: form.gender,
    image: form.image
  };

  try {
    await updateUser(updatePayload);
    const oldUser = userStore.userInfo.user || {};
    const newUser = {
      ...oldUser,
      ...updatePayload,
      image: form.image || currentAvatar.value
    };
    userStore.setUserInfo({
      token: userStore.userInfo.token,
      user: newUser
    });

    toast.success('用户信息保存成功！');
  } catch (error) {
    console.error(error);
    toast.error('保存失败：' + (error.message || '未知错误'));
  } finally {
    isLoading.value = false;
  }
};
</script>

<template>
  <div class="page-container">
    <div class="glass-card profile-layout">
      
      <!-- 左侧：头像与简介 -->
      <div class="profile-sidebar">
        <div class="avatar-wrapper">
          <img :src="currentAvatar" alt="Avatar" class="avatar-img" />
          <div class="avatar-upload-btn" @click="triggerUpload">
            <i class="fa-solid fa-camera"></i>
          </div>
          <input 
            type="file" 
            ref="fileInputRef" 
            accept="image/*" 
            style="display: none" 
            @change="handleFileChange"
          />
        </div>
        <h2 class="user-title">{{ form.username || 'User' }}</h2>
        <p class="user-role">管理员</p>
        
        <div class="stats-grid">
          <div class="stat-item">
            <span class="stat-val">12</span>
            <span class="stat-label">会议</span>
          </div>
          <div class="stat-item">
            <span class="stat-val">85%</span>
            <span class="stat-label">在线率</span>
          </div>
          <div class="stat-item">
            <span class="stat-val">4</span>
            <span class="stat-label">设备</span>
          </div>
        </div>
      </div>

      <!-- 右侧：详细编辑表单 -->
      <div class="profile-content">
        <div class="section-header">
          <h3><i class="fa-solid fa-id-card"></i> 基本资料</h3>
          <span class="sub-text">管理您的个人账户信息</span>
        </div>

        <form @submit.prevent="handleSave" class="info-form">
          <div class="form-row">
            <div class="form-group">
              <label>用户名</label>
              <input type="text" v-model="form.username" class="glass-input" />
            </div>
            <div class="form-group">
              <label>入职日期</label>
              <input type="text" v-model="form.joinDate" disabled class="glass-input disabled" />
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>电子邮箱</label>
              <input type="email" v-model="form.email" class="glass-input" />
            </div>
            <div class="form-group">
              <label>联系电话</label>
              <input type="tel" v-model="form.phone" class="glass-input" />
            </div>
          </div>

          <!-- 性别选择 -->
          <div class="form-group">
            <label>性别</label>
            <select v-model="form.gender" class="glass-input">
              <option :value="1">男</option>
              <option :value="2">女</option>
              <option :value="0">未知</option>
            </select>
          </div>

          <!-- 个人简介 -->
          <div class="form-group">
            <label>个人简介 (备注)</label>
            <textarea v-model="form.remark" rows="4" class="glass-input"></textarea>
          </div>

          <div class="form-actions">
            <button type="submit" class="save-btn" :disabled="isLoading">
              <i class="fa-solid fa-spinner fa-spin" v-if="isLoading"></i>
              <span v-else>保存更改</span>
            </button>
          </div>
        </form>
      </div>
      <!-- 图片裁剪模态框 -->
      <div v-if="showCropper" class="cropper-modal">
        <div class="cropper-card glass-card">
          <h3 class="cropper-title">裁剪头像</h3>
          <div class="cropper-content">
            <VueCropper
              ref="cropperRef"
              :img="option.img"
              :outputSize="option.outputSize"
              :outputType="option.outputType"
              :info="option.info"
              :canScale="option.canScale"
              :autoCrop="option.autoCrop"
              :autoCropWidth="option.autoCropWidth"
              :autoCropHeight="option.autoCropHeight"
              :fixed="option.fixed"
              :fixedNumber="option.fixedNumber"
              :full="option.full"
              :fixedBox="option.fixedBox"
              :canMoveBox="option.canMoveBox"
              :original="option.original"
              :centerBox="option.centerBox"
              :high="option.high"
            ></VueCropper>
          </div>
          <div class="cropper-actions">
            <button class="cancel-btn" @click="showCropper = false">取消</button>
            <button class="confirm-btn" @click="handleCropConfirm" :disabled="cropperLoading">
              <i class="fa-solid fa-spinner fa-spin" v-if="cropperLoading"></i>
              {{ cropperLoading ? '上传中...' : '确认裁剪' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-container {
  min-height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 2rem;
  box-sizing: border-box;
}

.glass-card {
  background: rgba(30, 41, 59, 0.6);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  box-shadow: 0 15px 35px rgba(0, 0, 0, 0.2);
  width: 100%;
  max-width: 1000px;
  overflow: hidden;
  display: flex;
}

.profile-sidebar {
  width: 320px;
  background: rgba(0, 0, 0, 0.2);
  padding: 40px 30px;
  display: flex;
  flex-direction: column;
  align-items: center;
  border-right: 1px solid rgba(255, 255, 255, 0.05);
}

.avatar-wrapper {
  position: relative;
  margin-bottom: 20px;
}
.avatar-img {
  width: 120px; height: 120px;
  border-radius: 50%;
  border: 4px solid #20ae7c8b;
  padding: 4px;
  object-fit: cover;
}
.avatar-upload-btn {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 36px;
  height: 36px;
  background: #20ae7c;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #fff;
  border: 3px solid rgba(30, 41, 59, 1);
  transition: all 0.3s;
  box-shadow: 0 4px 10px rgba(0,0,0,0.3);
}
.avatar-upload-btn:hover {
  transform: scale(1.1);
  background: #20ae7c;
}

.user-title { color: #fff; margin-bottom: 5px; font-size: 1.5rem; font-weight: bold; }
.user-role { color: #3da681; font-size: 0.9rem; margin-bottom: 30px; letter-spacing: 1px; }

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 15px;
  width: 100%;
  text-align: center;
}
.stat-val { display: block; color: #fff; font-size: 1.2rem; font-weight: bold; }
.stat-label { color: rgba(255,255,255,0.5); font-size: 0.8rem; }

/* 右侧内容 */
.profile-content {
  flex: 1;
  padding: 40px;
}

.section-header { margin-bottom: 30px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 15px; }
.section-header h3 { color: #fff; margin-bottom: 5px; font-size: 1.2rem; }
.section-header .sub-text { color: rgba(255,255,255,0.5); font-size: 0.9rem; }

/* 表单样式 */
.info-form { display: flex; flex-direction: column; gap: 20px; }
.form-row { display: flex; gap: 20px; }
.form-group { flex: 1; display: flex; flex-direction: column; gap: 8px; }

label { color: rgba(255,255,255,0.7); font-size: 0.9rem; font-weight: 500; }

.glass-input {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 12px 16px;
  color: #fff;
  font-size: 1rem;
  transition: all 0.3s ease;
  outline: none;
}
.glass-input:focus {
  border-color: #20ae7c;
  background: rgba(0, 0, 0, 0.4);
}
.glass-input.disabled {
  opacity: 0.6;
  cursor: not-allowed;
  background: rgba(255, 255, 255, 0.05);
}

select.glass-input option {
  background: #1e293b;
  color: #fff;
}

.save-btn {
  background: #20ae7c;
  color: #fff;
  border: none;
  padding: 12px 30px;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  float: right;
  min-width: 120px;
}
.save-btn:hover {
  filter: brightness(1.1);
  transform: translateY(-2px);
}
.save-btn:disabled { opacity: 0.7; cursor: not-allowed; }

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

@media (max-width: 768px) {
  .glass-card { flex-direction: column; overflow-y: auto; }
  .profile-sidebar { width: 100%; border-right: none; border-bottom: 1px solid rgba(255,255,255,0.05); }
  .form-row { flex-direction: column; gap: 20px; }
  .page-container { padding: 1rem; }
}
</style>