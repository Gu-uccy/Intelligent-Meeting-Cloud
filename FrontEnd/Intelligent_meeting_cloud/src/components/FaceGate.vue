<script setup>
/**
 * FaceGate.vue —— 通用「刷脸闸门」弹窗
 *
 * 两个用途（purpose）：
 *   booking : 刷脸换一次性预约凭据（1:1 核身），供 /user/reservation 的 X-Face-Ticket 校验
 *   unlock  : 刷脸解锁会议室（1:1 核身 + 预约时段校验 + 驱动门禁）
 *
 * 设计要点：
 *   1. 前端只负责「采集帧 + 发请求」，是否通过完全由人脸服务/后端判定（不默认放行）；
 *   2. 没有摄像头或权限被拒时，允许上传本地照片走同一条链路（答辩现场兜底）；
 *   3. 所有失败原因原样展示（未注册、不匹配、无有效预约、门禁驱动失败），便于排障与取证。
 */
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';
import { issueFaceTicket, unlockRoomByFace } from '@/apis/face';

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  purpose: { type: String, default: 'booking' }, // booking | unlock
  loginAccount: { type: String, default: '' },
  roomId: { type: [Number, String], default: null },
  roomName: { type: String, default: '' },
});

const emit = defineEmits(['update:modelValue', 'success']);

const videoRef = ref(null);
const canvasRef = ref(null);
const fileInputRef = ref(null);
const stream = ref(null);
const cameraReady = ref(false);
const cameraError = ref('');
const busy = ref(false);
const result = ref(null);
const errorMessage = ref('');
const lastShot = ref('');

const title = computed(() =>
  props.purpose === 'unlock' ? '刷脸解锁会议室' : '刷脸确认预约'
);
const subtitle = computed(() =>
  props.purpose === 'unlock'
    ? `核验「${props.roomName || '当前会议室'}」当前时段的预约权限；通过后门禁打开，3D 门同步开启`
    : '提交预约前需完成 1:1 人脸核身；凭据 5 分钟内有效且只能用一次'
);

function close() {
  stopCamera();
  emit('update:modelValue', false);
}

function resetState() {
  result.value = null;
  errorMessage.value = '';
  cameraError.value = '';
  lastShot.value = '';
}

async function startCamera() {
  resetState();
  if (!navigator.mediaDevices?.getUserMedia) {
    cameraError.value = '当前浏览器不支持摄像头，请改用「上传照片」';
    return;
  }
  try {
    stream.value = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' },
      audio: false,
    });
    await nextTick();
    if (videoRef.value) {
      videoRef.value.srcObject = stream.value;
      await videoRef.value.play().catch(() => {});
    }
    cameraReady.value = true;
  } catch (err) {
    cameraReady.value = false;
    cameraError.value = `无法打开摄像头（${err?.name || err?.message || '未知错误'}），可改用「上传照片」`;
  }
}

function stopCamera() {
  if (stream.value) {
    stream.value.getTracks().forEach((track) => track.stop());
    stream.value = null;
  }
  cameraReady.value = false;
}

function grabFrame() {
  const video = videoRef.value;
  const canvas = canvasRef.value;
  if (!video || !canvas || !video.videoWidth) return null;
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  return new Promise((resolve) => {
    canvas.toBlob((blob) => resolve(blob), 'image/jpeg', 0.92);
  });
}

function describeError(err) {
  const data = err?.response?.data;
  if (data?.error) return data.error;
  if (data?.msg) return data.msg;
  if (err?.response?.status === 403) return '服务端拒绝：' + (data?.error || '权限校验未通过');
  if (err?.response?.status === 422) return '未检测到人脸，请正对摄像头重试';
  if (err?.response?.status === 409) return data?.error || '该人脸已注册过其他账号';
  if (err?.code === 'ECONNABORTED') return '请求超时，请检查人脸服务（5001）是否运行';
  return err?.message || '请求失败';
}

async function submitBlob(blob) {
  if (!blob) return;
  if (!props.loginAccount) {
    errorMessage.value = '缺少登录账号，请重新登录后再试';
    return;
  }
  busy.value = true;
  errorMessage.value = '';
  result.value = null;
  lastShot.value = URL.createObjectURL(blob);
  const file = new File([blob], `face-${Date.now()}.jpg`, { type: 'image/jpeg' });
  try {
    let payload;
    if (props.purpose === 'unlock') {
      payload = await unlockRoomByFace(file, {
        loginAccount: props.loginAccount,
        roomId: props.roomId,
      });
    } else {
      payload = await issueFaceTicket(file, {
        loginAccount: props.loginAccount,
        purpose: 'booking',
      });
    }
    result.value = payload;
    if (payload?.granted) {
      setTimeout(() => {
        emit('success', payload);
        close();
      }, 900);
    } else {
      errorMessage.value = payload?.error || '识别未通过';
    }
  } catch (err) {
    errorMessage.value = describeError(err);
  } finally {
    busy.value = false;
  }
}

