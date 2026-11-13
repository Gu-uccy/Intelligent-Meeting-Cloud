import dayjs from 'dayjs';
import { createMockReservations, createMockRooms, MOCK_STORAGE_KEYS } from './seed';

const SLOT_START_HOUR = 8;
const SLOT_END_HOUR = 20;
const SLOT_DURATION_MINUTES = 30;

const hasWindow = () => typeof window !== 'undefined' && typeof window.localStorage !== 'undefined';

const readStorage = (key, fallback) => {
  if (!hasWindow()) return fallback;

  const raw = window.localStorage.getItem(key);
  if (!raw) return fallback;

  try {
    return JSON.parse(raw);
  } catch (error) {
    console.warn(`Failed to parse mock storage: ${key}`, error);
    return fallback;
  }
};

const writeStorage = (key, value) => {
  if (!hasWindow()) return;
  window.localStorage.setItem(key, JSON.stringify(value));
};

const sortReservations = (list) =>
  [...list].sort((a, b) => dayjs(a.startTime).valueOf() - dayjs(b.startTime).valueOf());

const buildReservationNo = () => `MOCK-${Date.now()}`;

const isSameDate = (dateText, reservation) =>
  dayjs(reservation.startTime).format('YYYY-MM-DD') === dayjs(dateText).format('YYYY-MM-DD');

const isOverlap = (slotStart, slotEnd, reservationStart, reservationEnd) =>
  slotStart.isBefore(reservationEnd) && slotEnd.isAfter(reservationStart);

export function ensureMockBookingDataset() {
  if (!hasWindow()) return;

  const rooms = readStorage(MOCK_STORAGE_KEYS.rooms, null);
  if (!rooms || !rooms.length) {
    writeStorage(MOCK_STORAGE_KEYS.rooms, createMockRooms());
  }

  const reservations = readStorage(MOCK_STORAGE_KEYS.reservations, null);
  if (!reservations || !reservations.length) {
    writeStorage(MOCK_STORAGE_KEYS.reservations, createMockReservations());
  }
}

export function resetMockBookingDataset() {
  if (!hasWindow()) return;
  writeStorage(MOCK_STORAGE_KEYS.rooms, createMockRooms());
  writeStorage(MOCK_STORAGE_KEYS.reservations, createMockReservations());
}

export function getMockRooms() {
  ensureMockBookingDataset();
  return readStorage(MOCK_STORAGE_KEYS.rooms, createMockRooms());
}

export function saveMockRooms(rooms) {
  writeStorage(MOCK_STORAGE_KEYS.rooms, rooms);
}

export function getMockReservations() {
  ensureMockBookingDataset();
  return sortReservations(readStorage(MOCK_STORAGE_KEYS.reservations, createMockReservations()));
}

export function saveMockReservations(reservations) {
  writeStorage(MOCK_STORAGE_KEYS.reservations, sortReservations(reservations));
}

export function createMockReservation(payload) {
  const reservations = getMockReservations();
  const now = dayjs().format('YYYY-MM-DD HH:mm:ss');
  const newReservation = {
    id: Date.now(),
    reservationNo: buildReservationNo(),
    adminId: null,
    status: 0,
    createTime: now,
    updateTime: now,
    remark: '',
    ...payload,
  };

  const nextReservations = [...reservations, newReservation];
  saveMockReservations(nextReservations);
  return newReservation;
}

export function cancelMockReservation(id) {
  const reservations = getMockReservations();
  const nextReservations = reservations.map((item) =>
    item.id === id
      ? {
          ...item,
          status: -1,
          updateTime: dayjs().format('YYYY-MM-DD HH:mm:ss'),
        }
      : item
  );

  saveMockReservations(nextReservations);
  return nextReservations.find((item) => item.id === id) || null;
}

export function getMockReservationsByRoom(roomId) {
  return getMockReservations().filter((item) => item.roomId === roomId);
}

export function getMockTimeSlots({ roomId, date }) {
  const targetDate = dayjs(date).format('YYYY-MM-DD');
  const today = dayjs();
  const roomReservations = getMockReservations().filter(
    (item) => item.roomId === Number(roomId) && item.status !== -1 && isSameDate(targetDate, item)
  );

  const slots = [];
  let cursor = dayjs(`${targetDate} ${String(SLOT_START_HOUR).padStart(2, '0')}:00:00`);
  const end = dayjs(`${targetDate} ${String(SLOT_END_HOUR).padStart(2, '0')}:00:00`);

  while (cursor.isBefore(end)) {
    const slotStart = cursor;
    const slotEnd = cursor.add(SLOT_DURATION_MINUTES, 'minute');
    const isBooked = roomReservations.some((reservation) =>
      isOverlap(slotStart, slotEnd, dayjs(reservation.startTime), dayjs(reservation.endTime))
    );

    let status = 0;
    if (slotEnd.isBefore(today)) {
      status = 2;
    } else if (isBooked) {
      status = 1;
    }

    slots.push({
      displayTime: `${slotStart.format('HH:mm')}-${slotEnd.format('HH:mm')}`,
      startTime: slotStart.format('HH:mm:ss'),
      endTime: slotEnd.format('HH:mm:ss'),
      status,
    });

    cursor = slotEnd;
  }

  return slots;
}
