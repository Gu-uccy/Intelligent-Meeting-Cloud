import dayjs from 'dayjs';
import avatar from '@/assets/imgs/avatar.svg';
import {
  createMockReservation,
  createMockReservations,
  createMockRooms,
  getMockReservations,
  getMockRooms,
  getMockTimeSlots,
  MOCK_STORAGE_KEYS,
  resetMockBookingDataset,
  saveMockReservations,
  saveMockRooms,
} from '@/mocks/bookingAssistant';

const STORAGE_KEYS = {
  users: 'imc_mock_users_v1',
  faults: 'imc_mock_faults_v1',
  notifications: 'imc_mock_notifications_v1',
};

const DEFAULT_PASSWORD = '123456';
const MOCK_DELAY = 120;

const withDelay = (payload) =>
  new Promise((resolve) => {
    window.setTimeout(() => resolve(payload), MOCK_DELAY);
  });

const success = (data = null, msg = 'success') => withDelay({ code: 1, data, msg });
const failure = (msg = 'Operation failed', data = null) => withDelay({ code: 0, data, msg });

const hasWindow = () => typeof window !== 'undefined' && typeof window.localStorage !== 'undefined';

const readStorage = (key, fallback) => {
  if (!hasWindow()) return fallback;
  const raw = window.localStorage.getItem(key);
  if (!raw) return fallback;

  try {
    return JSON.parse(raw);
  } catch (error) {
    console.warn(`Failed to parse storage for ${key}`, error);
    return fallback;
  }
};

const writeStorage = (key, value) => {
  if (!hasWindow()) return;
  window.localStorage.setItem(key, JSON.stringify(value));
};

const paginate = (list, { page = 1, pageSize = 10 } = {}) => {
  const currentPage = Number(page) || 1;
  const size = Number(pageSize) || 10;
  const start = (currentPage - 1) * size;

  return {
    records: list.slice(start, start + size),
    total: list.length,
    current: currentPage,
    pageSize: size,
  };
};

const omitPassword = (user) => {
  const { password, ...rest } = user;
  return rest;
};

const getPersistedUserState = () => readStorage('user', {});

const getCurrentUserProfile = () => {
  const persisted = getPersistedUserState();
  return persisted?.userInfo?.user || persisted?.userInfo || {};
};

const getCurrentUserId = () => {
  const profile = getCurrentUserProfile();
  return profile?.id || 3;
};

const getCurrentUserAccount = () => {
  const profile = getCurrentUserProfile();
  return profile?.loginAccount || '';
};

const createMockUsers = () => {
  const now = dayjs();

  return [
    {
      id: 1,
      loginAccount: 'sys_admin',
      password: DEFAULT_PASSWORD,
      username: 'System Admin',
      email: 'sys_admin@mock.local',
      phone: '13800000001',
      gender: 1,
      isActive: 1,
      isAdmin: 1,
      image: avatar,
      remark: 'Platform administrator account',
      createTime: now.subtract(90, 'day').format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      id: 2,
      loginAccount: 'room_admin',
      password: DEFAULT_PASSWORD,
      username: 'Room Admin',
      email: 'room_admin@mock.local',
      phone: '13800000002',
      gender: 2,
      isActive: 1,
      isAdmin: 1,
      image: avatar,
      remark: 'Meeting room operations manager',
      createTime: now.subtract(60, 'day').format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      id: 3,
      loginAccount: 'test_user',
      password: DEFAULT_PASSWORD,
      username: 'Test User',
      email: 'test_user@mock.local',
      phone: '13800000003',
      gender: 1,
      isActive: 1,
      isAdmin: 0,
      image: avatar,
      remark: 'Default user for booking demo',
      createTime: now.subtract(30, 'day').format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      id: 4,
      loginAccount: 'alice_pm',
      password: DEFAULT_PASSWORD,
      username: 'Alice PM',
      email: 'alice@mock.local',
      phone: '13800000004',
      gender: 2,
      isActive: 1,
      isAdmin: 0,
      image: avatar,
      remark: 'Product team member',
      createTime: now.subtract(20, 'day').format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      id: 5,
      loginAccount: 'bob_dev',
      password: DEFAULT_PASSWORD,
      username: 'Bob Dev',
      email: 'bob@mock.local',
      phone: '13800000005',
      gender: 1,
      isActive: 1,
      isAdmin: 0,
      image: avatar,
      remark: 'Engineering team member',
      createTime: now.subtract(15, 'day').format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      id: 6,
      loginAccount: 'carol_ops',
      password: DEFAULT_PASSWORD,
      username: 'Carol Ops',
      email: 'carol@mock.local',
      phone: '13800000006',
      gender: 2,
      isActive: 1,
      isAdmin: 0,
      image: avatar,
      remark: 'Office operations coordinator',
      createTime: now.subtract(7, 'day').format('YYYY-MM-DD HH:mm:ss'),
    },
  ];
};

