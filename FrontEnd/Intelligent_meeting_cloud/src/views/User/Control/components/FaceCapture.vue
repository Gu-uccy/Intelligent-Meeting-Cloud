<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { enrollFaceImage, getFaceHealth, verifyFaceImage } from '@/apis/face';
import { getMyReservations } from '@/apis/reservation';
import { useUserStore } from '@/stores/userStore';

const userStore = useUserStore();

const videoRef = ref(null);
const canvasRef = ref(null);
const stream = ref(null);
const cameraReady = ref(false);
const isStarting = ref(false);
const isVerifying = ref(false);
const isEnrolling = ref(false);
const errorMessage = ref('');
const successMessage = ref('');
const rawResult = ref(null);
const accessDecision = ref(null);
const snapshotUrl = ref('');
const enrollResult = ref(null);
const healthStatus = ref({
  label: '未检测',
  detail: '点击检测服务确认树莓派 5001 端口状态',
  ok: false,
});

const currentUser = computed(() => userStore.userInfo?.user || {});
const loginAccount = computed(() => currentUser.value.loginAccount || '');
const displayName = computed(() => currentUser.value.username || currentUser.value.loginAccount || '当前用户');
const enrollIdentity = computed(() => loginAccount.value || `user_${currentUser.value.id || 'local'}`);
const badgeText = computed(() => {
  const source = displayName.value || enrollIdentity.value;
  return source.slice(0, 2).toUpperCase();
});

const currentMeeting = computed(() => ({
  room: 'A101 智能会议室',
  topic: '人脸门禁演示预约',
  reservationNo: `FACE-DEMO-${currentUser.value.id || 'local'}`,
  timeRange: '当前时段',
  host: displayName.value,
  participants: [displayName.value],
}));

const accessLogs = ref([
  {
    id: 1,
    time: '13:56:18',
    person: displayName.value,
    room: 'A101',
    result: '通过',
    action: '预约人签到 / 门禁开启',
  },
  {
    id: 2,
    time: '13:48:42',
    person: '未知人员',
    room: 'A101',
    result: '拒绝',
    action: '未匹配底库 / 记录异常',
  },
]);

const doorStatus = computed(() => {
  if (!accessDecision.value) return { label: '待核验', icon: 'fa-lock', tone: 'idle' };
  if (accessDecision.value.allowed) return { label: '已开门', icon: 'fa-door-open', tone: 'success' };
  return { label: '保持关闭', icon: 'fa-lock', tone: 'danger' };
});

const signInStatus = computed(() => {
  if (!accessDecision.value) return { label: '未签到', icon: 'fa-clipboard-list', tone: 'idle' };
  if (accessDecision.value.allowed) return { label: '已自动签到', icon: 'fa-clipboard-check', tone: 'success' };
  return { label: '未授权', icon: 'fa-ban', tone: 'danger' };
});

const roomStatus = computed(() => {
  if (!accessDecision.value) return { label: '已预约', icon: 'fa-calendar-check', tone: 'idle' };
  if (accessDecision.value.allowed) return { label: '使用中', icon: 'fa-users-viewfinder', tone: 'success' };
  return { label: '异常访问', icon: 'fa-triangle-exclamation', tone: 'warning' };
});

const climateStatus = computed(() => {
  if (!accessDecision.value) return { label: '待机', icon: 'fa-sliders', tone: 'idle' };
  if (accessDecision.value.allowed) return { label: '自动模式', icon: 'fa-fan', tone: 'success' };
  return { label: '不联动', icon: 'fa-circle-pause', tone: 'idle' };
});

const resultTitle = computed(() => {
  if (!accessDecision.value) return '等待刷脸核验';
  return accessDecision.value.allowed ? '允许进入' : '拒绝进入';
});

const resultClass = computed(() => {
  if (!accessDecision.value) return '';
  return accessDecision.value.allowed ? 'success' : 'warning';
});

const serviceClass = computed(() => (healthStatus.value.ok ? 'online' : 'offline'));

function nowTime() {
  return new Date().toLocaleTimeString('zh-CN', { hour12: false });
}

