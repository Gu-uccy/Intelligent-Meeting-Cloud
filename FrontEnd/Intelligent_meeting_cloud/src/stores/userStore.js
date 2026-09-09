import { defineStore } from 'pinia';
import avatar from '@/assets/imgs/avatar.svg';

const fallbackUser = {
  loginAccount: '',
  image: avatar,
  username: '',
  isAdmin: 0,
  id: 0,
};

export const useUserStore = defineStore('user', {
  state: () => ({
    userInfo: {
      token: '',
      ...fallbackUser,
      user: { ...fallbackUser },
    },
  }),

  getters: {
    isLoggedIn: (state) => !!state.userInfo.token,
    loginAccount: (state) => state.userInfo.user?.loginAccount || '用户',
  },

  actions: {
    setUserInfo(info) {
      const nextUser = info.user ? { ...fallbackUser, ...info.user } : { ...fallbackUser, ...info };

      this.userInfo = {
        token: info.token || '',
        ...nextUser,
        user: nextUser,
      };
    },

    clearUserInfo() {
      this.userInfo = {
        token: '',
        ...fallbackUser,
        user: {},
      };
    },
  },

  persist: true,
});