const createMockFaults = () => {
  const now = dayjs();

  return [
    {
      id: 3001,
      faultNo: 'FAULT-3001',
      deviceName: 'Projector',
      roomId: 103,
      reportUserId: 3,
      status: 0,
      faultDesc: 'Projector image flickers during presentation.',
      createTime: now.subtract(1, 'day').format('YYYY-MM-DD HH:mm:ss'),
      updateTime: now.subtract(1, 'day').format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      id: 3002,
      faultNo: 'FAULT-3002',
      deviceName: 'Microphone',
      roomId: 104,
      reportUserId: 5,
      status: 1,
      faultDesc: 'Wireless microphone disconnects after a few minutes.',
      createTime: now.subtract(2, 'day').format('YYYY-MM-DD HH:mm:ss'),
      updateTime: now.subtract(1, 'day').format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      id: 3003,
      faultNo: 'FAULT-3003',
      deviceName: 'Display',
      roomId: 101,
      reportUserId: 4,
      status: 2,
      faultDesc: 'The wall display needed a reboot and now works normally.',
      createTime: now.subtract(4, 'day').format('YYYY-MM-DD HH:mm:ss'),
      updateTime: now.subtract(3, 'day').format('YYYY-MM-DD HH:mm:ss'),
    },
  ];
};

const createMockNotifications = () => [];

const getUsers = () => readStorage(STORAGE_KEYS.users, createMockUsers());
const saveUsers = (users) => writeStorage(STORAGE_KEYS.users, users);
const getFaults = () => readStorage(STORAGE_KEYS.faults, createMockFaults());
const saveFaults = (faults) => writeStorage(STORAGE_KEYS.faults, faults);
const getNotifications = () => readStorage(STORAGE_KEYS.notifications, createMockNotifications());
const saveNotifications = (notifications) => writeStorage(STORAGE_KEYS.notifications, notifications);

const getRoomMap = () =>
  getMockRooms().reduce((acc, room) => {
    acc[room.id] = room;
    return acc;
  }, {});

const getUserMap = () =>
  getUsers().reduce((acc, user) => {
    acc[user.id] = user;
    return acc;
  }, {});

const sortByTimeDesc = (list, field = 'createTime') =>
  [...list].sort((a, b) => dayjs(b[field]).valueOf() - dayjs(a[field]).valueOf());

const createApprovalNotification = ({ userId, reservation, status, remark }) => {
  const roomMap = getRoomMap();
  const room = roomMap[reservation.roomId];
  const roomLabel = room ? `${room.roomCode} ${room.location || ''}` : `会议室 #${reservation.roomId}`;
  const statusText = Number(status) === 1 ? '审核通过' : '审核驳回';
  const detailText = Number(status) === 1 ? '你现在可以按时使用该会议室。' : '你可以调整时间或会议室后重新提交申请。';

  return {
    id: Date.now(),
    userId: Number(userId),
    type: 'approval',
    status: Number(status),
    title: `预约${statusText}`,
    content: `${reservation.meetingTopic || '未命名会议'} · ${roomLabel} · ${dayjs(reservation.startTime).format('MM-DD HH:mm')}，${detailText}`,
    relatedId: reservation.id,
    remark: remark || '',
    isRead: false,
    createTime: dayjs().format('YYYY-MM-DD HH:mm:ss'),
  };
};

