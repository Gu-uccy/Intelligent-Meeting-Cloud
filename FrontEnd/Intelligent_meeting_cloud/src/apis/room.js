import request from '@/utils/http';
import {
  addRoomMock,
  deleteRoomsMock,
  getAdminRoomPageMock,
  getTimeSlotsMock,
  getUserRoomDetailMock,
  getUserRoomPageMock,
  setRoomActiveMock,
  updateRoomMock,
} from '@/mocks/platform/mockApi';

const USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false';

export function getUserRoomPage(params) {
  if (USE_MOCK) return getUserRoomPageMock(params);

  return request({
    url: '/user/room/page',
    method: 'get',
    params,
  });
}

export function getUserRoomDetail(id) {
  if (USE_MOCK) return getUserRoomDetailMock(id);

  return request({
    url: `/user/room/${id}`,
    method: 'get',
  });
}

export function getTimeSlots(params) {
  if (USE_MOCK) return getTimeSlotsMock(params);

  return request.get('/user/reservation/slots', { params });
}

export function addRoom(data) {
  if (USE_MOCK) return addRoomMock(data);

  return request({
    url: '/admin/room',
    method: 'post',
    data,
  });
}

export function updateRoom(data) {
  if (USE_MOCK) return updateRoomMock(data);

  return request({
    url: '/admin/room',
    method: 'put',
    data,
  });
}

export function deleteRooms(ids) {
  if (USE_MOCK) return deleteRoomsMock(ids);

  return request({
    url: '/admin/room',
    method: 'delete',
    params: { ids: ids.join(',') },
  });
}

export function setRoomActive(id, active) {
  if (USE_MOCK) return setRoomActiveMock(id, active);

  return request({
    url: '/admin/room/active',
    method: 'put',
    params: { id, active },
  });
}

export function getAdminRoomPage(params) {
  if (USE_MOCK) return getAdminRoomPageMock(params);

  return request({
    url: '/admin/room/page',
    method: 'get',
    params,
  });
}
