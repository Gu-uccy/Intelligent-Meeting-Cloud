<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { getCurrentSensorData, getSensorExportUrl, setDoorDevice, setLightingDevice } from '@/apis/sensor';

const viewportRef = ref(null);
const activeRoomId = ref('executive');
const activeMoodId = ref('focus');
const activeViewId = ref('overview');
const sensorState = ref('connecting');
const lastUpdated = ref('--');
const isLightingSaving = ref(false);
const isDoorSaving = ref(false);
const controlError = ref('');
const modelStatus = ref('正在加载 Blender 模型');
const retrySeconds = ref(3);
const controlsUnavailable = computed(() => ['connecting', 'disconnected'].includes(sensorState.value));
const sensorStatusText = computed(() => ({ live: '实时数据', simulation: '模拟数据', partial: '部分传感器异常', disconnected: '连接断开', connecting: '连接中', demo: '本地预览' }[sensorState.value]));
function applyDataStatus(data) {
  sensorState.value = data.source === 'simulation' ? 'simulation' : data.quality === 'partial' ? 'partial' : 'live';
}
const doorOverride = ref(null);
const sensorData = ref({
  temperature: null,
  humidity: null,
  light: null,
  smoke: null,
  motion: false,
  presence: false,
  people_count: null,
  door_open: undefined,
  door_source: undefined,
  distance: null,
  devices: {
    lighting: false,
    lighting_brightness: 0,
    lighting_source: 'demo',
  },
});

const roomOptions = [
  {
    id: 'executive',
    name: '董事会议室',
    badge: '12人',
    icon: 'fa-solid fa-chess-board',
    floor: 0x6a4637,
    wall: 0xf6efe4,
    accent: 0xb98552,
    chair: 0x334155,
    rug: 0xb77b47,
    screen: 0x172033,
  },
  {
    id: 'training',
    name: '培训研讨室',
    badge: '24人',
    icon: 'fa-solid fa-graduation-cap',
    floor: 0x53636d,
    wall: 0xe7eef2,
    accent: 0x2f7c9f,
    chair: 0x283747,
    rug: 0x6b9aa8,
    screen: 0xf7fafc,
  },
  {
    id: 'creative',
    name: '创意协作室',
    badge: '16人',
    icon: 'fa-solid fa-lightbulb',
    floor: 0x6b5b45,
    wall: 0xf4f0df,
    accent: 0x3b9f7f,
    chair: 0x475569,
    rug: 0xd6a84f,
    screen: 0x203040,
  },
];

const moodOptions = [
  {
    id: 'office',
    name: '日常办公',
    icon: 'fa-solid fa-sun',
    background: 0xcbd6dd,
    fog: 0xcbd6dd,
    hemi: 1.8,
    key: 2.4,
    fill: 1.2,
    lamp: 0xfff2d0,
    lampPower: 1.0,
    screenPower: 0.2,
  },
  {
    id: 'focus',
    name: '专注讨论',
    icon: 'fa-solid fa-comments',
    background: 0xbfcbd2,
    fog: 0xbfcbd2,
    hemi: 1.45,
    key: 2.0,
    fill: 1.8,
    lamp: 0xffd28a,
    lampPower: 1.25,
    screenPower: 0.5,
  },
  {
    id: 'presentation',
    name: '演示汇报',
    icon: 'fa-solid fa-display',
    background: 0xaeb9c2,
    fog: 0xaeb9c2,
    hemi: 0.9,
    key: 1.35,
    fill: 2.6,
    lamp: 0xbad7ff,
    lampPower: 0.45,
    screenPower: 1.35,
  },
];

const viewOptions = [
  {
    id: 'overview',
    name: '全景',
    icon: 'fa-solid fa-cube',
    position: new THREE.Vector3(10.8, 5.2, 11.2),
    target: new THREE.Vector3(0, 0.82, -0.35),
  },
  {
    id: 'front',
    name: '正前方',
    icon: 'fa-solid fa-door-open',
    position: new THREE.Vector3(0, 3.35, 11.8),
    target: new THREE.Vector3(0, 0.92, -0.65),
  },
  {
    id: 'top',
    name: '俯视',
    icon: 'fa-solid fa-location-crosshairs',
    position: new THREE.Vector3(0.02, 11.2, 0.02),
    target: new THREE.Vector3(0, 0, -0.4),
  },
];

const activeRoom = computed(() => roomOptions.find((item) => item.id === activeRoomId.value) || roomOptions[0]);
const activeMood = computed(() => moodOptions.find((item) => item.id === activeMoodId.value) || moodOptions[0]);
const thresholds = computed(() => ({ tempMin: sensorData.value.temp_min ?? 20, tempMax: sensorData.value.temp_max ?? 26, humidityMin: sensorData.value.humidity_min ?? 40, humidityMax: sensorData.value.humidity_max ?? 60, smoke: sensorData.value.smoke_threshold ?? 100 }));
const smokeAlarm = computed(() => Number(sensorData.value.smoke || 0) > thresholds.value.smoke || Boolean(sensorData.value.devices?.alarm));
const lightingDevice = computed(() => sensorData.value.devices || {});
const lightingEnabled = computed(() => Boolean(lightingDevice.value.lighting));
const lightingBrightness = computed(() => Number(lightingDevice.value.lighting_brightness ?? (lightingEnabled.value ? 100 : 0)));
const lightingSourceText = computed(() => {
  const source = lightingDevice.value.lighting_source;
  if (source === 'room-3d') return '3D页面控制';
  if (source === 'control-page') return '控制页同步';
  if (source === 'auto') return '自动联动';
  return '设备状态同步';
});

const roomState = computed(() => {
  const data = sensorData.value;
  const devices = data.devices || {};
  const occupied = Number(data.people_count ?? data.occupancy ?? 0) > 0 || Boolean(data.motion || data.presence);
  const rawPeopleCount = Number(data.people_count ?? data.occupancy ?? (occupied ? 1 : 0));
  const apiDoorState = data.door_open ?? devices.door_open;
  return {
    people: {
      occupied,
      countKnown: Number.isInteger(data.people_count) || Number.isInteger(data.occupancy),
      count: occupied ? Math.max(1, Math.min(8, Number.isFinite(rawPeopleCount) ? rawPeopleCount : 1)) : 0,
    },
    door: {
      open: doorOverride.value ?? (apiDoorState === undefined ? false : Boolean(apiDoorState)),
      source: doorOverride.value !== null
        ? 'local-preview'
        : data.door_source || devices.door_source || (apiDoorState === undefined ? 'local-preview' : 'sensor'),
    },
    climate: {
      temperature: data.temperature == null ? NaN : Number(data.temperature),
      humidity: data.humidity == null ? NaN : Number(data.humidity),
    },
    devices,
  };
});

const sensorCards = computed(() => {
  const data = sensorData.value;
  return [
    {
      label: '温度',
      value: formatValue(data.temperature, '℃', 1),
      icon: 'fa-solid fa-temperature-half',
      tone: data.temperature == null ? 'idle' : Number(data.temperature) > thresholds.value.tempMax || Number(data.temperature) < thresholds.value.tempMin ? 'warn' : 'ok',
    },
    {
      label: '湿度',
      value: formatValue(data.humidity, '%', 0),
      icon: 'fa-solid fa-droplet',
      tone: data.humidity == null ? 'idle' : Number(data.humidity) > thresholds.value.humidityMax || Number(data.humidity) < thresholds.value.humidityMin ? 'warn' : 'ok',
    },
    {
      label: '光照',
      value: formatValue(data.light, '', 0),
      icon: 'fa-solid fa-lightbulb',
      tone: Number(data.light) < 20 ? 'dim' : 'ok',
    },
    {
      label: '烟雾',
      value: formatValue(data.smoke, '', 0),
      icon: 'fa-solid fa-fire',
      tone: smokeAlarm.value ? 'danger' : 'ok',
    },
    {
      label: '人体',
      value: roomState.value.people.occupied ? roomState.value.people.countKnown ? `${roomState.value.people.count}人` : '有人' : '无人',
      icon: 'fa-solid fa-person-walking',
      tone: data.motion || data.presence ? 'active' : 'idle',
    },
    {
      label: '距离',
      value: formatValue(data.distance, 'cm', 1),
      icon: 'fa-solid fa-ruler-horizontal',
      tone: Number(data.distance) < 15 ? 'active' : 'ok',
    },
    {
      label: '门禁',
      value: roomState.value.door.open ? '已开' : '已关',
      icon: roomState.value.door.open ? 'fa-solid fa-door-open' : 'fa-solid fa-door-closed',
      tone: roomState.value.door.open ? 'active' : 'idle',
    },
    {
      label: '照明',
      value: lightingEnabled.value ? `${lightingBrightness.value}%` : '关闭',
      icon: 'fa-solid fa-lightbulb',
      tone: lightingEnabled.value ? 'active' : 'idle',
    },
  ];
});

