<script setup>
import { ref } from 'vue'
import { useRouter } from "vue-router";
import { loginAPI, registerAPI } from "@/apis/user"
import { toast } from '@/utils/message'
import '@/styles/el-message.css' 
import { useUserStore } from '@/stores/userStore'

import left from "@/assets/imgs/left.png";
import right from "@/assets/imgs/right.png";
import logo from "@/assets/imgs/logo.svg";

const router = useRouter();
const userStore = useUserStore();

const isSignUpMode = ref(false); 
const isLoading = ref(false);
const isShaking = ref(false);

const loginForm = ref({
  loginAccount: '',
  password: ''
});
const loginError = ref('');

const registerForm = ref({
  username: '',
  password: '',
  confirmPassword: '',
  email: '',
  phone: '',
  gender: '',
});
const registerError = ref('');

const handleModeSwitch = (isSignUp) => {
  isSignUpMode.value = isSignUp;
  loginError.value = '';
  registerError.value = '';
};

const handleLogin = async () => {
  userStore.clearUserInfo();
  loginError.value = '';
  isLoading.value = true;
  if (!loginForm.value.loginAccount || !loginForm.value.password) {
    toast.warning('请填写完整信息');
    triggerShake();
    isLoading.value = false;
    return
  }
  try {
    const res = await loginAPI(loginForm.value)
    if (res.code === 1) {
      toast.success('登录成功！');
      const { token, ...user } = res.data;
      userStore.setUserInfo({ token, user });
      if(res.data.isAdmin === 0) router.push('/');
      else router.push('/manager');
    } else {
      toast.warning(res.msg || '登录失败');
      triggerShake();
    }
  } catch (err) {
    console.log('登录异常', err);
    triggerShake();
  } finally {
    isLoading.value = false;
  }
}

const handleRegister = async () => {
  registerError.value = '';
  isLoading.value = true;
  
  if (!registerForm.value.username || !registerForm.value.password || !registerForm.value.confirmPassword || !registerForm.value.phone) {
    registerError.value = '请填写必填项';
    toast.warning('请填写完整信息');
    triggerShake();
    isLoading.value = false;
    return;
  }
  if (registerForm.value.password !== registerForm.value.confirmPassword) {
    registerError.value = '两次输入的密码不一致';
    triggerShake();
    isLoading.value = false;
    return;
  }

  let genderValue = 0;
  if (registerForm.value.gender === '男') genderValue = 1;
  else if (registerForm.value.gender === '女') genderValue = 2;
  
  const registerData = {
    loginAccount: registerForm.value.phone,  
    username: registerForm.value.username,
    password: registerForm.value.password,
    email: registerForm.value.email,
    phone: registerForm.value.phone,
    gender: genderValue,
  };

  try {
    const res = await registerAPI(registerData);
    if (res.code === 0) {
      toast.success('注册成功！请登录。');
      loginForm.value.loginAccount = registerForm.value.phone;
      handleModeSwitch(false);
      
      registerForm.value = {
        username: '',
        password: '',
        confirmPassword: '',
        email: '',
        phone: '',
        gender: '',
      }
    } else {
      registerError.value = res.msg || '注册失败';
      toast.warning(res.msg || '注册失败');
      triggerShake();
    }
  } catch (err) {
    console.error('注册异常', err);
    registerError.value = '网络连接异常或服务器错误';
    toast.error('网络连接异常或服务器错误');
    triggerShake();
  } finally {
    isLoading.value = false;
  }
}

const triggerShake = () => {
  isShaking.value = true;
  setTimeout(() => {
    isShaking.value = false;
  }, 500);
};
</script>

