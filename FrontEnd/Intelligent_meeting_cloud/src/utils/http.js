import axios from 'axios'
import { ElMessage } from 'element-plus'
import 'element-plus/theme-chalk/el-message.css'
import router from "@/router";
import { useUserStore } from "@/stores/userStore";

// 创建axios实例
const httpInstance = axios.create({
  baseURL: '/api',
  timeout: 3000
})

// axios请求拦截器
httpInstance.interceptors.request.use(config => {
  const userStore = useUserStore();
  const token = userStore.userInfo?.token;
  if (token) {
    config.headers['token'] = token 
  }
  return config
}, e => Promise.reject(e))

// axios响应式拦截器
httpInstance.interceptors.response.use(res => res.data, e => {
  const msg = e.response?.data?.message || e.message || "请求失败";
  ElMessage({
    type:'warning',
    message:msg
  })

  const userStore = useUserStore();
  if (e.response.status === 401) {
    ElMessage.error("登录已过期，请重新登录");
    userStore.clearUserInfo();
    router.push('/login')
  }

  return Promise.reject(e)
})


export default httpInstance