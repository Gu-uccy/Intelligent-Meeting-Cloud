<script setup>
import { nextTick, ref, watch } from 'vue';
import { useBookingAssistant } from '@/composables/useBookingAssistant';

const {
  draft,
  input,
  isSending,
  messages,
  missingFields,
  quickPrompts,
  sendMessage,
  confirmRoom,
  confirmCancellation,
  resetConversation,
} = useBookingAssistant();

const chatBodyRef = ref(null);

const fieldMap = {
  book_room: '预约会议室',
  cancel_reservation: '取消预约',
  welcome: '待命中',
};

const stageMap = {
  welcome: '待命中',
  clarify: '待补充',
  recommend: '已推荐',
  submitted: '待审核',
  success: '已完成',
  error: '处理失败',
};

const missingFieldMap = {
  date: '日期',
  startTime: '开始时间',
  attendeeCount: '人数',
};

const scrollToBottom = async () => {
  await nextTick();
  if (!chatBodyRef.value) return;
  chatBodyRef.value.scrollTop = chatBodyRef.value.scrollHeight;
};

watch(
  () => messages.value.length,
  () => {
    scrollToBottom();
  },
  { immediate: true },
);

const handleSend = () => {
  sendMessage();
};

const handleQuickPrompt = (prompt) => {
  sendMessage(prompt);
};

const getIntentLabel = (intent) => fieldMap[intent] || '处理中';
const getStageLabel = (stage) => stageMap[stage] || stage;
const getMissingFieldLabel = (field) => missingFieldMap[field] || field;
</script>

