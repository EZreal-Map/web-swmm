<template>
  <div ref="messagesRef" class="messages-container">
    <MessageItem v-for="message in messages" :key="message.id" :message="message" />
    <div v-if="isLoading" class="typing-indicator">
      <div class="typing-dots">
        <span></span>
        <span></span>
        <span></span>
      </div>
      <span class="typing-text">{{ agentStore.stepMessage }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, watch } from 'vue'
import MessageItem from '@/components/agent/MessageItem.vue'
import { useAgentStore } from '@/stores/agent'

const agentStore = useAgentStore()

// 使用更严格的 props 定义 - 单向数据流
const props = defineProps({
  messages: {
    type: Array,
    default: () => [],
    validator: (value) => Array.isArray(value),
  },
  isLoading: {
    type: Boolean,
    default: false,
  },
  autoScroll: {
    type: Boolean,
    default: true,
  },
})

const messagesRef = ref(null)

// 滚动到底部
function scrollToBottom(forceSend = false) {
  if (props.autoScroll && messagesRef.value) {
    nextTick(() => {
      const el = messagesRef.value
      // 距离底部的距离
      const distanceToBottom = el.scrollHeight - el.scrollTop - el.clientHeight
      if (forceSend || distanceToBottom < 300) {
        el.scrollTop = el.scrollHeight
      }
    })
  }
}

defineExpose({ scrollToBottom })

// 监听最后一条消息变化自动滚动
watch(
  () => props.messages.at(-1)?.text,
  () => {
    scrollToBottom()
  },
  { flush: 'post' },
)
// 监听加载状态
watch(
  () => props.isLoading,
  () => {
    scrollToBottom()
  },
  { flush: 'post' },
)
</script>

<style scoped>
.messages-container {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
  min-height: 0;
}

/* 滚动条样式 */
.messages-container::-webkit-scrollbar {
  width: 6px;
}

.messages-container::-webkit-scrollbar-track {
  background: transparent;
}

.messages-container::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.1);
  border-radius: 3px;
}

.messages-container::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.2);
}

/* 输入指示器 */
.typing-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  margin-bottom: 8px;
  background: #fff;
  border-radius: 16px;
  border-bottom-left-radius: 6px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  max-width: 75%;
  align-self: flex-start;
  animation: fadeIn 0.3s;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.typing-dots {
  display: flex;
  gap: 4px;
}

.typing-dots span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #94a3b8;
  animation: typingAnimation 1.4s infinite ease-in-out;
}

.typing-dots span:nth-child(1) {
  animation-delay: -0.32s;
}

.typing-dots span:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes typingAnimation {
  0%,
  80%,
  100% {
    transform: scale(0.8);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

.typing-text {
  font-size: 13px;
  color: #64748b;
}

/* 空状态 */
.messages-container:empty::before {
  content: '开始与 AI 对话吧 👋';
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #94a3b8;
  font-size: 14px;
  text-align: center;
}
</style>