const serializeReservationForView = (reservation) => {
  const roomMap = getRoomMap();
  const userMap = getUserMap();
  const room = roomMap[reservation.roomId];
  const booker = userMap[reservation.userId];

  return {
    ...reservation,
    title: reservation.meetingTopic,
    room: room ? `${room.roomCode} ${room.location || ''}` : `Room #${reservation.roomId}`,
    booker: booker?.username || booker?.loginAccount || 'User',
    timeRange: `${dayjs(reservation.startTime).format('MM-DD HH:mm')} - ${dayjs(reservation.endTime).format('HH:mm')}`,
  };
};

const ensureCurrentUserInMockUsers = () => {
  const currentUserId = Number(getCurrentUserId());
  const profile = getCurrentUserProfile();
  const loginAccount = profile?.loginAccount || getCurrentUserAccount();

  if (!currentUserId || !loginAccount) return;

  const now = dayjs();
  const users = getUsers();
  const targetIndex = users.findIndex((item) => item.id === currentUserId || item.loginAccount === loginAccount);
  const currentUser = {
    id: currentUserId,
    loginAccount,
    password: DEFAULT_PASSWORD,
    username: profile?.username || loginAccount,
    email: profile?.email || `${loginAccount}@mock.local`,
    phone: profile?.phone || '',
    gender: Number(profile?.gender || 1),
    isActive: Number(profile?.isActive ?? 1),
    isAdmin: Number(profile?.isAdmin || 0),
    image: profile?.image || avatar,
    remark: '当前演示登录用户',
    createTime: profile?.createTime || now.format('YYYY-MM-DD HH:mm:ss'),
  };

  const nextUsers = [...users];
  if (targetIndex >= 0) {
    nextUsers[targetIndex] = {
      ...nextUsers[targetIndex],
      ...currentUser,
      password: nextUsers[targetIndex].password || DEFAULT_PASSWORD,
    };
  } else {
    nextUsers.push(currentUser);
  }

  saveUsers(nextUsers);
};

const ensureCurrentUserFaceAccessReservation = () => {
  const currentUserId = Number(getCurrentUserId());
  if (!currentUserId) return;

  ensureCurrentUserInMockUsers();

  const now = dayjs();
  const reservationNo = `FACE-DEMO-${currentUserId}`;
  const reservations = getMockReservations();
  const targetIndex = reservations.findIndex((item) => item.reservationNo === reservationNo);
  const demoReservation = {
    id: 880000 + currentUserId,
    reservationNo,
    userId: currentUserId,
    adminId: 2,
    roomId: 101,
    status: 1,
    meetingTopic: '人脸门禁演示预约',
    participantNum: 1,
    startTime: now.subtract(15, 'minute').format('YYYY-MM-DD HH:mm:ss'),
    endTime: now.add(2, 'hour').format('YYYY-MM-DD HH:mm:ss'),
    createTime: now.subtract(1, 'hour').format('YYYY-MM-DD HH:mm:ss'),
    updateTime: now.format('YYYY-MM-DD HH:mm:ss'),
    remark: 'face-access-demo',
  };

  const nextReservations = [...reservations];
  if (targetIndex >= 0) {
    nextReservations[targetIndex] = {
      ...nextReservations[targetIndex],
      ...demoReservation,
      id: nextReservations[targetIndex].id || demoReservation.id,
    };
  } else {
    nextReservations.push(demoReservation);
  }

  saveMockReservations(nextReservations);
};

