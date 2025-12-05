<script setup>
import { ref, reactive, onMounted } from 'vue';
import { useUserStore } from '@/stores/userStore';
import { updateUser } from '@/apis/user-manage';
import { uploadFile } from '@/apis/common';
import { toast } from "@/utils/message";
import avatarImg from "@/assets/imgs/avatar.svg";

const userStore = useUserStore();
const isLoading = ref(false);
const fileInputRef = ref(null);
const currentAvatar = ref(avatarImg);

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

onMounted(() => {
  const user = userStore.userInfo || {};
  
  // 初始化表单
  form.id = user.id;
  form.username = user.username || '';
  form.loginAccount = user.loginAccount || 'Admin';
  form.email = user.email || '';
  form.phone = user.phone || '';
  form.remark = user.remark || '';
  form.gender = user.gender || 0;
  form.image = user.image || '';

  // 头像回显
  if (user.image) {
    currentAvatar.value = user.image;
  } else if (user.avatar) {
    currentAvatar.value = user.avatar;
  }
});

const triggerUpload = () => fileInputRef.value.click();

const handleFileChange = async (event) => {
  const file = event.target.files[0];
  if (!file) return;

  if (file.size > 2 * 1024 * 1024) return toast.warning('图片大小不能超过 2MB');

  try {
    isLoading.value = true;
    const res = await uploadFile(file);
    const url = res.data;
    
    currentAvatar.value = url;
    form.image = url;
    toast.success('头像上传成功');
  } catch (error) {
    toast.error('上传失败');
  } finally {
    isLoading.value = false;
  }
};

const handleSave = async () => {
  isLoading.value = true;
  const updatePayload = {
    id: form.id,
    username: form.username,
    email: form.email,
    phone: form.phone,
    remark: form.remark,
    gender: form.gender,
    image: form.image
  };

  try {
    await updateUser(updatePayload);
    
    // 同步更新 Store
    userStore.setUserInfo({
      ...userStore.userInfo,
      ...updatePayload,
      avatar: form.image || currentAvatar.value
    });

    toast.success('保存成功');
  } catch (error) {
    toast.error('保存失败：' + (error.message || '未知错误'));
  } finally {
    isLoading.value = false;
  }
};
</script>

<template>
  <div class="page-container">
    <div class="glass-card profile-layout">
      
      <!-- 左侧：头像区 -->
      <div class="profile-sidebar">
        <div class="avatar-wrapper">
          <img :src="currentAvatar" alt="Avatar" class="avatar-img" />
          <div class="avatar-upload-btn" @click="triggerUpload">
            <i class="fas fa-camera"></i>
          </div>
          <input type="file" ref="fileInputRef" accept="image/*" hidden @change="handleFileChange" />
        </div>
        <h2 class="user-title">{{ form.username || '管理员' }}</h2>
        <p class="user-role">超级管理员</p>
      </div>

      <!-- 右侧：表单区 -->
      <div class="profile-content">
        <div class="section-header">
          <h3><i class="fas fa-user-shield"></i> 管理员资料</h3>
          <span class="sub-text">更新您的管理账户信息</span>
        </div>

        <form @submit.prevent="handleSave" class="info-form">
          <div class="form-row">
            <div class="form-group">
              <label>登录账号 (不可修改)</label>
              <input type="text" v-model="form.loginAccount" disabled class="glass-input disabled" />
            </div>
            <div class="form-group">
              <label>管理员昵称</label>
              <input type="text" v-model="form.username" class="glass-input" />
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

          <div class="form-group">
            <label>性别</label>
            <select v-model="form.gender" class="glass-input">
              <option :value="1">男</option>
              <option :value="2">女</option>
              <option :value="0">未知</option>
            </select>
          </div>

          <div class="form-group">
            <label>备注说明</label>
            <textarea v-model="form.remark" rows="4" class="glass-input"></textarea>
          </div>

          <div class="form-actions">
            <button type="submit" class="save-btn" :disabled="isLoading">
              <i class="fas fa-spinner fa-spin" v-if="isLoading"></i>
              <span v-else>保存更改</span>
            </button>
          </div>
        </form>
      </div>

    </div>
  </div>
</template>

<style scoped>
.page-container {
  height: 100%;
  display: flex;
  justify-content: center;
  padding: 2rem;
  box-sizing: border-box;
}

.glass-card {
  background: #fff;
  border-radius: 20px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.05);
  border: 1px solid #e2e8f0;
  width: 100%;
  max-width: 900px;
  overflow: hidden;
  display: flex;
}

/* 左侧栏 */
.profile-sidebar {
  width: 280px;
  background: #f8fafc;
  padding: 40px 30px;
  display: flex;
  flex-direction: column;
  align-items: center;
  border-right: 1px solid #e2e8f0;
}

.avatar-wrapper { position: relative; margin-bottom: 20px; }
.avatar-img {
  width: 120px; height: 120px;
  border-radius: 50%;
  border: 4px solid rgba(32, 174, 124, 0.2);
  padding: 4px; object-fit: cover;
}
.avatar-upload-btn {
  position: absolute; bottom: 0; right: 0;
  width: 36px; height: 36px;
  background: #20ae7c;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; color: #fff;
  border: 3px solid #fff;
  transition: all 0.3s;
  box-shadow: 0 4px 10px rgba(0,0,0,0.1);
}
.avatar-upload-btn:hover { transform: scale(1.1); background: #189e6e; }

.user-title { color: #1e293b; margin-bottom: 5px; font-size: 1.4rem; font-weight: bold; }
.user-role { color: #20ae7c; font-size: 0.9rem; margin-bottom: 30px; letter-spacing: 1px; font-weight: 500; }

/* 右侧内容 */
.profile-content { flex: 1; padding: 40px; }

.section-header { margin-bottom: 30px; border-bottom: 1px solid #e2e8f0; padding-bottom: 15px; }
.section-header h3 { color: #1e293b; margin-bottom: 5px; font-size: 1.2rem; }
.section-header .sub-text { color: #64748b; font-size: 0.9rem; }

/* 表单样式 */
.info-form { display: flex; flex-direction: column; gap: 20px; }
.form-row { display: flex; gap: 20px; }
.form-group { flex: 1; display: flex; flex-direction: column; gap: 8px; }

label { color: #475569; font-size: 0.9rem; font-weight: 500; }

.glass-input {
  background: #fff;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 10px 16px;
  color: #334155;
  font-size: 0.95rem;
  transition: all 0.3s ease;
  outline: none;
}
.glass-input:focus { border-color: #20ae7c; box-shadow: 0 0 0 3px rgba(32, 174, 124, 0.1); }
.glass-input.disabled { background: #f1f5f9; cursor: not-allowed; color: #94a3b8; }

select.glass-input { appearance: none; }

.save-btn {
  background: #20ae7c; color: #fff;
  border: none; padding: 12px 30px; border-radius: 8px;
  font-size: 1rem; font-weight: 600; cursor: pointer;
  transition: all 0.3s; float: right; min-width: 120px;
}
.save-btn:hover { background: #189e6e; transform: translateY(-2px); box-shadow: 0 5px 15px rgba(32, 174, 124, 0.2); }
.save-btn:disabled { opacity: 0.7; cursor: not-allowed; }

@media (max-width: 768px) {
  .glass-card { flex-direction: column; height: auto; overflow-y: auto; }
  .profile-sidebar { width: 100%; border-right: none; border-bottom: 1px solid #e2e8f0; }
  .form-row { flex-direction: column; gap: 20px; }
  .page-container { padding: 1rem; }
}
</style>