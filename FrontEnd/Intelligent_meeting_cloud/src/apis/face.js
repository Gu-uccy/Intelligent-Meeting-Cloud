import axios from 'axios';

// 人脸服务基地址：
//   开发环境由 vite proxy 把 /face-api 转发到 127.0.0.1:5001（见 vite.config.js）
//   也可以用 VITE_FACE_API_URL=http://127.0.0.1:5001 绕过代理
const faceRequest = axios.create({
  baseURL: import.meta.env.VITE_FACE_API_URL || '/face-api',
  timeout: 120000,
});

faceRequest.interceptors.response.use(
  (res) => res.data,
  (error) => Promise.reject(error)
);

/** 服务健康：算法、底库人数、当前阈值、依赖版本 */
export function getFaceHealth() {
  return faceRequest.get('/health');
}

/** 1:N 识别（返回 matched / identity / confidence / threshold / scores） */
export function verifyFaceImage(file) {
  const formData = new FormData();
  formData.append('image', file);

  return faceRequest.post('/api/face/verify', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
}

/** 录入/追加一张人脸样本（identity 用登录账号，保证识别结果能对上数据库用户） */
export function enrollFaceImage(file, identityPayload = {}) {
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
    },
  });
}

/**
 * 刷脸换「一次性预约凭据」：1:1 核身（识别结果必须等于当前登录账号）。
 * 返回的 ticket 要放进预约接口的 X-Face-Ticket 请求头。
 */
export function issueFaceTicket(file, { loginAccount, purpose = 'booking' } = {}) {
  const formData = new FormData();
  formData.append('image', file);
  formData.append('login_account', loginAccount);
  formData.append('purpose', purpose);

  return faceRequest.post('/api/face/ticket', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
}

/**
 * 刷脸解锁会议室：1:1 核身 → 校验「当前时段该会议室是否有本人有效预约」→ 驱动门禁。
 * 只有服务端判定 granted=true 才算开门，前端不做二次判断。
 */
export function unlockRoomByFace(file, { loginAccount, roomId }) {
  const formData = new FormData();
  formData.append('image', file);
  formData.append('login_account', loginAccount);
  formData.append('room_id', String(roomId));

  return faceRequest.post('/api/face/unlock', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
}

/** 刷脸开门后可选开灯（硬件层与 3D 灯同步） */
export function faceLight(on = true) {
  const formData = new FormData();
  formData.append('state', on ? 'true' : 'false');
  return faceRequest.post('/api/face/light', formData);
}

/** 人脸审计日志（最近 N 条） */
export function getFaceAudit(limit = 20) {
  return faceRequest.get('/api/face/audit', { params: { limit } });
}

/** 已注册身份与样本数 */
export function getFaceGallery() {
  return faceRequest.get('/api/face/gallery');
}
