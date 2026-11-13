import dayjs from 'dayjs';
import { getUserRoomPage, getTimeSlots } from '@/apis/room';
import { addReservation, cancelReservation, getMyReservations } from '@/apis/reservation';
import {
  createEmptyAssistantDraft,
  mergeAssistantDraft,
  parseBookingAssistantMessage,
} from '@/utils/bookingAgentParser';
import { findAvailableRoomsForDraft, findCancelableReservations } from '@/utils/bookingAgentMatcher';

const USE_REMOTE_AGENT = import.meta.env.VITE_AGENT_MODE === 'deepseek';
const AGENT_PROXY_BASE = import.meta.env.VITE_AGENT_API_BASE || '/agent-api';

const TOOLS = {
  getUserRoomPage,
  getTimeSlots,
};

const FIELD_LABELS = {
  date: '日期',
  startTime: '开始时间',
  attendeeCount: '人数',
};

const TOOL_DEFINITIONS = [
  {
    type: 'function',
    function: {
      name: 'query_available_rooms',
      description: '根据日期、时间、人数、设备要求筛选可申请的会议室。',
      parameters: {
        type: 'object',
        properties: {
          date: { type: 'string', description: '格式为 YYYY-MM-DD' },
          startTime: { type: 'string', description: '格式为 HH:mm' },
          endTime: { type: 'string', description: '格式为 HH:mm' },
          attendeeCount: { type: 'number', description: '参会人数' },
          equipment: {
            type: 'array',
            items: { type: 'string' },
            description: '设备要求列表',
          },
          roomCode: { type: 'string', description: '指定会议室编号，可为空' },
        },
        required: ['date', 'startTime', 'endTime', 'attendeeCount'],
      },
    },
  },
  {
    type: 'function',
    function: {
      name: 'find_my_reservations',
      description: '查询当前用户可取消的预约记录。',
      parameters: {
        type: 'object',
        properties: {
          date: { type: 'string', description: '格式为 YYYY-MM-DD，可为空' },
          startTime: { type: 'string', description: '格式为 HH:mm，可为空' },
          roomCode: { type: 'string', description: '会议室编号，可为空' },
        },
      },
    },
  },
];

const buildSessionState = (draft, lastIntent = '', llmMessages = []) => ({
  draft,
  lastIntent,
  llmMessages,
});

const createResponse = (overrides = {}) => ({
  intent: 'book_room',
  stage: 'clarify',
  reply: '',
  extracted: createEmptyAssistantDraft(),
  missingFields: [],
  roomOptions: [],
  reservationOptions: [],
  assumptions: [],
  toolCalls: [],
  pendingAction: null,
  sessionState: buildSessionState(createEmptyAssistantDraft()),
  ...overrides,
});

const normalizeEquipment = (equipment) => {
  if (Array.isArray(equipment)) return equipment.filter(Boolean);
  if (!equipment) return [];
  return String(equipment)
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
};

const normalizeExtractedDraft = (draft = {}) => ({
  ...createEmptyAssistantDraft(),
  ...draft,
  attendeeCount:
    draft.attendeeCount === null || draft.attendeeCount === undefined || draft.attendeeCount === ''
      ? null
      : Number(draft.attendeeCount),
  equipment: normalizeEquipment(draft.equipment),
});

const inferDefaultEndTime = (draft, assumptions) => {
  if (!draft.startTime || draft.endTime) return draft;
  assumptions.push('未指定结束时间，已默认按 1 小时会议处理');
  return {
    ...draft,
    endTime: dayjs(`2026-01-01 ${draft.startTime}`).add(1, 'hour').format('HH:mm'),
  };
};

const getBookingMissingFields = (draft) => {
  const requiredFields = ['date', 'startTime', 'attendeeCount'];
  return requiredFields.filter((field) => !draft[field]);
};

const formatMissingFields = (fields = []) => fields.map((field) => FIELD_LABELS[field] || field).join('、');

const buildBookingReply = (roomOptions, draft) => {
  if (!roomOptions.length) {
    return `我按 ${draft.date} ${draft.startTime}-${draft.endTime}、${draft.attendeeCount} 人的条件查过了，当前没有完全匹配的会议室。可以试试放宽设备要求，或者换个时间。`;
  }

  return `我找到了 ${roomOptions.length} 个可选会议室，你可以直接提交预约申请，之后由管理员审核。`;
};

const buildReservationTitle = (draft) => {
  if (draft.meetingTopic) return draft.meetingTopic;
  return `AI助理预约 ${dayjs(draft.date).format('MM-DD')} ${draft.startTime}`;
};

