import request from '@/utils/http'

// 获取统计数据
export function getStatistics() {
  return request.get('/admin/statistics/近7天')
}