let scene;
let camera;
let renderer;
let controls;
let roomGroup;
let hemiLight;
let keyLight;
let fillLight;
let animationId = 0;
let resizeObserver;
let sensorTimer = 0;
let pollingStopped = true;
let pollInFlight = false;
let failureCount = 0;
let modelGeneration = 0;
let modelCameras = [];
const animationStartedAt = performance.now();
const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();

let liveObjects = createLiveObjectStore();

function createLiveObjectStore() {
  return {
    ceilingLights: [],
    ceilingLightMeshes: [],
    screenMaterials: [],
    smokeClouds: [],
    people: [],
    beacon: null,
    hvac: null,
    humidifier: null,
    lightMeter: null,
    distanceMarker: null,
    door: null,
    doorBeacon: null,
    dhtIndicator: null,
    pirIndicator: null,
    sensorDots: [],
    clickableLights: [],
    clickableDoors: [],
  };
}

function formatValue(value, unit, digits) {
  if (value === null || value === undefined || value === '') return '--';
  const number = Number(value);
  if (!Number.isFinite(number)) return '--';
  return `${number.toFixed(digits)}${unit}`;
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function createMaterial(color, options = {}) {
  return new THREE.MeshStandardMaterial({
    color,
    roughness: options.roughness ?? 0.72,
    metalness: options.metalness ?? 0.05,
    transparent: options.transparent ?? false,
    opacity: options.opacity ?? 1,
    depthWrite: options.depthWrite ?? true,
    emissive: options.emissive ?? 0x000000,
    emissiveIntensity: options.emissiveIntensity ?? 0,
    side: options.side ?? THREE.FrontSide,
  });
}

function addBox(parent, size, position, material, options = {}) {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(size[0], size[1], size[2]), material);
  mesh.position.set(position[0], position[1], position[2]);
  if (options.rotation) {
    mesh.rotation.set(options.rotation[0], options.rotation[1], options.rotation[2]);
  }
  mesh.castShadow = options.castShadow ?? true;
  mesh.receiveShadow = options.receiveShadow ?? true;
  parent.add(mesh);
  return mesh;
}

function addCylinder(parent, radiusTop, radiusBottom, height, position, material, options = {}) {
  const geometry = new THREE.CylinderGeometry(radiusTop, radiusBottom, height, options.segments ?? 32);
  const mesh = new THREE.Mesh(geometry, material);
  mesh.position.set(position[0], position[1], position[2]);
  if (options.rotation) {
    mesh.rotation.set(options.rotation[0], options.rotation[1], options.rotation[2]);
  }
  mesh.castShadow = options.castShadow ?? true;
  mesh.receiveShadow = options.receiveShadow ?? true;
  parent.add(mesh);
  return mesh;
}

function initScene() {
  if (!viewportRef.value) return;

  scene = new THREE.Scene();
  scene.background = new THREE.Color(activeMood.value.background);
  scene.fog = new THREE.Fog(activeMood.value.fog, 18, 42);

  camera = new THREE.PerspectiveCamera(42, 1, 0.1, 120);
  camera.position.copy(viewOptions[0].position);

  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFShadowMap;
  renderer.setClearColor(activeMood.value.background, 1);
  viewportRef.value.appendChild(renderer.domElement);

  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.minDistance = 4.2;
  controls.maxDistance = 60;
  controls.minPolarAngle = 0.05;
  controls.maxPolarAngle = Math.PI * 0.48;
  controls.target.copy(viewOptions[0].target);

  hemiLight = new THREE.HemisphereLight(0xffffff, 0x6f7f89, activeMood.value.hemi);
  scene.add(hemiLight);

  keyLight = new THREE.DirectionalLight(0xffffff, activeMood.value.key);
  keyLight.position.set(6, 8, 5);
  keyLight.castShadow = true;
  keyLight.shadow.mapSize.set(2048, 2048);
  keyLight.shadow.bias = -0.0002;
  keyLight.shadow.normalBias = 0.035;
  keyLight.shadow.camera.near = 1;
  keyLight.shadow.camera.far = 25;
  keyLight.shadow.camera.left = -8;
  keyLight.shadow.camera.right = 8;
  keyLight.shadow.camera.top = 8;
  keyLight.shadow.camera.bottom = -8;
  scene.add(keyLight);

  fillLight = new THREE.PointLight(0x9ad5ff, activeMood.value.fill, 18);
  fillLight.position.set(-5.2, 3.4, 4.4);
  scene.add(fillLight);

  resizeRenderer();
  resizeObserver = new ResizeObserver(resizeRenderer);
  resizeObserver.observe(viewportRef.value);

  buildActiveRoom();
  applyCameraPreset();
}

function resizeRenderer() {
  if (!viewportRef.value || !renderer || !camera) return;
  const width = Math.max(320, viewportRef.value.clientWidth);
  const height = Math.max(320, viewportRef.value.clientHeight);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  renderer.setSize(width, height);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  if (controls) applyCameraPreset();
}

function buildActiveRoom() {
  if (!scene) return;
  if (roomGroup) {
    scene.remove(roomGroup);
    disposeObject(roomGroup);
  }
  liveObjects = createLiveObjectStore();
  roomGroup = new THREE.Group();
  scene.add(roomGroup);

  buildRoomShell(roomGroup, activeRoom.value);

  if (activeRoomId.value === 'executive') {
    buildExecutiveRoom(roomGroup, activeRoom.value);
  } else if (activeRoomId.value === 'training') {
    buildTrainingRoom(roomGroup, activeRoom.value);
  } else {
    buildCreativeRoom(roomGroup, activeRoom.value);
  }

  addSensorLayer(roomGroup, activeRoom.value);
  applyMoodToScene();
  updateSensorVisuals();
  loadBlenderRoom();
}

async function loadBlenderRoom() {
  const generation = ++modelGeneration;
  modelCameras = [];
  if (activeRoomId.value !== 'executive') {
    modelStatus.value = '程序模型（备用布局）';
    return;
  }
  modelStatus.value = '正在加载 Blender 模型';
  try {
    const gltf = await new GLTFLoader().loadAsync(`${import.meta.env.BASE_URL}models/room_301.glb`);
    if (!scene || generation !== modelGeneration) { disposeObject(gltf.scene); return; }
    const next = createLiveObjectStore();
    gltf.scene.traverse((object) => {
      if (object.isMesh) {
        object.material = object.material.clone();
        object.castShadow = true;
        object.receiveShadow = true;
      }
      if (object.name.startsWith('Person_') && object.isMesh) {
        object.userData.baseY = object.position.y;
        next.people.push(object);
      }
      if (object.name.startsWith('CeilingLight_') && object.isMesh) {
        next.ceilingLightMeshes.push(object); next.clickableLights.push(object);
      }
      if (object.isPointLight) next.ceilingLights.push(object);
      if (object.name === 'Door_Leaf') {
        next.door = { group: object, closedRotation: Math.PI / 2, openRotation: Math.PI };
        next.clickableDoors.push(object);
      }
      if (object.name === 'DHT_Panel') next.dhtIndicator = object;
      if (object.name === 'SmokeBeacon') next.beacon = object;
      if (object.name === 'HVAC_Unit') next.hvac = object;
      if (object.name === 'Humidifier') next.humidifier = object;
    });
    if (!next.door || next.people.length !== 8 || next.ceilingLightMeshes.length !== 3) {
      disposeObject(gltf.scene); throw new Error('Missing Blender state anchors');
    }
    scene.remove(roomGroup); disposeObject(roomGroup);
    roomGroup = gltf.scene; scene.add(roomGroup);
    liveObjects = next; modelCameras = gltf.cameras;
    modelStatus.value = 'Blender 模型 · 301';
    applyCameraPreset(); applyMoodToScene(); updateSensorVisuals();
  } catch (error) {
    if (generation === modelGeneration && scene) modelStatus.value = '模型加载失败，已使用程序备用模型';
  }
}

