import axios from 'axios';

const sensorRequest = axios.create({
  baseURL: import.meta.env.VITE_SENSOR_API_URL || '/sensor-api',
  timeout: 5000,
});

sensorRequest.interceptors.response.use(
  (res) => res.data,
  (error) => Promise.reject(error)
);

export function getCurrentSensorData() {
  return sensorRequest.get('/current');
}

export function getSensorHistory() {
  return sensorRequest.get('/history');
}

export function getSensorExportUrl() {
  const base = import.meta.env.VITE_SENSOR_API_URL || '/sensor-api';
  return `${base}/export/csv`;
}

export function getSensorChartUrl(type) {
  const base = import.meta.env.VITE_SENSOR_CHART_URL || '/sensor-chart';
  const timestamp = Date.now();
  return `${base}/${type}?t=${timestamp}`;
}

export function controlClimateDevice(payload) {
  return sensorRequest.post('/control', payload);
}

export function setLightingDevice(enabled, brightness = enabled ? 100 : 0, source = 'frontend') {
  return controlClimateDevice({
    action: 'manual',
    device: 'lighting',
    state: enabled,
    brightness,
    source,
  });
}

export function getClimateChartUrl() {
  const base = import.meta.env.VITE_SENSOR_CHART_URL || '/sensor-chart';
  const timestamp = Date.now();
  return `${base}/sensor?t=${timestamp}`;
}