const ensureOverlapFree = ({ roomId, startTime, endTime, currentId = null }) => {
  const start = dayjs(startTime);
  const end = dayjs(endTime);

  return !getMockReservations().some((item) => {
    if (item.roomId !== Number(roomId) || item.status === -1) return false;
    if (currentId && item.id === currentId) return false;
    const itemStart = dayjs(item.startTime);
    const itemEnd = dayjs(item.endTime);
    return start.isBefore(itemEnd) && end.isAfter(itemStart);
  });
};

const fileToDataUrl = (file) =>
  new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });

export function initMockPlatform() {
  if (!hasWindow()) return;

  if (!window.localStorage.getItem(MOCK_STORAGE_KEYS.rooms)) {
    writeStorage(MOCK_STORAGE_KEYS.rooms, createMockRooms());
  }

  if (!window.localStorage.getItem(MOCK_STORAGE_KEYS.reservations)) {
    writeStorage(MOCK_STORAGE_KEYS.reservations, createMockReservations());
  }

  if (!window.localStorage.getItem(STORAGE_KEYS.users)) {
    saveUsers(createMockUsers());
  }

  if (!window.localStorage.getItem(STORAGE_KEYS.faults)) {
    saveFaults(createMockFaults());
  }

  if (!window.localStorage.getItem(STORAGE_KEYS.notifications)) {
    saveNotifications(createMockNotifications());
  }

  ensureCurrentUserFaceAccessReservation();
}

export function resetMockPlatform() {
  resetMockBookingDataset();
  saveUsers(createMockUsers());
  saveFaults(createMockFaults());
  saveNotifications(createMockNotifications());
}

export async function loginMock(userDto) {
  initMockPlatform();
  const { loginAccount, password } = userDto;
  const matchedUser = getUsers().find((item) => item.loginAccount === loginAccount);

  if (!matchedUser) {
    return failure('Account not found');
  }

  if (matchedUser.isActive !== 1) {
    return failure('Account has been disabled');
  }

  if (matchedUser.password !== password) {
    return failure('Incorrect password');
  }

  const token = `mock-token-${matchedUser.id}-${Date.now()}`;
  return success({
    token,
    ...omitPassword(matchedUser),
  }, 'Login successful');
}

export async function logoutMock() {
  return success(null, 'Logout successful');
}

export async function registerMock(registerForm) {
  initMockPlatform();
  const users = getUsers();

  if (users.some((item) => item.loginAccount === registerForm.loginAccount)) {
    return failure('Account already exists');
  }

  const nextUser = {
    id: Date.now(),
    loginAccount: registerForm.loginAccount,
    password: registerForm.password || DEFAULT_PASSWORD,
    username: registerForm.username || registerForm.loginAccount,
    email: registerForm.email || '',
    phone: registerForm.phone || '',
    gender: Number(registerForm.gender || 0),
    isActive: 1,
    isAdmin: 0,
    image: avatar,
    remark: '',
    createTime: dayjs().format('YYYY-MM-DD HH:mm:ss'),
  };

  saveUsers([...users, nextUser]);
  return success(omitPassword(nextUser), 'Register successful');
}

export async function getUserPageMock(params = {}) {
  initMockPlatform();
  const keyword = (params.username || '').trim().toLowerCase();
  const filtered = sortByTimeDesc(
    getUsers()
      .filter((item) =>
        !keyword ? true : item.username.toLowerCase().includes(keyword) || item.loginAccount.toLowerCase().includes(keyword)
      )
      .map(omitPassword),
    'createTime'
  );

  return success(paginate(filtered, params));
}

export async function addUserMock(data) {
  initMockPlatform();
  const users = getUsers();

  if (users.some((item) => item.loginAccount === data.loginAccount)) {
    return failure('Login account already exists');
  }

  const newUser = {
    id: Date.now(),
    loginAccount: data.loginAccount,
    password: data.password || DEFAULT_PASSWORD,
    username: data.username || data.loginAccount,
    email: data.email || '',
    phone: data.phone || '',
    gender: Number(data.gender || 0),
    isActive: Number(data.isActive ?? 1),
    isAdmin: Number(data.isAdmin ?? 0),
    image: data.image || avatar,
    remark: data.remark || '',
    createTime: dayjs().format('YYYY-MM-DD HH:mm:ss'),
  };

  saveUsers([...users, newUser]);
  return success(omitPassword(newUser), 'User created');
}

