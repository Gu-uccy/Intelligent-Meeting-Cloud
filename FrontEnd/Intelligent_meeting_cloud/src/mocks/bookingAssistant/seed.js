import dayjs from 'dayjs';
import roomImg from '@/assets/imgs/room.png';

const createReservationNo = (suffix) => `MOCK-${suffix}`;

export const MOCK_STORAGE_KEYS = {
  rooms: 'imc_mock_rooms_v1',
  reservations: 'imc_mock_reservations_v1',
};

export function createMockRooms() {
  return [
    {
      id: 101,
      roomCode: 'A101',
      capacity: 6,
      location: '1F North Wing',
      equipment: '白板,电视,无线投屏',
      image: roomImg,
      isActive: 1,
      remark: '适合站会和小型面试，靠近茶水间。',
    },
    {
      id: 102,
      roomCode: 'B201',
      capacity: 8,
      location: '2F East Wing',
      equipment: '投影仪,白板,视频会议',
      image: roomImg,
      isActive: 1,
      remark: '适合 6-8 人产品评审，支持远程连线。',
    },
    {
      id: 103,
      roomCode: 'C301',
      capacity: 12,
      location: '3F Center',
      equipment: '投影仪,白板,视频会议,音响',
      image: roomImg,
      isActive: 1,
      remark: '常用于项目复盘和跨部门协作会。',
    },
    {
      id: 104,
      roomCode: 'D401',
      capacity: 16,
      location: '4F South Wing',
      equipment: '双屏,视频会议,白板,麦克风',
      image: roomImg,
      isActive: 1,
      remark: '适合客户会议和多人路演。',
    },
    {
      id: 105,
      roomCode: 'E501',
      capacity: 20,
      location: '5F Multi Function Zone',
      equipment: '投影仪,双屏,音响,舞台灯光',
      image: roomImg,
      isActive: 0,
      remark: '当前维护中，暂不开放预约。',
    },
    {
      id: 106,
      roomCode: 'Innovation Hub',
      capacity: 10,
      location: '6F Creative Corner',
      equipment: '白板,无线投屏,视频会议,沙发区',
      image: roomImg,
      isActive: 1,
      remark: '适合头脑风暴、Workshop 和创意讨论。',
    },
  ];
}

export function createMockReservations() {
  const now = dayjs();
  const tomorrow = now.add(1, 'day');
  const dayAfterTomorrow = now.add(2, 'day');
  const nextWeek = now.add(7, 'day');

  return [
    {
      id: 9001,
      reservationNo: createReservationNo('9001'),
      userId: 3,
      adminId: 2,
      roomId: 102,
      status: 1,
      meetingTopic: '产品周会',
      participantNum: 8,
      startTime: tomorrow.hour(14).minute(0).second(0).format('YYYY-MM-DD HH:mm:ss'),
      endTime: tomorrow.hour(15).minute(0).second(0).format('YYYY-MM-DD HH:mm:ss'),
      createTime: now.subtract(2, 'day').format('YYYY-MM-DD HH:mm:ss'),
      updateTime: now.subtract(2, 'day').format('YYYY-MM-DD HH:mm:ss'),
      remark: '需要投影仪和视频会议。',
    },
    {
      id: 9002,
      reservationNo: createReservationNo('9002'),
      userId: 5,
      adminId: 2,
      roomId: 103,
      status: 1,
      meetingTopic: '技术评审会',
      participantNum: 10,
      startTime: tomorrow.hour(15).minute(0).second(0).format('YYYY-MM-DD HH:mm:ss'),
      endTime: tomorrow.hour(16).minute(30).second(0).format('YYYY-MM-DD HH:mm:ss'),
      createTime: now.subtract(1, 'day').format('YYYY-MM-DD HH:mm:ss'),
      updateTime: now.subtract(1, 'day').format('YYYY-MM-DD HH:mm:ss'),
      remark: '需要白板和音响。',
    },
    {
      id: 9003,
      reservationNo: createReservationNo('9003'),
      userId: 3,
      adminId: 2,
      roomId: 106,
      status: 1,
      meetingTopic: '用户访谈复盘',
      participantNum: 6,
      startTime: dayAfterTomorrow.hour(10).minute(0).second(0).format('YYYY-MM-DD HH:mm:ss'),
      endTime: dayAfterTomorrow.hour(11).minute(0).second(0).format('YYYY-MM-DD HH:mm:ss'),
      createTime: now.format('YYYY-MM-DD HH:mm:ss'),
      updateTime: now.format('YYYY-MM-DD HH:mm:ss'),
      remark: '偏轻松交流场景。',
    },
    {
      id: 9004,
      reservationNo: createReservationNo('9004'),
      userId: 3,
      adminId: 2,
      roomId: 104,
      status: 0,
      meetingTopic: '下周客户演示彩排',
      participantNum: 12,
      startTime: nextWeek.hour(9).minute(30).second(0).format('YYYY-MM-DD HH:mm:ss'),
      endTime: nextWeek.hour(11).minute(0).second(0).format('YYYY-MM-DD HH:mm:ss'),
      createTime: now.format('YYYY-MM-DD HH:mm:ss'),
      updateTime: now.format('YYYY-MM-DD HH:mm:ss'),
      remark: '等待审批。',
    },
    {
      id: 9005,
      reservationNo: createReservationNo('9005'),
      userId: 6,
      adminId: 2,
      roomId: 101,
      status: -1,
      meetingTopic: '已取消的培训签到说明会',
      participantNum: 4,
      startTime: now.subtract(1, 'day').hour(16).minute(0).second(0).format('YYYY-MM-DD HH:mm:ss'),
      endTime: now.subtract(1, 'day').hour(17).minute(0).second(0).format('YYYY-MM-DD HH:mm:ss'),
      createTime: now.subtract(3, 'day').format('YYYY-MM-DD HH:mm:ss'),
      updateTime: now.subtract(1, 'day').format('YYYY-MM-DD HH:mm:ss'),
      remark: '历史取消记录，方便演示取消态。',
    },
  ];
}
