<script setup>
import { useRouter, useRoute } from 'vue-router'
import { computed } from 'vue'

import HomeIcon from "@/assets/imgs/home.svg";
import UserIcon from '@/assets/imgs/user.svg'
import RoomIcon from '@/assets/imgs/room.svg'
import ReservationIcon from '@/assets/imgs/reservation.svg'
import FeedbackIcon from "@/assets/imgs/feedback.svg";
import ProfileIcon from "@/assets/imgs/profile.svg";

const router = useRouter()
const route = useRoute()
const activePath = computed(() => route.path)

const menu = [
  { path: '/manager', label: '首页', icon: HomeIcon },
  { path: '/manager/users', label: '用户管理', icon: UserIcon },
  { path: '/manager/rooms', label: '会议室管理', icon: RoomIcon },
  { path: '/manager/reservations', label: '预订管理', icon: ReservationIcon },
  { path: '/manager/feedback', label: '用户反馈处理', icon: FeedbackIcon },
  { path: '/manager/profile', label: '我的信息', icon: ProfileIcon }
]

const go = (p) => router.push(p)
</script>

<template>
  <aside class="sidebar">
    <ul>
      <li v-for="m in menu" :key="m.path"
          :class="{ active: activePath === m.path }"
          @click="go(m.path)">
        <span class="icon"><img :src="m.icon"></img></span>
        <span class="txt">{{ m.label }}</span>
      </li>
    </ul>
  </aside>
</template>

<style scoped lang="scss">
.sidebar {
  width: 210px;
  background: #0b7e7f;
  color: #cbd5e1;
  padding: 1.5rem 0;
  position: fixed;
  top: 64px;
  bottom: 0;
  left: 0;
  overflow-y: auto;
  border-right: 1px solid #086061;
}
ul { list-style:none; padding:0 1rem; }
li {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  margin: 0.25rem 0;
  cursor: pointer;
  border-radius: 10px;
  transition: all .5s ease;
  font-weight: 500;
}
li:hover { 
  background: #20ae7c87;
  color: #e2e8f0;
}
.active { 
  background: #20ae7c; 
  color: #ffffff; 
  box-shadow: 0 2px 8px rgba(32, 174, 124, 0.3);
}
.icon img {
  width: 20px;
  height: 20px;
  object-fit: contain;
  display: block;
}
.txt { font-size: 0.95rem; letter-spacing: 0.3px; }
</style>