export async function updateUserMock(data) {
  initMockPlatform();
  const users = getUsers();
  const targetIndex = users.findIndex((item) => item.id === Number(data.id));

  if (targetIndex === -1) {
    return failure('User not found');
  }

  const nextUsers = [...users];
  const previous = nextUsers[targetIndex];
  nextUsers[targetIndex] = {
    ...previous,
    ...data,
    id: previous.id,
    password: data.password || previous.password,
  };

  saveUsers(nextUsers);
  return success(omitPassword(nextUsers[targetIndex]), 'User updated');
}

export async function deleteUsersMock(ids = []) {
  initMockPlatform();
  const idSet = new Set(ids.map(Number));
  saveUsers(getUsers().filter((item) => !idSet.has(item.id)));
  return success(null, 'Users deleted');
}

export async function setUserActiveMock(status, id) {
  return updateUserMock({ id, isActive: Number(status) });
}

export async function getUserByIdMock(id) {
  initMockPlatform();
  const user = getUsers().find((item) => item.id === Number(id));
  return user ? success(omitPassword(user)) : failure('User not found');
}

export async function getUserRoomPageMock(params = {}) {
  initMockPlatform();
  const keyword = (params.roomCode || '').trim().toLowerCase();
  const filtered = getMockRooms().filter((room) => {
    const matchesId = params.id ? room.id === Number(params.id) : true;
    const matchesKeyword = keyword
      ? room.roomCode.toLowerCase().includes(keyword) || (room.location || '').toLowerCase().includes(keyword)
      : true;
    return matchesId && matchesKeyword;
  });

  return success(paginate(filtered, params));
}

export async function getUserRoomDetailMock(id) {
  initMockPlatform();
  const room = getMockRooms().find((item) => item.id === Number(id));
  return room ? success(room) : failure('Room not found');
}

export async function getTimeSlotsMock(params) {
  initMockPlatform();
  return success(getMockTimeSlots(params));
}

export async function addRoomMock(data) {
  initMockPlatform();
  const rooms = getMockRooms();

  if (rooms.some((item) => item.roomCode === data.roomCode)) {
    return failure('Room code already exists');
  }

  const nextRoom = {
    id: Date.now(),
    roomCode: data.roomCode,
    capacity: Number(data.capacity || 0),
    location: data.location || '',
    equipment: data.equipment || '',
    image: data.image || '',
    isActive: Number(data.isActive ?? 1),
    remark: data.remark || '',
  };

  saveMockRooms([...rooms, nextRoom]);
  return success(nextRoom, 'Room created');
}

export async function updateRoomMock(data) {
  initMockPlatform();
  const rooms = getMockRooms();
  const targetIndex = rooms.findIndex((item) => item.id === Number(data.id));

  if (targetIndex === -1) {
    return failure('Room not found');
  }

  const nextRooms = [...rooms];
  nextRooms[targetIndex] = {
    ...nextRooms[targetIndex],
    ...data,
    capacity: Number(data.capacity ?? nextRooms[targetIndex].capacity),
    isActive: Number(data.isActive ?? nextRooms[targetIndex].isActive),
  };

  saveMockRooms(nextRooms);
  return success(nextRooms[targetIndex], 'Room updated');
}

export async function deleteRoomsMock(ids = []) {
  initMockPlatform();
  const idSet = new Set(ids.map(Number));
  saveMockRooms(getMockRooms().filter((item) => !idSet.has(item.id)));
  return success(null, 'Rooms deleted');
}

export async function setRoomActiveMock(id, active) {
  return updateRoomMock({ id, isActive: Number(active) });
}

export async function getAdminRoomPageMock(params = {}) {
  return getUserRoomPageMock(params);
}