function getIdentityKey(identity) {
  if (!identity) return '';
  const fileName = String(identity).split(/[\\/]/).pop() || '';
  return fileName.replace(/\.[^.]+$/, '');
}

function resolveProfile(identity) {
  const identityKey = getIdentityKey(identity);
  if (identityKey === enrollIdentity.value || identityKey === loginAccount.value) {
    return {
      id: identityKey,
      name: displayName.value,
      loginAccount: loginAccount.value,
      role: '当前登录用户',
      department: '会议预约用户',
      badge: badgeText.value,
    };
  }

  if (identityKey === 'id_1') {
    return {
      id: 'id_1',
      name: 'Test User',
      loginAccount: 'test_user',
      role: '预约人',
      department: '产品研发部',
      badge: 'TU',
    };
  }

  return {
    id: identityKey || 'unknown',
    name: identityKey || '未知人员',
    loginAccount: '',
    role: '访客',
    department: '未登记',
    badge: '??',
  };
}

function buildAccessDecision(faceResult) {
  if (!faceResult?.matched) {
    return {
      allowed: false,
      reason: faceResult?.error || '未匹配到底库人员，无法确认会议权限',
      profile: {
        id: 'unknown',
        name: '未知人员',
        loginAccount: '',
        role: '未登记',
        department: '未登记',
        badge: '?',
      },
      action: '门禁保持关闭，生成异常访问记录',
    };
  }

  const resolvedProfile = resolveProfile(faceResult.identity);
  // 1:1 核身口径：识别出的身份必须是当前登录账号，否则一律不放行。
  // （旧版本在这里用「演示预约」兜底直接放行，属于任务书明确禁止的「失败默认放行」，已移除）
  const allowedByCurrentUser = Boolean(
    resolvedProfile.loginAccount && resolvedProfile.loginAccount === loginAccount.value
  );
  const allowed = allowedByCurrentUser;
  const profile = resolvedProfile;

  return {
    allowed,
    reason: allowed
      ? '识别人员与当前登录账号一致，且门禁联动已由服务端复核预约时段'
      : '识别成功，但识别到的身份与当前登录账号不一致',
    profile,
    action: allowed
      ? '记录签到、联动门禁（门禁是否真正开启由服务端预约校验结果决定）'
      : '门禁保持关闭，仅记录一次异常访问',
  };
}

function appendAccessLog(decision) {
  accessLogs.value.unshift({
    id: Date.now(),
    time: nowTime(),
    person: decision.profile.name,
    room: 'A101',
    result: decision.allowed ? '通过' : '拒绝',
    action: decision.action,
  });
  accessLogs.value = accessLogs.value.slice(0, 6);
}

async function checkFaceService() {
  errorMessage.value = '';
  healthStatus.value = {
    label: '检测中',
    detail: '正在连接树莓派人脸识别服务',
    ok: false,
  };

  try {
    const health = await getFaceHealth();
    healthStatus.value = {
      label: '在线',
      detail: `${health.model_name || 'ArcFace'} / 阈值 ${health.threshold ?? '--'}`,
      ok: true,
    };
  } catch (error) {
    healthStatus.value = {
      label: '离线',
      detail: '无法连接树莓派 5001 人脸识别服务',
      ok: false,
    };
    errorMessage.value = '无法连接人脸识别服务，请确认树莓派 5001 服务已启动';
  }
}

async function startCamera() {
  errorMessage.value = '';
  successMessage.value = '';
  rawResult.value = null;
  accessDecision.value = null;
  isStarting.value = true;

  try {
    stopCamera();
    stream.value = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: 960 },
        height: { ideal: 720 },
        facingMode: 'user',
      },
      audio: false,
    });

    if (videoRef.value) {
      videoRef.value.srcObject = stream.value;
      await videoRef.value.play();
      cameraReady.value = true;
    }
  } catch (error) {
    errorMessage.value = '无法打开摄像头，请允许浏览器摄像头权限';
    cameraReady.value = false;
  } finally {
    isStarting.value = false;
  }
}

