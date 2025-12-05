import request from '@/utils/http';

// 用户端：分页查询会议室
export function getUserRoomPage(params) {
  return request({
    url: '/user/room/page',
    method: 'get',
    params
  });
}

// 用户端：获取会议室详情
export function getUserRoomDetail(id) {
  return request({
    url: `/user/room/${id}`,
    method: 'get'
  });
}

// 管理端：新增会议室
export function addRoom(data) {
  return request({
    url: '/admin/room',
    method: 'post',
    data
  });
}

// 管理端：修改会议室
export function updateRoom(data) {
  return request({
    url: '/admin/room',
    method: 'put',
    data
  });
}

// 管理端：删除会议室 (ids 为数组)
export function deleteRooms(ids) {
  return request({
    url: '/admin/room',
    method: 'delete',
    params: { ids: ids.join(',') }
  });
}

// 管理端：设置激活状态
export function setRoomActive(id, active) {
  return request({
    url: '/admin/room/active',
    method: 'put',
    params: { id, active }
  });
}

// 管理端：分页查询会议室
export function getAdminRoomPage(params) {
  return request({
    url: '/admin/room/page',
    method: 'get',
    params
  });
}