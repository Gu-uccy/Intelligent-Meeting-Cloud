import request from '@/utils/http';
import { uploadFileMock } from '@/mocks/platform/mockApi';

const USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false';

export function uploadFile(file) {
  if (USE_MOCK) return uploadFileMock(file);

  const formData = new FormData();
  formData.append('file', file);

  return request.post('/admin/common/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
}
