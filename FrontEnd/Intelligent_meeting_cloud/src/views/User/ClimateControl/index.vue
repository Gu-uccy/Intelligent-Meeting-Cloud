<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue';
import {
  controlClimateDevice,
  getClimateChartUrl,
  getCurrentSensorData,
  getSensorExportUrl,
  getSensorHistory,
} from '@/apis/sensor';

const currentData = ref(null);
const historyData = ref([]);
const isLoading = ref(true);
const isRefreshing = ref(false);
const isSaving = ref(false);
const errorMessage = ref('');
const lastUpdated = ref('--');
const climateChart = ref(getClimateChartUrl());

const params = ref({
  temp_min: 20,
  temp_max: 26,
  humidity_min: 40,
  humidity_max: 60,
});

let dataTimer = null;
let chartTimer = null;

const metricCards = computed(() => [
  {
    key: 'temperature',
    label: '温度',
    icon: 'fa-temperature-half',
    value: formatNumber(currentData.value?.temperature),
    unit: '°C',
    tone: 'temperature',
    hint: `目标 ${params.value.temp_min}-${params.value.temp_max}°C`,
  },
  {
    key: 'humidity',
    label: '湿度',
    icon: 'fa-droplet',
    value: formatNumber(currentData.value?.humidity),
    unit: '%',
    tone: 'humidity',
    hint: `目标 ${params.value.humidity_min}-${params.value.humidity_max}%`,
  },
  {
    key: 'light',
    label: '光照',
    icon: 'fa-sun',
    value: formatRaw(currentData.value?.light),
    unit: '',
    tone: 'light',
    hint: 'PCF8591 采样值 0-255',
  },
  {
    key: 'smoke',
    label: '烟雾',
    icon: 'fa-smog',
    value: formatRaw(currentData.value?.smoke),
    unit: '',
    tone: 'smoke',
    hint: '烟雾浓度采样值',
  },
  {
    key: 'presence',
    label: '人体检测',
    icon: 'fa-person-rays',
    value: currentData.value?.presence ? '有人' : '无人',
    unit: '',
    tone: currentData.value?.presence ? 'presence-active' : 'presence-idle',
    hint: 'PIR 红外检测',
  },
]);

const deviceItems = [
  { key: 'cooling', label: '制冷', icon: 'fa-snowflake' },
  { key: 'heating', label: '加热', icon: 'fa-fire' },
  { key: 'humidifier', label: '加湿', icon: 'fa-cloud-rain' },
  { key: 'dehumidifier', label: '除湿', icon: 'fa-wind' },
  { key: 'lighting', label: '照明', icon: 'fa-lightbulb' },
  { key: 'alarm', label: '报警', icon: 'fa-bell' },
];

const latestRows = computed(() => historyData.value.slice(-8).reverse());
const devices = computed(() => currentData.value?.devices || {});
const autoMode = computed(() => devices.value.auto_mode !== false);
const exportUrl = computed(() => getSensorExportUrl());
const connectionText = computed(() => (errorMessage.value ? '连接异常' : '环境控制在线'));

function formatNumber(value) {
  if (typeof value !== 'number') return '--';
  return value.toFixed(1);
}

function formatRaw(value) {
  if (typeof value !== 'number') return '--';
  return String(value);
}

function syncParams(data) {
  params.value = {
    temp_min: data?.temp_min ?? params.value.temp_min,
    temp_max: data?.temp_max ?? params.value.temp_max,
    humidity_min: data?.humidity_min ?? params.value.humidity_min,
    humidity_max: data?.humidity_max ?? params.value.humidity_max,
  };
}

function refreshChart() {
  climateChart.value = getClimateChartUrl();
}

async function fetchClimateData(showLoading = false) {
  if (showLoading) isLoading.value = true;
  isRefreshing.value = true;
  errorMessage.value = '';

  try {
    const [current, history] = await Promise.all([
      getCurrentSensorData(),
      getSensorHistory(),
    ]);
    currentData.value = current;
    historyData.value = Array.isArray(history) ? history : [];
    syncParams(current);
    lastUpdated.value = current?.timestamp || new Date().toLocaleString();
  } catch (error) {
    const status = error?.response?.status;
    errorMessage.value = status === 503
      ? '传感器数据暂未就绪，请稍后刷新。'
      : '无法连接智能温湿度控制 Flask 服务。';
  } finally {
    isLoading.value = false;
    isRefreshing.value = false;
  }
}

