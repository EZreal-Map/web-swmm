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
          <div class="message-content">
            {{ msg.text }}
            <!-- 只在 assistant 消息且有确认弹窗时显示按钮 -->
            <template v-if="msg.role === 'assistant' && msg.type === 'confirm' && !msg.confirmed">
              <div style="margin-top: 8px">
                <span>{{ msg.confirmQuestion }}</span>
                <button @click="handleConfirm(msg, true)" style="margin-left: 8px">是</button>
                <button @click="handleConfirm(msg, false)" style="margin-left: 4px">否</button>
              </div>
            </template>
          </div>
          <div class="message-time">{{ formatTime(msg.timestamp) }}</div>
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
import { flyToEntityByNameTool, initEntitiesTool } from '@/tools/webgis'

// 父组件可传的参数

const serverUrl = 'ws://localhost:8080/agent/ws/test-client'
// 生成唯一会话ID
const conversationId = 'conv-123' + Math.random().toString(36).substring(2, 15)
const userId = 'user-123'

const showDialog = defineModel('showDialog')

function closeDialog() {
  showDialog.value = false
}

/**
 * 消息类型常量 - 与后端保持一致
 */
const MessageType = {
  PING: 'ping',
  PONG: 'pong',
  START: 'start',
  AI_MESSAGE: 'AIMessage',
  HUMAN_FEEDBACK: 'HumanFeedback',
  TOOL_MESSAGE: 'ToolMessage',
  FUNCTION_CALL: 'FunctionCall',
  COMPLETE: 'complete',
  ERROR: 'error',
  CHAT_ERROR: 'Chat processing failed',
  STREAM_ERROR: 'Stream processing failed',
  INVALID_JSON: 'INVALID_JSON',
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  PROCESSING_ERROR: 'PROCESSING_ERROR',
}

/**
 * WebSocket 连接管理器
 */
class WebSocketManager {
  constructor(serverUrl, messageHandler, statusChangeHandler) {
    this.serverUrl = serverUrl
    this.messageHandler = messageHandler
    this.statusChangeHandler = statusChangeHandler
    this.ws = null
    this.connected = false
    this.heartbeatInterval = null
  }

  connect() {
    try {
      this.ws = new WebSocket(this.serverUrl)
      this.setupEventHandlers()
    } catch (error) {
      console.error('WebSocket 连接失败:', error)
      this.statusChangeHandler(false, '连接失败')
    }
  }

  setupEventHandlers() {
    this.ws.onopen = () => {
      this.connected = true
      this.statusChangeHandler(true, '已连接到服务器')
      this.startHeartbeat()
      console.log('WebSocket 连接成功')
    }

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        this.messageHandler(data)
      } catch (error) {
        console.error('解析消息失败:', error)
      }
    }

    this.ws.onclose = (event) => {
      this.connected = false
      this.stopHeartbeat()
      this.statusChangeHandler(false, '连接已断开')
      console.log('WebSocket 连接关闭:', event.code, event.reason)
    }

    this.ws.onerror = (error) => {
      console.error('WebSocket 错误:', error)
      this.statusChangeHandler(false, '连接出错')
    }
  }

  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
      return true
    } else {
      console.warn('WebSocket 未连接，消息发送失败')
      return false
    }
  }

  disconnect() {
    this.stopHeartbeat()
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.connected = false
  }

  startHeartbeat() {
    this.stopHeartbeat()
    this.heartbeatInterval = setInterval(() => {
      if (this.connected) {
        this.send({ type: MessageType.PING })
      }
    }, 30000)
  }

  stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = null
    }
  }

  isConnected() {
    return this.connected
  }
}

/**
 * 消息响应处理器
 */
class MessageResponseHandler {
  constructor(messages, wsManager, addMessage) {
    this.messages = messages
    this.wsManager = wsManager
    this.addMessage = addMessage
    this.functionMap = {
      flyToEntityByNameTool: flyToEntityByNameTool,
      initEntitiesTool: initEntitiesTool,
      showConfirmInChat: showConfirmInChat,
      // 可以继续添加其他可调用的函数
    }
  }