function buildRoomShell(parent, config) {
  const floorMat = createMaterial(config.floor, { roughness: 0.82 });
  const wallMat = createMaterial(config.wall, { roughness: 0.9 });
  const trimMat = createMaterial(0xded5c8, { roughness: 0.8 });
  const ceilingMat = createMaterial(0xf7f7f3, {
    roughness: 0.76,
    transparent: true,
    opacity: 0.1,
    depthWrite: false,
  });

  addBox(parent, [8.6, 0.16, 6.4], [0, -0.08, 0], floorMat, { receiveShadow: true });
  addBox(parent, [8.7, 3.1, 0.16], [0, 1.5, -3.2], wallMat, { receiveShadow: true });
  addBox(parent, [0.16, 3.1, 6.4], [-4.3, 1.5, 0], wallMat, { receiveShadow: true });
  // Leave a real opening in the right wall for the door assembly.
  const doorOpeningStart = 0.95;
  const doorOpeningEnd = 2.29;
  const wallBeforeDoorLength = doorOpeningStart + 3.2;
  const wallAfterDoorLength = 3.2 - doorOpeningEnd;
  addBox(parent, [0.16, 3.1, wallBeforeDoorLength], [4.3, 1.5, -3.2 + wallBeforeDoorLength / 2], wallMat, { receiveShadow: true });
  addBox(parent, [0.16, 3.1, wallAfterDoorLength], [4.3, 1.5, doorOpeningEnd + wallAfterDoorLength / 2], wallMat, { receiveShadow: true });
  addBox(parent, [0.16, 0.72, doorOpeningEnd - doorOpeningStart], [4.3, 2.74, (doorOpeningStart + doorOpeningEnd) / 2], wallMat, { receiveShadow: true });
  addBox(parent, [8.9, 0.16, 6.5], [0, 3.08, -0.02], ceilingMat, { receiveShadow: true });
  addBox(parent, [8.8, 0.08, 0.12], [0, 0.15, -3.08], trimMat);
  addBox(parent, [0.12, 0.08, 6.2], [-4.18, 0.15, 0], trimMat);
  addBox(parent, [0.12, 0.08, 6.2], [4.18, 0.15, 0], trimMat);

  const windowMat = createMaterial(0xa7c3d6, {
    roughness: 0.25,
    metalness: 0,
    transparent: true,
    opacity: 0.72,
  });
  addBox(parent, [1.25, 0.9, 0.04], [-2.7, 1.9, -3.08], windowMat);
  addBox(parent, [1.25, 0.9, 0.04], [2.7, 1.9, -3.08], windowMat);
  addBox(parent, [1.35, 0.08, 0.08], [-2.7, 2.4, -3.02], trimMat);
  addBox(parent, [1.35, 0.08, 0.08], [2.7, 2.4, -3.02], trimMat);

  addDoor(parent);

  addCeilingLight(parent, [-2.4, 2.92, -0.9], 1.3);
  addCeilingLight(parent, [0, 2.92, -0.9], 1.4);
  addCeilingLight(parent, [2.4, 2.92, -0.9], 1.3);
}

function addDoor(parent) {
  const frameMat = createMaterial(0x7c5b43, { roughness: 0.64 });
  const panelMat = createMaterial(0x9b6e4d, { roughness: 0.58 });
  const glassMat = createMaterial(0x9fc4d1, {
    roughness: 0.2,
    transparent: true,
    opacity: 0.7,
  });
  const doorCenterZ = 1.62;

  // The wall occupies x=4.22..4.38; use four bars so the doorway remains open.
  const frameX = 4.42;
  const openingWidth = 1.34;
  const frameDepth = 0.12;
  const frameHeight = 2.38;
  const sideWidth = 0.12;
  addBox(parent, [frameDepth, frameHeight, sideWidth], [frameX, frameHeight / 2, doorCenterZ - openingWidth / 2 + sideWidth / 2], frameMat);
  addBox(parent, [frameDepth, frameHeight, sideWidth], [frameX, frameHeight / 2, doorCenterZ + openingWidth / 2 - sideWidth / 2], frameMat);
  addBox(parent, [frameDepth, 0.12, openingWidth], [frameX, frameHeight - 0.06, doorCenterZ], frameMat);
  addBox(parent, [frameDepth, 0.08, openingWidth], [frameX, 0.04, doorCenterZ], frameMat);

  const group = new THREE.Group();
  group.position.set(4.43, 0, doorCenterZ + 0.58);
  const panel = addBox(group, [0.08, 2.18, 1.16], [0, 1.09, -0.58], panelMat);
  addBox(group, [0.04, 1.15, 0.74], [-0.05, 1.25, -0.59], glassMat, {
    castShadow: false,
    receiveShadow: false,
  });
  addCylinder(group, 0.055, 0.055, 0.16, [-0.08, 1.02, -0.07], createMaterial(0xe8c47d, { metalness: 0.45 }), {
    rotation: [Math.PI / 2, 0, 0],
  });
  parent.add(group);

  const beacon = addBox(parent, [0.08, 0.18, 0.22], [4.42, 2.22, doorCenterZ + 0.18], createMaterial(0xef4444, {
    emissive: 0xef4444,
    emissiveIntensity: 0.85,
  }));
  liveObjects.door = { group, panel, closedRotation: 0, openRotation: -Math.PI * 0.52 };
  liveObjects.doorBeacon = beacon;
  liveObjects.clickableDoors.push(panel);
}

function addCeilingLight(parent, position, width) {
  const material = createMaterial(0xfff0c2, {
    emissive: activeMood.value.lamp,
    emissiveIntensity: activeMood.value.lampPower,
  });
  const mesh = addBox(parent, [width, 0.05, 0.18], position, material, { castShadow: false });
  const light = new THREE.PointLight(activeMood.value.lamp, activeMood.value.lampPower, 5);
  light.position.set(position[0], position[1] - 0.12, position[2]);
  parent.add(light);
  liveObjects.ceilingLightMeshes.push(mesh);
  liveObjects.ceilingLights.push(light);
  liveObjects.clickableLights.push(mesh);
}

function buildExecutiveRoom(parent, config) {
  const tableMat = createMaterial(0xb88455, { roughness: 0.66 });
  const tableTop = addBox(parent, [5.5, 0.15, 1.2], [0, 0.72, -0.2], tableMat);
  addBox(parent, [5.2, 0.08, 0.16], [0, 0.64, -0.74], createMaterial(0xe3c09b));
  addBox(parent, [5.2, 0.08, 0.16], [0, 0.64, 0.34], createMaterial(0xe3c09b));
  [-2.45, 2.45].forEach((x) => {
    [-0.64, 0.24].forEach((z) => addBox(parent, [0.16, 0.72, 0.16], [x, 0.34, z], tableMat));
  });

  for (let index = 0; index < 6; index += 1) {
    const x = -2.45 + index * 0.98;
    addChair(parent, [x, 0, 0.8], Math.PI, config.chair);
    addChair(parent, [x, 0, -1.2], 0, config.chair);
  }
  addChair(parent, [-3.25, 0, -0.2], Math.PI / 2, 0x536273);
  addChair(parent, [3.25, 0, -0.2], -Math.PI / 2, 0x536273);

  addBox(parent, [5.8, 0.06, 2.0], [0, 0.02, -0.2], createMaterial(config.rug), { receiveShadow: true });
  addScreen(parent, [0, 1.72, -3.08], [1.65, 0.95], config.screen, true);
  addWhiteboard(parent, [-2.65, 1.8, -3.07], 1.35, 0.9);
  addCabinet(parent, [3.2, 0, -2.55], config.accent);
  addPlant(parent, [-3.55, 0, 1.95], 0.95);
  addPlant(parent, [3.5, 0, 1.65], 0.72);
}

