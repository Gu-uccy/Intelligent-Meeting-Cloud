import request from '@/utils/http';

// 用户：提交预约
export function addReservation(data) {
  return request({
    url: '/user/reservation',
    method: 'post',
    data,
    timeout: 15000
  });
}

// 用户：获取我的预约
export function getMyReservations() {
  return request({
    url: '/user/reservation/my',
    method: 'get'
  });
}

// 用户：取消预约
export function cancelReservation(id) {
  return request({
    url: `/user/reservation/cancel/${id}`,
    method: 'put'
  });
}

// 管理员：分页查询预约列表
export function getAdminReservationPage(params) {
  return request({
    url: '/admin/reservation/page',
    method: 'get',
    params
  });
}

// 管理员：根据ID更新预约
export function updateReservation(data) {
  return request({
    url: '/admin/reservation',
    method: 'put',
    data
  });
}

export function auditReservation(data) {
  // data: { id: 1, status: 1, remark: "通过" }
  return request.post('/admin/reservation/audit', data)
}