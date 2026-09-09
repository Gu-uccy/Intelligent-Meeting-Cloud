import dayjs from 'dayjs';

const EQUIPMENT_KEYWORDS = [
  { label: '投影仪', patterns: ['投影', '投影仪', '投屏'] },
  { label: '白板', patterns: ['白板'] },
  { label: '视频会议', patterns: ['视频会议', '视频', '远程会议', '线上会议'] },
  { label: '无线投屏', patterns: ['无线投屏', '无线投影', '投屏'] },
  { label: '双屏', patterns: ['双屏', '双显示屏'] },
  { label: '音响', patterns: ['音响', '音箱'] },
  { label: '麦克风', patterns: ['麦克风', '话筒'] },
  { label: '沙发区', patterns: ['沙发', '沙发区'] },
];

const CHINESE_NUMBER_MAP = {
  一: 1,
  二: 2,
  两: 2,
  三: 3,
  四: 4,
  五: 5,
  六: 6,
  七: 7,
  八: 8,
  九: 9,
  十: 10,
};

const WEEKDAY_MAP = {
  日: 0,
  天: 0,
  一: 1,
  二: 2,
  三: 3,
  四: 4,
  五: 5,
  六: 6,
};

export function createEmptyAssistantDraft() {
  return {
    intent: '',
    date: '',
    startTime: '',
    endTime: '',
    attendeeCount: null,
    equipment: [],
    durationHours: null,
    roomCode: '',
    meetingTopic: '',
  };
}

const uniqueList = (list) => [...new Set(list.filter(Boolean))];

const normalizeHour = (hour, meridiem) => {
  let normalizedHour = Number(hour);

  if (meridiem === '下午' || meridiem === '晚上') {
    if (normalizedHour < 12) normalizedHour += 12;
  }

  if (meridiem === '中午' && normalizedHour >= 1 && normalizedHour <= 4) {
    normalizedHour += 12;
  }

  if (meridiem === '凌晨' && normalizedHour === 12) {
    normalizedHour = 0;
  }

  return normalizedHour;
};

const formatTime = (hour, minute = 0) =>
  `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`;

const readChineseNumber = (value) => CHINESE_NUMBER_MAP[value] || null;

const parseDurationHours = (message) => {
  const numericMatch = message.match(/(\d+(?:\.\d+)?)\s*小时/);
  if (numericMatch) return Number(numericMatch[1]);

  const chineseMatch = message.match(/([一二两三四五六七八九十])\s*个?小时/);
  if (chineseMatch) {
    return readChineseNumber(chineseMatch[1]);
  }

  return null;
};

const parseDate = (message, baseDate = dayjs()) => {
  const exactDateMatch = message.match(/(\d{4}-\d{1,2}-\d{1,2})/);
  if (exactDateMatch) {
    return dayjs(exactDateMatch[1]).format('YYYY-MM-DD');
  }

  const monthDateMatch = message.match(/(\d{1,2})月(\d{1,2})日/);
  if (monthDateMatch) {
    const year = baseDate.year();
    return dayjs(`${year}-${monthDateMatch[1]}-${monthDateMatch[2]}`).format('YYYY-MM-DD');
  }

  if (message.includes('今天')) return baseDate.format('YYYY-MM-DD');
  if (message.includes('明天')) return baseDate.add(1, 'day').format('YYYY-MM-DD');
  if (message.includes('后天')) return baseDate.add(2, 'day').format('YYYY-MM-DD');

  const weekdayMatch = message.match(/(下周|下下周|这周|本周)?周([一二三四五六日天])/);
  if (weekdayMatch) {
    const prefix = weekdayMatch[1] || '这周';
    const targetWeekday = WEEKDAY_MAP[weekdayMatch[2]];
    const currentWeekday = baseDate.day();
    let offset = targetWeekday - currentWeekday;

    if (prefix === '下周') offset += 7;
    if (prefix === '下下周') offset += 14;
    if ((prefix === '这周' || prefix === '本周') && offset < 0) offset += 7;

    return baseDate.add(offset, 'day').format('YYYY-MM-DD');
  }

  return '';
};

const extractTimeParts = (segment) => {
  const match = segment.match(/(凌晨|上午|中午|下午|晚上)?\s*(\d{1,2})(?:(?::|点)(\d{1,2}))?(半)?/);
  if (!match) return null;

  const sourceText = match[0];
  const hasTimeToken = /凌晨|上午|中午|下午|晚上|:|点|半/.test(sourceText);
  if (!hasTimeToken) return null;

  const meridiem = match[1] || '';
  const hour = normalizeHour(match[2], meridiem);
  const minute = match[4] ? 30 : Number(match[3] || 0);

  if (Number.isNaN(hour) || Number.isNaN(minute)) return null;

  return {
    meridiem,
    time: formatTime(hour, minute),
  };
};