function buildTrainingRoom(parent, config) {
  const deskMat = createMaterial(0xd7b36d, { roughness: 0.7 });
  const rowZ = [1.3, 0.35, -0.6];
  rowZ.forEach((z, row) => {
    for (let col = 0; col < 4; col += 1) {
      const x = -2.7 + col * 1.8;
      addBox(parent, [1.28, 0.12, 0.52], [x, 0.66, z], deskMat);
      addBox(parent, [0.08, 0.62, 0.08], [x - 0.5, 0.32, z - 0.18], deskMat);
      addBox(parent, [0.08, 0.62, 0.08], [x + 0.5, 0.32, z - 0.18], deskMat);
      addChair(parent, [x, 0, z + 0.62], Math.PI, row % 2 ? 0x2f455d : config.chair);
    }
  });

  addBox(parent, [2.15, 0.18, 0.68], [0, 0.72, -2.25], createMaterial(config.accent, { roughness: 0.62 }));
  addBox(parent, [0.22, 0.72, 0.22], [-0.8, 0.34, -2.25], createMaterial(0x24536b));
  addBox(parent, [0.22, 0.72, 0.22], [0.8, 0.34, -2.25], createMaterial(0x24536b));
  addScreen(parent, [0, 1.76, -3.08], [2.2, 1.18], config.screen, false);
  addWhiteboard(parent, [2.85, 1.78, -3.07], 1.2, 0.95);
  addProjector(parent, [0, 2.62, 0.65]);
  addBox(parent, [7.3, 0.05, 4.65], [0, 0.02, 0.15], createMaterial(0x7c9daa), { receiveShadow: true });
  addPlant(parent, [-3.55, 0, -2.25], 0.72);
}

function buildCreativeRoom(parent, config) {
  addBox(parent, [6.9, 0.055, 4.9], [0, 0.02, 0.1], createMaterial(config.rug), { receiveShadow: true });
  addRoundTableCluster(parent, [-2.05, 0, 0.8], config.accent, config.chair);
  addRoundTableCluster(parent, [0.55, 0, 0.55], 0xd19a43, 0x536273);
  addRoundTableCluster(parent, [2.35, 0, -1.05], 0x497e9f, config.chair);
  addSofa(parent, [-3.1, 0, -1.85]);
  addScreen(parent, [0, 1.68, -3.08], [1.65, 0.95], config.screen, true);
  addIdeaBoard(parent, [-2.65, 1.75, -3.07]);
  addIdeaBoard(parent, [2.65, 1.75, -3.07]);
  addCabinet(parent, [3.45, 0, 1.65], config.accent);
  addPlant(parent, [-3.55, 0, 2.05], 1.05);
  addPlant(parent, [3.65, 0, -2.2], 0.82);
}

function addChair(parent, position, rotationY, color) {
  const group = new THREE.Group();
  group.position.set(position[0], position[1], position[2]);
  group.rotation.y = rotationY;
  const seatMat = createMaterial(color, { roughness: 0.78 });
  const legMat = createMaterial(0x1f2933, { roughness: 0.6, metalness: 0.15 });
  addBox(group, [0.42, 0.09, 0.42], [0, 0.46, 0], seatMat);
  addBox(group, [0.42, 0.54, 0.09], [0, 0.74, 0.24], seatMat);
  [-0.15, 0.15].forEach((x) => {
    [-0.15, 0.15].forEach((z) => addBox(group, [0.055, 0.45, 0.055], [x, 0.23, z], legMat));
  });
  parent.add(group);
  return group;
}

function addScreen(parent, position, size, color, glowing) {
  const frame = createMaterial(0x111827, { roughness: 0.55 });
  const screenMat = createMaterial(color, {
    roughness: 0.38,
    emissive: glowing ? color : 0x000000,
    emissiveIntensity: glowing ? activeMood.value.screenPower : 0.05,
  });
  addBox(parent, [size[0] + 0.16, size[1] + 0.16, 0.07], position, frame);
  const screen = addBox(parent, [size[0], size[1], 0.08], [position[0], position[1], position[2] + 0.045], screenMat);
  liveObjects.screenMaterials.push(screen.material);
  return screen;
}

function addWhiteboard(parent, position, width, height) {
  const frame = createMaterial(0xc9b28e);
  const board = createMaterial(0xf8fafc, { roughness: 0.36 });
  addBox(parent, [width + 0.12, height + 0.12, 0.04], position, frame);
  addBox(parent, [width, height, 0.05], [position[0], position[1], position[2] + 0.035], board);
  addBox(parent, [width * 0.36, 0.035, 0.055], [position[0] - width * 0.2, position[1] - height * 0.18, position[2] + 0.07], createMaterial(0x64748b));
  addBox(parent, [width * 0.28, 0.035, 0.055], [position[0] + width * 0.25, position[1] + height * 0.05, position[2] + 0.07], createMaterial(0x2f7c9f));
}

function addIdeaBoard(parent, position) {
  addWhiteboard(parent, position, 1.25, 0.9);
  const colors = [0xeab308, 0xef6f6c, 0x3b9f7f, 0x6b9aa8, 0xd6a84f];
  colors.forEach((color, index) => {
    const x = position[0] - 0.42 + (index % 3) * 0.36;
    const y = position[1] + 0.22 - Math.floor(index / 3) * 0.34;
    addBox(parent, [0.2, 0.14, 0.06], [x, y, position[2] + 0.09], createMaterial(color));
  });
}

function addCabinet(parent, position, color) {
  const mat = createMaterial(color, { roughness: 0.76 });
  addBox(parent, [1.1, 0.68, 0.36], [position[0], 0.34, position[2]], mat);
  addBox(parent, [0.44, 0.48, 0.04], [position[0] - 0.25, 0.38, position[2] + 0.2], createMaterial(0xf3eee4));
  addBox(parent, [0.44, 0.48, 0.04], [position[0] + 0.25, 0.38, position[2] + 0.2], createMaterial(0xf3eee4));
}

function addProjector(parent, position) {
  const mat = createMaterial(0xf8fafc, { roughness: 0.42 });
  addBox(parent, [0.58, 0.18, 0.38], position, mat);
  addCylinder(
    parent,
    0.08,
    0.08,
    0.06,
    [position[0], position[1] - 0.02, position[2] - 0.23],
    createMaterial(0x1f2937),
    { rotation: [Math.PI / 2, 0, 0] },
  );
  const beamMat = createMaterial(0xdbeafe, {
    transparent: true,
    opacity: 0.12,
    side: THREE.DoubleSide,
    emissive: 0xdbeafe,
    emissiveIntensity: 0.3,
  });
  addBox(parent, [1.75, 0.02, 2.1], [0, 1.98, -1.22], beamMat, {
    rotation: [0.18, 0, 0],
    castShadow: false,
    receiveShadow: false,
  });
}

function addRoundTableCluster(parent, position, tableColor, chairColor) {
  addCylinder(parent, 0.62, 0.62, 0.12, [position[0], 0.7, position[2]], createMaterial(tableColor));
  addCylinder(parent, 0.12, 0.16, 0.65, [position[0], 0.34, position[2]], createMaterial(0x273447));
  for (let index = 0; index < 5; index += 1) {
    const angle = (index / 5) * Math.PI * 2;
    const x = position[0] + Math.sin(angle) * 1.02;
    const z = position[2] + Math.cos(angle) * 1.02;
    addChair(parent, [x, 0, z], angle + Math.PI, chairColor);
  }
}

function addSofa(parent, position) {
  const mat = createMaterial(0x3f5f68, { roughness: 0.78 });
  addBox(parent, [1.65, 0.42, 0.62], [position[0], 0.32, position[2]], mat);
  addBox(parent, [1.65, 0.62, 0.16], [position[0], 0.64, position[2] - 0.28], mat);
  addBox(parent, [0.16, 0.48, 0.62], [position[0] - 0.9, 0.44, position[2]], mat);
  addBox(parent, [0.16, 0.48, 0.62], [position[0] + 0.9, 0.44, position[2]], mat);
}

function addPlant(parent, position, scale = 1) {
  const potMat = createMaterial(0xc07d52, { roughness: 0.78 });
  const leafMat = createMaterial(0x3f8a5a, { roughness: 0.74 });
  addCylinder(parent, 0.19 * scale, 0.27 * scale, 0.34 * scale, [position[0], 0.17 * scale, position[2]], potMat);
  addCylinder(parent, 0.04 * scale, 0.06 * scale, 0.68 * scale, [position[0], 0.63 * scale, position[2]], createMaterial(0x6b4e38));
  addCylinder(parent, 0.24 * scale, 0.05 * scale, 0.5 * scale, [position[0] - 0.12 * scale, 0.88 * scale, position[2]], leafMat, {
    rotation: [0.1, 0.2, -0.35],
  });
  addCylinder(parent, 0.24 * scale, 0.05 * scale, 0.5 * scale, [position[0] + 0.13 * scale, 1.08 * scale, position[2] + 0.02], leafMat, {
    rotation: [0.15, -0.2, 0.38],
  });
  addCylinder(parent, 0.22 * scale, 0.05 * scale, 0.46 * scale, [position[0] - 0.02 * scale, 1.25 * scale, position[2]], leafMat);
}

