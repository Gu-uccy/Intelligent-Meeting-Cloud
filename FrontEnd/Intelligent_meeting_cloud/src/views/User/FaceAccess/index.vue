<script setup>
import FaceCapture from '../Control/components/FaceCapture.vue';
</script>

<template>
  <div class="face-access-page">
    <header class="face-access-header">
      <div>
        <p class="eyebrow">Raspberry Pi Face Access</p>
        <h1>会议室人脸门禁</h1>
        <p class="header-subtitle">课堂模拟：服务端核验身份与预约，收到模拟设备确认后记录通行；真实人脸指标待实测</p>
      </div>
    </header>

    <FaceCapture />
  </div>
</template>

<style scoped>
* {
  box-sizing: border-box;
}

.face-access-page {
  width: 100%;
  min-height: 100%;
  padding: 1.5rem;
  color: #f8fafc;
}

.face-access-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}

.eyebrow {
  margin: 0 0 0.35rem;
  color: #2dd4bf;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.face-access-header h1 {
  margin: 0;
  font-size: 2rem;
  line-height: 1.15;
}

.header-subtitle {
  margin: 0.55rem 0 0;
  color: #a7b5c8;
}

@media (max-width: 760px) {
  .face-access-page {
    padding: 1rem;
  }

  .face-access-header {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
