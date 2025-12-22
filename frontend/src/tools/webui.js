import { useAgentStore } from '@/stores/agent'
import { reactive } from 'vue'
/**
 * 在聊天中插入一个确认弹窗（如“是否继续？”），并将回调与 UI 状态绑定。
 *
 * @param {string} confirmQuestion - 确认内容（问题文本）
 * @param {Object} [options] - 可选项
 * @param {string} [options.yesMsg='人工确定'] - 用户点击“确定”时反馈给后端的消息
 * @param {string} [options.noMsg='人工取消'] - 用户点击“取消”时反馈给后端的消息
 *
 * 用法说明：
 * - 会在最后一条 assistant 消息的 extra 数组中插入一个 confirm UI 对象。
 * - confirm UI 对象包含 onYes/onNo 回调，回调内可直接修改 UI 状态（如 active=false），并发送反馈消息。
 * - 通过闭包保证 onYes/onNo 始终引用正确的 ui 对象。
 */
export const showConfirmBoxUITool = async ({ confirm_question: confirmQuestion }) => {
  const options = { yesMsg: '人工确定删除', noMsg: '人工取消删除' }
  const agentStore = useAgentStore()
  // 1. 获取最后一条 assistant 消息
  const lastMessage = agentStore.lastAssistantMessage
  if (!lastMessage) return

  // 2. 先声明 ui 对象
  // (实测：这里用reactive包裹才能更快被响应式系统追踪)
  const ui = reactive({
    type: 'confirm', // UI 类型
    active: true, // 控制显示/隐藏
    confirmQuestion, // 确认内容
    onYes: null, // 占位，后续回调通过闭包引用
    onNo: null,
  })

  // 3. 定义回调，直接操作 ui.active (隐藏ui) 并发送反馈信息给后端
  ui.onYes = () => {
    ui.active = false
    agentStore.messageSender.sendFeedbackMessage(options.yesMsg, true)
  }
  ui.onNo = () => {
    ui.active = false
    agentStore.messageSender.sendFeedbackMessage(options.noMsg, false)
  }

  // 4. 挂载到消息 extra 字段，供渲染和交互
  lastMessage.extra.push(ui)
}

export const showEchartsUITool = async ({ name, kind, variable }) => {
  const agentStore = useAgentStore()
  // 1. 获取最后一条 assistant 消息
  const lastMessage = agentStore.lastAssistantMessage
  if (!lastMessage) return

  // 2. 声明 ui 对象
  const ui = reactive({
    type: 'echarts', // UI 类型
    active: true, // 控制显示/隐藏
    name,
    kind,
    variable,
  })

  // 3. 挂载到消息 extra 字段，供渲染和交互
  lastMessage.extra.push(ui)
}

/**
 * 在聊天中插入一个信息补充输入框UI
 * @param {string} inputTitle - 输入提示标题
 */
export const showHumanInfoUITool = async ({ input_title: inputTitle }) => {
  const agentStore = useAgentStore()
  const lastMessage = agentStore.lastAssistantMessage
  if (!lastMessage) return

  // 响应式UI对象
  const ui = reactive({
    type: 'human-info', // UI 类型
    active: true,
    inputTitle,
    inputValue: '', // 用户输入内容
    onOk: null,
    onCancel: null,
  })

  // 回调
  ui.onOk = () => {
    ui.active = false
    const trimmedValue = (ui.inputValue || '').trim()
    agentStore.messageSender.sendFeedbackMessage(trimmedValue || '人工未填写', true)
  }
  ui.onCancel = () => {
    ui.active = false
    agentStore.messageSender.sendFeedbackMessage('人工取消填写', false)
  }

  lastMessage.extra.push(ui)
}