const parseTimeRange = (message) => {
  const rangeMatch = message.match(
    /((?:凌晨|上午|中午|下午|晚上)?\s*\d{1,2}(?:(?::|点)\d{1,2})?(?:半)?)[\s]*(?:到|至|\-|~|—)[\s]*((?:凌晨|上午|中午|下午|晚上)?\s*\d{1,2}(?:(?::|点)\d{1,2})?(?:半)?)/,
  );

  if (!rangeMatch) return null;

  const start = extractTimeParts(rangeMatch[1]);
  const end = extractTimeParts(rangeMatch[2]);

  if (!start || !end) return null;

  if (!rangeMatch[2].match(/凌晨|上午|中午|下午|晚上/) && start.meridiem) {
    const normalizedEnd = extractTimeParts(`${start.meridiem}${rangeMatch[2]}`);
    if (normalizedEnd) {
      return {
        startTime: start.time,
        endTime: normalizedEnd.time,
      };
    }
  }

  return {
    startTime: start.time,
    endTime: end.time,
  };
};

const parseSingleTime = (message) => {
  const match = message.match(
    /(凌晨|上午|中午|下午|晚上)\s*\d{1,2}(?:(?::|点)\d{1,2})?(半)?|\d{1,2}:\d{1,2}|\d{1,2}点(?:\d{1,2}分?)?(半)?/,
  );
  if (!match) return '';

  const timeInfo = extractTimeParts(match[0]);
  return timeInfo?.time || '';
};

const parseAttendeeCount = (message) => {
  const match = message.match(/(\d+)\s*(?:人|位|个人)/);
  return match ? Number(match[1]) : null;
};

const parseRoomCode = (message) => {
  const match = message.match(/\b([A-Z][A-Z]?\d{2,4}|Innovation Hub)\b/i);
  return match ? match[1] : '';
};

const parseMeetingTopic = (message) => {
  const quoted = message.match(/[“"']([^“"']{2,20})[”"']/);
  if (quoted) return quoted[1];

  const topicMatch = message.match(/主题[是为]?\s*([^\s，。,；;]{2,20})/);
  return topicMatch ? topicMatch[1] : '';
};

const detectIntent = (message, previousDraft) => {
  if (/(取消|撤销|删掉|不要了)/.test(message) && /(预约|预订|会议|记录)?/.test(message)) {
    return 'cancel_reservation';
  }

  if (/(订|预订|预定|预约|找|推荐|查询|看看).*(会议室)?/.test(message) || /会议室/.test(message)) {
    return 'book_room';
  }

  return previousDraft.intent || 'book_room';
};

export function mergeAssistantDraft(previousDraft = createEmptyAssistantDraft(), nextDraft = {}) {
  const merged = {
    ...createEmptyAssistantDraft(),
    ...previousDraft,
    ...nextDraft,
  };

  merged.equipment = uniqueList([...(previousDraft.equipment || []), ...(nextDraft.equipment || [])]);
  return merged;
}

export function parseBookingAssistantMessage(message, previousDraft = createEmptyAssistantDraft()) {
  const normalizedMessage = String(message || '').trim();
  const intent = detectIntent(normalizedMessage, previousDraft);
  const extracted = createEmptyAssistantDraft();
  const assumptions = [];

  extracted.intent = intent;
  extracted.date = parseDate(normalizedMessage);

  const range = parseTimeRange(normalizedMessage);
  if (range) {
    extracted.startTime = range.startTime;
    extracted.endTime = range.endTime;
  } else {
    extracted.startTime = parseSingleTime(normalizedMessage);
  }

  extracted.attendeeCount = parseAttendeeCount(normalizedMessage);
  extracted.durationHours = parseDurationHours(normalizedMessage);
  extracted.roomCode = parseRoomCode(normalizedMessage);
  extracted.meetingTopic = parseMeetingTopic(normalizedMessage);
  extracted.equipment = EQUIPMENT_KEYWORDS
    .filter((item) => item.patterns.some((pattern) => normalizedMessage.includes(pattern)))
    .map((item) => item.label);

  if (!extracted.endTime && extracted.startTime && extracted.durationHours) {
    extracted.endTime = dayjs(`2026-01-01 ${extracted.startTime}`).add(extracted.durationHours, 'hour').format('HH:mm');
    assumptions.push(`根据“${extracted.durationHours}小时”自动补全了结束时间`);
  }

  return {
    intent,
    extracted,
    assumptions,
  };
}