<template>
  <div class="container" :class="{ 'sign-up-mode': isSignUpMode, 'shake-animation': isShaking }">
    <div class="forms-container">
      <div class="signin-signup">
        <form @submit.prevent="handleLogin" class="sign-in-form">
          <img :src="logo" alt="Logo" class="form-logo" />
          <h2 class="main-title">欢迎使用 智会云 会议室管理系统</h2>
          <h2 class="title">登录</h2>
          <div class="input-field">
            <i class="fas fa-user"></i> <input type="text" placeholder="用户名" v-model="loginForm.loginAccount" required />
          </div>
          <div class="input-field">
            <i class="fas fa-lock"></i>
            <input type="password" placeholder="密码" v-model="loginForm.password" required />
          </div>
          <p class="error-text" v-if="loginError">{{ loginError }}</p>
          <input type="submit" :value="isLoading ? '登录中...' : '登录'" class="btn solid" :disabled="isLoading" />
          
          <p class="social-text">或通过社交平台登录</p>
          <div class="social-media">
            <a href="#" class="social-icon"><i class="fab fa-weixin"></i></a>
            <a href="#" class="social-icon"><i class="fab fa-qq"></i></a>
            <a href="#" class="social-icon"><i class="fab fa-google"></i></a>
          </div>
        </form>

        <form @submit.prevent="handleRegister" class="sign-up-form">
          <img :src="logo" alt="Logo" class="form-logo" />
          <h2 class="main-title">欢迎使用 智会云 会议室管理系统</h2>
          <h2 class="title">注册</h2>
          
          <div class="input-field">
            <i class="fas fa-phone"></i>
            <input type="text" placeholder="电话号码 (作为账号)" v-model="registerForm.phone" required />
          </div>
          <div class="input-field">
            <i class="fas fa-user"></i>
            <input type="text" placeholder="用户名" v-model="registerForm.username" required />
          </div>
          <div class="input-field">
            <i class="fas fa-lock"></i>
            <input type="password" placeholder="密码" v-model="registerForm.password" required />
          </div>
          <div class="input-field">
            <i class="fas fa-lock"></i>
            <input type="password" placeholder="确认密码" v-model="registerForm.confirmPassword" required />
          </div>
          <div class="input-field">
            <i class="fas fa-envelope"></i>
            <input type="email" placeholder="邮箱" v-model="registerForm.email" required />
          </div>
           <div class="input-field">
            <i class="fas fa-venus-mars"></i>
            <select v-model="registerForm.gender">
                <option value="" disabled selected hidden>性别(可选)</option>
                <option value="男">男</option>
                <option value="女">女</option>
                <option value="未知">未知</option>
            </select>
          </div>

          <p class="error-text" v-if="registerError">{{ registerError }}</p>
          <input type="submit" :value="isLoading ? '注册中...' : '注册'" class="btn solid" :disabled="isLoading" />
        </form>
      </div>
    </div>

    <div class="panels-container">
      <div class="panel left-panel">
        <div class="content">
          <h3>新用户 ?</h3>
          <p>加入我们要探索更多精彩内容，只需几步即可轻松注册。</p>
          <button class="btn transparent" @click="handleModeSwitch(true)">去注册</button>
        </div>
        <img :src="left" class="image" alt="" />
      </div>
      
      <div class="panel right-panel">
        <div class="content">
          <h3>已有账号 ?</h3>
          <p>如果您已经拥有账号，请直接登录。</p>
          <button class="btn transparent" @click="handleModeSwitch(false)">去登录</button>
        </div>
        <img :src="right" class="image" alt="" />
      </div>
    </div>
  </div>
</template>

<style scoped>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
  user-select: none;
}

.container {
  position: relative;
  width: 100%;
  background-color: #f6fff8;
  min-height: 100vh;
  overflow: hidden;
  font-family: 'Poppins', sans-serif;
}

@keyframes animateBubble {
  0% { transform: translateY(0) scale(0.8); opacity: 0; }
  20% { opacity: 1; }
  100% { transform: translateY(-100vh) scale(1.2); opacity: 0; }
}

.forms-container {
  position: absolute;
  width: 100%;
  height: 100%;
  top: 0;
  left: 0;
}

.signin-signup {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  left: 75%;
  width: 35%;
  height: 90%;
  transition:1s ease-in-out;
  display: grid;
  grid-template-columns: 1fr;
  z-index: 5;
  background-color: #fcfffdd7;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px); 
  border-radius: 75px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.15);
}