const normalizeDraft = (sessionState, message) => {
  const previousDraft = sessionState?.draft || createEmptyAssistantDraft();
  const parseResult = parseBookingAssistantMessage(message, previousDraft);
  const mergedDraft = mergeAssistantDraft(previousDraft, parseResult.extracted);

  return {
    intent: parseResult.intent,
    draft: mergedDraft,
    assumptions: [...parseResult.assumptions],
  };
};

const callAgentProxy = async ({ messages, tools }) => {
  const response = await fetch(`${AGENT_PROXY_BASE}/chat/completions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      messages,
      tools,
      temperature: 0.2,
      tool_choice: 'auto',
      max_tokens: 1400,
    }),
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok || data?.error?.message) {
    throw new Error(data?.error?.message || 'Agent proxy request failed.');
  }

  return data;
};

const safeParseJson = (content) => {
  if (!content) return {};

  const normalizedContent = String(content)
    .trim()
    .replace(/^```json\s*/i, '')
    .replace(/^```\s*/i, '')
    .replace(/\s*```$/, '');

  try {
    return JSON.parse(normalizedContent);
  } catch (error) {
    return {
      reply: normalizedContent,
    };
  }
};

const buildSystemPrompt = () => {
  const today = dayjs().format('YYYY-MM-DD');

  return `
你是“会议室预订智能助理”。
今天日期是 ${today}。

目标：
1. 理解用户是想预约会议室还是取消预约。
2. 信息不完整时追问补全。
3. 需要查询数据时，优先调用工具，不要自己编造会议室结果。
4. 用户确认前，不要主动创建或取消预约。
5. 所有最终回答都必须只返回 JSON，不要加 Markdown。

业务规则：
- 预约必须至少明确日期、开始时间、人数。
- 如果用户未提供结束时间，但提供了开始时间，默认按 1 小时处理。
- 预约申请提交后，需要等待管理员审核通过后才算预约成功。
- 取消预约时，如果命中多条记录，需要返回候选列表让用户选择。

最终返回 JSON 结构：
{
  "intent": "book_room | cancel_reservation",
  "stage": "clarify | recommend | submitted | success | error",
  "reply": "给用户看的中文回复",
  "extracted": {
    "intent": "",
    "date": "",
    "startTime": "",
    "endTime": "",
    "attendeeCount": null,
    "equipment": [],
    "durationHours": null,
    "roomCode": "",
    "meetingTopic": ""
  },
  "missingFields": [],
  "roomOptions": [],
  "reservationOptions": [],
  "assumptions": [],
  "pendingAction": null
}

调用工具后，请基于工具结果把 roomOptions 或 reservationOptions 原样放进最终 JSON。
`.trim();
};

const createInitialLlmMessages = (draft) => [
  {
    role: 'system',
    content: buildSystemPrompt(),
  },
  {
    role: 'system',
    content: `当前已知会话草稿：${JSON.stringify(normalizeExtractedDraft(draft))}`,
  },
];

const executeRemoteTool = async ({ toolName, argumentsObject, currentDraft }) => {
  if (toolName === 'query_available_rooms') {
    const nextDraft = inferDefaultEndTime(
      mergeAssistantDraft(currentDraft, normalizeExtractedDraft(argumentsObject)),
      [],
    );

    const roomOptions = await findAvailableRoomsForDraft(nextDraft, TOOLS);

    return {
      tool: toolName,
      draft: nextDraft,
      roomOptions,
    };
  }

  if (toolName === 'find_my_reservations') {
    const nextDraft = mergeAssistantDraft(currentDraft, normalizeExtractedDraft(argumentsObject));
    const reservationResponse = await getMyReservations();
    const reservationOptions = findCancelableReservations(nextDraft, reservationResponse?.data || []);

    return {
      tool: toolName,
      draft: nextDraft,
      reservationOptions,
    };
  }

  return {
    tool: toolName,
    error: `Unsupported tool: ${toolName}`,
  };
};

