<template>
  <div v-if="showDialog" class="chat-widget" :style="widgetStyle">
    <!-- Header -->
    <div class="chat-header" @mousedown="startDrag">
      <div class="header-left">
        <div class="chat-avatar">🤖</div>
        <span class="chat-title">AI 聊天助手</span>
        <div class="connection-status" :class="{ connected }"></div>
        <div></div>
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
        <button class="header-btn" @click.stop="openSettings" :disabled="isLoading" title="设置">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
            <path
              d="M19.14 12.94c.04-.31.06-.63.06-.94s-.02-.63-.06-.94l2.03-1.58a.5.5 0 0 0 .11-.64l-1.92-3.32a.5.5 0 0 0-.61-.22l-2.39.96a7.1 7.1 0 0 0-1.63-.94l-.36-2.54A.5.5 0 0 0 14.84 2h-3.68a.5.5 0 0 0-.49.41l-.36 2.54a7.1 7.1 0 0 0-1.63.94l-2.39-.96a.5.5 0 0 0-.61.22L3.76 8.47a.5.5 0 0 0 .11.64l2.03 1.58c-.04.31-.06.63-.06.94s.02.63.06.94l-2.03 1.58a.5.5 0 0 0-.11.64l1.92 3.32a.5.5 0 0 0 .61.22l2.39-.96c.5.38 1.05.7 1.63.94l.36 2.54c.04.24.25.41.49.41h3.68c.24 0 .45-.17.49-.41l.36-2.54c.58-.24 1.13-.56 1.63-.94l2.39.96c.23.09.5 0 .61-.22l1.92-3.32a.5.5 0 0 0-.11-.64l-2.03-1.58ZM12 15.5A3.5 3.5 0 1 1 12 8.5a3.5 3.5 0 0 1 0 7Z"
            />
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
      <!-- 消息列表组件 -->
      <MessageList :messages="messages" :is-loading="isLoading" ref="messageListRef" />
      <!-- 输入框组件 -->
      <ChatInput v-model="input" :disabled="!connected" @send="sendMessage" />
    </div>

    <!-- Resize handles -->
    <div class="resize-handle bottom-right" @mousedown.stop="startResize"></div>
    <div class="resize-handle bottom" @mousedown.stop="startResizeVertical"></div>
    <div class="resize-handle right" @mousedown.stop="startResizeHorizontal"></div>
    <div v-if="showSettingsDialog" class="settings-overlay" @click.self="closeSettings">
      <div class="settings-dialog">
        <div class="settings-header">
          <span>设置</span>
          <button class="header-btn" @click="closeSettings" title="关闭设置">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
              <path
                d="M19 6.41 17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"
              />
            </svg>
          </button>
        </div>
        <div class="settings-body">
          <div class="settings-field">
            <label for="agent-mode" class="settings-label">Agent 模式</label>
            <select id="agent-mode" v-model="tempSelectedAgentMode" class="settings-select">
              <option v-for="option in agentModeOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </div>
          <div class="settings-field">
            <label for="model-select" class="settings-label">模型</label>
            <select id="model-select" v-model="selectedLLMModel" class="settings-select">
              <option v-for="model in modelOptions" :key="model.value" :value="model.value">
                {{ model.label }}
              </option>
            </select>
          </div>
          <div class="settings-footer">
            <button class="settings-btn ghost" @click="closeSettings">取消</button>
            <button class="settings-btn primary" @click="confirmSettings">确认</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, computed } from 'vue'
import { flyToEntityByNameTool, initEntitiesTool } from '@/tools/webgis'
import { showConfirmBoxUITool, showEchartsUITool, showHumanInfoUITool } from '@/tools/webui'
import MessageList from '@/components/agent/MessageList.vue'
import ChatInput from '@/components/agent/ChatInput.vue'
import { useAgentStore } from '@/stores/agent'
import { getChatWSURL } from '@/apis/wsURL'
import { getAgentModelInfoAxios, updateAgentModelAxios } from '@/apis/chat'

const agentStore = useAgentStore()

// 控制对话框显示隐藏，这个参数可以从父组件传入，所以使用 defineModel，双向绑定
const showDialog = defineModel('showDialog', { type: Boolean, default: false })

// 生成唯一会话ID - 使用模板字符串
const conversationId = `conv-123${Math.random().toString(36).substring(2, 15)}`
const userId = 'user-123'
const clientId = `${userId}@@${conversationId}`
const serverUrl = getChatWSURL(clientId)

