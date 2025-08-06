<template>
  <div v-if="showDialog" class="chat-widget" :style="widgetStyle" @mousedown="startDrag">
    <!-- Header -->
    <div class="chat-header" @mousedown.stop="startDrag">
      <div class="header-left">
        <div class="chat-avatar">🤖</div>
        <span class="chat-title">AI 聊天助手</span>
        <div class="connection-status" :class="{ connected }"></div>
      </div>
      <div class="header-actions">
        <button
          class="header-btn"
          @click.stop="toggleCollapse"
          :title="collapsed ? '展开' : '收起'"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
            <path v-if="collapsed" d="M7 14l5-5 5 5z" />
            <path v-else d="M7 10l5 5 5-5z" />
          </svg>
        </button>
        <button class="header-btn close-btn" @click.stop="closeDialog" title="关闭">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
            <path
              d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"
            />
          </svg>
        </button>
      </div>
    </div>

    <!-- Chat Body -->
    <div v-if="!collapsed" class="chat-body">
      <div class="messages" ref="messagesContainer">
        <div v-for="(msg, i) in messages" :key="i" :class="['message', msg.role]">
          <div class="message-content">{{ msg.text }}</div>
          <div class="message-time">{{ formatTime(new Date()) }}</div>
        </div>
      </div>

      <div class="input-container">
        <div class="input-box">
          <textarea
            v-model="input"
            @keydown="handleKeyDown"
            placeholder="输入消息... (Shift+Enter 换行)"
            class="message-input"
            rows="1"
            ref="inputRef"
          ></textarea>
          <button
            @click="sendMessage"
            :disabled="!connected || !input.trim()"
            class="send-btn"
            title="发送消息"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- Resize handles -->
    <div class="resize-handle bottom-right" @mousedown.stop="startResize"></div>
    <div class="resize-handle bottom" @mousedown.stop="startResizeVertical"></div>
    <div class="resize-handle right" @mousedown.stop="startResizeHorizontal"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick, computed } from 'vue'

// 父组件可传的参数

const serverUrl = 'ws://localhost:8080/agent/ws/chat/test-client'
const conversationId = 'conv-123'
const userId = 'user-123'

const showDialog = defineModel('showDialog')

function closeDialog() {
  showDialog.value = false
}

// WebSocket
const ws = ref(null)
const connected = ref(false)
let heartbeatInterval = null

function connectWS() {
  ws.value = new WebSocket(serverUrl)

  ws.value.onopen = () => {
    connected.value = true
    addMessage('system', '已连接到服务器')
    startHeartbeat()
  }

  ws.value.onmessage = (event) => {
    const data = JSON.parse(event.data)
    handleResponse(data)
  }

  ws.value.onclose = () => {
    connected.value = false
    addMessage('system', '连接已断开')
    stopHeartbeat()
  }

  ws.value.onerror = () => {
    addMessage('system', '连接出错')
  }
}

function disconnectWS() {
  if (ws.value) ws.value.close()
  stopHeartbeat()
}

function startHeartbeat() {
  stopHeartbeat()
  heartbeatInterval = setInterval(() => {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify({ type: 'ping' }))
    }
  }, 30000)
}

function stopHeartbeat() {
  if (heartbeatInterval) {
    clearInterval(heartbeatInterval)
    heartbeatInterval = null
  }
}

// 消息管理
const messages = ref([])
const input = ref('')
const messagesContainer = ref(null)
const inputRef = ref(null)

