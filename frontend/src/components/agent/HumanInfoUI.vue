<template>
  <div class="human-info-box">
    <span class="input-title">{{ inputTitle }}</span>
    <el-input
      v-model="inputValue"
      class="human-info-input"
      :placeholder="'请输入内容...'"
      @keydown.enter="onOk?.()"
    />
    <div class="human-info-actions">
      <button class="info-btn ok" @click="onOk?.()">确定</button>
      <button class="info-btn cancel" @click="onCancel?.()">取消</button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  inputTitle: { type: String, required: true },
  onOk: { type: Function, required: true },
  onCancel: { type: Function, required: true },
})
const inputValue = defineModel('inputValue', { type: String, default: '' })
</script>

<style scoped>
.human-info-box {
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
.input-title {
  color: #333;
  margin-bottom: 10px;
  font-weight: 500;
}
.human-info-input {
  width: 100%;
  margin-bottom: 12px;
  padding: 7px 10px;
  font-size: 13px;
  outline: none;
  transition: border 0.2s;
}
.human-info-input:focus {
  border-color: #667eea;
}
.human-info-actions {
  display: flex;
  gap: 10px;
}
.info-btn {
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
.info-btn.ok {
  background: linear-gradient(90deg, #667eea 0%, #d8c3f0 100%);
  color: #fff;
  border: none;
}
.info-btn.ok:hover {
  background: linear-gradient(90deg, #5a67d8 0%, #6c4997 100%);
}
.info-btn.cancel {
  background: #f3f3f3;
  color: #666;
  border: 1px solid #e0e0e0;
}
.info-btn.cancel:hover {
  background: #f8d7da;
  color: #c0392b;
  border-color: #f5c6cb;
}
</style>