async function capture() {
  const blob = await grabFrame();
  if (!blob) {
    errorMessage.value = '没有取到画面，请等待摄像头就绪';
    return;
  }
  submitBlob(blob);
}

function onFilePicked(event) {
  const file = event.target.files?.[0];
  if (file) submitBlob(file);
  event.target.value = '';
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) startCamera();
    else stopCamera();
  }
);

onBeforeUnmount(stopCamera);
</script>

<template>
  <Teleport to="body">
    <div v-if="modelValue" class="face-gate-mask" @click.self="close">
      <section class="face-gate">
        <header class="gate-header">
          <div>
            <p class="eyebrow">
              <i class="fa-solid fa-shield-halved"></i>
              {{ purpose === 'unlock' ? 'Face Unlock' : 'Face Confirm' }}
            </p>
            <h3>{{ title }}</h3>
            <p class="subtitle">{{ subtitle }}</p>
          </div>
          <button class="btn-close" @click="close"><i class="fa-solid fa-xmark"></i></button>
        </header>

        <div class="gate-body">
          <div class="camera-box">
            <video
              v-show="cameraReady && !lastShot"
              ref="videoRef"
              class="camera"
              playsinline
              muted
            ></video>
            <img v-if="lastShot" :src="lastShot" class="camera" alt="抓拍画面" />
            <div v-if="!cameraReady && !lastShot" class="camera-placeholder">
              <i class="fa-solid fa-video-slash"></i>
              <p>{{ cameraError || '正在打开摄像头…' }}</p>
            </div>
            <div v-if="busy" class="busy-cover">
              <i class="fa-solid fa-spinner fa-spin"></i>
              <span>正在识别…</span>
            </div>
            <canvas ref="canvasRef" class="hidden-canvas"></canvas>
          </div>

          <div class="gate-side">
            <div class="account-chip">
              <i class="fa-solid fa-user-check"></i>
              <span>当前账号</span>
              <strong>{{ loginAccount || '未登录' }}</strong>
            </div>
            <div v-if="roomId" class="account-chip">
              <i class="fa-solid fa-door-open"></i>
              <span>目标会议室</span>
              <strong>{{ roomName || roomId }}</strong>
            </div>

            <ul class="rules">
              <li>识别结果必须与当前登录账号一致</li>
              <li>开门额外校验「当前时段有效预约」</li>
              <li>未注册 / 不匹配 / 无预约 → 一律拒绝并写审计日志</li>
            </ul>

            <div v-if="result?.granted" class="ok-box">
              <i class="fa-solid fa-circle-check"></i>
              <div>
                <strong>{{ purpose === 'unlock' ? '已解锁，门禁开启' : '核身通过，可以预约' }}</strong>
                <p>
                  相似度 {{ result.confidence }} / 阈值 {{ result.threshold }}
                  <template v-if="result.reservation_no">｜ 预约号 {{ result.reservation_no }}</template>
                </p>
                <p v-if="result.window">
                  有效时段 {{ result.window.start_time }} ~ {{ result.window.end_time }}
                </p>
              </div>
            </div>

            <div v-if="errorMessage" class="err-box">
              <i class="fa-solid fa-triangle-exclamation"></i>
              <div>
                <strong>识别未通过</strong>
                <p>{{ errorMessage }}</p>
                <p v-if="/未注册|未录入/.test(errorMessage)" class="hint">
                  请先到「人脸门禁」页面录入本人人脸后再试。
                </p>
              </div>
            </div>
          </div>
        </div>

        <footer class="gate-footer">
          <button class="btn-ghost" @click="fileInputRef.click()">
            <i class="fa-solid fa-upload"></i> 上传照片
          </button>
          <button class="btn-ghost" @click="startCamera">
            <i class="fa-solid fa-rotate"></i> 重开摄像头
          </button>
          <button class="btn-primary" :disabled="busy || !cameraReady" @click="capture">
            <i class="fa-solid fa-camera"></i>
            {{ busy ? '识别中…' : '拍照并识别' }}
          </button>
          <input ref="fileInputRef" type="file" accept="image/*" class="hidden-input" @change="onFilePicked" />
        </footer>
      </section>
    </div>
  </Teleport>
