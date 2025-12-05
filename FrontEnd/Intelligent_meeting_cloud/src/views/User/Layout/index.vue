<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import LayoutNav from './components/LayoutNav.vue';
import LayoutFooter from './components/LayoutFooter.vue';

const bgContainer = ref(null);

const handleMouseMove = (e) => {
  if (!bgContainer.value) return;
  const x = e.clientX;
  const y = e.clientY;
  bgContainer.value.style.setProperty('--mouse-x', `${x}px`);
  bgContainer.value.style.setProperty('--mouse-y', `${y}px`);
};

onMounted(() => {
  window.addEventListener('mousemove', handleMouseMove);
});

onUnmounted(() => {
  window.removeEventListener('mousemove', handleMouseMove);
});
</script>

<template>
  <div class="main-layout">
    <div class="css-bg-container" ref="bgContainer">
      <div class="blob interactive-blob"></div>
      <div class="blob ambient-blob-1"></div> <div class="blob ambient-blob-2"></div> <div class="blob ambient-blob-3"></div>
      <div class="backdrop-overlay"></div>
      <div class="grid-pattern"></div>
    </div>

    <div class="content-wrapper">
      <LayoutNav />
      <main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
      <LayoutFooter />
    </div>
  </div>
</template>

<style scoped>
.main-layout {
  position: relative;
  min-height: 100vh;
  width: 100%;
  overflow-x: hidden;
  font-family: 'Poppins', sans-serif;
  color: #fff;
  background-color: #0f172a; 
}

.css-bg-container {
  position: fixed;
  top: 0; left: 0; width: 100%; height: 100%;
  z-index: 0;
  overflow: hidden;
  background: #0f172a; 
  --mouse-x: 50vw;
  --mouse-y: 50vh;
}

.blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.8;
  mix-blend-mode: screen;
}

.interactive-blob {
  top: 0; left: 0;
  width: 120vw; height: 120vw; 
  background: radial-gradient(
    circle, 
    rgba(74, 222, 128, 1) 0%,
    rgba(32, 174, 124, 0.8) 30%,
    rgba(32, 174, 124, 0.1) 70%, 
    transparent 100%
  );
  z-index: 10;
  transform: translate3d(calc(var(--mouse-x) - 50%), calc(var(--mouse-y) - 50%), 0);
  transition: transform 10s cubic-bezier(0.075, 0.82, 0.165, 1);
  opacity: 1;
  filter: blur(50px);
}

.ambient-blob-1 {
  bottom: -10%;
  right: -10%;
  width: 45vw; height: 45vw;
  background: #0cc2ffcd;
  animation: float-blue 10s infinite ease-in-out alternate;
  z-index: 1;
}

.ambient-blob-2 {
  top: -10%;
  left: -10%;
  width: 40vw; height: 40vw;
  background: #00f2fe;
  opacity: 0.5;
  animation: float-cyan 20s infinite ease-in-out alternate;
  z-index: 2;
}

.ambient-blob-3 {
  bottom: 10%;
  left: 20%;
  width: 50vw; height: 50vw;
  background: #4f46e5;
  opacity: 0.4;
  animation: float-purple 15s infinite ease-in-out alternate-reverse;
  z-index: 0;
}

@keyframes float-blue {
  0% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(-20vw, -20vh) scale(1.2); }
  100% { transform: translate(-40vw, 10vh) scale(0.9); }
}

@keyframes float-cyan {
  0% { transform: translate(0, 0) rotate(0deg); }
  50% { transform: translate(30vw, 20vh) rotate(180deg); }
  100% { transform: translate(10vw, 40vh) rotate(360deg); }
}

@keyframes float-purple {
  0% { transform: translate(0, 0) scale(1); border-radius: 50%; }
  50% { transform: translate(20vw, -20vh) scale(1.1); border-radius: 40% 60% 70% 30%; }
  100% { transform: translate(-10vw, -10vh) scale(1); border-radius: 50%; }
}

/* --- 遮罩层 --- */
.backdrop-overlay {
  position: absolute;
  top: 0; left: 0; width: 100%; height: 100%;
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(50px); 
  pointer-events: none;
  z-index: 20;
}

.grid-pattern {
  position: absolute;
  top: 0; left: 0; width: 100%; height: 100%;
  z-index: 21;
  pointer-events: none;
  background-image: 
    linear-gradient(rgba(255, 255, 255, 0.1) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.1) 1px, transparent 1px);
  background-size: 60px 60px;
  mask-image: radial-gradient(
    450px circle at var(--mouse-x) var(--mouse-y), 
    black 0%, 
    transparent 100%
  );
  -webkit-mask-image: radial-gradient(
    450px circle at var(--mouse-x) var(--mouse-y), 
    black 0%, 
    transparent 100%
  );
}

.content-wrapper {
  position: relative;
  z-index: 30;
  display: flex; flex-direction: column; min-height: 100vh;
}
.main-content {
  flex: 1; width: 100%; max-width: 1400px; margin: 0 auto; padding: 30px;
}
.fade-enter-active, .fade-leave-active { transition: opacity 0.4s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>