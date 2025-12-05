import { createRouter, createWebHistory } from 'vue-router';
import Login from "@/views/Login";
import UserLayout from "@/views/User/Layout";
import Home from "@/views/User/Home";
import Booking from "@/views/User/Booking";
import Schedule from "@/views/User/Schedule";
import Control from "@/views/User/Control"; 
import UserProfile from "@/views/User/UserProfile";
import ChangePassword from "@/views/User/ChangePassword";
import ManagerLayout from '@/views/Manager/Layout';
import ManagerHome from '@/views/Manager/Home';
import Users from "@/views/Manager/Users";
import Rooms from "@/views/Manager/Rooms";
import Reservations from "@/views/Manager/Reservations";
import FeedBack from "@/views/Manager/FeedBack";
import ManagerProfile from "@/views/Manager/ManagerProfile";
import ManagerChangePassword from "@/views/Manager/ChangePassword";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
        path: '/',
        name: 'UserLayout',
        component: UserLayout,
        children: [
        {
          path: '',
          name: 'Home',
          component: Home,
        },
        {
          path: 'booking',
          name: 'Booking',
          component: Booking,
        },
        {
          path: 'schedule',
          name: 'Schedule',
          component: Schedule,
        },
        {
          path: 'control',
          name: 'Control',
          component: Control,
        },
        {
          path: '/profile',
          name: 'UserProfile',
          component: UserProfile,
          meta: { requiresAuth: true }
        },
        {
          path: '/change-password',
          name: 'ChangePassword',
          component: ChangePassword,
          meta: { requiresAuth: true }
        }
      ],
    },
    {
      path: '/manager',
      name: 'ManagerLayout',
      component: ManagerLayout,
      meta: { title: '管理员首页' },
      children: [
        {
          path: '',
          name: 'manager-home',
          component: ManagerHome,
        },        
        {
          path: 'users',
          name: 'Users',
          component: Users,
          meta: { title: '用户管理' },
        },
        {
          path: 'rooms',
          name: 'Rooms',
          component: Rooms,
          meta: { title: '会议室管理' },
        },
        {
          path: 'reservations',
          name: 'Reservations',
          component: Reservations,
          meta: { title: '预约管理' },
        },
        {
          path: 'feedback',
          name: 'FeedBack',
          component: FeedBack,
          meta: { title: '用户反馈处理' },
        },
        {
          path: 'profile',
          name: 'ManagerProfile',
          component: ManagerProfile,
          meta: { title: '我的信息' }
        },
        {
          path: 'change-password',
          name: 'ManagerChangePassword',
          component: ManagerChangePassword,
          meta: { title: '修改密码' }
        }
      ],
    },
    {
        path: '/login',
        name: 'Login',
        component: Login
    }
  ],
  //路由滚动规则配置
  scrollBehavior () {
    return {
      top: 0
    }
  }
});


export default router;