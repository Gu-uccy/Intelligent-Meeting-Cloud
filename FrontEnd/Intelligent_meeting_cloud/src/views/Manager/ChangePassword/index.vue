<script setup>
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useUserStore } from '@/stores/userStore';
import { loginAPI } from '@/apis/user';
import { updateUser } from '@/apis/user-manage';
import { toast } from "@/utils/message";

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

const isValid = computed(() => {
  return form.value.newPassword.length >= 6 && 
         form.value.newPassword === form.value.confirmPassword &&
         form.value.oldPassword;
});

const handleSubmit = async () => {
  if (form.value.newPassword !== form.value.confirmPassword) {
    return toast.error("两次输入的密码不一致");
  }
  
  isLoading.value = true;

  try {
    const account = userStore.userInfo?.loginAccount || userStore.userInfo?.user?.loginAccount;
    
    // 1. 验证旧密码
    await loginAPI({
      loginAccount: account,
      password: form.value.oldPassword
    });

    // 2. 更新新密码
    await updateUser({
      id: userStore.userInfo.id,
      password: form.value.newPassword
    });

    toast.success('密码修改成功，请重新登录');
    
    // 3. 登出
    userStore.clearUserInfo();
    router.push('/login');

  } catch (error) {
    toast.error('修改失败：旧密码错误或系统异常');
  } finally {
    isLoading.value = false;
  }
};
</script>

<template>
  <div class="page-center">
    <div class="auth-card">
      <div class="card-header">
        <div class="icon-circle">
          <i class="fas fa-lock"></i>
        </div>
        <h2>修改密码</h2>
        <p>为了账号安全，建议定期更换密码</p>
      </div>

      <form @submit.prevent="handleSubmit" class="auth-form">
        
        <div class="input-group">
          <label>当前密码</label>
          <div class="input-wrapper">
            <i class="fas fa-key input-icon"></i>
            <input :type="showOld ? 'text' : 'password'" v-model="form.oldPassword" placeholder="请输入当前密码" />
            <i class="fas eye-icon" :class="showOld ? 'fa-eye-slash' : 'fa-eye'" @click="showOld = !showOld"></i>
          </div>
        </div>

        <div class="input-group">
          <label>新密码</label>
          <div class="input-wrapper">
            <i class="fas fa-unlock-alt input-icon"></i>
            <input :type="showNew ? 'text' : 'password'" v-model="form.newPassword" placeholder="请输入新密码 (至少6位)" />
            <i class="fas eye-icon" :class="showNew ? 'fa-eye-slash' : 'fa-eye'" @click="showNew = !showNew"></i>
          </div>
        </div>

        <div class="input-group">
          <label>确认新密码</label>
          <div class="input-wrapper">
            <i class="fas fa-check-circle input-icon"></i>
            <input :type="showConfirm ? 'text' : 'password'" v-model="form.confirmPassword" placeholder="请再次输入新密码" />
            <i class="fas eye-icon" :class="showConfirm ? 'fa-eye-slash' : 'fa-eye'" @click="showConfirm = !showConfirm"></i>
          </div>
        </div>

        <div class="form-actions">
          <button type="submit" class="submit-btn" :disabled="!isValid || isLoading">
            <i class="fas fa-spinner fa-spin" v-if="isLoading"></i>
            <span v-else>确认修改</span>
          </button>
        </div>

      </form>
    </div>
  </div>
</template>

<style scoped>
.page-center {
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: flex-start; /* 稍微靠上一点 */
  padding-top: 4rem;
}

.auth-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05);
  padding: 40px;
  width: 100%;
  max-width: 420px;
}

.card-header { text-align: center; margin-bottom: 30px; }
.icon-circle {
  width: 60px; height: 60px;
  background: rgba(32, 174, 124, 0.1);
  color: #20ae7c;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.5rem;
  margin: 0 auto 15px;
}
.card-header h2 { color: #1e293b; margin-bottom: 8px; font-weight: 600; }
.card-header p { color: #64748b; font-size: 0.9rem; }

.auth-form { display: flex; flex-direction: column; gap: 20px; }

.input-group label {
  display: block; color: #475569; margin-bottom: 8px; font-size: 0.9rem; font-weight: 500;
}

.input-wrapper { position: relative; display: flex; align-items: center; }

.input-wrapper input {
  width: 100%;
  background: #fff;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 12px 40px;
  color: #334155;
  font-size: 1rem;
  transition: all 0.2s;
  outline: none;
}
.input-wrapper input:focus {
  border-color: #20ae7c;
  box-shadow: 0 0 0 3px rgba(32, 174, 124, 0.1);
}

.input-icon { position: absolute; left: 15px; color: #94a3b8; }
.eye-icon { position: absolute; right: 15px; color: #94a3b8; cursor: pointer; transition: color 0.2s; }
.eye-icon:hover { color: #20ae7c; }

.form-actions { margin-top: 10px; }

.submit-btn {
  width: 100%;
  padding: 12px;
  border-radius: 8px;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.3s;
  border: none;
  background: #20ae7c;
  color: #fff;
  font-weight: 600;
}
.submit-btn:hover:not(:disabled) { background: #189e6e; transform: translateY(-1px); box-shadow: 0 4px 12px rgba(32, 174, 124, 0.25); }
.submit-btn:disabled { opacity: 0.6; cursor: not-allowed; }
</style>