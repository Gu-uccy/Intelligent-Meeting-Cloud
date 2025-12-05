import request from '@/utils/http';

// 用户：上报故障
export function reportFault(data) {
  return request({
    url: '/user/equipment/fault',
    method: 'post',
    data
  });
}

// 管理员：处理故障
export function getFaultPage(params) {
  return request.get('/admin/equipment/page', { 
    params // { page, pageSize, status, faultNo ... }
  })
}

export function handleFault(params) {
  return request({
    url: '/admin/equipment/handle',
    method: 'put',
    params
  });
}
