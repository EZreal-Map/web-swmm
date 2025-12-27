<template>
  <el-dialog v-model="dialogVisible" title="打断河流" width="400px" @close="handleClose">
    <el-form :model="form" label-width="120px">
      <el-form-item label="打断距离 (m)">
        <el-input-number
          v-model="form.breakDistance"
          :min="1"
          :max="10000"
          :step="100"
          class="input-class"
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" @click="handleConfirm">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  showDialog: {
    type: Boolean,
    required: true,
  },
})

const emit = defineEmits(['update:showDialog', 'confirm'])

const dialogVisible = computed({
  get: () => props.showDialog,
  set: (val) => emit('update:showDialog', val),
})

const form = ref({
  breakDistance: 1000, // 默认1000米
})

const handleClose = () => {
  dialogVisible.value = false
}

const handleConfirm = () => {
  emit('confirm', form.value.breakDistance)
  handleClose()
}
</script>

<style lang="css" scoped>
:deep(.el-input-number) {
  margin-left: 30px;
}
</style>