export async function addReservationMock(data) {
  initMockPlatform();

  if (!ensureOverlapFree({ roomId: data.roomId, startTime: data.startTime, endTime: data.endTime })) {
    return failure('Selected room is not available during this time range');
  }

  const reservation = createMockReservation({
    userId: Number(data.userId || getCurrentUserId()),
    roomId: Number(data.roomId),
    meetingTopic: data.meetingTopic || 'Untitled Meeting',
    startTime: data.startTime,
    endTime: data.endTime,
    remark: data.remark || '',
    participantNum: Number(data.participantNum || 1),
  });

  return success(serializeReservationForView(reservation), 'Reservation request submitted for approval');
}

export async function getMyReservationsMock() {
  initMockPlatform();
  ensureCurrentUserFaceAccessReservation();
  const currentUserId = getCurrentUserId();
  const list = sortByTimeDesc(
    getMockReservations()
      .filter((item) => item.userId === Number(currentUserId))
      .map(serializeReservationForView),
    'startTime'
  );

  return success(list);
}

export async function getReservationsByRoomIdMock(roomId) {
  initMockPlatform();
  ensureCurrentUserFaceAccessReservation();
  const records = sortByTimeDesc(
    getMockReservations()
      .filter((item) => item.roomId === Number(roomId))
      .map(serializeReservationForView),
    'startTime'
  );

  return success({ records, total: records.length });
}

export async function cancelReservationMock(id) {
  initMockPlatform();
  const target = getMockReservations().find((item) => item.id === Number(id));
  if (!target) {
    return failure('Reservation not found');
  }

  const nextReservations = getMockReservations().map((item) =>
    item.id === Number(id)
      ? {
          ...item,
          status: -1,
          updateTime: dayjs().format('YYYY-MM-DD HH:mm:ss'),
        }
      : item
  );

  saveMockReservations(nextReservations);
  return success(serializeReservationForView(nextReservations.find((item) => item.id === Number(id))), 'Reservation cancelled');
}

export async function getAdminReservationPageMock(params = {}) {
  initMockPlatform();
  ensureCurrentUserFaceAccessReservation();
  const keyword = (params.reservationNo || '').trim().toLowerCase();
  const records = sortByTimeDesc(
    getMockReservations()
      .filter((item) => {
        const matchesNo = keyword ? item.reservationNo.toLowerCase().includes(keyword) : true;
        const matchesRoom = params.roomId ? item.roomId === Number(params.roomId) : true;
        const matchesStatus = params.status === undefined ? true : item.status === Number(params.status);
        return matchesNo && matchesRoom && matchesStatus;
      })
      .map(serializeReservationForView),
    'startTime'
  );

  return success(paginate(records, params));
}

export async function updateReservationMock(data) {
  initMockPlatform();
  const reservations = getMockReservations();
  const targetIndex = reservations.findIndex((item) => item.id === Number(data.id));

  if (targetIndex === -1) {
    return failure('Reservation not found');
  }

  if (
    (data.startTime || data.endTime || data.roomId) &&
    !ensureOverlapFree({
      roomId: data.roomId || reservations[targetIndex].roomId,
      startTime: data.startTime || reservations[targetIndex].startTime,
      endTime: data.endTime || reservations[targetIndex].endTime,
      currentId: reservations[targetIndex].id,
    })
  ) {
    return failure('Updated time conflicts with another reservation');
  }

  const nextReservations = [...reservations];
  nextReservations[targetIndex] = {
    ...nextReservations[targetIndex],
    ...data,
    roomId: Number(data.roomId ?? nextReservations[targetIndex].roomId),
    participantNum: Number(data.participantNum ?? nextReservations[targetIndex].participantNum),
    updateTime: dayjs().format('YYYY-MM-DD HH:mm:ss'),
  };

  saveMockReservations(nextReservations);
  return success(serializeReservationForView(nextReservations[targetIndex]), 'Reservation updated');
}

