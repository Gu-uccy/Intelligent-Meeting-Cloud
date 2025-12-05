<script setup>
import { ref,onMounted,onUnmounted } from 'vue';
import SideBar from "@/views/Manager/Layout/components/SideBar.vue";
import { useRouter } from "vue-router";
import { toast } from "@/utils/message";
import BreadcrumbNav from "@/components/BreadcrumbNav.vue";
import managerAvatar from '@/assets/imgs/avatar.svg';

const router = useRouter();

const showMenu = ref(false);
const showUserMenu = ref(false); 

const user = ref({
  name: '张三',
  avatarUrl: managerAvatar
});

const viewProfile = () => {
  showUserMenu.value = false;
  router.push('/manager/profile');
};

const changePassword = () => {
  showUserMenu.value = false;
  router.push('/manager/change-password');
};

const logout = () => {
  showUserMenu.value = false;
  router.push({ path: '/login' });  
  toast.success('已退出登录'); 
};

const userMenuRef = ref(null); 

const handleClickOutside = (event) => {
  if (userMenuRef.value && !userMenuRef.value.contains(event.target)) {
    showUserMenu.value = false;
  }
};

onMounted(() => {
  document.addEventListener('click', handleClickOutside);
});

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside);
});
</script>

<template>
  <nav class="nav">
    <div class="nav-group-left">
      
      <div class="nav-left">
        <img src="@/assets/imgs/logo.svg" alt="Logo" class="logo" />
        <span class="title">智会云</span>
      </div>

      <BreadcrumbNav /> 
    </div>
    
    <div class="nav-right">
      <div class="user-menu-container" ref="userMenuRef"> 
          <div class="nav-user" @click.stop="showUserMenu = !showUserMenu"> 
            <img :src="user.avatarUrl" alt="User Avatar" class="user-avatar" />
            <span class="user-name">{{ user.name }}</span>
          </div>
          
          <ul v-if="showUserMenu" class="user-menu">
            <li @click="viewProfile">查看个人信息</li>
            <li @click="changePassword">修改密码</li>
            <li @click="logout" class="logout-item">退出登录</li>
          </ul>
      </div>
      
      <button class="hamburger" @click="showMenu = !showMenu">
        ☰
      </button>
    </div>
  </nav>

  <Teleport to="body">
    <div v-if="showMenu" class="mobile-sidebar" @click="showMenu=false">
      <SideBar @click.stop />
    </div>
  </Teleport>
</template>

<style scoped lang="scss">
.nav {
  position: fixed; top:0; left:0; right:0; height: 64px; background: #ffffff;
  border-bottom: 1px solid #e2e8f0; display: flex; align-items: center;
  justify-content: space-between; padding: 0 2rem; z-index: 999;
  box-shadow: 0 1px 3px rgba(0,0,0,.04);
}
.nav-group-left { display: flex; align-items: center; gap: 2.5rem; }
.nav-left { display:flex; align-items:center; gap:1rem; }
.logo { width:40px; height:40px; border-radius:8px; }
.title { font-weight: 600; font-size: 1.35rem; color: #20ae7c; letter-spacing: -0.5px; }

.nav-right {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.user-menu-container {
    position: relative;
}

.nav-user {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0;
  cursor: pointer;
  user-select: none; 
  transition: opacity 0.2s;
  
  &:hover {
    opacity: 0.8;
  }
}

.user-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  object-fit: cover;
  border: 2px solid #20ae7c;
}

.user-name {
  font-size: 1rem;
  font-weight: 500;
  color: #1e293b;
  @media (max-width: 500px) { 
    display: none;
  }
}

.user-menu {
  position: absolute;
  top: 100%;
  right: 0;
  z-index: 1000; 
  margin-top: 10px; 
  min-width: 150px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,.1);
  padding: 8px 0;
  list-style: none;
  margin: 0;
}

.user-menu li {
  padding: 10px 15px;
  font-size: 0.95rem;
  color: #334155;
  cursor: pointer;
  transition: background-color 0.2s;
  white-space: nowrap;
  
  &:hover {
    background-color: #f1f5f9;
  }
}

.user-menu .logout-item {
  border-top: 1px solid #f1f5f9;
  margin-top: 5px;
  padding-top: 10px;
  color: #ef4444;
}


.hamburger { display:none; font-size:1.8rem; color:#64748b; }

@media (max-width: 767px) { 
  .hamburger { 
    display:block; 
  }
  .user-menu-container {
    display: none;
  }
}
</style>