async function setAutoMode(enabled) {
  isSaving.value = true;
  try {
    const res = await controlClimateDevice({ action: 'set_auto', enabled });
    currentData.value = {
      ...currentData.value,
      devices: res?.devices || { ...devices.value, auto_mode: enabled },
    };
    await fetchClimateData(false);
  } catch (error) {
    errorMessage.value = '自动/手动模式切换失败。';
  } finally {
    isSaving.value = false;
  }
}

async function saveParams() {
  isSaving.value = true;
  try {
    await controlClimateDevice({
      action: 'set_params',
      temp_min: Number(params.value.temp_min),
      temp_max: Number(params.value.temp_max),
      humidity_min: Number(params.value.humidity_min),
      humidity_max: Number(params.value.humidity_max),
    });
    await fetchClimateData(false);
  } catch (error) {
    errorMessage.value = '阈值参数保存失败。';
  } finally {
    isSaving.value = false;
  }
}

async function toggleDevice(deviceKey) {
  isSaving.value = true;
  try {
    const state = !devices.value[deviceKey];
    const res = await controlClimateDevice({
      action: 'manual',
      device: deviceKey,
      state,
      brightness: deviceKey === 'lighting' && state ? 100 : 0,
      source: deviceKey === 'lighting' ? 'control-page' : 'manual',
    });
    currentData.value = {
      ...currentData.value,
      devices: res?.devices || {
        ...devices.value,
        [deviceKey]: state,
        ...(deviceKey === 'lighting'
          ? {
            lighting_brightness: state ? 100 : 0,
            lighting_source: 'control-page',
            auto_mode: false,
          }
          : {}),
      },
    };
  } catch (error) {
    errorMessage.value = '设备手动控制失败。';
  } finally {
    isSaving.value = false;
  }
}

onMounted(() => {
  fetchClimateData(true);
  dataTimer = window.setInterval(() => fetchClimateData(false), 2000);
  chartTimer = window.setInterval(refreshChart, 60000);
});

onUnmounted(() => {
  if (dataTimer) window.clearInterval(dataTimer);
  if (chartTimer) window.clearInterval(chartTimer);
});
</script>