export async function auditReservationMock(data) {
  const auditResponse = await updateReservationMock({
    id: data.id,
    status: Number(data.status),
    remark: data.remark,
  });

  if (auditResponse.code === 1) {
    const reservation = getMockReservations().find((item) => item.id === Number(data.id));
    if (reservation) {
      const notifications = getNotifications();
      const approvalNotification = createApprovalNotification({
        userId: reservation.userId,
        reservation,
        status: data.status,
        remark: data.remark,
      });
      saveNotifications(sortByTimeDesc([approvalNotification, ...notifications]));
    }
  }

  return auditResponse;
}

export async function getMyNotificationsMock() {
  initMockPlatform();
  const currentUserId = getCurrentUserId();
  const list = sortByTimeDesc(
    getNotifications().filter((item) => Number(item.userId) === Number(currentUserId)),
  );

  return success(list);
}

export async function reportFaultMock(data) {
  initMockPlatform();
  const faults = getFaults();
  const nextFault = {
    id: Date.now(),
    faultNo: `FAULT-${Date.now()}`,
    deviceName: data.deviceName || 'Unknown Device',
    roomId: Number(data.roomId || 0),
    reportUserId: getCurrentUserId(),
    status: 0,
    faultDesc: data.faultDesc || '',
    createTime: dayjs().format('YYYY-MM-DD HH:mm:ss'),
    updateTime: dayjs().format('YYYY-MM-DD HH:mm:ss'),
  };

  saveFaults([nextFault, ...faults]);
  return success(nextFault, 'Fault reported');
}

export async function getFaultPageMock(params = {}) {
  initMockPlatform();
  const keyword = (params.faultNo || '').trim().toLowerCase();
  const records = sortByTimeDesc(
    getFaults().filter((item) => {
      const matchesNo = keyword ? item.faultNo.toLowerCase().includes(keyword) : true;
      const matchesStatus = params.status === undefined ? true : item.status === Number(params.status);
      return matchesNo && matchesStatus;
    }),
    'createTime'
  );

  return success(paginate(records, params));
}

export async function handleFaultMock(params) {
  initMockPlatform();
  const faults = getFaults();
  const targetIndex = faults.findIndex((item) => item.faultNo === params.faultNo);

  if (targetIndex === -1) {
    return failure('Fault record not found');
  }

  const nextFaults = [...faults];
  nextFaults[targetIndex] = {
    ...nextFaults[targetIndex],
    status: Number(params.status),
    updateTime: dayjs().format('YYYY-MM-DD HH:mm:ss'),
  };

  saveFaults(nextFaults);
  return success(nextFaults[targetIndex], 'Fault updated');
}

export async function uploadFileMock(file) {
  initMockPlatform();

  if (!file) {
    return failure('No file selected');
  }

  const resolvedFile = file instanceof File ? file : file.get?.('file') || null;

  if (!resolvedFile) {
    return failure('Invalid file payload');
  }

  const dataUrl = await fileToDataUrl(resolvedFile);
  return success(dataUrl, 'Upload successful');
}

export async function getStatisticsMock() {
  initMockPlatform();
  const reservations = getMockReservations().filter((item) => item.status !== -1);
  const faults = getFaults();
  const rooms = getMockRooms();

  const dailyData = Array.from({ length: 7 }).map((_, index) => {
    const date = dayjs().subtract(6 - index, 'day');
    const dayReservations = reservations.filter((item) =>
      dayjs(item.startTime).format('YYYY-MM-DD') === date.format('YYYY-MM-DD')
    );

    const totalUsageMinutes = dayReservations.reduce((sum, item) => {
      return sum + dayjs(item.endTime).diff(dayjs(item.startTime), 'minute');
    }, 0);

    return {
      date: date.format('YYYY-MM-DD'),
      totalUsageMinutes,
    };
  });

  return success({
    totalUsageCount: reservations.length,
    totalFaultCount: faults.length,
    totalRoomCount: rooms.length,
    dailyData,
  });
}
