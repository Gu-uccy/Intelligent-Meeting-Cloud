import request from '@/utils/http'

// 通用文件上传
export function uploadFile(file) {
  const formData = new FormData()
  formData.append('file', file)

  return request.post('/admin/common/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}