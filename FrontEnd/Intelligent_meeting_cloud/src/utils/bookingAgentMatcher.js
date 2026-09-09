import dayjs from 'dayjs';

const parseEquipment = (equipment) =>
  Array.isArray(equipment)
    ? equipment
    : String(equipment || '')
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean);

const matchesEquipment = (roomEquipment, requiredEquipment = []) =>
  requiredEquipment.every((item) => roomEquipment.some((roomItem) => roomItem.includes(item) || item.includes(roomItem)));

const toDateTime = (date, timeText) => dayjs(`${date} ${timeText}:00`);

const slotOverlaps = (slot, startTime, endTime, date) => {
  const slotStart = dayjs(`${date} ${slot.startTime}`);
  const slotEnd = dayjs(`${date} ${slot.endTime}`);
  const targetStart = toDateTime(date, startTime);
  const targetEnd = toDateTime(date, endTime);

  return targetStart.isBefore(slotEnd) && targetEnd.isAfter(slotStart);
};

export async function findAvailableRoomsForDraft(draft, tools) {
  const roomsResponse = await tools.getUserRoomPage({ page: 1, pageSize: 100 });
  const rawRooms = roomsResponse?.data?.records || [];
  const activeRooms = rawRooms.filter((room) => Number(room.isActive) === 1);

  const candidateRooms = activeRooms.filter((room) => {
    const roomEquipment = parseEquipment(room.equipment);
    const capacityMatch = draft.attendeeCount ? Number(room.capacity) >= Number(draft.attendeeCount) : true;
    const equipmentMatch = matchesEquipment(roomEquipment, draft.equipment || []);
    const roomCodeMatch = draft.roomCode ? String(room.roomCode).toLowerCase().includes(String(draft.roomCode).toLowerCase()) : true;
    return capacityMatch && equipmentMatch && roomCodeMatch;
  });

  const roomResults = await Promise.all(
    candidateRooms.map(async (room) => {
      const slotResponse = await tools.getTimeSlots({
        roomId: room.id,
        date: draft.date,
      });

      const slots = slotResponse?.data || [];
      const hasConflict = slots.some((slot) => slot.status === 1 && slotOverlaps(slot, draft.startTime, draft.endTime, draft.date));

      if (hasConflict) return null;

      const roomEquipment = parseEquipment(room.equipment);
      const capacityGap = Number(room.capacity) - Number(draft.attendeeCount || 0);
      const matchReasons = [
        `容量 ${room.capacity} 人`,
        ...(draft.equipment || []).filter((item) => roomEquipment.some((roomItem) => roomItem.includes(item) || item.includes(roomItem))),
      ];

      return {
        id: room.id,
        roomId: room.id,
        roomCode: room.roomCode,
        location: room.location || '位置待补充',
        capacity: room.capacity,
        equipment: roomEquipment,
        startTime: draft.startTime,
        endTime: draft.endTime,
        date: draft.date,
        score: capacityGap >= 0 ? capacityGap : 999,
        matchReasons,
      };
    }),
  );

  return roomResults
    .filter(Boolean)
    .sort((a, b) => a.score - b.score)
    .slice(0, 4);
}

const matchesDate = (reservation, date) => (!date ? true : reservation.date === date);

const matchesTime = (reservation, startTime) => {
  if (!startTime) return true;
  return String(reservation.time || '').startsWith(startTime);
};

const matchesRoom = (reservation, roomCode) => {
  if (!roomCode) return true;
  return String(reservation.room || '').toLowerCase().includes(String(roomCode).toLowerCase());
};

export function findCancelableReservations(draft, reservations = []) {
  const activeReservations = reservations.filter((item) => item.status !== 'cancelled');

  const matched = activeReservations.filter(
    (item) => matchesDate(item, draft.date) && matchesTime(item, draft.startTime) && matchesRoom(item, draft.roomCode),
  );

  const finalList = matched.length ? matched : activeReservations;

  return finalList.slice(0, 5).map((item) => ({
    id: item.id,
    reservationId: item.id,
    title: item.title,
    room: item.room,
    date: item.date,
    time: item.time,
    status: item.status,
  }));
}
