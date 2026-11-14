import axios from 'axios';

const faceRequest = axios.create({
  baseURL: import.meta.env.VITE_FACE_API_URL || '/face-api',
  timeout: 120000,
});

faceRequest.interceptors.response.use(
  (res) => res.data,
  (error) => Promise.reject(error)
);

export function getFaceHealth() {
  return faceRequest.get('/health');
}

export function verifyFaceImage(file, room = 'A101') {
  const formData = new FormData();
  formData.append('image', file);
  formData.append('room', room);

  return faceRequest.post('/api/face/verify', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
}

export function enrollFaceImage(file, identityPayload = {}, adminToken = '') {
  const formData = new FormData();
  formData.append('image', file);

  Object.entries(identityPayload).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      formData.append(key, value);
    }
  });

  return faceRequest.post('/api/face/enroll', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
      'X-Face-Admin-Token': adminToken,
    },
  });
}