<template>
  <div class="assistant-layout">
    <section class="assistant-chat">
      <div class="assistant-header">
        <div>
          <p class="eyebrow">AI Agent MVP</p>
          <h2>会议室预订智能助理</h2>
          <p class="sub-text">支持自然语言理解、工具调用、结果确认和取消预约。</p>
        </div>
        <button class="ghost-btn" @click="resetConversation">重置对话</button>
      </div>

      <div class="quick-prompt-row">
        <button
          v-for="prompt in quickPrompts"
          :key="prompt"
          class="quick-prompt"
          @click="handleQuickPrompt(prompt)"
        >
          {{ prompt }}
        </button>
      </div>

      <div ref="chatBodyRef" class="chat-body custom-scrollbar">
        <div
          v-for="message in messages"
          :key="message.id"
          class="message-row"
          :class="message.role === 'user' ? 'is-user' : 'is-assistant'"
        >
          <div class="avatar-chip">
            {{ message.role === 'user' ? '我' : 'AI' }}
          </div>

          <div class="bubble">
            <template v-if="message.role === 'user'">
              <p>{{ message.text }}</p>
            </template>

            <template v-else>
              <div class="bubble-head">
                <span class="status-tag">{{ getIntentLabel(message.response.intent) }}</span>
                <span class="stage-tag">{{ getStageLabel(message.response.stage) }}</span>
              </div>
              <p>{{ message.response.reply }}</p>

              <div v-if="message.response.assumptions?.length" class="assumption-box">
                <span v-for="item in message.response.assumptions" :key="item" class="assumption-chip">
                  {{ item }}
                </span>
              </div>

              <div v-if="message.response.roomOptions?.length" class="card-list">
                <article v-for="room in message.response.roomOptions" :key="room.roomId" class="result-card">
                  <div class="result-card-top">
                    <div>
                      <h3>{{ room.roomCode }}</h3>
                      <p>{{ room.location }}</p>
                    </div>
                    <span class="capacity-badge">{{ room.capacity }} 人</span>
                  </div>
                  <div class="meta-row">
                    <span>{{ room.date }}</span>
                    <span>{{ room.startTime }} - {{ room.endTime }}</span>
                  </div>
                  <div class="chip-row">
                    <span v-for="item in room.equipment" :key="item" class="mini-chip">{{ item }}</span>
                  </div>
                  <div class="chip-row">
                    <span v-for="reason in room.matchReasons" :key="reason" class="mini-chip reason-chip">
                      {{ reason }}
                    </span>
                  </div>
                  <button class="primary-btn" :disabled="isSending" @click="confirmRoom(room)">
                    提交预约申请
                  </button>
                </article>
              </div>

              <div v-if="message.response.reservationOptions?.length" class="card-list">
                <article
                  v-for="reservation in message.response.reservationOptions"
                  :key="reservation.reservationId"
                  class="result-card danger-card"
                >
                  <div class="result-card-top">
                    <div>
                      <h3>{{ reservation.title }}</h3>
                      <p>{{ reservation.room }}</p>
                    </div>
                    <span class="capacity-badge danger-badge">待取消</span>
                  </div>
                  <div class="meta-row">
                    <span>{{ reservation.date }}</span>
                    <span>{{ reservation.time }}</span>
                  </div>
                  <button class="danger-btn" :disabled="isSending" @click="confirmCancellation(reservation)">
                    确认取消
                  </button>
                </article>
              </div>

              <div v-if="message.response.toolCalls?.length" class="tool-row">
                <span v-for="toolCall in message.response.toolCalls" :key="`${toolCall.tool}-${toolCall.status}`" class="tool-chip">
                  {{ toolCall.tool }} · {{ toolCall.status }}
                </span>
              </div>
            </template>
          </div>
        </div>
      </div>

      <div class="composer">
        <textarea
          v-model="input"
          class="composer-input"
          rows="3"
          placeholder="例如：帮我订明天下午 3 点 8 人的会议室，需要投影仪"
          @keydown.enter.exact.prevent="handleSend"
        />
        <div class="composer-footer">
          <span class="hint-text">按 Enter 发送，Shift + Enter 换行</span>
          <button class="primary-btn" :disabled="isSending || !input.trim()" @click="handleSend">
            {{ isSending ? '处理中...' : '发送给助理' }}
          </button>
        </div>
      </div>
    </section>

    <aside class="assistant-panel">
      <div class="panel-card">
        <div class="panel-title-row">
          <h3>当前理解结果</h3>
          <span class="panel-dot"></span>
        </div>
        <div class="summary-grid">
          <div class="summary-item">
            <span>意图</span>
            <strong>{{ getIntentLabel(draft.intent || 'welcome') }}</strong>
          </div>
          <div class="summary-item">
            <span>日期</span>
            <strong>{{ draft.date || '待补充' }}</strong>
          </div>
          <div class="summary-item">
            <span>开始时间</span>
            <strong>{{ draft.startTime || '待补充' }}</strong>
          </div>
          <div class="summary-item">
            <span>结束时间</span>
            <strong>{{ draft.endTime || '待补充' }}</strong>
          </div>
          <div class="summary-item">
            <span>人数</span>
            <strong>{{ draft.attendeeCount || '待补充' }}</strong>
          </div>
          <div class="summary-item">
            <span>房间编号</span>
            <strong>{{ draft.roomCode || '不限' }}</strong>
          </div>
        </div>
      </div>

      <div class="panel-card">
        <h3>设备要求</h3>
        <div class="chip-row">
          <span v-if="!draft.equipment?.length" class="mini-chip empty-chip">暂无要求</span>
          <span v-for="item in draft.equipment" :key="item" class="mini-chip">{{ item }}</span>
        </div>
      </div>

      <div class="panel-card">
        <h3>待补充字段</h3>
        <div class="chip-row">
          <span v-if="!missingFields.length" class="mini-chip success-chip">信息完整</span>
          <span v-for="field in missingFields" :key="field" class="mini-chip warn-chip">{{ getMissingFieldLabel(field) }}</span>
        </div>
      </div>

      <div class="panel-card">
        <h3>展示亮点</h3>
        <ul class="value-list">
          <li>结构化 JSON 返回，便于前端渲染</li>
          <li>对话中间层负责工具编排和状态管理</li>
          <li>结果卡片支持一键提交预约申请和取消</li>
        </ul>
      </div>
    </aside>
  </div>