  /**
   * 主要的响应处理入口
   */
  handle(data) {
    console.log('收到响应:', data.type, data)

    switch (data.type) {
      case MessageType.PONG:
        this.handlePong()
        break
      case MessageType.START:
        this.handleStart(data)
        break
      case MessageType.AI_MESSAGE:
        this.handleAIMessage(data)
        break
      case MessageType.HUMAN_FEEDBACK:
        this.handleHumanFeedback(data)
        break
      case MessageType.TOOL_MESSAGE:
        this.handleToolMessage(data)
        break
      case MessageType.FUNCTION_CALL:
        this.handleFunctionCall(data)
        break
      case MessageType.COMPLETE:
        this.handleComplete(data)
        break
      case MessageType.ERROR:
      case MessageType.CHAT_ERROR:
      case MessageType.STREAM_ERROR:
      case MessageType.INVALID_JSON:
      case MessageType.VALIDATION_ERROR:
      case MessageType.PROCESSING_ERROR:
        this.handleError(data)
        break
      default:
        console.warn('未知消息类型:', data.type, data)
    }
  }

  handlePong() {
    console.log('收到心跳响应')
  }

  handleStart(data) {
    this.addMessage('assistant', '')
    console.log('开始处理响应:', data.message)
  }

  handleAIMessage(data) {
    const lastMessage = this.getLastAssistantMessage()
    if (lastMessage) {
      lastMessage.text += data.content || ''
    }
  }

  handleHumanFeedback(data) {
    const lastMessage = this.getLastAssistantMessage()
    if (lastMessage) {
      lastMessage.text += data.content || ''
    }
  }

  handleToolMessage(data) {
    console.log('工具消息:', data.tool_name, data.content)
    // 可以选择是否显示工具消息
    // this.addMessage('system', `工具 ${data.tool_name}: ${data.content}`)
  }

  async handleFunctionCall(data) {
    const { function_name, args, success_msg, is_direct_feedback } = data
    try {
      const fn = this.functionMap[function_name]

      if (typeof fn === 'function') {
        // 1. 执行函数调用
        // 将 args 对象的值作为参数数组传递
        const functionArgs = args ? Object.values(args) : []
        await fn(...functionArgs)
        // 2. 如果是直接反馈函数，就是可以直接运行得到反馈（回调），不要人工回调
        if (is_direct_feedback) {
          // 2.2 如果 后端工具没有定义 success_msg，就使用默认 success_msg
          const successMsg =
            success_msg || `已成功执行：${function_name}，参数：${JSON.stringify(args)}`
          this.sendFeedback(successMsg)
          console.log('函数调用成功:', function_name, args)
        }
      } else {
        const errorMsg = `未找到函数：${function_name}`
        this.sendFeedback(errorMsg, false)
        console.error('函数未找到:', function_name)
      }
    } catch (error) {
      const errorMsg = `${function_name}函数调用失败：${error.message}，参数：${JSON.stringify(args)}`
      this.sendFeedback(errorMsg, false)
      console.error('函数调用异常:', error)
    }
  }

  handleComplete(data) {
    // const lastMessage = this.getLastAssistantMessage()
    // if (lastMessage && data.message) {
    //   lastMessage.text = data.message
    // }
    // TODO: 暂时保留 astream 流式输出 complete处理，实际上它只能算作一次流式输出的结束，并不是整个对话的complete
    console.log('响应完成，总长度:', data.total_length)
  }

  handleError(data) {
    const errorMsg = data.error || data.message || '发生未知错误'
    this.addMessage('system', `错误: ${errorMsg}`)
    console.error('收到错误响应:', data.type, errorMsg)
  }

  getLastAssistantMessage() {
    const messages = this.messages.value
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === 'assistant') {
        return messages[i]
      }
    }
    return null
  }

  sendFeedback(message, success = true) {
    this.wsManager.send({
      message,
      conversation_id: conversationId,
      user_id: userId,
      feedback: true,
      success,
    })
  }
}

/**
 * 消息发送管理器
 */
class MessageSender {
  constructor(wsManager) {
    this.wsManager = wsManager
  }

