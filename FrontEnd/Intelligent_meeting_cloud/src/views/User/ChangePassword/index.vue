<script setup>
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useUserStore } from '@/stores/userStore';
import { loginAPI } from '@/apis/user';
import { updateUser } from '@/apis/user-manage';
import { toast } from '@/utils/message'
import '@/styles/el-message.css' 

const router = useRouter();
const userStore = useUserStore();
const isLoading = ref(false);

const form = ref({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
});

const showOld = ref(false);
const showNew = ref(false);
const showConfirm = ref(false);

const errorMessage = ref('');
const isValid = computed(() => {
  return form.value.newPassword.length >= 6 && 
         form.value.newPassword === form.value.confirmPassword &&
         form.value.oldPassword;
});

const handleSubmit = async () => {
  if (form.value.newPassword !== form.value.confirmPassword) {
    errorMessage.value = "两次输入的密码不一致";
    return;
  }
  
  isLoading.value = true;
  errorMessage.value = '';

  try {
    // 1. 验证旧密码 (通过尝试登录来验证)
    const currentUserAccount = userStore.userInfo?.loginAccount;
    if (!currentUserAccount) {
      throw new Error('用户信息丢失，请重新登录');
    }

    try {
      await loginAPI({
        loginAccount: currentUserAccount,
        password: form.value.oldPassword
      });
    } catch (e) {
      throw new Error('当前密码输入错误');
    }

    // 更新新密码
    await updateUser({
      id: userStore.userInfo.id,
      password: form.value.newPassword
    });

    toast.success('密码修改成功，请重新登录');
    
    // 3. 登出并跳转
    userStore.clearUserInfo();
    router.push('/login');

  } catch (error) {
    errorMessage.value = error.message || '修改失败，请稍后重试';
  } finally {
    isLoading.value = false;
  }
};
</script>

<template>
  <div class="page-container">
    <div class="glass-card auth-card">
      <div class="card-header">
        <div class="icon-circle">
          <i class="fa-solid fa-lock"></i>
        </div>
        <h2>修改密码</h2>
        <p>为了您的账号安全，建议定期更换密码</p>
      </div>

      <form @submit.prevent="handleSubmit" class="auth-form">
        
        <!-- 旧密码 -->
        <div class="input-group">
          <label>当前密码</label>
          <div class="input-wrapper">
            <i class="fa-solid fa-key input-icon"></i>
            <input 
              :type="showOld ? 'text' : 'password'" 
              v-model="form.oldPassword" 
              placeholder="请输入当前密码"
            />
            <i 
              class="fa-solid eye-icon" 
              :class="showOld ? 'fa-eye-slash' : 'fa-eye'"
              @click="showOld = !showOld"
            ></i>
          </div>
        </div>

        <!-- 新密码 -->
        <div class="input-group">
          <label>新密码</label>
          <div class="input-wrapper">
            <i class="fa-solid fa-unlock-keyhole input-icon"></i>
            <input 
              :type="showNew ? 'text' : 'password'" 
              v-model="form.newPassword" 
              placeholder="请输入新密码 (至少6位)"
            />
            <i 
              class="fa-solid eye-icon" 
              :class="showNew ? 'fa-eye-slash' : 'fa-eye'"
              @click="showNew = !showNew"
            ></i>
          </div>
        </div>

        <!-- 确认密码 -->
        <div class="input-group">
          <label>确认新密码</label>
          <div class="input-wrapper">
            <i class="fa-solid fa-circle-check input-icon"></i>
            <input 
              :type="showConfirm ? 'text' : 'password'" 
              v-model="form.confirmPassword" 
              placeholder="请再次输入新密码"
            />
            <i 
              class="fa-solid eye-icon" 
              :class="showConfirm ? 'fa-eye-slash' : 'fa-eye'"
              @click="showConfirm = !showConfirm"
            ></i>
          </div>
          <!-- 错误提示 -->
          <div class="error-text" v-if="errorMessage">
            <i class="fa-solid fa-circle-exclamation"></i> {{ errorMessage }}
          </div>
        </div>

        <div class="form-actions">
          <button type="button" class="cancel-btn" @click="router.back()">取消</button>
          <button type="submit" class="submit-btn" :disabled="!isValid || isLoading">
            <i class="fa-solid fa-spinner fa-spin" v-if="isLoading"></i>
            <span v-else>确认修改</span>
          </button>
        </div>

      </form>
    </div>
  </div>
</template>

<style scoped>
:root {
  --primary: #20ae7c;
  --bg-dark: #113a2c;
  --text-main: #ffffff;
}

.page-container {
  min-height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 1rem;
  box-sizing: border-box;
}

.glass-card {
  background: rgba(30, 41, 59, 0.6);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  box-shadow: 0 15px 35px rgba(0, 0, 0, 0.2);
  padding: 40px;
  width: 100%;
  max-width: 480px;
}

.card-header { text-align: center; margin-bottom: 30px; }
.icon-circle {
  width: 60px; height: 60px;
  background: #20ae7c1a;
  color: #20ae7c;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.5rem;
  margin: 0 auto 15px;
  box-shadow: 0 0 15px #20ae7c33;
}
.card-header h2 { color: #fff; margin-bottom: 8px; font-weight: 600; }
.card-header p { color: rgba(255,255,255,0.5); font-size: 0.9rem; }

.auth-form { display: flex; flex-direction: column; gap: 20px; }

.input-group label {
  display: block;
  color: rgba(255,255,255,0.8);
  margin-bottom: 8px;
  font-size: 0.9rem;
  font-weight: 500;
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.input-wrapper input {
  width: 100%;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  padding: 12px 40px;
  color: #fff;
  font-size: 1rem;
  transition: all 0.3s;
  outline: none;
  box-sizing: border-box;
}
.input-wrapper input:focus {
  border-color: #20ae7c;
  box-shadow: 0 0 10px rgba(37, 99, 235, 0.15);
  background: rgba(0, 0, 0, 0.3);
}

.input-icon {
  position: absolute;
  left: 15px;
  color: rgba(255,255,255,0.4);
}

.eye-icon {
  position: absolute;
  right: 15px;
  color: rgba(255,255,255,0.4);
  cursor: pointer;
  transition: color 0.3s;
}
.eye-icon:hover { color: #fff; }

.error-text {
  color: #f87171;
  font-size: 0.85rem;
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.form-actions {
  display: flex;
  gap: 15px;
  margin-top: 10px;
}

.submit-btn, .cancel-btn {
  flex: 1;
  padding: 12px;
  border-radius: 10px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  border: none;
}

.submit-btn {
  background: #20ae7c;
  color: #fff;
}
.submit-btn:hover:not(:disabled) {
  filter: brightness(1.1);
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(37, 99, 235, 0.3);
}
.submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: #334155;
}

.cancel-btn {
  background: transparent;
  border: 1px solid rgba(255,255,255,0.1);
  color: rgba(255,255,255,0.7);
}
.cancel-btn:hover {
  background: rgba(255,255,255,0.05);
  color: #fff;
  border-color: rgba(255,255,255,0.3);
}
</style>