</template>

<style scoped>
.assistant-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.7fr) minmax(280px, 0.9fr);
  gap: 1.5rem;
  min-height: 100%;
}

.assistant-chat,
.assistant-panel {
  min-width: 0;
}

.assistant-chat {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.assistant-header,
.panel-card,
.composer,
.chat-body,
.quick-prompt {
  background: rgba(15, 23, 42, 0.55);
  border: 1px solid rgba(148, 163, 184, 0.14);
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.18);
  backdrop-filter: blur(14px);
}

.assistant-header,
.panel-card,
.composer {
  border-radius: 20px;
}

.assistant-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  padding: 1.3rem 1.4rem;
}

.eyebrow {
  margin: 0 0 0.4rem;
  font-size: 0.78rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #7dd3a7;
}

.assistant-header h2,
.panel-card h3 {
  margin: 0;
  color: #f8fafc;
}

.sub-text {
  margin: 0.55rem 0 0;
  color: #94a3b8;
  line-height: 1.6;
}

.ghost-btn,
.quick-prompt,
.primary-btn,
.danger-btn {
  border-radius: 14px;
  font-weight: 600;
  transition: all 0.2s ease;
  cursor: pointer;
}

.ghost-btn {
  border: 1px solid rgba(125, 211, 167, 0.35);
  background: rgba(32, 174, 124, 0.08);
  color: #bbf7d0;
  padding: 0.75rem 1rem;
}

.ghost-btn:hover {
  border-color: rgba(125, 211, 167, 0.7);
  background: rgba(32, 174, 124, 0.14);
}

.quick-prompt-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.quick-prompt {
  border: none;
  color: #e2e8f0;
  padding: 0.85rem 1rem;
}

.quick-prompt:hover {
  transform: translateY(-2px);
}

.chat-body {
  border-radius: 24px;
  padding: 1.25rem;
  min-height: 520px;
  max-height: 62vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.message-row {
  display: flex;
  gap: 0.85rem;
  align-items: flex-start;
}

.message-row.is-user {
  flex-direction: row-reverse;
}

.avatar-chip {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #20ae7c, #0f766e);
  color: white;
  font-size: 0.85rem;
  font-weight: 700;
  flex-shrink: 0;
}

.message-row.is-user .avatar-chip {
  background: linear-gradient(135deg, #334155, #1e293b);
}

.bubble {
  max-width: min(760px, 100%);
  padding: 1rem 1.1rem;
  border-radius: 18px;
  background: rgba(30, 41, 59, 0.8);
  border: 1px solid rgba(148, 163, 184, 0.16);
}

.message-row.is-user .bubble {
  background: rgba(32, 174, 124, 0.15);
}

.bubble p {
  margin: 0;
  color: #e2e8f0;
  line-height: 1.7;
}

.bubble-head,
.tool-row,
.chip-row,
.composer-footer,
.result-card-top,
.meta-row,
.panel-title-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.6rem;
}

.bubble-head {
  margin-bottom: 0.75rem;
}

.status-tag,
.stage-tag,
.tool-chip,
.mini-chip,
.capacity-badge {
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
}

.status-tag {
  padding: 0.3rem 0.7rem;
  background: rgba(32, 174, 124, 0.14);
  color: #86efac;
}

.stage-tag {
  padding: 0.3rem 0.7rem;
  background: rgba(59, 130, 246, 0.12);
  color: #93c5fd;
}

.assumption-box,
.tool-row {
  margin-top: 0.85rem;
}

.assumption-chip {
  margin-right: 0.45rem;
  margin-top: 0.45rem;
  border-radius: 999px;
  background: rgba(250, 204, 21, 0.12);
  color: #fde68a;
  font-size: 0.78rem;
  padding: 0.28rem 0.7rem;
}

.tool-chip,
.mini-chip,
.capacity-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.28rem 0.7rem;
}

