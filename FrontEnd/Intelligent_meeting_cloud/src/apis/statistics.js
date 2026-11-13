import request from '@/utils/http';
import { getStatisticsMock } from '@/mocks/platform/mockApi';

const USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false';

export function getStatistics() {
  if (USE_MOCK) return getStatisticsMock();

  return request.get('/admin/statistics');
}
