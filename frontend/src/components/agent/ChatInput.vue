<template>
  <div class="chat-input-container">
    <div class="input-actions">
      <div class="input-row">
        <textarea
          ref="textareaRef"
          v-model="inputText"
          :placeholder="placeholder"
          :disabled="disabled"
          @keydown="handleKeydown"
          @input="adjustHeight"
          rows="1"
          class="chat-input"
        >
        </textarea>
        <button @click="handleSend" :disabled="disabled || !inputText.trim()" class="send-btn">
          <svg viewBox="0 0 24 24" width="16" height="16">
            <path fill="currentColor" d="M2,21L23,12L2,3V10L17,12L2,14V21Z" />
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'

// 使用 Vue 3.4+ 的 defineModel 语法糖
const inputText = defineModel({ type: String, default: '' })

const props = defineProps({
  placeholder: {
    type: String,
    default: '请输入您的问题...',
  },
  disabled: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['send'])

const textareaRef = ref(null)

// 自适应高度
function adjustHeight() {
  nextTick(() => {
    const textarea = textareaRef.value
    if (textarea) {
      textarea.style.height = 'auto'
      const maxHeight = 120
      const scrollHeight = textarea.scrollHeight
      textarea.style.height = Math.min(scrollHeight, maxHeight) + 'px'
      // 超过最大高度时显示滚动条，否则隐藏
      if (scrollHeight > maxHeight) {
        textarea.style.overflowY = 'auto'
      } else {
        textarea.style.overflowY = 'hidden'
      }
    }
  })
}

// 键盘事件
function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

// 发送消息
function handleSend() {
  const message = inputText.value.trim()
  if (message && !props.disabled) {
    emit('send', message)
    inputText.value = ''
    nextTick(() => {
      adjustHeight()
    })
  }
}

// 初始化高度
nextTick(() => {
  adjustHeight()
})
</script>

<style scoped>
.chat-input-container {
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  padding: 12px;
  background: #fff;
}

.input-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.input-row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}

.chat-input {
  flex: 1;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 14px;
  line-height: 20px;
  resize: none;
  outline: none;
  transition: border-color 0.2s;
  height: 36px;
  max-height: 120px;
  font-family: inherit;
  box-sizing: border-box;
  overflow-y: auto;
}

.chat-input:focus {
  border-color: #667eea;
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.1);
}

.chat-input:disabled {
  background-color: #f8f9fa;
  cursor: not-allowed;
  opacity: 0.7;
}

.chat-input::placeholder {
  color: #94a3b8;
}

.send-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 6px;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.send-btn:disabled {
  background: #e2e8f0;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.send-btn:active:not(:disabled) {
  transform: translateY(0);
}

.send-btn svg {
  transition: transform 0.2s;
}

.send-btn:hover:not(:disabled) svg {
  transform: scale(1.1);
}
</style>
