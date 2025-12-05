import { defineStore } from 'pinia'
import avatar from "@/assets/imgs/avatar.svg";

export const useUserStore = defineStore('user', {
  state: () => ({
    userInfo: {
      token: '',
      user: {loginAccount:'',image:avatar,username:'',isAdmin:0,id:0}
    }
  }),

  getters: {
    isLoggedIn: (state) => !!state.userInfo.token,
    loginAccount: (state) => state.userInfo.user?.loginAccount || '用户'
  },

  actions: {
    setUserInfo(info) {
      this.userInfo = {
        token: info.token || '',
        user: info.user || {loginAccount:'admin',image:avatar,username:'管理员',isAdmin:0,id:0}
      }
    },

    clearUserInfo() {
      this.userInfo = { token: '', user: {} }
    }
  },

  persist: true
})