// AI助手弹窗关闭函数
function closeDialog() {
  showDialog.value = false
}

/**
 * 消息类型常量 - 与后端保持一致
 */
// 前端请求消息类型
const RequestMessageType = {
  PING: 'ping',
  CHAT: 'chat',
  FEEDBACK: 'feedback',
}

// 后端响应消息类型
const ResponseMessageType = {
  PONG: 'pong',
  START: 'start',
  AI_MESSAGE: 'AIMessage',
  TOOL_MESSAGE: 'ToolMessage',
  FUNCTION_CALL: 'FunctionCall',
  COMPLETE: 'complete',
  ERROR: 'error',
  STEP: 'step',
}

// Agent模式
const AgentMode = {
  TOOL: 'TOOL',
  PLAN: 'PLAN',
}

const agentModeOptions = [
  { value: AgentMode.TOOL, label: '工具模式' },
  { value: AgentMode.PLAN, label: '计划模式' },
]

const modelOptions = ref([{ value: 'gpt-4o-mini', label: 'GPT-4o mini' }])

// 选择的Agent模式和模型
// TODO: 把selectedAgentMode使用pinia存储起来（还是放在后端变量吧）
const selectedAgentMode = ref(AgentMode.PLAN)
const selectedLLMModel = ref(modelOptions.value[0].value)

const tempSelectedAgentMode = ref(selectedAgentMode.value)
const showSettingsDialog = ref(false)

const openSettings = async () => {
  const modelInfo = await getAgentModelInfoAxios()
  selectedLLMModel.value = modelInfo.data.selected_model
  modelOptions.value = modelInfo.data.models.map((model) => ({
    value: model,
    label: model,
  }))
  showSettingsDialog.value = true
}

const closeSettings = () => {
  showSettingsDialog.value = false
}