function addMessage(role, text) {
  messages.value.push({ role, text, timestamp: new Date() })
  nextTick(() => {
    const el = messagesContainer.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

function sendMessage() {
  if (!connected.value || !input.value.trim()) return
  const msg = input.value.trim()
  addMessage('user', msg)
  ws.value.send(
    JSON.stringify({
      message: msg,
      conversation_id: conversationId,
      user_id: userId,
    }),
  )
  input.value = ''
  adjustTextareaHeight()
}

function handleKeyDown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
  nextTick(() => adjustTextareaHeight())
}

function adjustTextareaHeight() {
  const textarea = inputRef.value
  if (textarea) {
    textarea.style.height = 'auto'
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px'
  }
}

function formatTime(date) {
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

function handleResponse(data) {
  if (data.type === 'start') {
    addMessage('assistant', '')
  } else if (data.type === 'chunk') {
    const last = messages.value[messages.value.length - 1]
    if (last && last.role === 'assistant') {
      last.text = data.accumulated_content || last.text + data.content
    }
  } else if (data.type === 'complete') {
    const last = messages.value[messages.value.length - 1]
    if (last && last.role === 'assistant') {
      last.text = data.message
    }
  } else if (data.message) {
    addMessage('assistant', data.message)
  }
}

// 拖拽 & 缩放
const collapsed = ref(false)
const pos = ref({ x: 210, y: 10 })
const size = ref({ width: 350, height: 500 })
let dragging = false
let dragOffset = { x: 0, y: 0 }
let resizing = false
let resizeStart = { x: 0, y: 0, w: 0, h: 0 }

const widgetStyle = computed(() => ({
  top: pos.value.y + 'px',
  left: pos.value.x + 'px',
  width: size.value.width + 'px',
  height: size.value.height + 'px',
}))

function startDrag(e) {
  dragging = true
  dragOffset = { x: e.clientX - pos.value.x, y: e.clientY - pos.value.y }
  window.addEventListener('mousemove', onDrag)
  window.addEventListener('mouseup', stopDrag)
}
function onDrag(e) {
  if (!dragging) return
  pos.value.x = e.clientX - dragOffset.x
  pos.value.y = e.clientY - dragOffset.y
}
function stopDrag() {
  dragging = false
  window.removeEventListener('mousemove', onDrag)
  window.removeEventListener('mouseup', stopDrag)
}

function startResize(e) {
  resizing = true
  resizeStart = { x: e.clientX, y: e.clientY, w: size.value.width, h: size.value.height }
  window.addEventListener('mousemove', onResize)
  window.addEventListener('mouseup', stopResize)
}

function startResizeHorizontal(e) {
  resizing = true
  resizeStart = { x: e.clientX, y: e.clientY, w: size.value.width, h: size.value.height }
  window.addEventListener('mousemove', onResizeHorizontal)
  window.addEventListener('mouseup', stopResize)
}

function startResizeVertical(e) {
  resizing = true
  resizeStart = { x: e.clientX, y: e.clientY, w: size.value.width, h: size.value.height }
  window.addEventListener('mousemove', onResizeVertical)
  window.addEventListener('mouseup', stopResize)
}

function onResize(e) {
  if (!resizing) return
  const newWidth = Math.max(
    280,
    Math.min(window.innerWidth * 0.9, resizeStart.w + (e.clientX - resizeStart.x)),
  )
  const newHeight = Math.max(
    350,
    Math.min(window.innerHeight * 0.8, resizeStart.h + (e.clientY - resizeStart.y)),
  )
  size.value.width = newWidth
  size.value.height = newHeight
}

function onResizeHorizontal(e) {
  if (!resizing) return
  const newWidth = Math.max(
    280,
    Math.min(window.innerWidth * 0.9, resizeStart.w + (e.clientX - resizeStart.x)),
  )
  size.value.width = newWidth
}

function onResizeVertical(e) {
  if (!resizing) return
  const newHeight = Math.max(
    350,
    Math.min(window.innerHeight * 0.8, resizeStart.h + (e.clientY - resizeStart.y)),
  )
  size.value.height = newHeight
}

function stopResize() {
  resizing = false
  window.removeEventListener('mousemove', onResize)
  window.removeEventListener('mousemove', onResizeHorizontal)
  window.removeEventListener('mousemove', onResizeVertical)
  window.removeEventListener('mouseup', stopResize)
}

function toggleCollapse() {
  collapsed.value = !collapsed.value
}

onMounted(() => {
  connectWS()
})
onBeforeUnmount(() => {
  disconnectWS()
})
</script>

<style scoped>
.chat-widget {
  position: fixed;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  z-index: 9999;
  min-width: 280px;
  min-height: 350px;
  max-width: 90vw;
  max-height: 80vh;
  border: 1px solid rgba(0, 0, 0, 0.06);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.chat-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 12px 16px;
  cursor: grab;
  display: flex;
  justify-content: space-between;
  align-items: center;
  user-select: none;
  border-radius: 12px 12px 0 0;
}

.chat-header:active {
  cursor: grabbing;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.chat-avatar {
  font-size: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.chat-title {
  font-weight: 600;
  font-size: 14px;
}

.connection-status {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ff4757;
  transition: background 0.3s ease;
}

.connection-status.connected {
  background: #2ed573;
}

.header-actions {
  display: flex;
  gap: 4px;
}

.header-btn {
  background: rgba(255, 255, 255, 0.1);
  border: none;
  color: white;
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s ease;
}

.header-btn:hover {
  background: rgba(255, 255, 255, 0.2);
}

.close-btn:hover {
  background: rgba(255, 77, 87, 0.8);
}

.chat-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.messages {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
  background: #fafbfc;
  min-height: 0;
}

.messages::-webkit-scrollbar {
  width: 6px;
}

.messages::-webkit-scrollbar-track {
  background: transparent;
}

.messages::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.1);
  border-radius: 3px;
}

.messages::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.2);
}

.message {
  margin-bottom: 12px;
  display: flex;
  flex-direction: column;
  animation: fadeIn 0.3s ease;
  width: fit-content;
  max-width: 75%;
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

.message.user {
  align-self: flex-end;
  align-items: flex-end;
  margin-left: auto;
}

.message.assistant {
  align-self: flex-start;
  align-items: flex-start;
  margin-right: auto;
}

.message.system {
  align-self: center;
  align-items: center;
  max-width: 70%;
  margin-left: auto;
  margin-right: auto;
}

.message-content {
  padding: 10px 14px;
  border-radius: 16px;
  word-wrap: break-word;
  white-space: pre-wrap;
  line-height: 1.4;
  font-size: 14px;
  display: inline-block;
  text-align: left;
  max-width: 100%;
}

.message.user .message-content {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-bottom-right-radius: 6px;
}

.message.assistant .message-content {
  background: white;
  color: #2c3e50;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-bottom-left-radius: 6px;
}

.message.system .message-content {
  background: #fff3cd;
  color: #856404;
  border: 1px solid #ffeaa7;
  text-align: center;
  font-size: 13px;
}

.message-time {
  font-size: 11px;
  color: #95a5a6;
  margin-top: 4px;
  padding: 0 4px;
}

.input-container {
  background: white;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  padding: 12px 16px;
}

.input-box {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  background: #f8f9fa;
  border-radius: 24px;
  padding: 8px 12px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  transition: border-color 0.2s ease;
}

.input-box:focus-within {
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.message-input {
  flex: 1;
  border: none;
  background: transparent;
  resize: none;
  outline: none;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.4;
  max-height: 120px;
  min-height: 20px;
  padding: 6px 0;
  color: #2c3e50;
}

.message-input::placeholder {
  color: #95a5a6;
}

.send-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  color: white;
  cursor: pointer;
  padding: 8px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  width: 36px;
  height: 36px;
  flex-shrink: 0;
}

.send-btn:hover:not(:disabled) {
  transform: scale(1.05);
}

.send-btn:disabled {
  background: #bdc3c7;
  cursor: not-allowed;
  transform: none;
}

.resize-handle {
  position: absolute;
  background: transparent;
}

.resize-handle.bottom-right {
  width: 16px;
  height: 16px;
  right: 0;
  bottom: 0;
  cursor: se-resize;
}

.resize-handle.bottom {
  width: calc(100% - 16px);
  height: 4px;
  left: 0;
  bottom: 0;
  cursor: s-resize;
}

.resize-handle.right {
  width: 4px;
  height: calc(100% - 16px);
  right: 0;
  top: 0;
  cursor: e-resize;
}

.resize-handle.bottom-right::after {
  content: '';
  position: absolute;
  right: 2px;
  bottom: 2px;
  width: 12px;
  height: 12px;
  background: linear-gradient(
    -45deg,
    transparent 0%,
    transparent 40%,
    #bdc3c7 40%,
    #bdc3c7 60%,
    transparent 60%,
    transparent 100%
  );
  background-size: 4px 4px;
  opacity: 0.5;
}
</style>