function addSensorLayer(parent, config) {
  const sensorMat = createMaterial(0x26364a, { roughness: 0.6 });
  const activeMat = createMaterial(0x38bdf8, { emissive: 0x38bdf8, emissiveIntensity: 0.85 });

  liveObjects.hvac = addBox(parent, [1.0, 0.28, 0.18], [3.35, 2.35, -3.02], createMaterial(0xe5e7eb, { roughness: 0.45 }));
  liveObjects.humidifier = addCylinder(parent, 0.18, 0.22, 0.55, [-3.45, 0.28, -2.35], createMaterial(0xd8ecf0));

  const dht = addBox(parent, [0.22, 0.32, 0.08], [-3.72, 1.28, -2.2], sensorMat);
  const pir = addCylinder(parent, 0.13, 0.13, 0.08, [-3.95, 2.15, -2.85], sensorMat, { rotation: [Math.PI / 2, 0, 0] });
  const smoke = addCylinder(parent, 0.18, 0.18, 0.08, [0, 2.9, -0.05], sensorMat);
  const light = addBox(parent, [0.24, 0.08, 0.24], [1.85, 0.86, 0.18], sensorMat);
  const ultrasonic = addBox(parent, [0.52, 0.22, 0.1], [3.95, 1.25, 1.25], sensorMat);
  addCylinder(parent, 0.075, 0.075, 0.04, [3.81, 1.25, 1.31], activeMat, { rotation: [Math.PI / 2, 0, 0] });
  addCylinder(parent, 0.075, 0.075, 0.04, [4.09, 1.25, 1.31], activeMat, { rotation: [Math.PI / 2, 0, 0] });

  liveObjects.sensorDots.push(dht, pir, smoke, light, ultrasonic);
  liveObjects.dhtIndicator = dht;
  liveObjects.pirIndicator = pir;
  liveObjects.lightMeter = light;
  liveObjects.distanceMarker = addBox(parent, [0.08, 0.08, 1.0], [3.95, 1.02, 0.65], createMaterial(config.accent, { emissive: config.accent, emissiveIntensity: 0.2 }));

  liveObjects.beacon = addCylinder(parent, 0.16, 0.16, 0.18, [3.55, 2.86, -2.7], createMaterial(0xef4444, {
    emissive: 0xef4444,
    emissiveIntensity: 1.1,
    transparent: true,
    opacity: 0.85,
  }));

  const smokeMat = createMaterial(0x9ca3af, {
    transparent: true,
    opacity: 0.16,
    side: THREE.DoubleSide,
  });
  [0, 1, 2].forEach((index) => {
    const cloud = addCylinder(parent, 0.35 + index * 0.08, 0.2, 0.42, [-0.35 + index * 0.32, 2.15 + index * 0.18, -0.32], smokeMat, {
      castShadow: false,
      receiveShadow: false,
    });
    liveObjects.smokeClouds.push(cloud);
  });

  createPeople(parent, config);
}

function createPeople(parent, config) {
  const personMat = createMaterial(config.accent, { roughness: 0.62 });
  const headMat = createMaterial(0xf0c9a2, { roughness: 0.68 });
  const positions = activeRoomId.value === 'training'
    ? [[-2.7, 1.03], [-0.9, 0.08], [0.9, 1.03], [2.7, 0.08]]
    : activeRoomId.value === 'creative'
      ? [[-2.0, 0.7], [0.55, 0.48], [2.35, -0.95], [-3.05, -1.72]]
      : [[-1.15, 0.74], [0.25, -1.05], [1.6, 0.74], [-2.25, -1.05]];

  positions.forEach(([x, z]) => {
    const group = new THREE.Group();
    group.position.set(x, 0, z);
    addCylinder(group, 0.12, 0.16, 0.46, [0, 0.72, 0], personMat);
    addCylinder(group, 0.13, 0.13, 0.16, [0, 1.08, 0], headMat);
    parent.add(group);
    liveObjects.people.push(group);
  });
}

function applyMoodToScene() {
  if (!scene) return;
  const mood = activeMood.value;
  scene.background = new THREE.Color(mood.background);
  scene.fog = new THREE.Fog(mood.fog, 18, 42);
  renderer?.setClearColor(mood.background, 1);
  if (hemiLight) hemiLight.intensity = mood.hemi;
  if (keyLight) keyLight.intensity = mood.key;
  if (fillLight) fillLight.intensity = mood.fill;

  liveObjects.ceilingLights.forEach((light) => {
    light.color.setHex(mood.lamp);
    light.intensity = mood.lampPower;
  });
  liveObjects.ceilingLightMeshes.forEach((mesh) => {
    mesh.material.color.setHex(mood.lamp);
    mesh.material.emissive.setHex(mood.lamp);
    mesh.material.emissiveIntensity = mood.lampPower;
  });
  liveObjects.screenMaterials.forEach((material) => {
    material.emissive.setHex(material.color.getHex());
    material.emissiveIntensity = mood.screenPower;
  });
  updateLightingVisuals();
}

function updateLightingVisuals() {
  const enabled = lightingEnabled.value;
  const normalizedBrightness = clamp(lightingBrightness.value / 100, 0, 1);
  const power = enabled ? activeMood.value.lampPower * (0.35 + normalizedBrightness * 1.35) : 0;
  const glow = enabled ? activeMood.value.lampPower * (0.28 + normalizedBrightness * 1.15) : 0.04;
  const color = enabled ? activeMood.value.lamp : 0x6b7280;

  liveObjects.ceilingLights.forEach((light) => {
    light.color.setHex(activeMood.value.lamp);
    light.intensity = power;
  });
  liveObjects.ceilingLightMeshes.forEach((mesh) => {
    mesh.material.color.setHex(color);
    mesh.material.emissive.setHex(activeMood.value.lamp);
    mesh.material.emissiveIntensity = glow;
  });
}

function updateSensorVisuals() {
  const data = sensorData.value;
  const state = roomState.value;
  const lightLevel = clamp(Number(data.light ?? 50) / 100, 0.18, 1);
  const hot = state.climate.temperature > thresholds.value.tempMax;
  const cold = state.climate.temperature < thresholds.value.tempMin;
  const dry = state.climate.humidity < thresholds.value.humidityMin;
  const wet = state.climate.humidity > thresholds.value.humidityMax;
  const occupied = state.people.occupied;
  const smoke = smokeAlarm.value;

  updateLightingVisuals();

  if (liveObjects.hvac) {
    const color = state.devices.cooling ? 0x60a5fa : state.devices.heating ? 0xf97316 : 0xe5e7eb;
    liveObjects.hvac.material.color.setHex(color);
    liveObjects.hvac.material.emissive.setHex(state.devices.cooling || state.devices.heating ? color : 0x000000);
    liveObjects.hvac.material.emissiveIntensity = state.devices.cooling || state.devices.heating ? 0.3 : 0;
  }

  if (liveObjects.humidifier) {
    const visible = Boolean(state.devices.humidifier || state.devices.dehumidifier);
    liveObjects.humidifier.material.color.setHex(dry ? 0x93c5fd : wet ? 0x94a3b8 : 0xd8ecf0);
    liveObjects.humidifier.material.emissive.setHex(visible ? 0x7dd3fc : 0x000000);
    liveObjects.humidifier.material.emissiveIntensity = visible ? 0.25 : 0;
  }

  if (liveObjects.dhtIndicator) {
    const climateColor = hot || wet ? 0xf97316 : cold || dry ? 0x60a5fa : 0x34d399;
    liveObjects.dhtIndicator.material.color.setHex(climateColor);
    liveObjects.dhtIndicator.material.emissive.setHex(climateColor);
    liveObjects.dhtIndicator.material.emissiveIntensity = 0.24;
  }

  if (liveObjects.pirIndicator) {
    const pirColor = occupied ? 0x22c55e : 0x64748b;
    liveObjects.pirIndicator.material.color.setHex(pirColor);
    liveObjects.pirIndicator.material.emissive.setHex(pirColor);
    liveObjects.pirIndicator.material.emissiveIntensity = occupied ? 0.9 : 0.12;
  }

  if (liveObjects.lightMeter) {
    liveObjects.lightMeter.material.color.setHex(lightLevel < 0.28 ? 0xf59e0b : 0x38bdf8);
    liveObjects.lightMeter.material.emissive.setHex(lightLevel < 0.28 ? 0xf59e0b : 0x38bdf8);
    liveObjects.lightMeter.material.emissiveIntensity = 0.18 + lightLevel * 0.6;
  }

  if (liveObjects.distanceMarker) {
    const distance = clamp(Number(data.distance ?? 0), 0, 120);
    liveObjects.distanceMarker.scale.z = clamp(distance / 55, 0.18, 1.8);
    liveObjects.distanceMarker.material.emissiveIntensity = Number(data.distance) < 15 ? 0.75 : 0.22;
  }

  if (liveObjects.beacon) {
    liveObjects.beacon.visible = smoke;
  }
  liveObjects.smokeClouds.forEach((cloud) => {
    cloud.visible = smoke;
  });
  liveObjects.people.forEach((person, index) => {
    person.visible = occupied && index < state.people.count;
  });
  if (liveObjects.door) {
    liveObjects.door.group.rotation.y = state.door.open ? liveObjects.door.openRotation : liveObjects.door.closedRotation;
  }
  if (liveObjects.doorBeacon) {
    const doorColor = state.door.open ? 0x22c55e : 0xf59e0b;
    liveObjects.doorBeacon.material.color.setHex(doorColor);
    liveObjects.doorBeacon.material.emissive.setHex(doorColor);
    liveObjects.doorBeacon.material.emissiveIntensity = state.door.open ? 0.95 : 0.42;
  }
}