.container.shake-animation .signin-signup {
  animation: shake 0.5s;
}

@keyframes shake {
  0%, 100% { transform: translate(-50%, -50%); }
  10%, 30%, 50%, 70%, 90% { transform: translate(calc(-50% - 5px), -50%); }
  20%, 40%, 60%, 80% { transform: translate(calc(-50% + 5px), -50%); }
}

.form-logo {
  width: 70px;
  margin-bottom: 20px;
  max-width: 100%;
}

form {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  padding: 0rem 3rem;
  transition: all 0.2s 0.7s;
  overflow: hidden;
  grid-column: 1 / 2;
  grid-row: 1 / 2;
}

form.sign-in-form {
  z-index: 2;
  pointer-events: all;
}

form.sign-up-form {
  z-index: 1;
  opacity: 0;
  pointer-events: none;
}

.main-title {
  font-size: 1.5rem;
  color: #444444be;
  margin-bottom: 20px;
  transition: 0.5s; 
}

.title {
  font-size: 2.2rem;
  color: #444;
  margin-bottom: 10px;
  transition: 0.5s; 
}

.input-field {
  max-width: 380px;
  width: 100%;
  background-color: #f5f5f5;
  margin: 10px 0;
  height: 55px;
  border-radius: 55px;
  display: grid;
  grid-template-columns: 15% 85%;
  padding: 0 0.4rem;
  position: relative;
  transition: transform 0.3s ease, box-shadow 0.3s ease, background-color 0.3s;
}

.input-field:hover {
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.15); 
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.15), inset 0 0 0 1px rgba(32, 174, 124, 0.2);
}

.input-field:focus-within {
  transform: scale(1.02);
  background-color: #fff;
  box-shadow: 0 4px 15px rgba(32, 174, 124, 0.15);
  border: 1px solid rgba(32, 174, 124, 0.2);
}

.input-field i {
  text-align: center;
  line-height: 55px;
  color: #acacac;
  transition: 0.5s;
  font-size: 1.1rem;
  margin-left: 20%;
}
   
.input-field:focus-within i {
  color: #20ae7c;
}

.input-field input, .input-field select {
  background: none;
  outline: none;
  border: none;
  line-height: 1;
  font-weight: 600;
  font-size: 1.1rem;
  color: #333;
  width: 100%;
}
.input-field select {
  appearance: none;
  cursor: pointer;
  padding-left: 0.5rem;
}
.input-field input::placeholder {
  color: #aaa;
  font-weight: 500;
}

.btn {
  width: 180px;
  background-color: #20ae7c;
  border: none;
  outline: none;
  height: 70px;
  border-radius: 49px;
  color: #fff;
  text-transform: uppercase;
  font-size: 1.5rem;
  font-weight: 600;
  margin: 30px 0;
  cursor: pointer;
  transition: 0.5s;
  transition: 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275); 
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}
.btn:hover {
  background-color: #35bc88;
  transform: translateY(-3px);
  box-shadow: 0 8px 15px rgba(32, 174, 124, 0.3);
}
.btn:active {
  transform: translateY(-1px) scale(0.98);
}