.tool-chip {
  background: rgba(148, 163, 184, 0.12);
  color: #cbd5e1;
}

.card-list {
  display: grid;
  gap: 0.9rem;
  margin-top: 0.95rem;
}

.result-card {
  padding: 1rem;
  border-radius: 18px;
  background: rgba(15, 23, 42, 0.68);
  border: 1px solid rgba(125, 211, 167, 0.16);
}

.danger-card {
  border-color: rgba(248, 113, 113, 0.18);
}

.result-card h3 {
  margin: 0;
  color: #f8fafc;
}

.result-card p,
.meta-row span {
  color: #94a3b8;
}

.meta-row {
  justify-content: space-between;
  margin: 0.75rem 0;
}

.capacity-badge {
  background: rgba(125, 211, 167, 0.14);
  color: #bbf7d0;
}

.danger-badge {
  background: rgba(248, 113, 113, 0.14);
  color: #fecaca;
}

.mini-chip {
  background: rgba(255, 255, 255, 0.08);
  color: #e2e8f0;
}

.reason-chip {
  background: rgba(59, 130, 246, 0.12);
  color: #bfdbfe;
}

.warn-chip {
  background: rgba(250, 204, 21, 0.12);
  color: #fde68a;
}

.success-chip {
  background: rgba(32, 174, 124, 0.14);
  color: #bbf7d0;
}

.empty-chip {
  opacity: 0.75;
}

.primary-btn,
.danger-btn {
  margin-top: 0.9rem;
  width: 100%;
  padding: 0.82rem 1rem;
  border: none;
}

.primary-btn {
  background: linear-gradient(135deg, #20ae7c, #0f766e);
  color: white;
}

.primary-btn:hover:not(:disabled),
.danger-btn:hover:not(:disabled) {
  transform: translateY(-1px);
}

.danger-btn {
  background: linear-gradient(135deg, #ef4444, #b91c1c);
  color: white;
}

.primary-btn:disabled,
.danger-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.composer {
  padding: 1rem;
}

.composer-input {
  width: 100%;
  border: none;
  resize: none;
  outline: none;
  background: rgba(15, 23, 42, 0.2);
  border-radius: 16px;
  padding: 0.95rem 1rem;
  color: #f8fafc;
  line-height: 1.6;
}

.composer-footer {
  justify-content: space-between;
  margin-top: 0.85rem;
}

.hint-text {
  color: #64748b;
  font-size: 0.82rem;
}

.assistant-panel {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.panel-card {
  padding: 1.15rem 1.2rem;
}

.panel-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #34d399;
  box-shadow: 0 0 16px rgba(52, 211, 153, 0.8);
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.9rem;
  margin-top: 1rem;
}

.summary-item {
  padding: 0.9rem;
  border-radius: 16px;
  background: rgba(15, 23, 42, 0.44);
  border: 1px solid rgba(148, 163, 184, 0.1);
}

.summary-item span {
  display: block;
  color: #64748b;
  font-size: 0.82rem;
  margin-bottom: 0.4rem;
}

.summary-item strong {
  color: #f8fafc;
  font-size: 0.95rem;
}

.value-list {
  margin: 1rem 0 0;
  padding-left: 1rem;
  color: #cbd5e1;
  line-height: 1.8;
}

@media (max-width: 1120px) {
  .assistant-layout {
    grid-template-columns: 1fr;
  }

  .chat-body {
    max-height: none;
  }
}

@media (max-width: 720px) {
  .assistant-header,
  .composer-footer,
  .result-card-top,
  .meta-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .summary-grid {
    grid-template-columns: 1fr;
  }

  .quick-prompt-row {
    flex-direction: column;
  }

  .quick-prompt {
    width: 100%;
    text-align: left;
  }
}
</style>
