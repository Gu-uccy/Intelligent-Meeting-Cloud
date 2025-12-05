import request from '@/utils/http';

// 分页获取用户列表
export function getUserPage(params) {
  return request({
    url: '/admin/user/page',
    method: 'get',
    params
  });
}

// 新增用户
export function addUser(data) {
  return request({
    url: '/admin/user',
    method: 'post',
    data
  });
}

// 修改用户
export function updateUser(data) {
  return request({
    url: '/admin/user',
    method: 'put',
    data
  });
}

// 删除用户
export function deleteUsers(ids) {
  return request({
    url: '/admin/user',
    method: 'delete',
    params: { ids: ids.join(',') }
  });
}

// 设置用户状态（激活/禁用）
export function setUserActive(status, id) {
  return request({
    url: `/admin/user/active/${status}`,
    method: 'put',
    params: { id }
  });
}

// 根据ID获取用户详情
export const getByIdAPI = (id) => {
  return request({
    url: `/admin/user/${id}`,
    method: 'GET'
  })
}