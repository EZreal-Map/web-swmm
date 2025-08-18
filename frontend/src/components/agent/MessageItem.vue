<template>
  <div :class="['message', message.role]">
    <div class="message-content">
      <!-- 1. Assistant 消息使用 markdown 渲染 -->
      <div v-if="message.role === 'assistant'">
        <!-- 1.1 文本 -->
        <div class="markdown-content" v-html="renderedMarkdown"></div>
        <!-- 1.2 额外组件 -->
        <div v-for="(item, index) in message.extra" :key="index">
          <!-- 确认弹窗 -->
          <!-- 传递回调函数给 ConfirmBoxUI，供按钮点击时调用 -->
          <ConfirmBoxUI
            v-if="item.active && item.type === 'confirm'"
            :question="item.confirmQuestion"
            :on-yes="item.onYes"
            :on-no="item.onNo"
          />
          <!-- 图组件 -->
          <EchartsUI
            v-else-if="item.type === 'echarts'"
            :query-entity-name="item.name"
            :entity-kind="item.kind"
            :variable-select="item.variable"
          />
        </div>
      </div>
      <!-- 2. 其他消息类型显示原始文本 -->
      <span v-else>{{ message.text }}</span>
    </div>
    <div class="message-time">{{ formatTime(message.timestamp) }}</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js'
import ConfirmBoxUI from '@/components/agent/ConfirmBoxUI.vue'

// 配置 marked
marked.setOptions({
  highlight: function (code, lang) {
    const language = hljs.getLanguage(lang) ? lang : 'plaintext'
    return hljs.highlight(code, { language }).value
  },
  langPrefix: 'hljs language-',
  breaks: true,
  gfm: true,
})

// 使用更详细的 props 定义，提供更好的类型检查 - 单向数据流
const props = defineProps({
  message: {
    type: Object,
    required: true,
    validator: (value) => {
      return value && typeof value.role === 'string' && typeof value.text === 'string'
    },
  },
})

// 计算属性：渲染 markdown
const renderedMarkdown = computed(() => {
  if (props.message.role === 'assistant') {
    return marked.parse(props.message.text)
  }
  return props.message.text
})

function formatTime(date) {
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}
</script>

<style scoped>
.message {
  margin-bottom: 12px;
  display: flex;
  flex-direction: column;
  animation: fadeIn 0.3s;
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
  color: #fff;
  border-bottom-right-radius: 6px;
}

.message.assistant .message-content {
  background: #fff;
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
</style>