const confirmSettings = async () => {
  const response = await updateAgentModelAxios(selectedLLMModel.value)
  const selectOption = agentModeOptions.find(
    (option) => option.value === tempSelectedAgentMode.value,
  )
  selectedAgentMode.value = tempSelectedAgentMode.value
  ElMessage.success('Agent模式已切换为' + selectOption.label)
  ElMessage.success(response.message)
  showSettingsDialog.value = false
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
      const payload = {
        ...data,
        timestamp: Date.now(), // 添加当前时间戳
      }
      this.ws.send(JSON.stringify(payload))
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
        this.send({ type: RequestMessageType.PING })
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
      flyToEntityByNameTool,
      initEntitiesTool,
      showConfirmBoxUITool,
      showEchartsUITool,
      showHumanInfoUITool,
      // 可以继续添加其他可调用的函数
    }
  }

  /**
   * 主要的响应处理入口
   */
  handle(data) {
    switch (data.type) {
      case ResponseMessageType.PONG:
        this.handlePong()
        break
      case ResponseMessageType.START:
        this.handleStart(data)
        break
      case ResponseMessageType.AI_MESSAGE:
        this.handleAIMessage(data)
        break
      case ResponseMessageType.TOOL_MESSAGE:
        this.handleToolMessage(data)
        break
      case ResponseMessageType.FUNCTION_CALL:
        this.handleFunctionCall(data)
        break
      case ResponseMessageType.COMPLETE:
        this.handleComplete(data)
        break
      case ResponseMessageType.ERROR:
        this.handleError(data)
        break
      case ResponseMessageType.STEP:
        this.handleStep(data)
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
    isLoading.value = true
    console.log(`开始处理响应 - data.type:${data.type}`)
  }

  handleAIMessage(data) {
    const lastMessage = agentStore.lastAssistantMessage
    lastMessage.text += data.content || ''
    // 如果 aimessage 有 tool_calls
    if (data.tool_calls && data.tool_calls.length > 0) {
      // 处理工具调用
      data.tool_calls.forEach((toolCall) => {
        // 采用统一风格
        const toolMessage = `\n- 🛠️工具调用：\`${toolCall.name}\`\n- 参数：\n\`\`\`json\n${JSON.stringify(toolCall.args, null, 2)}\n\`\`\``
        lastMessage.text += toolMessage
      })
    }
  }

  handleToolMessage(data) {
    // data.content 是 JSON 字符串
    const result = JSON.parse(data.content)
    // console.log('工具消息:', data.tool_name, result)

    const lastMessage = agentStore.lastAssistantMessage
    // 确保 ToolMessage 的 content里面 都要 message 字段
    let toolMessage = `\n- 🛠️工具执行：\`${data.name}\`\n- success：${result.success}\n- message：${result.message}`

    // 只对数组类型做省略处理，对对象类型始终完整展示
    if (result.data !== undefined && result.data !== null) {
      let dataStr = ''
      let isArray = Array.isArray(result.data)
      let showData = result.data
      let omitted = false
      // 只显示前3个元素（数组时）
      if (isArray && result.data.length > 3) {
        showData = result.data.slice(0, 3)
        omitted = true
      }
      dataStr = `\n- data：\n\`\`\`json\n${JSON.stringify(showData, null, 2)}\n\`\`\``
      if (omitted) {
        dataStr += `\n...数据已省略，仅展示前3项，实际共${result.data.length}项`
      }
      toolMessage += dataStr
    }
    lastMessage.text += toolMessage
  }

  // 重要
  async handleFunctionCall(data) {
    const { function_name, args, success_message, is_direct_feedback } = data
    try {
      const fn = this.functionMap[function_name]

      if (typeof fn === 'function') {
        // 1. 执行函数调用
        // 将 args 对象的值作为Object直接传递给fn，需要前后端字段大小写完全保存一直，顺序没有关系
        await fn(args)
        // 2. 如果是直接反馈函数，就是可以直接运行得到反馈（回调），不要人工回调
        if (is_direct_feedback) {
          // 2.2 如果 后端工具没有定义 success_message，就使用默认 success_message
          const successMsg =
            success_message || `已成功执行：${function_name}，参数：${JSON.stringify(args)}`
          messageSender.sendFeedbackMessage(successMsg)
          console.log('函数调用成功:', function_name, args)
        }
      } else {
        const errorMsg = `未找到函数：${function_name}`
        messageSender.sendFeedbackMessage(errorMsg, false)
        console.error('函数未找到:', function_name)
      }
    } catch (error) {
      const errorMsg = `${function_name}函数调用失败：${error.message}，参数：${JSON.stringify(args)}`
      messageSender.sendFeedbackMessage(errorMsg, false)
      console.error('函数调用异常:', error)
    }
  }

  handleComplete(data) {
    isLoading.value = false
    agentStore.setStepMessage() // 重新初始化步骤消息
    console.log('响应完成，总长度:', data)
  }

  handleError(data) {
    isLoading.value = false
    const errorMsg = data.error || data.message || '发生未知错误'
    this.addMessage('system', `错误: ${errorMsg}`)
    console.error('收到错误响应:', data.type, errorMsg)
  }

  handleStep(data) {
    // 处理步骤消息
    // 1. 存储步骤消息
    agentStore.setStepMessage(data.content)
    // 2.1 删除 data.content 里 ']' 及其之后的内容
    let content = data.content
    const idx = content.indexOf(']')
    if (idx !== -1) {
      content = content.slice(0, idx + 1)
    }
    // 2.2 作为标题显示到对话框中
    const lastMessage = agentStore.lastAssistantMessage
    const stepTitle = `\n\n\n## ${content}\n\n\n`
    lastMessage.text += stepTitle
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
      type: RequestMessageType.CHAT,
      mode: selectedAgentMode.value,
    })
  }

  sendFeedbackMessage(message, success = true) {
    return this.wsManager.send({
      message,
      type: RequestMessageType.FEEDBACK,
      success,
      mode: selectedAgentMode.value,
    })
  }

  sendPing() {
    return this.wsManager.send({
      type: RequestMessageType.PING,
    })
  }
}

// 状态管理
const connected = ref(false)
const messages = reactive([])
const input = ref('')
const isLoading = ref(false)
const messageListRef = ref(null)