function applyCameraPreset() {
  if (!camera || !controls) return;
  const preset = viewOptions.find((item) => item.id === activeViewId.value) || viewOptions[0];
  const cameraName = { overview: 'Camera_Overview', front: 'Camera_Front', top: 'Camera_Top' }[activeViewId.value];
  const authoredCamera = modelCameras.find((item) => item.name === cameraName);
  if (authoredCamera) authoredCamera.getWorldPosition(camera.position);
  else camera.position.copy(preset.position);
  controls.target.copy(preset.target);
  // Preserve the authored direction while widening the framing for narrow screens.
  const offset = camera.position.clone().sub(controls.target);
  if (camera.aspect < 1) camera.position.copy(controls.target).add(offset.multiplyScalar(1 / camera.aspect));
  controls.update();
}

async function refreshSensorData() {
  if (pollInFlight || pollingStopped) return;
  window.clearTimeout(sensorTimer);
  pollInFlight = true;
  try {
    const data = await getCurrentSensorData();
    if (pollingStopped) return;
    failureCount = 0;
    if (Object.prototype.hasOwnProperty.call(data || {}, 'door_open')
      || Object.prototype.hasOwnProperty.call(data?.devices || {}, 'door_open')) {
      doorOverride.value = null;
    }
    sensorData.value = {
      ...sensorData.value,
      ...data,
      motion: Boolean(data.motion),
      presence: Boolean(data.presence ?? data.devices?.presence),
      devices: {
        ...sensorData.value.devices,
        ...(data.devices || {}),
      },
    };
    applyDataStatus(data);
    lastUpdated.value = new Date().toLocaleTimeString('zh-CN', { hour12: false });
  } catch (error) {
    if (pollingStopped) return;
    failureCount += 1;
    sensorState.value = 'disconnected';
    lastUpdated.value = '连接失败，保留最后状态';
  }
  finally {
    pollInFlight = false;
    retrySeconds.value = Math.min(30, 3 * 2 ** failureCount);
    if (!pollingStopped) sensorTimer = window.setTimeout(refreshSensorData, retrySeconds.value * 1000);
  }
  updateSensorVisuals();
}

function handleVisibilityChange() {
  if (!document.hidden) refreshSensorData();
}

async function toggleRoomLighting() {
  if (isLightingSaving.value || controlsUnavailable.value) return;

  const nextState = !lightingEnabled.value;
  isLightingSaving.value = true;
  controlError.value = '';
  try {
    const result = await setLightingDevice(nextState, nextState ? 100 : 0, 'room-3d');
    if (result?.success !== true || typeof result?.devices?.lighting !== 'boolean') {
      throw new Error('Lighting command was not acknowledged');
    }
    sensorData.value = {
      ...sensorData.value,
      devices: {
        ...sensorData.value.devices,
        ...(result?.devices || {}),
        lighting: result?.devices?.lighting ?? nextState,
        lighting_brightness: result?.devices?.lighting_brightness ?? (nextState ? 100 : 0),
        lighting_source: result?.devices?.lighting_source ?? 'room-3d',
      },
    };
    applyDataStatus(result);
    lastUpdated.value = new Date().toLocaleTimeString('zh-CN', { hour12: false });
  } catch (error) {
    controlError.value = '灯光控制失败，保留最后确认状态，请检查连接后重试。';
  } finally {
    isLightingSaving.value = false;
    updateSensorVisuals();
  }
}

async function toggleRoomDoor() {
  if (isDoorSaving.value || controlsUnavailable.value) return;
  isDoorSaving.value = true;
  controlError.value = '';
  const nextState = !roomState.value.door.open;
  try {
    const result = await setDoorDevice(nextState, 'room-3d');
    const serverDoorState = result?.devices?.door_open ?? result?.door_open;
    if (result?.success !== true || typeof serverDoorState !== 'boolean') {
      throw new Error('Door servo endpoint is not available on the connected backend');
    }
    doorOverride.value = null;
    sensorData.value = {
      ...sensorData.value,
      ...(result || {}),
      devices: {
        ...sensorData.value.devices,
        ...(result?.devices || {}),
        door_open: serverDoorState,
        door_source: result?.devices?.door_source ?? 'room-3d',
      },
      door_open: serverDoorState,
      door_source: result?.devices?.door_source ?? 'room-3d',
    };
    applyDataStatus(result);
    lastUpdated.value = new Date().toLocaleTimeString('zh-CN', { hour12: false });
  } catch (error) {
    controlError.value = '门控制失败，保留最后确认状态，请检查连接后重试。';
  } finally {
    isDoorSaving.value = false;
  }
  updateSensorVisuals();
}

function handleViewportClick(event) {
  if (!renderer || !camera) return;

  const rect = renderer.domElement.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const lightHits = raycaster.intersectObjects(liveObjects.clickableLights, false);
  const doorHits = raycaster.intersectObjects(liveObjects.clickableDoors, false);
  if (doorHits.length) {
    toggleRoomDoor();
  } else if (lightHits.length) {
    toggleRoomLighting();
  }
}

function animate() {
  animationId = window.requestAnimationFrame(animate);
  const elapsed = (performance.now() - animationStartedAt) / 1000;

  liveObjects.people.forEach((person, index) => {
    person.position.y = (person.userData.baseY ?? 0) + Math.sin(elapsed * 2 + index) * 0.025;
  });
  liveObjects.smokeClouds.forEach((cloud, index) => {
    cloud.position.y += Math.sin(elapsed * 0.9 + index) * 0.0008;
    cloud.rotation.y += 0.003 + index * 0.001;
  });
  if (liveObjects.beacon?.visible) {
    liveObjects.beacon.material.emissiveIntensity = 0.65 + Math.sin(elapsed * 8) * 0.45;
  }

  controls?.update();
  renderer?.render(scene, camera);
}

function disposeObject(object) {
  object.traverse((child) => {
    if (child.geometry) child.geometry.dispose();
    if (child.material) {
      const materials = Array.isArray(child.material) ? child.material : [child.material];
      materials.forEach((material) => material.dispose());
    }
  });
}

function disposeScene() {
  window.cancelAnimationFrame(animationId);
  pollingStopped = true;
  modelGeneration += 1;
  window.clearTimeout(sensorTimer);
  document.removeEventListener('visibilitychange', handleVisibilityChange);
  resizeObserver?.disconnect();
  controls?.dispose();
  if (roomGroup) disposeObject(roomGroup);
  renderer?.dispose();
  renderer?.domElement?.remove();
  scene = null;
  camera = null;
  renderer = null;
  controls = null;
  roomGroup = null;
}

watch(activeRoomId, () => {
  buildActiveRoom();
  applyCameraPreset();
});

watch(activeMoodId, () => {
  applyMoodToScene();
  updateSensorVisuals();
});

watch(activeViewId, applyCameraPreset);

onMounted(() => {
  initScene();
  pollingStopped = false;
  refreshSensorData();
  document.addEventListener('visibilitychange', handleVisibilityChange);
  animate();
});

onUnmounted(disposeScene);
</script>

