<script setup>
import { ref } from 'vue';
import BookingTab from './components/Booking';
import RecordsTab from './components/Records';
import FeedbackTab from './components/Feedback';
import AssistantTab from './components/Assistant.vue';

const currentTab = ref('booking');

const tabs = [
  { key: 'booking', label: '立即预约', icon: 'fa-calendar-plus', component: BookingTab },
  { key: 'records', label: '我的预约', icon: 'fa-list-check', component: RecordsTab },
  { key: 'feedback', label: '问题反馈', icon: 'fa-screwdriver-wrench', component: FeedbackTab },
  { key: 'assistant', label: '智能助理', icon: 'fa-robot', component: AssistantTab },
];
</script>

<template>
  <div class="booking-wrapper">
    <div class="main-card">
      <div class="tabs-header">
        <div
          v-for="tab in tabs"
          :key="tab.key"
          class="tab-item"
          :class="{ active: currentTab === tab.key }"
          @click="currentTab = tab.key"
        >
          <i class="fa-solid" :class="tab.icon"></i>
          {{ tab.label }}
        </div>
      </div>

      <div class="card-content custom-scrollbar">
        <KeepAlive>
          <component :is="tabs.find((tab) => tab.key === currentTab)?.component || BookingTab" />
        </KeepAlive>
      </div>
    </div>
  </div>
</template>

<style scoped>
:root {
  --primary: #20ae7c;
  --bg-dark: #1e293b;
  --text-main: #ffffff;
  --border-color: #334155;
}

* {
  box-sizing: border-box;
  user-select: none;
}

.booking-wrapper {
  width: 100%;
  height: 100%;
  padding: 1.5rem;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  overflow: hidden;
}

.main-card {
  height: 100%;
  background: rgba(30, 41, 59, 0.6);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.tabs-header {
  display: flex;
  flex-wrap: wrap;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  padding: 0 1.5rem;
  flex-shrink: 0;
  background: rgba(0, 0, 0, 0.1);
}

.tab-item {
  padding: 1.25rem 1.5rem;
  cursor: pointer;
  color: #94a3b8;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
  position: relative;
  transition: color 0.2s;
}

.tab-item:hover {
  color: #fff;
}

.tab-item.active {
  color: #20ae7c;
}

.tab-item.active::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  width: 100%;
  height: 3px;
  background: #20ae7c;
  border-radius: 3px 3px 0 0;
}

.card-content {
  padding: 2rem;
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.2);
  cursor: pointer;
}
</style>
