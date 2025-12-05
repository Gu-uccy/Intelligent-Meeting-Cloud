<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useUserStore } from '@/stores/userStore';
import { logoutAPI } from "@/apis/user";
import logo from "@/assets/imgs/logo.svg"; 
import avatar from "@/assets/imgs/avatar.svg";

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();
const userInfo = computed(() => userStore.userInfo.user || { username: 'Admin', avatar: avatar });

const menuItems = [
  { name: '首页公告', path: '/', icon: 'fas fa-chart-pie' },
  { name: '会议预定', path: '/booking', icon: 'fas fa-calendar-alt' },
  { name: '日程管理', path: '/schedule', icon: 'fas fa-clock' },
  { name: '智能物联', path: '/control', icon: 'fas fa-wifi' },
];

// --- 导航栏滑块 ---
const navRefs = ref([]);
const sliderStyle = ref({ left: '0px', width: '0px', opacity: 0 });

const setNavRef = (el, index) => {
  if (el) navRefs.value[index] = el.$el || el;
};

const updateSlider = async () => {
  await nextTick();
  const activeIndex = menuItems.findIndex(item => item.path === route.path);
  if (activeIndex !== -1 && navRefs.value[activeIndex]) {
    const activeEl = navRefs.value[activeIndex];
    sliderStyle.value = {
      left: `${activeEl.offsetLeft}px`,
      width: `${activeEl.offsetWidth}px`,
      opacity: 1
    };
  } else {
    sliderStyle.value = { ...sliderStyle.value, opacity: 0 };
  }
};

watch(() => route.path, () => { updateSlider(); }, { immediate: true });

// --- 用户下拉菜单 ---
const showUserMenu = ref(false);
const userMenuRef = ref(null);

const toggleUserMenu = () => {
  showUserMenu.value = !showUserMenu.value;
};

const handleClickOutside = (event) => {
  if (userMenuRef.value && !userMenuRef.value.contains(event.target)) {
    showUserMenu.value = false;
  }
};

const handleViewProfile = () => {
  showUserMenu.value = false;
  router.push('/profile');
};

const handleChangePassword = () => {
  showUserMenu.value = false;
  router.push('/change-password');
};

const handleLogout = async () => {
  try {
    await logoutAPI();
  } catch (error) {
    console.error('登出失败', error);
  } finally {
    userStore.clearUserInfo();
    localStorage.removeItem('token');
    router.replace('/login');
  }
};

onMounted(() => {
  window.addEventListener('resize', updateSlider);
  document.addEventListener('click', handleClickOutside);
  updateSlider();
});

onUnmounted(() => {
  window.removeEventListener('resize', updateSlider);
  document.removeEventListener('click', handleClickOutside);
});
</script>

<template>
  <nav class="transparent-nav">
    <div class="nav-brand" @click="router.push('/')">
      <img :src="logo" alt="Logo" class="nav-logo" /> 
      <span class="brand-text">智会云</span>
    </div>

    <div class="nav-links">
      <div class="nav-slider" :style="sliderStyle"></div>
      <router-link 
        v-for="(item, index) in menuItems" 
        :key="item.path" 
        :to="item.path"
        class="nav-item"
        :class="{ active: route.path === item.path }"
        :ref="(el) => setNavRef(el, index)"
      >
        <div class="glass-bg"></div> 
        <span class="content">
          <i :class="item.icon"></i>
          <span>{{ item.name }}</span>
        </span>
      </router-link>
    </div>

    <div class="nav-user" ref="userMenuRef">
      <div class="user-profile nav-item" :class="{ active: showUserMenu }" @click.stop="toggleUserMenu">
         <div class="glass-bg"></div>
         <span class="content user-content">
            <div class="avatar-circle"><img v-if="userInfo.avatar" :src="userInfo.avatar" class="avatar-img" /></div>
            <span class="username">{{ userInfo.username }}</span>
            <i class="fas fa-chevron-down arrow-icon" :class="{ 'rotate': showUserMenu }"></i>
         </span>
      </div>

      <transition name="fade-slide">
        <div class="user-dropdown" v-show="showUserMenu">
          <div class="dropdown-item" @click="handleViewProfile">
            <i class="fas fa-user-circle"></i>
            <span>用户信息</span>
          </div>
          <div class="dropdown-item" @click="handleChangePassword">
            <i class="fas fa-key"></i>
            <span>修改密码</span>
          </div>
          <div class="dropdown-divider"></div>
          <div class="dropdown-item logout" @click="handleLogout">
            <i class="fas fa-sign-out-alt"></i>
            <span>退出登录</span>
          </div>
        </div>
      </transition>
    </div>
  </nav>