<template>
  <div class="climate-page">
    <header class="climate-header">
      <div>
        <p class="eyebrow">Raspberry Pi Climate Control</p>
        <h1>智能温湿度控制系统</h1>
        <p class="header-subtitle">温湿度、光照、烟雾、人体红外与设备联动控制</p>
      </div>
      <div class="header-actions">
        <span class="status-pill" :class="{ danger: errorMessage }">
          <i class="fa-solid" :class="errorMessage ? 'fa-triangle-exclamation' : 'fa-circle-dot'"></i>
          {{ connectionText }}
        </span>
        <button class="icon-button" title="刷新数据" :disabled="isRefreshing" @click="fetchClimateData(false)">
          <i class="fa-solid" :class="isRefreshing ? 'fa-spinner fa-spin' : 'fa-rotate-right'"></i>
        </button>
        <a class="export-button" :href="exportUrl">
          <i class="fa-solid fa-file-csv"></i>
          导出 CSV
        </a>
      </div>
    </header>

    <section v-if="errorMessage" class="alert-bar">
      <i class="fa-solid fa-circle-info"></i>
      <span>{{ errorMessage }}</span>
    </section>

    <section class="overview-grid">
      <article v-for="card in metricCards" :key="card.key" class="metric-card" :class="card.tone">
        <div class="metric-top">
          <span class="metric-icon">
            <i class="fa-solid" :class="card.icon"></i>
          </span>
          <span class="metric-label">{{ card.label }}</span>
        </div>
        <div class="metric-value">
          <span>{{ isLoading ? '--' : card.value }}</span>
          <small>{{ card.unit }}</small>
        </div>
        <p>{{ card.hint }}</p>
      </article>
    </section>

    <section class="control-grid">
      <article class="panel params-panel">
        <div class="panel-header">
          <div>
            <h2>自动控制阈值</h2>
            <span>最后更新：{{ lastUpdated }}</span>
          </div>
          <div class="mode-switch">
            <button :class="{ active: autoMode }" :disabled="isSaving" @click="setAutoMode(true)">
              自动
            </button>
            <button :class="{ active: !autoMode }" :disabled="isSaving" @click="setAutoMode(false)">
              手动
            </button>
          </div>
        </div>

        <div class="param-body">
          <label>
            <span>最低温度</span>
            <input v-model.number="params.temp_min" type="number" min="10" max="30">
          </label>
          <label>
            <span>最高温度</span>
            <input v-model.number="params.temp_max" type="number" min="15" max="40">
          </label>
          <label>
            <span>最低湿度</span>
            <input v-model.number="params.humidity_min" type="number" min="10" max="80">
          </label>
          <label>
            <span>最高湿度</span>
            <input v-model.number="params.humidity_max" type="number" min="30" max="95">
          </label>
          <button class="save-button" :disabled="isSaving" @click="saveParams">
            <i class="fa-solid" :class="isSaving ? 'fa-spinner fa-spin' : 'fa-sliders'"></i>
            保存参数
          </button>
        </div>
      </article>

      <article class="panel devices-panel">
        <div class="panel-header">
          <div>
            <h2>设备状态</h2>
            <span>手动模式下可直接切换设备</span>
          </div>
        </div>
        <div class="device-grid">
          <button
            v-for="device in deviceItems"
            :key="device.key"
            class="device-button"
            :class="{ active: devices[device.key] }"
            :disabled="isSaving || (autoMode && device.key !== 'lighting')"
            @click="toggleDevice(device.key)"
          >
            <i class="fa-solid" :class="device.icon"></i>
            <span>{{ device.label }}</span>
            <strong>{{ devices[device.key] ? '开启' : '关闭' }}</strong>
          </button>
        </div>
      </article>
    </section>

    <section class="detail-grid">
      <article class="panel chart-panel">
        <div class="panel-header">
          <div>
            <h2>综合趋势图</h2>
            <span>温湿度、光照、烟雾与人体检测趋势</span>
          </div>
        </div>
        <div class="chart-frame">
          <img :src="climateChart" alt="智能温湿度控制综合趋势图">
        </div>
      </article>

      <article class="panel table-panel">
        <div class="panel-header">
          <div>
            <h2>最近记录</h2>
            <span>展示最新 8 条采样与控制状态</span>
          </div>
        </div>
        <div class="record-table">
          <div class="table-head">
            <span>时间</span>
            <span>温度</span>
            <span>湿度</span>
            <span>光照</span>
            <span>烟雾</span>
            <span>人体</span>
          </div>
          <div v-if="!latestRows.length" class="empty-row">暂无历史数据</div>
          <div v-for="row in latestRows" :key="`${row.timestamp}-${row.time}`" class="table-row">
            <span>{{ row.time }}</span>
            <span>{{ formatNumber(row.temperature) }}°C</span>
            <span>{{ formatNumber(row.humidity) }}%</span>
            <span>{{ formatRaw(row.light) }}</span>
            <span>{{ formatRaw(row.smoke) }}</span>
            <span :class="row.presence ? 'row-active' : 'row-idle'">{{ row.presence ? '有人' : '无人' }}</span>
          </div>
        </div>
      </article>
    </section>
  </div>
</template>

<style scoped>
* {
  box-sizing: border-box;
}

.climate-page {
  width: 100%;
  min-height: 100%;
  padding: 1.5rem;
  color: #f8fafc;
}

