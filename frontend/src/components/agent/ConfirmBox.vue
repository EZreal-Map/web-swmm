<template>
  <div class="confirm-box">
    <span class="confirm-question">{{ question }}</span>
    <div class="confirm-actions">
      <button class="confirm-btn yes" @click="onYes?.()">是</button>
      <button class="confirm-btn no" @click="onNo?.()">否</button>
    </div>
  </div>
</template>

<script setup>
// 使用对象语法定义 props，类型检查更严格 - 单向数据流
defineProps({
  question: { type: String, required: true },
  onYes: { type: Function, required: true },
  onNo: { type: Function, required: true },
})
</script>

<style scoped>
.confirm-box {
  margin-top: 10px;
  border: 1.5px solid #e0e0e0;
  border-radius: 10px;
  background: #f9fafb;
  padding: 14px 18px 12px 18px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  box-shadow: 0 2px 8px 0 rgba(102, 126, 234, 0.06);
  max-width: 320px;
}
.confirm-question {
  color: #333;
  margin-bottom: 12px;
  font-weight: 500;
}
.confirm-actions {
  display: flex;
  gap: 10px;
}
.confirm-btn {
  min-width: 20px;
  padding: 6px 14px;
  border-radius: 6px;
  border: none;
  font-size: 10px;
  font-weight: 500;
  cursor: pointer;
  transition:
    background 0.2s,
    color 0.2s;
}
.confirm-btn.yes {
  background: linear-gradient(90deg, #667eea 0%, #d8c3f0 100%);
  color: #fff;
  border: none;
}
.confirm-btn.yes:hover {
  background: linear-gradient(90deg, #5a67d8 0%, #6c4997 100%);
}
.confirm-btn.no {
  background: #f3f3f3;
  color: #666;
  border: 1px solid #e0e0e0;
}
.confirm-btn.no:hover {
  background: #f8d7da;
  color: #c0392b;
  border-color: #f5c6cb;
}
</style>
