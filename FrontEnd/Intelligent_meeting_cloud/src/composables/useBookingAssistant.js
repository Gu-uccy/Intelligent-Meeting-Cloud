import { computed, ref } from 'vue';
import {
  confirmAssistantCancellation,
  confirmAssistantReservation,
  sendReservationAgentMessage,
} from '@/apis/assistant';
import { createEmptyAssistantDraft } from '@/utils/bookingAgentParser';
import { toast } from '@/utils/message';

const QUICK_PROMPTS = [
  '帮我订明天下午 3 点 8 人的会议室',
  '推荐一个明天上午 10 点 6 人带投影仪的会议室',
  '帮我取消明天下午的预约',
];

const createMessage = (payload) => ({
  id: `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
  createdAt: Date.now(),
  ...payload,
});

const createWelcomeResponse = () => ({
  intent: 'book_room',
  stage: 'welcome',
  reply: '我是会议室预订智能助理。你可以直接告诉我时间、人数和设备要求，我会先理解需求，再帮你查询、预约或取消。',
  extracted: createEmptyAssistantDraft(),
  missingFields: [],
  roomOptions: [],
  reservationOptions: [],
  assumptions: [],
  toolCalls: [],
  pendingAction: null,
  sessionState: {
    draft: createEmptyAssistantDraft(),
    lastIntent: '',
    llmMessages: [],
  },
});

export function useBookingAssistant() {
  const input = ref('');
  const isSending = ref(false);
  const sessionState = ref({
    draft: createEmptyAssistantDraft(),
    lastIntent: '',
    llmMessages: [],
  });
  const messages = ref([
    createMessage({
      role: 'assistant',
      response: createWelcomeResponse(),
    }),
  ]);

  const draft = computed(() => sessionState.value.draft || createEmptyAssistantDraft());
  const missingFields = computed(() => {
    const currentMessage = [...messages.value].reverse().find((item) => item.role === 'assistant' && item.response);
    return currentMessage?.response?.missingFields || [];
  });

  const appendAssistantResponse = (response) => {
    sessionState.value = response.sessionState || sessionState.value;
    messages.value.push(
      createMessage({
        role: 'assistant',
        response,
      }),
    );
  };

  const sendMessage = async (value) => {
    const messageText = String(value || input.value || '').trim();
    if (!messageText || isSending.value) return;

    messages.value.push(
      createMessage({
        role: 'user',
        text: messageText,
      }),
    );

    input.value = '';
    isSending.value = true;

    try {
      const response = await sendReservationAgentMessage({
        message: messageText,
        sessionState: sessionState.value,
      });
      appendAssistantResponse(response);
    } catch (error) {
      toast.error('智能助理暂时不可用，请稍后再试');
      messages.value.push(
        createMessage({
          role: 'assistant',
          response: {
            ...createWelcomeResponse(),
            stage: 'error',
            reply: '刚才处理失败了，不过你可以再发一次，我会继续接着当前上下文理解。',
            sessionState: sessionState.value,
          },
        }),
      );
    } finally {
      isSending.value = false;
    }
  };

  const confirmRoom = async (roomOption) => {
    if (isSending.value) return;
    isSending.value = true;

    try {
      const response = await confirmAssistantReservation({
        roomOption,
        sessionState: sessionState.value,
      });
      appendAssistantResponse(response);
      if (response.stage === 'submitted') {
        toast.success('预约申请已提交');
      }
    } catch (error) {
      toast.error('预约失败，请稍后重试');
    } finally {
      isSending.value = false;
    }
  };

  const confirmCancellation = async (reservationOption) => {
    if (isSending.value) return;
    isSending.value = true;

    try {
      const response = await confirmAssistantCancellation({
        reservationOption,
        sessionState: sessionState.value,
      });
      appendAssistantResponse(response);
      if (response.stage === 'success') {
        toast.success('预约已取消');
      }
    } catch (error) {
      toast.error('取消失败，请稍后重试');
    } finally {
      isSending.value = false;
    }
  };

  const resetConversation = () => {
    sessionState.value = {
      draft: createEmptyAssistantDraft(),
      lastIntent: '',
      llmMessages: [],
    };
    messages.value = [
      createMessage({
        role: 'assistant',
        response: createWelcomeResponse(),
      }),
    ];
  };

  return {
    draft,
    input,
    isSending,
    messages,
    missingFields,
    quickPrompts: QUICK_PROMPTS,
    sendMessage,
    confirmRoom,
    confirmCancellation,
    resetConversation,
  };
}