<template>
  <div class="model-page">
    <aside class="control-rail">
      <section class="hero-panel">
        <p class="eyebrow">SECOND SEMESTER DEMO</p>
        <h1>3D智能会议室模型展厅</h1>
        <div class="requirement-line">
          <i class="fa-solid fa-cubes"></i>
          <span>{{ modelStatus }}</span>
        </div>
      </section>

      <section class="control-panel lighting-panel">
        <h2>灯光联动</h2>
        <button
          type="button"
          class="lighting-toggle"
          :class="{ active: lightingEnabled }"
          :disabled="isLightingSaving || controlsUnavailable"
          @click="toggleRoomLighting"
        >
          <i class="fa-solid" :class="isLightingSaving ? 'fa-spinner fa-spin' : 'fa-lightbulb'"></i>
          <span>{{ lightingEnabled ? '关闭LED灯' : '打开LED灯' }}</span>
          <small>{{ lightingEnabled ? `${lightingBrightness}%` : 'OFF' }}</small>
        </button>
        <p class="lighting-copy">
          {{ lightingSourceText }}，{{ sensorState === 'simulation' ? '模拟设备与3D顶灯同步' : '根据设备响应更新3D顶灯' }}
        </p>
      </section>

      <section class="control-panel state-panel">
        <h2>统一状态对象</h2>
        <div class="state-list">
          <div class="state-row">
            <span class="state-icon people"><i class="fa-solid fa-person"></i></span>
            <span class="state-label">人员</span>
            <strong>{{ roomState.people.occupied ? roomState.people.countKnown ? `${roomState.people.count} 人` : '有人（PIR）' : '无人' }}</strong>
          </div>
          <button type="button" class="state-row state-button" :disabled="isDoorSaving || controlsUnavailable" @click="toggleRoomDoor">
            <span class="state-icon door"><i class="fa-solid" :class="roomState.door.open ? 'fa-door-open' : 'fa-door-closed'"></i></span>
            <span class="state-label">门禁</span>
            <strong>{{ roomState.door.open ? '已开启' : '已关闭' }}</strong>
            <small>点击切换</small>
          </button>
          <div class="state-row">
            <span class="state-icon climate"><i class="fa-solid fa-temperature-half"></i></span>
            <span class="state-label">环境</span>
            <strong>{{ formatValue(roomState.climate.temperature, '℃', 1) }} / {{ formatValue(roomState.climate.humidity, '%', 0) }}</strong>
          </div>
          <div class="state-row">
            <span class="state-icon device"><i class="fa-solid fa-lightbulb"></i></span>
            <span class="state-label">设备</span>
            <strong>{{ lightingEnabled ? '照明开启' : '照明关闭' }}</strong>
          </div>
        </div>
        <p class="lighting-copy">门状态来源：{{ roomState.door.source === 'local-preview' ? '本地演示' : roomState.door.source === 'simulation' ? '模拟接口' : '后端指令状态（未接门磁）' }}</p>
        <a class="export-link" :href="getSensorExportUrl()" download="unified_meeting_room_data.csv">导出采样 CSV</a>
        <p v-if="controlError" class="control-error" role="alert">{{ controlError }}</p>
      </section>

      <section class="control-panel">
        <h2>会议室切换</h2>
        <div class="button-stack">
          <button
            v-for="room in roomOptions"
            :key="room.id"
            type="button"
            class="choice-button"
            :class="{ active: activeRoomId === room.id }"
            :title="room.name"
            @click="activeRoomId = room.id"
          >
            <i :class="room.icon"></i>
            <span>{{ room.name }}</span>
            <small>{{ room.badge }}</small>
          </button>
        </div>
      </section>

      <section class="control-panel">
        <h2>氛围模式</h2>
        <div class="button-stack">
          <button
            v-for="mood in moodOptions"
            :key="mood.id"
            type="button"
            class="choice-button compact"
            :class="{ active: activeMoodId === mood.id }"
            :title="mood.name"
            @click="activeMoodId = mood.id"
          >
            <i :class="mood.icon"></i>
            <span>{{ mood.name }}</span>
          </button>
        </div>
      </section>

      <section class="control-panel">
        <h2>视角预设</h2>
        <div class="button-stack">
          <button
            v-for="view in viewOptions"
            :key="view.id"
            type="button"
            class="choice-button compact"
            :class="{ active: activeViewId === view.id }"
            :title="view.name"
            @click="activeViewId = view.id"
          >
            <i :class="view.icon"></i>
            <span>{{ view.name }}</span>
          </button>
        </div>
      </section>
    </aside>

    <main class="model-stage">
      <div v-if="smokeAlarm && sensorState !== 'disconnected'" class="sensor-warning" role="alert">{{ Number(sensorData.smoke) > thresholds.smoke ? '烟雾越界，报警中' : '设备报警已开启' }}</div>
      <div v-else-if="sensorState === 'partial'" class="sensor-warning" role="alert">部分传感器不可用或数据过期；温湿度缺失显示 --，门灯状态仍可同步</div>
      <div v-else-if="sensorState === 'disconnected'" class="sensor-warning" role="alert">传感器服务连接断开，当前数值为最后状态；{{ retrySeconds }} 秒后重试 <button type="button" @click="refreshSensorData">立即重连</button></div>
      <div ref="viewportRef" class="viewport" @click="handleViewportClick"></div>

      <div class="stage-bar">
        <div>
          <p>{{ activeRoom.name }}</p>
          <strong>{{ activeMood.name }}</strong>
        </div>
        <div class="stage-state" aria-label="场景状态">
          <span :class="{ active: roomState.people.occupied }"><i class="fa-solid fa-person"></i>{{ roomState.people.occupied ? roomState.people.countKnown ? `${roomState.people.count}人` : '有人' : '无人' }}</span>
          <span :class="{ active: roomState.door.open }"><i class="fa-solid" :class="roomState.door.open ? 'fa-door-open' : 'fa-door-closed'"></i>{{ roomState.door.open ? '门开' : '门关' }}</span>
          <span :class="{ active: lightingEnabled }"><i class="fa-solid fa-lightbulb"></i>{{ lightingEnabled ? '灯开' : '灯关' }}</span>
        </div>
        <div class="status-pill" :class="sensorState">
          <i class="fa-solid fa-signal"></i>
          <span>{{ sensorStatusText }}</span>
          <small>{{ lastUpdated }}</small>
        </div>
      </div>

      <div class="sensor-dock">
        <div
          v-for="item in sensorCards"
          :key="item.label"
          class="sensor-card"
          :class="item.tone"
        >
          <i :class="item.icon"></i>
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.export-link { color: #5eead4; font-size: 0.8rem; }
.sensor-warning { position: absolute; top: 76px; left: 18px; right: 18px; z-index: 3; padding: 10px; background: #7c2d12; color: white; border-radius: 8px; font-size: 0.82rem; }
.status-pill.disconnected, .status-pill.partial { color: #b45309; }
* {
  box-sizing: border-box;
}

.model-page {
  min-height: calc(100vh - 72px);
  display: grid;
  grid-template-columns: 336px minmax(0, 1fr);
  background: #0b1418;
  color: #f8fafc;
}

.control-rail {
  position: relative;
  z-index: 2;
  min-height: calc(100vh - 72px);
  padding: 14px 12px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  background: #0b1418;
  border-right: 1px solid rgba(226, 232, 240, 0.12);
}

.hero-panel,
.control-panel {
  border: 1px solid rgba(226, 232, 240, 0.14);
  background: rgba(12, 24, 29, 0.94);
  border-radius: 8px;
}

.hero-panel {
  padding: 22px;
}

.eyebrow {
  margin: 0 0 10px;
  color: #f3b75b;
  font-size: 0.78rem;
  line-height: 1;
  font-weight: 800;
  letter-spacing: 0;
}

.hero-panel h1 {
  margin: 0;
  max-width: 260px;
  font-size: 1.72rem;
  line-height: 1.18;
  color: #f8fafc;
}

.requirement-line {
  margin-top: 16px;
  height: 34px;
  display: inline-flex;
  align-items: center;
  gap: 9px;
  padding: 0 12px;
  border-radius: 8px;
  border: 1px solid rgba(243, 183, 91, 0.36);
  color: #ffd18a;
  background: rgba(99, 73, 32, 0.38);
  font-size: 0.86rem;
  font-weight: 800;
}

.control-panel {
  padding: 16px 18px 18px;
}

.control-panel h2 {
  margin: 0 0 12px;
  color: #ffd18a;
  font-size: 0.96rem;
  line-height: 1;
}

.button-stack {
  display: grid;
  gap: 10px;
}

.choice-button {
  width: 100%;
  min-height: 44px;
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  padding: 0 13px;
  border-radius: 8px;
  border: 1px solid rgba(226, 232, 240, 0.12);
  background: #1a252a;
  color: #eef6fb;
  text-align: left;
  cursor: pointer;
  font: inherit;
  font-size: 0.88rem;
  font-weight: 800;
  transition: transform 160ms ease, border-color 160ms ease, background 160ms ease;
}

.choice-button i {
  color: #9fb3bd;
  text-align: center;
}

.choice-button small {
  color: #9fb3bd;
  font-size: 0.76rem;
  font-weight: 800;
}

.choice-button span {
  min-width: 0;
  overflow-wrap: anywhere;
}

.choice-button:hover {
  transform: translateY(-1px);
  border-color: rgba(243, 183, 91, 0.34);
}

.choice-button.active {
  background: #4a3721;
  border-color: rgba(243, 183, 91, 0.72);
  color: #ffffff;
}

.choice-button.active i,
.choice-button.active small {
  color: #ffd18a;
}

.choice-button.compact {
  grid-template-columns: 22px minmax(0, 1fr);
  min-height: 42px;
}

.lighting-toggle {
  width: 100%;
  min-height: 56px;
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  padding: 0 13px;
  border-radius: 8px;
  border: 1px solid rgba(226, 232, 240, 0.12);
  background: #1a252a;
  color: #eef6fb;
  font: inherit;
  font-weight: 900;
  cursor: pointer;
}

.lighting-toggle i {
  color: #94a3b8;
}

.lighting-toggle small {
  color: #9fb3bd;
  font-size: 0.76rem;
  font-weight: 900;
}

.lighting-toggle.active {
  background: #4a3721;
  border-color: rgba(243, 183, 91, 0.82);
  box-shadow: 0 0 22px rgba(243, 183, 91, 0.16);
}

.lighting-toggle.active i,
.lighting-toggle.active small {
  color: #ffd18a;
}

.lighting-copy {
  margin: 10px 0 0;
  color: #9fb3bd;
  font-size: 0.78rem;
  line-height: 1.45;
}

.state-list {
  display: grid;
  gap: 7px;
}

.state-row {
  min-height: 38px;
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  color: #d7e5ea;
  font-size: 0.82rem;
}

.state-row strong {
  color: #f8fafc;
  font-size: 0.8rem;
  white-space: nowrap;
}

.state-row small {
  grid-column: 2 / -1;
  color: #8fa4ad;
  font-size: 0.7rem;
  line-height: 1;
}

.state-icon {
  width: 24px;
  height: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 7px;
  background: rgba(255, 255, 255, 0.08);
  color: #93c5fd;
}

.state-icon.people { color: #5eead4; }
.state-icon.door { color: #fbbf24; }
.state-icon.climate { color: #fb7185; }
.state-icon.device { color: #facc15; }

.state-button {
  width: 100%;
  padding: 0;
  border: 0;
  background: transparent;
  text-align: left;
  cursor: pointer;
  font: inherit;
}

.state-button:hover .state-icon.door {
  color: #fef08a;
  background: rgba(250, 204, 21, 0.16);
}

.model-stage {
  position: relative;
  min-height: calc(100vh - 72px);
  overflow: hidden;
  background: #cbd6dd;
}

.viewport {
  position: absolute;
  inset: 0;
}

.viewport :deep(canvas) {
  display: block;
  width: 100%;
  height: 100%;
  outline: none;
}

.stage-bar {
  position: absolute;
  top: 18px;
  left: 18px;
  right: 18px;
  min-height: 58px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  pointer-events: none;
}

.stage-state {
  min-height: 42px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 0 8px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(10px);
}

.stage-state span {
  min-height: 28px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 0 8px;
  border-radius: 6px;
  color: #52646d;
  background: rgba(15, 23, 42, 0.06);
  font-size: 0.74rem;
  font-weight: 900;
  white-space: nowrap;
}

.stage-state span.active {
  color: #0f766e;
  background: rgba(20, 184, 166, 0.16);
}

.stage-bar > div:first-child {
  min-width: 180px;
  padding: 10px 14px;
  border-radius: 8px;
  color: #0f172a;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(10px);
}

.stage-bar p {
  margin: 0 0 3px;
  color: #40515b;
  font-size: 0.78rem;
  font-weight: 800;
}

.stage-bar strong {
  color: #0b1418;
  font-size: 1.06rem;
}

.status-pill {
  height: 42px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 0 13px;
  border-radius: 8px;
  color: #0f172a;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(10px);
  font-size: 0.84rem;
  font-weight: 900;
}

.status-pill.live i {
  color: #16a34a;
}

.status-pill.demo i {
  color: #d97706;
}

.status-pill.connecting i {
  color: #2563eb;
}

.status-pill small {
  color: #52646d;
  font-size: 0.76rem;
  font-weight: 800;
}

.sensor-dock {
  position: absolute;
  left: 18px;
  right: 18px;
  bottom: 18px;
  display: grid;
  grid-template-columns: repeat(8, minmax(72px, 1fr));
  gap: 10px;
  pointer-events: none;
}

.sensor-card {
  min-height: 70px;
  display: grid;
  grid-template-columns: 16px minmax(0, 1fr);
  grid-template-rows: auto auto;
  align-items: center;
  column-gap: 6px;
  row-gap: 3px;
  padding: 11px 8px;
  border-radius: 8px;
  color: #0f172a;
  background: rgba(255, 255, 255, 0.76);
  border: 1px solid rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(10px);
}

.sensor-card i {
  grid-row: 1 / 3;
  font-size: 1rem;
  color: #3b6470;
}

.sensor-card span {
  color: #52646d;
  font-size: 0.76rem;
  line-height: 1;
  font-weight: 900;
}

.sensor-card strong {
  min-width: 0;
  color: #0b1418;
  font-size: 1.05rem;
  line-height: 1.12;
  white-space: nowrap;
}

.sensor-card.warn i,
.sensor-card.dim i {
  color: #d97706;
}

.sensor-card.danger i {
  color: #dc2626;
}

.sensor-card.active i,
.sensor-card.ok i {
  color: #16876a;
}

.sensor-card.idle i {
  color: #64748b;
}

.control-error { color: #fca5a5; font-size: 0.85rem; line-height: 1.5; }

@media (min-width: 981px) {
  .model-page { height: max(640px, calc(100vh - 170px)); min-height: 0; }
  .control-rail { min-height: 0; overflow-y: auto; }
  .model-stage { min-height: 0; }
}

@media (min-width: 981px) and (max-width: 1200px) {
  .sensor-dock { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  .viewport { bottom: 170px; top: 70px; }
}

@media (max-width: 980px) {
  .model-page {
    grid-template-columns: 1fr;
  }

  .control-rail {
    min-height: 0;
    border-right: 0;
    border-bottom: 1px solid rgba(226, 232, 240, 0.12);
  }

  .hero-panel {
    padding: 18px;
  }

  .hero-panel h1 {
    max-width: none;
    font-size: 1.45rem;
  }

  .control-panel {
    padding: 14px;
  }

  .button-stack {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .choice-button,
  .choice-button.compact {
    grid-template-columns: 20px minmax(0, 1fr);
    min-height: 44px;
  }

  .choice-button small {
    display: none;
  }

  .model-stage {
    min-height: 620px;
  }

  .sensor-dock {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .model-page {
    display: flex;
    flex-direction: column;
  }

  .model-stage {
    order: 1;
  }

  .control-rail {
    order: 2;
  }

  .control-rail {
    padding: 10px;
    gap: 10px;
  }

  .button-stack {
    grid-template-columns: 1fr;
  }

  .model-stage {
    min-height: 640px;
  }

  .stage-bar {
    top: 10px;
    left: 10px;
    right: 10px;
    align-items: stretch;
    flex-direction: column;
  }

  .status-pill {
    justify-content: flex-start;
  }

  .stage-state {
    width: 100%;
    justify-content: space-between;
  }

  .sensor-dock {
    left: 10px;
    right: 10px;
    bottom: 10px;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .sensor-card {
    min-height: 62px;
  }

  .model-stage { display: flex; flex-direction: column; min-height: 0; }
  .stage-bar { order: 0; position: relative; inset: auto; padding: 10px; }
  .viewport { order: 1; position: relative; inset: auto; height: 360px; flex: none; }
  .sensor-dock { order: 2; position: relative; inset: auto; margin: 10px; }
  .sensor-warning { order: 0; position: relative; inset: auto; margin: 10px; }
}
</style>
