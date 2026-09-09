import request from '@/utils/http';
import { getMyNotificationsMock } from '@/mocks/platform/mockApi';

const USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false';

export function getMyNotifications() {
  if (USE_MOCK) return getMyNotificationsMock();

  return request({
    url: '/user/notification/my',
    method: 'get',
  });
}