const normalizeModelResponse = ({ content, previousDraft, toolTrace, llmMessages }) => {
  const parsed = safeParseJson(content);
  const mergedDraft = mergeAssistantDraft(previousDraft, normalizeExtractedDraft(parsed.extracted || {}));

  return createResponse({
    intent: parsed.intent || mergedDraft.intent || 'book_room',
    stage: parsed.stage || 'clarify',
    reply: parsed.reply || '我已经处理完成这一步了。',
    extracted: mergedDraft,
    missingFields: Array.isArray(parsed.missingFields) ? parsed.missingFields : [],
    roomOptions: Array.isArray(parsed.roomOptions) ? parsed.roomOptions : [],
    reservationOptions: Array.isArray(parsed.reservationOptions) ? parsed.reservationOptions : [],
    assumptions: Array.isArray(parsed.assumptions) ? parsed.assumptions : [],
    toolCalls: toolTrace,
    pendingAction: parsed.pendingAction || null,
    sessionState: buildSessionState(mergedDraft, parsed.intent || mergedDraft.intent || '', llmMessages),
  });
};

async function sendReservationAgentMessageLocal({ message, sessionState }) {
  const toolCalls = [{ tool: 'parse_message', status: 'success' }];
  const { intent, draft: mergedDraft, assumptions } = normalizeDraft(sessionState, message);

  if (intent === 'cancel_reservation') {
    toolCalls.push({ tool: 'get_my_reservations', status: 'running' });
    const reservationResponse = await getMyReservations();
    const reservationOptions = findCancelableReservations(mergedDraft, reservationResponse?.data || []);
    toolCalls[1].status = 'success';

    if (!reservationOptions.length) {
      return createResponse({
        intent,
        stage: 'error',
        reply: '我没有找到可以取消的预约记录，你可以先去“我的预约”里确认一下。',
        extracted: mergedDraft,
        assumptions,
        toolCalls,
        sessionState: buildSessionState(mergedDraft, intent),
      });
    }

    return createResponse({
      intent,
      stage: 'recommend',
      reply: reservationOptions.length === 1 ? '我帮你定位到 1 条预约，确认后就能取消。' : '我筛到了几条可能要取消的预约，选中后我就帮你处理。',
      extracted: mergedDraft,
      reservationOptions,
      assumptions,
      toolCalls,
      pendingAction: {
        type: 'cancel_reservation',
      },
      sessionState: buildSessionState(mergedDraft, intent),
    });
  }

  const draftWithEndTime = inferDefaultEndTime(mergedDraft, assumptions);
  const missingFields = getBookingMissingFields(draftWithEndTime);

  if (missingFields.length) {
    return createResponse({
      intent,
      stage: 'clarify',
      reply: `我已经理解到你是在找会议室，但还缺少 ${formatMissingFields(missingFields)}，补充后我就能继续推荐。`,
      extracted: draftWithEndTime,
      missingFields,
      assumptions,
      toolCalls,
      sessionState: buildSessionState(draftWithEndTime, intent),
    });
  }

  toolCalls.push({ tool: 'query_room_candidates', status: 'running' });
  const roomOptions = await findAvailableRoomsForDraft(draftWithEndTime, TOOLS);
  toolCalls[1].status = 'success';
  toolCalls.push({ tool: 'rank_recommendations', status: 'success' });

  return createResponse({
    intent,
    stage: 'recommend',
    reply: buildBookingReply(roomOptions, draftWithEndTime),
    extracted: draftWithEndTime,
    assumptions,
    roomOptions,
    toolCalls,
    pendingAction: {
      type: 'book_room',
    },
    sessionState: buildSessionState(draftWithEndTime, intent),
  });
}

async function sendReservationAgentMessageRemote({ message, sessionState }) {
  const previousDraft = normalizeExtractedDraft(sessionState?.draft || createEmptyAssistantDraft());
  const llmMessages =
    Array.isArray(sessionState?.llmMessages) && sessionState.llmMessages.length
      ? [...sessionState.llmMessages]
      : createInitialLlmMessages(previousDraft);

  llmMessages.push({
    role: 'user',
    content: JSON.stringify(
      {
        userMessage: message,
        currentDraft: previousDraft,
      },
      null,
      2,
    ),
  });

  const toolTrace = [{ tool: 'deepseek_function_calling', status: 'success' }];
  let currentDraft = previousDraft;

  for (let index = 0; index < 4; index += 1) {
    const completion = await callAgentProxy({
      messages: llmMessages,
      tools: TOOL_DEFINITIONS,
    });

    const assistantMessage = completion?.choices?.[0]?.message;
    if (!assistantMessage) {
      throw new Error('DeepSeek did not return a valid message.');
    }

    if (assistantMessage.tool_calls?.length) {
      llmMessages.push({
        role: 'assistant',
        content: assistantMessage.content || '',
        tool_calls: assistantMessage.tool_calls,
      });

      for (const toolCall of assistantMessage.tool_calls) {
        const toolName = toolCall.function?.name;
        const argumentsObject = safeParseJson(toolCall.function?.arguments || '{}');
        const toolResult = await executeRemoteTool({
          toolName,
          argumentsObject,
          currentDraft,
        });

        currentDraft = mergeAssistantDraft(currentDraft, normalizeExtractedDraft(toolResult.draft || {}));
        toolTrace.push({ tool: toolName, status: toolResult.error ? 'failed' : 'success' });

        llmMessages.push({
          role: 'tool',
          tool_call_id: toolCall.id,
          content: JSON.stringify(toolResult),
        });
      }

      continue;
    }

    llmMessages.push({
      role: 'assistant',
      content: assistantMessage.content || '',
    });

    return normalizeModelResponse({
      content: assistantMessage.content,
      previousDraft: currentDraft,
      toolTrace,
      llmMessages,
    });
  }

  return createResponse({
    intent: currentDraft.intent || 'book_room',
    stage: 'error',
    reply: '模型进行了太多轮工具调用，我先停在这里。你可以换一种说法再试一次。',
    extracted: currentDraft,
    toolCalls: toolTrace,
    sessionState: buildSessionState(currentDraft, currentDraft.intent || '', llmMessages),
  });
}