function stopCamera() {
  if (stream.value) {
    stream.value.getTracks().forEach((track) => track.stop());
  }
  stream.value = null;
  cameraReady.value = false;
  if (videoRef.value) {
    videoRef.value.srcObject = null;
  }
}

function canvasToBlob(canvas) {
  return new Promise((resolve) => {
    canvas.toBlob((blob) => resolve(blob), 'image/jpeg', 0.9);
  });
}

async function captureSnapshotBlob() {
  if (!videoRef.value || !canvasRef.value || !cameraReady.value) {
    throw new Error('请先打开摄像头');
  }

  const video = videoRef.value;
  const canvas = canvasRef.value;
  const width = video.videoWidth || 960;
  const height = video.videoHeight || 720;

  canvas.width = width;
  canvas.height = height;
  canvas.getContext('2d').drawImage(video, 0, 0, width, height);

  if (snapshotUrl.value) URL.revokeObjectURL(snapshotUrl.value);
  const blob = await canvasToBlob(canvas);
  snapshotUrl.value = URL.createObjectURL(blob);
  return blob;
}

async function captureAndVerify() {
  errorMessage.value = '';
  successMessage.value = '';
  rawResult.value = null;
  accessDecision.value = null;
  isVerifying.value = true;

  try {
    const blob = await captureSnapshotBlob();
    const file = new File([blob], `face-${Date.now()}.jpg`, { type: 'image/jpeg' });
    rawResult.value = await verifyFaceImage(file);
    accessDecision.value = buildAccessDecision(rawResult.value);
    appendAccessLog(accessDecision.value);
  } catch (error) {
    const responseError = error?.response?.data?.error;
    const fallbackResult = {
      matched: false,
      error: responseError || error?.message || '人脸识别失败，请重新拍照',
    };
    rawResult.value = fallbackResult;
    accessDecision.value = buildAccessDecision(fallbackResult);
    appendAccessLog(accessDecision.value);
    errorMessage.value = fallbackResult.error;
  } finally {
    isVerifying.value = false;
  }
}

async function captureAndEnroll() {
  errorMessage.value = '';
  successMessage.value = '';
  enrollResult.value = null;
  isEnrolling.value = true;

  try {
    const blob = await captureSnapshotBlob();
    const file = new File([blob], `${enrollIdentity.value}.jpg`, { type: 'image/jpeg' });
    enrollResult.value = await enrollFaceImage(file, {
      identity: enrollIdentity.value,
      login_account: loginAccount.value,
      username: displayName.value,
      user_id: currentUser.value.id,
    });

    successMessage.value = `已录入 ${displayName.value} 的人脸，可直接刷脸核验`;
    await checkFaceService();
  } catch (error) {
    const responseError = error?.response?.data?.error;
    errorMessage.value = responseError || error?.message || '人脸录入失败，请调整光线后重新拍照';
  } finally {
    isEnrolling.value = false;
  }
}

// —— 无摄像头时的兜底：直接上传照片完成录入/核验（答辩现场或笔记本无摄像头时常用）——
const enrollUploadRef = ref(null);
const verifyUploadRef = ref(null);

async function enrollFile(file) {
  errorMessage.value = '';
  successMessage.value = '';
  enrollResult.value = null;
  isEnrolling.value = true;
  try {
    enrollResult.value = await enrollFaceImage(file, {
      identity: enrollIdentity.value,
      login_account: loginAccount.value,
      username: displayName.value,
      user_id: currentUser.value.id,
    });
    successMessage.value = `已录入 ${displayName.value} 的人脸，可直接刷脸核验`;
    await checkFaceService();
  } catch (error) {
    const responseError = error?.response?.data?.error;
    errorMessage.value = responseError || error?.message || '人脸录入失败，请换一张更清晰的正面照';
  } finally {
    isEnrolling.value = false;
  }
}

