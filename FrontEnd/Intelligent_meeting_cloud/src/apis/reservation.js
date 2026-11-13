import request from '@/utils/http';
import {
  addReservationMock,
  auditReservationMock,
  cancelReservationMock,
  getAdminReservationPageMock,
  getMyReservationsMock,
  getReservationsByRoomIdMock,
  updateReservationMock,
} from '@/mocks/platform/mockApi';

const USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false';

/**
 * 创建预约。
 * faceTicket：刷脸核身后拿到的一次性凭据，后端 FaceTicketInterceptor 会强制校验
 *（缺省/过期/已用 → 403，预约不会落库）。
 */
export function addReservation(data, faceTicket) {
  if (USE_MOCK) return addReservationMock(data);

  return request({
    url: '/user/reservation',
    method: 'post',
    data,
    timeout: 15000,
    headers: faceTicket ? { 'X-Face-Ticket': faceTicket } : {},
  });
}

export function getMyReservations() {
  if (USE_MOCK) return getMyReservationsMock();

  return request({
    url: '/user/reservation/my',
    method: 'get',
  });
}

export function getReservationsByRoomId(roomId) {
  if (USE_MOCK) return getReservationsByRoomIdMock(roomId);

  return request.get('/admin/reservation/page', {
    params: { roomId, pageSize: 100 },
  });
}

export function cancelReservation(id) {
  if (USE_MOCK) return cancelReservationMock(id);

  return request({
    url: `/user/reservation/cancel/${id}`,
    method: 'put',
  });
}

export function getAdminReservationPage(params) {
  if (USE_MOCK) return getAdminReservationPageMock(params);

  return request({
    url: '/admin/reservation/page',
    method: 'get',
    params,
  });
}

export function updateReservation(data) {
  if (USE_MOCK) return updateReservationMock(data);

  return request({
    url: '/admin/reservation',
    method: 'put',
    data,
  });
}

export function auditReservation(data) {
  if (USE_MOCK) return auditReservationMock(data);

  return request({
    url: '/admin/reservation/audit',
    method: 'post',
    data,
    timeout: 15000,
  });
}
