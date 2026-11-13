import request from '@/utils/http';
import { getFaultPageMock, handleFaultMock, reportFaultMock } from '@/mocks/platform/mockApi';

const USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false';

export function reportFault(data) {
  if (USE_MOCK) return reportFaultMock(data);

  return request({
    url: '/user/equipment/fault',
    method: 'post',
    data,
  });
}

export function getFaultPage(params) {
  if (USE_MOCK) return getFaultPageMock(params);

  return request.get('/admin/equipment/page', {
    params,
  });
}

export function handleFault(params) {
  if (USE_MOCK) return handleFaultMock(params);

  return request({
    url: '/admin/equipment/handle',
    method: 'put',
    params,
  });
}