async function verifyFile(file) {
  errorMessage.value = '';
  successMessage.value = '';
  rawResult.value = null;
  accessDecision.value = null;
  isVerifying.value = true;
  try {
    rawResult.value = await verifyFaceImage(file);
    accessDecision.value = buildAccessDecision(rawResult.value);
    appendAccessLog(accessDecision.value);
  } catch (error) {
    const responseError = error?.response?.data?.error;
    const fallbackResult = {
      matched: false,
      error: responseError || error?.message || '人脸识别失败，请换一张照片重试',
    };
    rawResult.value = fallbackResult;
    accessDecision.value = buildAccessDecision(fallbackResult);
    appendAccessLog(accessDecision.value);
    errorMessage.value = fallbackResult.error;
  } finally {
    isVerifying.value = false;
  }
}

function onEnrollUpload(event) {
  const file = event.target.files?.[0];
  if (file) enrollFile(file);
  event.target.value = '';
}

function onVerifyUpload(event) {
  const file = event.target.files?.[0];
  if (file) verifyFile(file);
  event.target.value = '';
}

onMounted(() => {
  getMyReservations().catch(() => {});
  checkFaceService();
});

onBeforeUnmount(() => {
  stopCamera();
  if (snapshotUrl.value) URL.revokeObjectURL(snapshotUrl.value);
});
</script>