  sendChatMessage(message) {
    return this.wsManager.send({
      message,
      conversation_id: conversationId,
      user_id: userId,
      feedback: false,
    })
  }

  sendPing() {
    return this.wsManager.send({
      type: MessageType.PING,
    })
  }
}

// 状态管理
const connected = ref(false)
const messages = ref([])
const input = ref('')
const messagesContainer = ref(null)
const inputRef = ref(null)

function addMessage(role, text, type = 'text', extra = {}) {
  messages.value.push({ role, text, type, ...extra, timestamp: new Date() })
  nextTick(() => {
    const el = messagesContainer.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

// 唤起确认组件的函数
/**
 * 唤起确认组件，返回 keepGoing 参数（true/false）
 * @param {string} confirm_question - 确认内容
 * @param {object} [options] - 可选，定制按钮行为
 * @param {string} [options.yesMsg] - 确认时发送的内容
 * @param {string} [options.noMsg] - 取消时发送的内容
 * @returns {Promise<boolean>} - keepGoing true/false
 */
/**
 * 在最后一条 assistant 消息下渲染确认弹窗
 * @param {string} question - 确认内容
 * @param {object} [options] - 可选，定制按钮行为
 * @param {string} [options.yesMsg] - 确认时发送的内容
 * @param {string} [options.noMsg] - 取消时发送的内容
 * @returns {Promise<{msg: string, keepGoing: boolean}>}
 */
function showConfirmInChat(question, { yesMsg = '人工确定', noMsg = '人工取消' } = {}) {
  return new Promise((resolve) => {
    // 找到最后一条 assistant 消息
    const lastMessage = messageHandler.getLastAssistantMessage()
    if (!lastMessage) {
      // 没有 assistant 消息，插入一条
      addMessage('assistant', question)
      const msg = messageHandler.getLastAssistantMessage()
      if (!msg) return resolve({ msg: '无可确认消息', keepGoing: false })
      msg.type = 'confirm'
      msg.confirmed = false
      msg.confirmQuestion = question
      msg.onYes = () => {
        msg.confirmed = true
        messageHandler.sendFeedback(yesMsg, true)
        resolve({ msg: yesMsg, keepGoing: true })
      }
      msg.onNo = () => {
        msg.confirmed = true
        messageHandler.sendFeedback(noMsg, false)
        resolve({ msg: noMsg, keepGoing: false })
      }
    } else {
      // 在 lastMessage 上挂载确认弹窗
      lastMessage.type = 'confirm'
      lastMessage.confirmed = false
      lastMessage.confirmQuestion = question
      lastMessage.onYes = () => {
        lastMessage.confirmed = true
        messageHandler.sendFeedback(yesMsg, true)
        resolve({ msg: yesMsg, keepGoing: true })
      }
      lastMessage.onNo = () => {
        lastMessage.confirmed = true
        messageHandler.sendFeedback(noMsg, false)
        resolve({ msg: noMsg, keepGoing: false })
      }
    }
  })
}

// 处理按钮点击
function handleConfirm(msg, isYes) {
  msg.confirmed = true // 禁用按钮
  if (isYes) {
    msg.onYes && msg.onYes()
  } else {
    msg.onNo && msg.onNo()
  }
}

// 创建一个临时的消息处理函数
let messageHandler = null

// 初始化WebSocket管理器
const wsManager = new WebSocketManager(
  serverUrl,
  (data) => messageHandler?.handle(data), // 使用可选链操作符
  (isConnected, message) => {
    connected.value = isConnected
    if (message) {
      addMessage('system', message)
    }
  },
)

// 现在创建实际的消息处理器
messageHandler = new MessageResponseHandler(messages, wsManager, addMessage)
const messageSender = new MessageSender(wsManager)

function connectWS() {
  wsManager.connect()
}

function disconnectWS() {
  wsManager.disconnect()
}

function sendMessage() {
  if (!wsManager.isConnected() || !input.value.trim()) return

  const msg = input.value.trim()
  addMessage('user', msg)

  const success = messageSender.sendChatMessage(msg)

  if (success) {
    input.value = ''
    adjustTextareaHeight()
  } else {
    addMessage('system', '消息发送失败，请检查连接')
  }
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