</template>

<style scoped>
.transparent-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 3rem;
  height: 80px;
  width: 100%;
  background: linear-gradient(to bottom, rgba(0,0,0,0.4), transparent);
  position: relative;
  z-index: 100;
}

.nav-brand {
  display: flex;
  align-items: center;
  cursor: pointer;
  gap:1rem;
}
.nav-logo { width:40px; height:40px; border-radius:8px; }
.brand-text { font-size: 1.6rem; font-weight: 700; color: #20ae7c; letter-spacing: 1px; }

.nav-links { 
  display: flex; 
  gap: 20px; 
  position: relative;
}

.nav-slider {
  position: absolute;
  height: 100%;
  top: 0;
  border-radius: 12px;
  background: rgba(32, 174, 124, 0.85); 
  backdrop-filter: blur(10px);
  border: 1px solid rgba(32, 174, 124, 0.5);
  box-shadow: 0 0 15px rgba(32, 174, 124, 0.4);
  transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 1;
  pointer-events: none;
}

.nav-item {
  position: relative;
  text-decoration: none;
  color: rgba(255, 255, 255, 0.75);
  padding: 10px 24px;
  border-radius: 12px;
  transition: color 0.5s ease;
  overflow: visible;
  cursor: pointer;
  z-index: 2;
  display: flex;
  align-items: center;
}

.nav-item .content {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  font-size: 1rem;
}

.nav-item .glass-bg {
  position: absolute;
  top: 0; left: 0; width: 100%; height: 100%;
  z-index: 1;
  background: rgba(255, 255, 255, 0.1);
  opacity: 0;
  transform: scale(0.95);
  transition: all 0.5s ease;
  border-radius: 12px;
}

.nav-item:not(.active):hover .glass-bg,
.nav-item.active .glass-bg {
  opacity: 1;
  backdrop-filter: blur(10px);
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.nav-item:not(.active):hover {
  color: #fff;
}

.nav-item.active {
  color: #fff;
}
.nav-links .nav-item.active .glass-bg {
  opacity: 0;
}
.user-profile.active .glass-bg {
  opacity: 1;
}

.user-content { display: flex; align-items: center; gap: 10px; }
.avatar-circle {
  width: 32px; height: 32px;
  background: #20ae7c;
  color: #fff;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 0.9rem;
  text-transform: uppercase;
}
.avatar-circle img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 50%;
}

.nav-user {
  position: relative;
}

.arrow-icon {
  font-size: 0.8rem;
  transition: transform 0.3s ease;
}
.arrow-icon.rotate {
  transform: rotate(180deg);
}

.user-dropdown {
  position: absolute;
  top: calc(100% + 10px);
  right: 0;
  width: 180px;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(15px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  padding: 8px 0;
  overflow: hidden;
  z-index: 1000;
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 20px;
  color: rgba(255, 255, 255, 0.8);
  font-size: 0.95rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.dropdown-item i {
  width: 16px;
  text-align: center;
}

.dropdown-item:hover {
  background: rgba(32, 174, 124, 0.2);
  color: #fff;
  padding-left: 24px;
}

.dropdown-divider {
  height: 1px;
  background: rgba(255, 255, 255, 0.1);
  margin: 4px 0;
}

.dropdown-item.logout:hover {
  background: rgba(255, 77, 79, 0.2);
  color: #ff4d4f;
}

.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.fade-slide-enter-from,
.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-10px) scale(0.95);
}
</style>