<template>
  <article class="panel face-panel">
    <div class="panel-header">
      <div>
        <h2>会议室刷脸门禁与签到</h2>
        <span>先录入当前用户人脸，再进行预约权限核验、签到和门禁联动</span>
      </div>
      <div class="header-tools">
        <span class="service-pill" :class="serviceClass">
          <i class="fa-solid" :class="healthStatus.ok ? 'fa-circle-check' : 'fa-circle-exclamation'"></i>
          {{ healthStatus.label }}
        </span>
        <button class="small-button" type="button" @click="checkFaceService">
          <i class="fa-solid fa-heart-pulse"></i>
          检测服务
        </button>
      </div>
    </div>

    <div class="meeting-strip">
      <div>
        <span>当前会议室</span>
        <strong>{{ currentMeeting.room }}</strong>
      </div>
      <div>
        <span>当前预约</span>
        <strong>{{ currentMeeting.topic }}</strong>
      </div>
      <div>
        <span>预约时段</span>
        <strong>{{ currentMeeting.timeRange }}</strong>
      </div>
      <div>
        <span>录入身份</span>
        <strong>{{ displayName }}</strong>
      </div>
    </div>

    <div class="face-content">
      <section class="camera-section">
        <div class="camera-box">
          <video ref="videoRef" class="camera-video" playsinline muted></video>
          <div v-if="!cameraReady" class="camera-placeholder">
            <i class="fa-solid fa-camera"></i>
            <span>摄像头未开启</span>
          </div>
        </div>

        <div class="face-actions">
          <button type="button" class="action-button" :disabled="isStarting" @click="startCamera">
            <i class="fa-solid" :class="isStarting ? 'fa-spinner fa-spin' : 'fa-video'"></i>
            {{ isStarting ? '开启中...' : '打开摄像头' }}
          </button>
          <button type="button" class="action-button enroll" :disabled="!cameraReady || isEnrolling" @click="captureAndEnroll">
            <i class="fa-solid" :class="isEnrolling ? 'fa-spinner fa-spin' : 'fa-user-plus'"></i>
            {{ isEnrolling ? '录入中...' : '录入当前用户' }}
          </button>
          <button type="button" class="action-button primary" :disabled="!cameraReady || isVerifying" @click="captureAndVerify">
            <i class="fa-solid" :class="isVerifying ? 'fa-spinner fa-spin' : 'fa-user-check'"></i>
            {{ isVerifying ? '核验中...' : '刷脸核验' }}
          </button>
          <button type="button" class="icon-only" :disabled="!cameraReady" title="关闭摄像头" @click="stopCamera">
            <i class="fa-solid fa-power-off"></i>
          </button>
        </div>
      </section>

      <section class="verification-section">
        <!-- 无摄像头兜底：上传照片走同一条自研链路（录入 / 核验） -->
        <div class="upload-fallback">
          <span><i class="fa-solid fa-upload"></i> 没有摄像头？用照片同样可以</span>
          <div class="upload-actions">
            <button type="button" class="action-button" :disabled="isEnrolling" @click="enrollUploadRef.click()">
              <i class="fa-solid fa-id-card"></i> 上传照片录入
            </button>
            <button type="button" class="action-button" :disabled="isVerifying" @click="verifyUploadRef.click()">
              <i class="fa-solid fa-user-check"></i> 上传照片核验
            </button>
          </div>
          <input ref="enrollUploadRef" type="file" accept="image/*" class="hidden-upload" @change="onEnrollUpload" />
          <input ref="verifyUploadRef" type="file" accept="image/*" class="hidden-upload" @change="onVerifyUpload" />
        </div>
        <div class="enroll-card">
          <div class="identity-avatar">{{ badgeText }}</div>
          <div>
            <span class="result-label">人脸录入</span>
            <strong>{{ enrollResult?.enrolled ? '已录入' : '等待录入' }}</strong>
            <p>保存身份：{{ enrollIdentity }}。录入后会写入树莓派人脸库并刷新识别缓存。</p>
          </div>
        </div>

        <div v-if="successMessage" class="face-success">
          <i class="fa-solid fa-circle-check"></i>
          {{ successMessage }}
        </div>

        <div v-if="errorMessage" class="face-error">
          <i class="fa-solid fa-triangle-exclamation"></i>
          {{ errorMessage }}
        </div>

        <div class="identity-card" :class="resultClass">
          <div class="identity-avatar">
            {{ accessDecision?.profile?.badge || '?' }}
          </div>
          <div>
            <span class="result-label">核验结论</span>
            <strong>{{ resultTitle }}</strong>
            <p>{{ accessDecision?.reason || '等待拍照后调用树莓派人脸识别服务' }}</p>
          </div>
        </div>

        <div class="profile-grid">
          <div>
            <span>识别人员</span>
            <strong>{{ accessDecision?.profile?.name || '--' }}</strong>
          </div>
          <div>
            <span>人员身份</span>
            <strong>{{ accessDecision?.profile?.role || '--' }}</strong>
          </div>
          <div>
            <span>部门</span>
            <strong>{{ accessDecision?.profile?.department || '--' }}</strong>
          </div>
          <div>
            <span>账号</span>
            <strong>{{ accessDecision?.profile?.loginAccount || '--' }}</strong>
          </div>
        </div>

        <div class="score-card">
          <span>识别分数</span>
          <strong>
            {{ typeof rawResult?.distance === 'number' ? rawResult.distance.toFixed(4) : '--' }}
          </strong>
          <small>阈值 {{ rawResult?.threshold ?? '--' }}，距离越低匹配越稳定</small>
        </div>

        <div v-if="snapshotUrl" class="snapshot">
          <span>最近拍照</span>
          <img :src="snapshotUrl" alt="最近拍照">
        </div>
      </section>
    </div>

    <section class="workflow-grid">
      <article class="workflow-card" :class="doorStatus.tone">
        <i class="fa-solid" :class="doorStatus.icon"></i>
        <span>门禁状态</span>
        <strong>{{ doorStatus.label }}</strong>
      </article>
      <article class="workflow-card" :class="signInStatus.tone">
        <i class="fa-solid" :class="signInStatus.icon"></i>
        <span>签到状态</span>
        <strong>{{ signInStatus.label }}</strong>
      </article>
      <article class="workflow-card" :class="roomStatus.tone">
        <i class="fa-solid" :class="roomStatus.icon"></i>
        <span>会议室状态</span>
        <strong>{{ roomStatus.label }}</strong>
      </article>
      <article class="workflow-card" :class="climateStatus.tone">
        <i class="fa-solid" :class="climateStatus.icon"></i>
        <span>设备联动</span>
        <strong>{{ climateStatus.label }}</strong>
      </article>
    </section>

    <section class="access-log">
      <div class="access-log-header">
        <div>
          <h3>门禁访问记录</h3>
          <span>{{ healthStatus.detail }}</span>
        </div>
        <span class="reservation-pill">{{ currentMeeting.reservationNo }}</span>
      </div>

      <div class="log-table">
        <div class="log-head">
          <span>时间</span>
          <span>人员</span>
          <span>会议室</span>
          <span>结果</span>
          <span>动作</span>
        </div>
        <div v-for="log in accessLogs" :key="log.id" class="log-row">
          <span>{{ log.time }}</span>
          <span>{{ log.person }}</span>
          <span>{{ log.room }}</span>
          <span :class="log.result === '通过' ? 'pass-text' : 'deny-text'">{{ log.result }}</span>
          <span>{{ log.action }}</span>
        </div>
      </div>
    </section>

    <canvas ref="canvasRef" class="hidden-canvas"></canvas>
  </article>