.climate-header {
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

.climate-header h1 {
  margin: 0;
  font-size: 2rem;
  line-height: 1.15;
}

.header-subtitle {
  margin: 0.55rem 0 0;
  color: #a7b5c8;
}

.header-actions,
.mode-switch {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.status-pill,
.export-button,
.icon-button,
.save-button,
.mode-switch button {
  min-height: 40px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(15, 23, 42, 0.62);
  color: #e2e8f0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.status-pill {
  padding: 0 0.85rem;
  color: #67e8f9;
}

.status-pill.danger {
  color: #fca5a5;
}

.icon-button {
  width: 40px;
  cursor: pointer;
}

.export-button,
.save-button,
.mode-switch button.active {
  padding: 0 1rem;
  text-decoration: none;
  color: #ffffff;
  background: rgba(32, 174, 124, 0.82);
  border-color: rgba(45, 212, 191, 0.45);
}

button {
  cursor: pointer;
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.58;
}

.alert-bar {
  min-height: 44px;
  margin-bottom: 1rem;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 0.65rem;
  background: rgba(248, 113, 113, 0.14);
  border: 1px solid rgba(248, 113, 113, 0.32);
  color: #fecaca;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 1rem;
}

.metric-card,
.panel {
  background: rgba(30, 41, 59, 0.62);
  border: 1px solid rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(12px);
  border-radius: 8px;
  box-shadow: 0 18px 45px rgba(2, 6, 23, 0.2);
}

.metric-card {
  padding: 1.1rem;
  min-height: 158px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.metric-top {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.metric-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.08);
}

.metric-label {
  color: #cbd5e1;
  font-weight: 700;
}

.metric-value {
  display: flex;
  align-items: baseline;
  gap: 0.35rem;
}

.metric-value span {
  font-size: 2.35rem;
  font-weight: 800;
  line-height: 1;
}

.metric-card p {
  margin: 0;
  color: #9fb0c7;
  font-size: 0.86rem;
}

.temperature .metric-icon,
.temperature .metric-value span {
  color: #fb7185;
}

.humidity .metric-icon,
.humidity .metric-value span {
  color: #38bdf8;
}

.light .metric-icon,
.light .metric-value span {
  color: #facc15;
}

.smoke .metric-icon,
.smoke .metric-value span {
  color: #c084fc;
}

.presence-active .metric-icon,
.presence-active .metric-value span {
  color: #34d399;
}

.presence-idle .metric-icon,
.presence-idle .metric-value span {
  color: #93c5fd;
}

.control-grid {
  display: grid;
  grid-template-columns: minmax(0, 0.95fr) minmax(0, 1.05fr);
  gap: 1rem;
  margin-top: 1rem;
}

.panel {
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
}

.panel-header span {
  color: #94a3b8;
  font-size: 0.82rem;
}

.param-body {
  padding: 1.25rem;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.param-body label {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  color: #cbd5e1;
  font-weight: 700;
}

.param-body input {
  height: 42px;
  border-radius: 8px;
  border: 1px solid rgba(148, 163, 184, 0.28);
  background: rgba(15, 23, 42, 0.62);
  color: #ffffff;
  padding: 0 0.8rem;
}

.save-button {
  grid-column: 1 / -1;
}

.device-grid {
  padding: 1.25rem;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.85rem;
}

.device-button {
  min-height: 92px;
  border-radius: 8px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(15, 23, 42, 0.5);
  color: #e2e8f0;
  display: grid;
  place-items: center;
  gap: 0.35rem;
}

.device-button i {
  font-size: 1.35rem;
  color: #94a3b8;
}

.device-button strong {
  color: #94a3b8;
}

.device-button.active {
  border-color: rgba(45, 212, 191, 0.48);
  background: rgba(20, 184, 166, 0.16);
}

.device-button.active i,
.device-button.active strong {
  color: #5eead4;
}

.detail-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(0, 0.9fr);
  gap: 1rem;
  margin-top: 1rem;
}

.chart-frame {
  height: 390px;
  padding: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.chart-frame img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  border-radius: 8px;
  background: rgba(248, 250, 252, 0.96);
}

.record-table {
  padding: 0.75rem 1rem 1rem;
}

.table-head,
.table-row {
  display: grid;
  grid-template-columns: 1fr 0.75fr 0.75fr 0.65fr 0.65fr 0.65fr;
  gap: 0.65rem;
  align-items: center;
  min-height: 38px;
}

.table-head {
  color: #94a3b8;
  font-size: 0.78rem;
}

.table-row {
  color: #e2e8f0;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  font-size: 0.88rem;
}

.row-active {
  color: #5eead4;
}

.row-idle {
  color: #bfdbfe;
}

.empty-row {
  min-height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
}

@media (max-width: 1280px) {
  .overview-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .control-grid,
  .detail-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .climate-page {
    padding: 1rem;
  }

  .climate-header,
  .panel-header {
    align-items: stretch;
    flex-direction: column;
  }

  .header-actions,
  .mode-switch {
    justify-content: flex-start;
  }

  .overview-grid,
  .param-body,
  .device-grid {
    grid-template-columns: 1fr;
  }

  .table-head,
  .table-row {
    grid-template-columns: 1fr 0.75fr 0.75fr;
  }

  .table-head span:nth-child(n + 4),
  .table-row span:nth-child(n + 4) {
    display: none;
  }

  .chart-frame {
    height: 290px;
  }
}
</style>