export async function sendReservationAgentMessage({ message, sessionState }) {
  if (USE_REMOTE_AGENT) {
    return sendReservationAgentMessageRemote({ message, sessionState });
  }

  return sendReservationAgentMessageLocal({ message, sessionState });
}

export async function confirmAssistantReservation({ roomOption, sessionState }) {
  const draft = sessionState?.draft || createEmptyAssistantDraft();
  const bookingDate = draft.date || roomOption.date;
  const bookingStartTime = draft.startTime || roomOption.startTime;
  const bookingEndTime = draft.endTime || roomOption.endTime;
  const attendeeCount = Number(draft.attendeeCount || roomOption.capacity || 1);
  const equipmentText = draft.equipment?.length ? draft.equipment.join('、') : '';
  const payload = {
    roomId: roomOption.roomId,
    meetingTopic: buildReservationTitle({
      ...draft,
      date: bookingDate,
      startTime: bookingStartTime,
    }),
    startTime: `${bookingDate} ${bookingStartTime}:00`,
    endTime: `${bookingDate} ${bookingEndTime}:00`,
    participantNum: attendeeCount,
    remark: equipmentText ? `设备要求：${equipmentText}` : '来自 AI 助理预约',
  };

  const reservationResponse = await addReservation(payload);

  if (reservationResponse?.code === 0) {
    return createResponse({
      intent: 'book_room',
      stage: 'error',
      reply: reservationResponse.msg || '预约失败了，请换一个会议室再试一次。',
      extracted: draft,
      toolCalls: [{ tool: 'create_reservation', status: 'failed' }],
      sessionState: buildSessionState(draft, 'book_room', sessionState?.llmMessages || []),
    });
  }

  return createResponse({
    intent: 'book_room',
    stage: 'submitted',
    reply: `已帮你提交 ${roomOption.roomCode} 的预约申请，时间是 ${bookingDate} ${bookingStartTime}-${bookingEndTime}，需要等待管理员审核通过后才算预约成功。`,
    extracted: createEmptyAssistantDraft(),
    assumptions: [],
    toolCalls: [{ tool: 'create_reservation', status: 'success' }],
    pendingAction: null,
    sessionState: buildSessionState(createEmptyAssistantDraft(), '', []),
  });
}

export async function confirmAssistantCancellation({ reservationOption, sessionState }) {
  const draft = sessionState?.draft || createEmptyAssistantDraft();
  const cancelResponse = await cancelReservation(reservationOption.reservationId);

  if (cancelResponse?.code === 0) {
    return createResponse({
      intent: 'cancel_reservation',
      stage: 'error',
      reply: cancelResponse.msg || '取消失败了，请稍后再试。',
      extracted: draft,
      toolCalls: [{ tool: 'cancel_reservation', status: 'failed' }],
      sessionState: buildSessionState(draft, 'cancel_reservation', sessionState?.llmMessages || []),
    });
  }

  return createResponse({
    intent: 'cancel_reservation',
    stage: 'success',
    reply: `已取消 ${reservationOption.date} ${reservationOption.time} 的预约。`,
    extracted: createEmptyAssistantDraft(),
    assumptions: [],
    toolCalls: [{ tool: 'cancel_reservation', status: 'success' }],
    sessionState: buildSessionState(createEmptyAssistantDraft(), '', []),
  });
}
