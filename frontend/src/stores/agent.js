import { defineStore } from 'pinia'
import { ref } from 'vue'

// agent 聊天相关 pinia 存储
export const useAgentStore = defineStore('agent', () => {
  // 最近一条消息
  const lastAssistantMessage = ref(null)
  // 消息发送器（单例模式）
  const messageSender = ref(null)
  // 步骤消息
  const stepMessage = ref(null)

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

  return {
    lastAssistantMessage,
    setLastAssistantMessage,
    messageSender,
    setMessageSender,
    stepMessage,
    setStepMessage,
  }
})