.social-text { padding: 0.7rem 0; font-size: 1rem; }
.social-media { display: flex; justify-content: center; }
.social-icon {
  height: 46px; width: 46px;
  display: flex; justify-content: center; align-items: center;
  margin: 0 0.45rem; color: #333;
  border-radius: 50%; border: 1px solid #333;
  text-decoration: none; font-size: 1.1rem;
  transition: 0.3s;
}
.social-icon:hover { color: #20ae7c; border-color: #20ae7c; }
.error-text { color: #ef4444; font-size: 0.85rem; margin-bottom: 5px; }

/* --- 面板容器 --- */
.panels-container {
  position: absolute;
  height: 100%;
  width: 100%;
  top: 0;
  left: 0;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
}

/* ---背景--- */
.container:before {
  content: "";
  position: absolute;
  height: 2000px;
  width: 2000px;
  top: -10%;
  right: 45%; /* 圆在左侧 (盖住45%以左的区域) */
  transform: translateY(-50%);
  background-image: linear-gradient(-45deg, #20ae7c 0%, #04befe 100%);
  transition: 1.2s ease-in-out;
  border-radius: 50%;
  z-index: 6;
  pointer-events: none;
}

.panel {
  height: 50%;
  margin-right: 5%;
  display: flex;
  flex-direction: column;
  justify-content: space-around;
  text-align: center;
  padding: 3rem 10%;
  z-index: 6;
  position: relative;
}

/* --- 左侧面板 (Go to Register) --- */
.left-panel {
  pointer-events: all;
  padding: 3rem 17% 2rem 12%;
  align-items: flex-start;
}
.left-panel .content, .left-panel .image {
  transform: translateX(0px); /* 默认不偏移 */
  transition: transform 0.75s ease-in-out;
  transition-delay: 0.2s;
}
.left-panel .image {
  bottom: -15%;
  left: 37.5%;
}

/* --- 右侧面板 (Go to Login) --- */
.right-panel {
  pointer-events: none;
  padding: 3rem 17% 2rem 12%;
  align-items: flex-end;
}
.right-panel .content, .right-panel .image {
  transform: translateX(800px); /* 默认移到右边外面 */
  transition: transform 0.75s ease-in-out;
  transition-delay: 0.2s;
}
.right-panel .image {
  bottom: -12%;
  right:32%;
}

.panel .content { color: #fff; }
.panel h3 { font-weight: 600; line-height: 1; font-size: 2.5rem; margin-bottom: 8%;}
.panel p { font-size: 1.3rem; padding: 0.7rem 0; margin-bottom: 8%;}
.btn.transparent {
  margin: 0; margin-right: 2%; background: none; border: 2px solid #fff;
  width: 160px; height: 73px; font-weight: 600; font-size: 1.5rem;
}
.image { 
  width: 15%;
  transition: transform 1.0s ease-in-out;
  transition-delay: 0.4s;
  position: absolute;
  transform: translateY(10%);
}

form .main-title,form .form-logo,form .input-field, form .btn, form .social-text, form .social-media, form .title {
  transition: 0.6s;
  opacity: 0; 
  transform: translateX(400px); /* 默认向右偏移 */
}

.container:not(.sign-up-mode) .sign-in-form .form-logo,
.container:not(.sign-up-mode) .sign-in-form .main-title,
.container:not(.sign-up-mode) .sign-in-form .title,
.container:not(.sign-up-mode) .sign-in-form .input-field,
.container:not(.sign-up-mode) .sign-in-form .btn,
.container:not(.sign-up-mode) .sign-in-form .social-text,
.container:not(.sign-up-mode) .sign-in-form .social-media {
    opacity: 1;
    transform: translateX(0);
}

.container.sign-up-mode .sign-up-form .form-logo,
.container.sign-up-mode .sign-up-form .main-title,
.container.sign-up-mode .sign-up-form .title,
.container.sign-up-mode .sign-up-form .input-field,
.container.sign-up-mode .sign-up-form .btn,
.container.sign-up-mode .sign-up-form .error-text {
    opacity: 1;
    transform: translateX(0);
}

.container.sign-up-mode .sign-in-form .form-logo,
.container.sign-up-mode .sign-in-form .main-title,
.container.sign-up-mode .sign-in-form .title,
.container.sign-up-mode .sign-in-form .input-field,
.container.sign-up-mode .sign-in-form .btn,
.container.sign-up-mode .sign-in-form .social-text,
.container.sign-up-mode .sign-in-form .social-media {
    opacity: 0;
    transform: translateX(-400px);
}

/* 动画 */

.container.sign-up-mode .signin-signup { left: 25%; }

.container.sign-up-mode form.sign-up-form {
  opacity: 1;
  z-index: 2;
  pointer-events: all;
}
.container.sign-up-mode form.sign-in-form {
  opacity: 0;
  z-index: 1;
  pointer-events: none;
}

.container.sign-up-mode:before {
  transform: translate(100%, -50%);
  right: 52%;
}

.container.sign-up-mode .left-panel .image,
.container.sign-up-mode .left-panel .content {
  transform: translateX(-800px);
}

.container.sign-up-mode .right-panel .image,
.container.sign-up-mode .right-panel .content {
  transform: translateX(0%);
}

.container.sign-up-mode .left-panel {
  pointer-events: none;
}

.container.sign-up-mode .right-panel {
  pointer-events: all;
}

/* --- 移动端适配 --- */
@media (max-width: 870px) {
  .container { min-height: 800px; height: 100vh; }
  .signin-signup {
    width: 100%;
    top: 95%;
    left: 50%;
    transform: translate(-50%, -100%);
    transition: 1s 0.8s ease-in-out;
  }
  .signin-signup, .container.sign-up-mode .signin-signup { left: 50%; }

  .panels-container {
    grid-template-columns: 1fr;
    grid-template-rows: 1fr 2fr 1fr;
  }
  .panel {
    flex-direction: row;
    justify-content: center; align-items: center;
    padding: 2.5rem 8%; grid-column: 1 / 2;
    margin-bottom: 0;
  }
  .right-panel { grid-row: 3 / 4; }
  .left-panel { grid-row: 1 / 2; }
  
  .image { width: 0px; transition: transform 0.9s ease-in-out; transition-delay: 0.6s; }
  .content { padding-right: 15%; transition: transform 0.9s ease-in-out; transition-delay: 0.8s; }
  
  .container:before {
    width: 1500px; height: 1500px;
    transform: translateX(-50%);
    left: 30%; bottom: 68%;
    right: initial; top: initial;
    transition: 2s ease-in-out;
  }

  .container.sign-up-mode:before {
    transform: translate(-50%, 100%);
    bottom: 32%; right: initial;
  }
  
  .container.sign-up-mode .signin-signup { top: 5%; transform: translate(-50%, 0); }
  
  .left-panel .image, .left-panel .content { transform: translateY(0); }
  .right-panel .image, .right-panel .content { transform: translateY(300px); }
  
  .container.sign-up-mode .left-panel .image,
  .container.sign-up-mode .left-panel .content { transform: translateY(-300px); }
  
  .container.sign-up-mode .right-panel .image,
  .container.sign-up-mode .right-panel .content { transform: translateY(0px); }

  .form-logo {
    width: 40px;
    margin-bottom: 5px;
  }
  .main-title {
    font-size: 1.2rem;
    margin-bottom: 5px;
  }
  .title {
    font-size: 1.5rem;
    margin-bottom: 5px;
  }
  .input-field {
    width: 80%;
    height: 40px;
  }
  .input-field i {
    line-height: 40px;
    height: 100%;
  }
  .input-field .fas {
    font-size: 0.8rem;
  }
  .input-field input, .input-field select {
    font-size: 0.7rem;
    font-weight: 500;
    line-height: 40px;
    height: 100%;
  }
  .input-field .fas {
    font-size: 0.8rem;
    height: 50%;
  }
  .btn {
    font-size: 1rem;
    height: 45px;
    width: 130px;
  }
  .social-text {
    font-size: 0.7rem;
  }
  .panel h3 {
    font-size: 1.5rem;
  }
  .panel p {
    font-size: 0.8rem;
  }
  .btn.transparent {
    font-size: 1rem;
    width: 100px;
    height: 40px;
  }
  .error-text {
    font-size: 0.6rem;
  }
  @keyframes shake {
    0%, 100% { transform: translate(-50%, -100%); }
    10%, 30%, 50%, 70%, 90% { transform: translate(calc(-50% - 2px), -100%); }
    20%, 40%, 60%, 80% { transform: translate(calc(-50% + 2px), -100%); }
  }
  .container.shake-animation .signin-signup {
    animation: shake 0.5s;
  }
  .signin-signup {
    height: 60%;
  }
  .input-field {
    margin: 5px 0;
  }
  .btn {
    margin: 10px 0;
  }
}
</style>