</template>

<style scoped>
.panel {
  background: rgba(30, 41, 59, 0.62);
  border: 1px solid rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(12px);
  border-radius: 8px;
  box-shadow: 0 18px 45px rgba(2, 6, 23, 0.2);
  overflow: hidden;
}

.panel-header {
  min-height: 72px;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.panel-header h2 {
  margin: 0 0 0.2rem;
  font-size: 1.08rem;
  color: #f8fafc;
}

.panel-header span {
  color: #94a3b8;
  font-size: 0.82rem;
}

.header-tools,
.face-actions {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  flex-wrap: wrap;
}

.small-button,
.action-button,
.icon-only,
.service-pill,
.reservation-pill {
  height: 38px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(15, 23, 42, 0.62);
  color: #e2e8f0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.small-button,
.action-button,
.reservation-pill {
  padding: 0 0.85rem;
}

.small-button,
.action-button,
.icon-only {
  cursor: pointer;
}

.service-pill.online {
  color: #86efac;
}

.service-pill.offline {
  color: #fca5a5;
}

.meeting-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1px;
  background: rgba(255, 255, 255, 0.08);
}

.meeting-strip div {
  min-height: 76px;
  padding: 0.95rem 1.1rem;
  background: rgba(15, 23, 42, 0.42);
}

.meeting-strip span,
.profile-grid span,
.score-card span,
.snapshot span,
.workflow-card span {
  display: block;
  color: #94a3b8;
  font-size: 0.78rem;
  margin-bottom: 0.25rem;
}

.meeting-strip strong,
.profile-grid strong,
.score-card strong,
.workflow-card strong {
  color: #f8fafc;
  font-size: 1rem;
}

.face-content {
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(320px, 0.92fr);
  gap: 1rem;
  padding: 1rem;
}

.camera-section,
.verification-section {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.camera-box {
  position: relative;
  min-height: 372px;
  border-radius: 8px;
  overflow: hidden;
  background: rgba(15, 23, 42, 0.76);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.camera-video {
  width: 100%;
  height: 100%;
  min-height: 372px;
  object-fit: cover;
  display: block;
}

.camera-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 0.8rem;
  color: #94a3b8;
}

.camera-placeholder i {
  font-size: 2.6rem;
  color: #38bdf8;
}

.action-button.primary {
  color: #ffffff;
  background: rgba(32, 174, 124, 0.84);
  border-color: rgba(45, 212, 191, 0.45);
}

.action-button.enroll {
  color: #ffffff;
  background: rgba(59, 130, 246, 0.84);
  border-color: rgba(147, 197, 253, 0.45);
}

.action-button:disabled,
.icon-only:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.icon-only {
  width: 38px;
}

.face-error,
.face-success,
.enroll-card,
.identity-card,
.profile-grid,
.score-card,
.snapshot,
.access-log {
  border-radius: 8px;
  padding: 0.85rem;
  background: rgba(15, 23, 42, 0.48);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.face-error {
  color: #fecaca;
  background: rgba(248, 113, 113, 0.14);
  border-color: rgba(248, 113, 113, 0.32);
}

.face-success {
  color: #bbf7d0;
  background: rgba(34, 197, 94, 0.14);
  border-color: rgba(74, 222, 128, 0.32);
}

.enroll-card,
.identity-card {
  min-height: 126px;
  display: grid;
  grid-template-columns: 76px minmax(0, 1fr);
  align-items: center;
  gap: 0.9rem;
  color: #cbd5e1;
}

.identity-card.success {
  border-color: rgba(52, 211, 153, 0.44);
  background: rgba(16, 185, 129, 0.14);
}

.identity-card.warning {
  border-color: rgba(251, 191, 36, 0.42);
  background: rgba(251, 191, 36, 0.12);
}

.identity-avatar {
  width: 66px;
  height: 66px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(56, 189, 248, 0.16);
  color: #bae6fd;
  font-size: 1.2rem;
  font-weight: 800;
}

.result-label {
  display: block;
  color: #94a3b8;
  font-size: 0.78rem;
  margin-bottom: 0.25rem;
}

.enroll-card strong,
.identity-card strong {
  display: block;
  color: #f8fafc;
  font-size: 1.45rem;
}

.enroll-card p,
.identity-card p,
.score-card small {
  margin: 0.45rem 0 0;
  color: #cbd5e1;
}

.profile-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
}

.score-card strong {
  display: block;
  font-size: 1.5rem;
}

.snapshot {
  display: grid;
  gap: 0.5rem;
  color: #94a3b8;
}

.snapshot img {
  width: 100%;
  max-height: 150px;
  object-fit: cover;
  border-radius: 8px;
}

.workflow-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1rem;
  padding: 0 1rem 1rem;
}

.workflow-card {
  min-height: 112px;
  border-radius: 8px;
  padding: 1rem;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(15, 23, 42, 0.48);
}

.workflow-card i {
  color: #93c5fd;
  font-size: 1.25rem;
  margin-bottom: 0.7rem;
}

.workflow-card.success i,
.workflow-card.success strong {
  color: #86efac;
}

.workflow-card.warning i,
.workflow-card.warning strong {
  color: #fde68a;
}

.workflow-card.danger i,
.workflow-card.danger strong {
  color: #fca5a5;
}

.access-log {
  margin: 0 1rem 1rem;
  padding: 0;
  overflow: hidden;
}

.access-log-header {
  min-height: 68px;
  padding: 1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.access-log-header h3 {
  margin: 0 0 0.2rem;
  font-size: 1rem;
}

.access-log-header span {
  color: #94a3b8;
  font-size: 0.82rem;
}

.log-table {
  padding: 0.75rem 1rem 1rem;
}

.log-head,
.log-row {
  display: grid;
  grid-template-columns: 0.8fr 1fr 0.8fr 0.7fr 1.8fr;
  gap: 0.75rem;
  align-items: center;
  min-height: 38px;
}

.log-head {
  color: #94a3b8;
  font-size: 0.78rem;
}

.log-row {
  color: #e2e8f0;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  font-size: 0.9rem;
}

.pass-text {
  color: #86efac;
}

.deny-text {
  color: #fca5a5;
}

.hidden-canvas {
  display: none;
}

@media (max-width: 1080px) {
  .meeting-strip,
  .workflow-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .face-content {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .panel-header,
  .access-log-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .meeting-strip,
  .workflow-grid,
  .profile-grid {
    grid-template-columns: 1fr;
  }

  .camera-box,
  .camera-video {
    min-height: 280px;
  }

  .log-head,
  .log-row {
    grid-template-columns: 0.9fr 1fr 0.7fr;
  }

  .log-head span:nth-child(3),
  .log-head span:nth-child(5),
  .log-row span:nth-child(3),
  .log-row span:nth-child(5) {
    display: none;
  }
}

/* 无摄像头兜底上传区 */
.upload-fallback {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.8rem;
  margin-bottom: 1rem;
  padding: 0.75rem 0.9rem;
  border-radius: 12px;
  border: 1px dashed rgba(45, 212, 191, 0.35);
  background: rgba(15, 118, 110, 0.1);
  color: #a7f3d0;
  font-size: 0.84rem;
}

.upload-actions {
  display: flex;
  gap: 0.6rem;
  flex-wrap: wrap;
}

.hidden-upload {
  display: none;
}
</style>
