import request from '@/utils/http';
import {
  addUserMock,
  deleteUsersMock,
  getUserByIdMock,
  getUserPageMock,
  setUserActiveMock,
  updateUserMock,
} from '@/mocks/platform/mockApi';

const USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false';

export function getUserPage(params) {
  if (USE_MOCK) return getUserPageMock(params);

  return request({
    url: '/admin/user/page',
    method: 'get',
    params,
  });
}

export function addUser(data) {
  if (USE_MOCK) return addUserMock(data);

  return request({
    url: '/admin/user',
    method: 'post',
    data,
  });
}

export function updateUser(data) {
  if (USE_MOCK) return updateUserMock(data);

  return request({
    url: '/admin/user',
    method: 'put',
    data,
  });
}

export function deleteUsers(ids) {
  if (USE_MOCK) return deleteUsersMock(ids);

  return request({
    url: '/admin/user',
    method: 'delete',
    params: { ids: ids.join(',') },
  });
}

export function setUserActive(status, id) {
  if (USE_MOCK) return setUserActiveMock(status, id);

  return request({
    url: `/admin/user/active/${status}`,
    method: 'put',
    params: { id },
  });
}

export const getByIdAPI = (id) => {
  if (USE_MOCK) return getUserByIdMock(id);

  return request({
    url: `/admin/user/${id}`,
    method: 'GET',
  });
};