// role：'user' | 'assistant' | 'system'
// text：消息内容
// 为消息添加 id
let messageId = 0
function addMessage(role, text) {
  const message = {
    id: ++messageId,
    role,
    text,
    extra: [],
    timestamp: new Date(),
  }
  // 将消息添加到消息列表
  messages.push(message)
  // 更新 agentStore 中的 lastMessage
  if (role === 'assistant') {
    agentStore.setLastAssistantMessage(message)
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
// 存储 messageSender
agentStore.setMessageSender(messageSender)

function connectWS() {
  wsManager.connect()
}

function disconnectWS() {
  wsManager.disconnect()
}

/**
 * 发送消息函数
 * @param {string} messageText - 要发送的消息文本
 */
function sendMessage(messageText) {
  if (!wsManager.isConnected() || !messageText.trim()) return
  // 跳转到最底部
  messageListRef.value?.scrollToBottom(true)
  const msg = messageText.trim()
  addMessage('user', msg)

  const success = messageSender.sendChatMessage(msg)

  if (success) {
    isLoading.value = true
    input.value = ''
  } else {
    addMessage('system', '消息发送失败，请检查连接')
  }
}

// 拖拽 & 缩放
const collapsed = ref(false)
const pos = ref({ x: 210, y: 10 })
const size = ref({ width: 500, height: 600 })
let dragging = false
let dragOffset = { x: 0, y: 0 }
let resizing = false
let resizeStart = { x: 0, y: 0, w: 0, h: 0 }

const widgetStyle = computed(() => ({
  top: pos.value.y + 'px',
  left: pos.value.x + 'px',
  width: size.value.width + 'px',
  height: collapsed.value ? '48px' : size.value.height + 'px',
  minHeight: collapsed.value ? '48px' : '48px',
  maxHeight: collapsed.value ? '48px' : '100vh',
  overflow: 'hidden',
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
    Math.min(window.innerWidth, resizeStart.w + (e.clientX - resizeStart.x)),
  )
  const newHeight = Math.max(
    350,
    Math.min(window.innerHeight, resizeStart.h + (e.clientY - resizeStart.y)),
  )
  size.value.width = newWidth
  size.value.height = newHeight
}

function onResizeHorizontal(e) {
  if (!resizing) return
  const newWidth = Math.max(
    280,
    Math.min(window.innerWidth, resizeStart.w + (e.clientX - resizeStart.x)),
  )
  size.value.width = newWidth
}

function onResizeVertical(e) {
  if (!resizing) return
  const newHeight = Math.max(
    350,
    Math.min(window.innerHeight, resizeStart.h + (e.clientY - resizeStart.y)),
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
/* 主体样式 */
.chat-widget {
  position: fixed;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
  display: flex;
  flex-direction: column;
  z-index: 99;
  border: 1px solid rgba(0, 0, 0, 0.06);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

/* 头部样式 */

.chat-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  padding: 12px 16px;
  cursor: move; /* 浏览器自带的移动图标 */
  display: flex;
  justify-content: space-between;
  align-items: center;
  user-select: none;
  border-radius: 12px 12px 0 0;
  z-index: 9999; /* 确保头部在最上层 */
}

.chat-header:active {
  cursor: move;
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
  transition: background 0.3s;
}

.connection-status.connected {
  background: #2ed573;
}

.header-actions {
  display: flex;
  gap: 4px;
}

.settings-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.settings-dialog {
  background: #fff;
  border-radius: 12px;
  width: 400px;
  box-shadow: 0 20px 45px rgba(0, 0, 0, 0.2);
  overflow: hidden;
  animation: fadeIn 0.2s ease;
}

.settings-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
}

.settings-body {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.settings-field {
  display: flex;
  align-items: center;
  gap: 12px;
}

.settings-label {
  font-size: 13px;
  font-weight: 600;
  color: #555;
  min-width: 80px;
}

.settings-select {
  border: 1px solid #d9d9d9;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 13px;
  outline: none;
  transition: border-color 0.2s;
  flex: 1;
}

.settings-select:focus {
  border-color: #7c5dfa;
  box-shadow: 0 0 0 2px rgba(124, 93, 250, 0.15);
}

.settings-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.settings-btn {
  min-width: 72px;
  padding: 6px 12px;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  transition: all 0.2s ease;
}

.settings-btn.ghost {
  background: transparent;
  color: #666;
  border: 1px solid #dcdcdc;
}

.settings-btn.ghost:hover {
  border-color: #999;
  color: #333;
}

.settings-btn.primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  border: none;
}

.settings-btn.primary:hover {
  opacity: 0.9;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.header-btn {
  background: rgba(255, 255, 255, 0.1);
  border: none;
  color: #fff;
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}

.header-btn:hover {
  background: rgba(255, 255, 255, 0.2);
}

.header-btn:disabled {
  cursor: not-allowed;
}

.close-btn:hover {
  background: rgba(255, 77, 87, 0.8);
}

/* 聊天主体 */
.chat-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

/* 缩放手柄 */
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
  z-index: 9999;
}

.resize-handle.bottom {
  width: calc(100% - 16px);
  height: 4px;
  left: 0;
  bottom: 0;
  cursor: s-resize;
  z-index: 9999;
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
