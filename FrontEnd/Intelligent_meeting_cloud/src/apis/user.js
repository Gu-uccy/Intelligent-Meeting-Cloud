import request from '@/utils/http';
import { loginMock, logoutMock, registerMock } from '@/mocks/platform/mockApi';

const USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false';

export const loginAPI = (userDto) => {
  if (USE_MOCK) return loginMock(userDto);

  return request({
    url: '/login',
    method: 'POST',
    data: userDto,
  });
};

export const logoutAPI = () => {
  if (USE_MOCK) return logoutMock();

  return request({
    url: '/logout',
    method: 'POST',
  });
};

export const registerAPI = (registerForm) => {
  if (USE_MOCK) return registerMock(registerForm);

  return request({
    url: '/register',
    method: 'POST',
    data: registerForm,
  });
};
