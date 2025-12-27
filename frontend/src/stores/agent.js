import { defineStore } from 'pinia'
import { ref } from 'vue'

// Agent模式
export const AgentModeType = {
  TOOL: 'TOOL',
  PLAN: 'PLAN',
}

// agent 聊天相关 pinia 存储
export const useAgentStore = defineStore(
  'agent',
  () => {
    // 最近一条消息
    const lastAssistantMessage = ref(null)
    // 消息发送器（单例模式）
    const messageSender = ref(null)
    // 步骤消息
    const stepMessage = ref(null)
    // Agent模式
    const agentMode = ref(AgentModeType.PLAN) // 默认 PLAN 模式

    // 设置 lastAssistantMessage
    function setLastAssistantMessage(message) {
      lastAssistantMessage.value = message
    }
    // 设置 messageSender
    function setMessageSender(sender) {
      messageSender.value = sender
    }

    // 设置 stepMessage
    function setStepMessage(message) {
      if (!message) {
        message = 'AI 正在思考...'
      }
      stepMessage.value = message
    }

    // 设置 agentMode
    function setAgentMode(mode) {
      if (Object.values(AgentModeType).includes(mode)) {
        agentMode.value = mode
      } else {
        throw new Error('无效的 Agent 模式：' + mode)
      }
    }

    return {
      lastAssistantMessage,
      setLastAssistantMessage,
      messageSender,
      setMessageSender,
      stepMessage,
      setStepMessage,
      agentMode,
      setAgentMode,
    }
  },
  {
    persist: {
      paths: ['agentMode'],
    },
  },
)