</template>

<style scoped>
.face-gate-mask {
  position: fixed;
  inset: 0;
  z-index: 3000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
  background: rgba(2, 6, 23, 0.72);
  backdrop-filter: blur(6px);
}

.face-gate {
  width: min(880px, 100%);
  max-height: 92vh;
  overflow: auto;
  border-radius: 18px;
  border: 1px solid rgba(45, 212, 191, 0.28);
  background: linear-gradient(160deg, #0f172a 0%, #111c33 60%, #0b1220 100%);
  color: #e2e8f0;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.45);
}

.gate-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  padding: 1.4rem 1.6rem 1rem;
  border-bottom: 1px solid rgba(148, 163, 184, 0.18);
}

.eyebrow {
  margin: 0 0 0.35rem;
  font-size: 0.75rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #2dd4bf;
  font-weight: 700;
}

.gate-header h3 {
  margin: 0;
  font-size: 1.35rem;
}

.subtitle {
  margin: 0.45rem 0 0;
  color: #94a3b8;
  font-size: 0.86rem;
  line-height: 1.5;
}

.btn-close {
  border: 1px solid rgba(148, 163, 184, 0.3);
  background: transparent;
  color: #cbd5e1;
  width: 34px;
  height: 34px;
  border-radius: 10px;
  cursor: pointer;
}

.gate-body {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(0, 1fr);
  gap: 1.2rem;
  padding: 1.2rem 1.6rem;
}

.camera-box {
  position: relative;
  border-radius: 14px;
  overflow: hidden;
  background: #020617;
  border: 1px solid rgba(148, 163, 184, 0.2);
  aspect-ratio: 4 / 3;
}

.camera {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.camera-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.6rem;
  color: #94a3b8;
  font-size: 0.85rem;
  padding: 1rem;
  text-align: center;
}

.camera-placeholder i {
  font-size: 2rem;
  opacity: 0.6;
}

.busy-cover {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.6rem;
  background: rgba(2, 6, 23, 0.55);
  color: #5eead4;
  font-weight: 600;
}

.hidden-canvas,
.hidden-input {
  display: none;
}

.gate-side {
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
}

.account-chip {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  padding: 0.55rem 0.75rem;
  border-radius: 10px;
  background: rgba(148, 163, 184, 0.1);
  font-size: 0.84rem;
  color: #cbd5e1;
}

.account-chip strong {
  margin-left: auto;
  color: #5eead4;
}

.rules {
  margin: 0.2rem 0 0;
  padding-left: 1.1rem;
  color: #94a3b8;
  font-size: 0.8rem;
  line-height: 1.7;
}

.ok-box,
.err-box {
  display: flex;
  gap: 0.7rem;
  padding: 0.8rem 0.9rem;
  border-radius: 12px;
  font-size: 0.84rem;
  line-height: 1.5;
}

.ok-box {
  background: rgba(16, 185, 129, 0.12);
  border: 1px solid rgba(16, 185, 129, 0.35);
  color: #a7f3d0;
}

.err-box {
  background: rgba(239, 68, 68, 0.12);
  border: 1px solid rgba(248, 113, 113, 0.35);
  color: #fecaca;
}

.ok-box p,
.err-box p {
  margin: 0.2rem 0 0;
  color: inherit;
  opacity: 0.85;
}

.hint {
  font-size: 0.78rem;
}

.gate-footer {
  display: flex;
  flex-wrap: wrap;
  gap: 0.7rem;
  justify-content: flex-end;
  padding: 1rem 1.6rem 1.4rem;
  border-top: 1px solid rgba(148, 163, 184, 0.18);
}

.btn-ghost,
.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.62rem 1.05rem;
  border-radius: 10px;
  font-size: 0.86rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.18s ease;
}

.btn-ghost {
  background: transparent;
  color: #cbd5e1;
  border: 1px solid rgba(148, 163, 184, 0.35);
}

.btn-ghost:hover {
  background: rgba(148, 163, 184, 0.12);
}

.btn-primary {
  background: #0f766e;
  border: 1px solid #14b8a6;
  color: #ecfeff;
}

.btn-primary:hover:not(:disabled) {
  background: #0d9488;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 820px) {
  .gate-body {
    grid-template-columns: 1fr;
  }
}
</style>
