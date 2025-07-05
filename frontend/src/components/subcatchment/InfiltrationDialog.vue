<template>
  <el-dialog
    v-model="visible"
    title="编辑子汇水区下渗参数"
    width="400px"
    :close-on-click-modal="false"
  >
    <div class="form-container">
      <el-form :model="form" label-width="130px" label-position="left">
        <el-form-item>
          <template #label>
            <el-tooltip effect="dark" content="子汇水区名称" placement="left">
              <span>子汇水区名称</span>
            </el-tooltip>
          </template>
          <el-input v-model="form.subcatchment" disabled class="full-width" />
        </el-form-item>

        <el-form-item>
          <template #label>
            <el-tooltip
              effect="dark"
              content="霍顿曲线最大入渗速率，单位 mm/hr，默认3.0，代表降雨初期土壤最大吸水速率"
              placement="left"
            >
              <span>最大入渗速率</span>
            </el-tooltip>
          </template>
          <el-input-number v-model="form.rate_max" :step="0.1" :min="0" class="full-width" />
        </el-form-item>

        <el-form-item>
          <template #label>
            <el-tooltip
              effect="dark"
              content="霍顿曲线最小入渗速率，单位 mm/hr，默认0.5，表示土壤饱和后残留入渗速率"
              placement="left"
            >
              <span>最小入渗速率</span>
            </el-tooltip>
          </template>
          <el-input-number v-model="form.rate_min" :step="0.1" :min="0" class="full-width" />
        </el-form-item>

        <el-form-item>
          <template #label>
            <el-tooltip
              effect="dark"
              content="霍顿曲线衰减常数，单位 1/hr，默认4.0，描述入渗速率从最大降至最小的速度"
              placement="left"
            >
              <span>衰减常数</span>
            </el-tooltip>
          </template>
          <el-input-number v-model="form.decay" :step="0.1" :min="0" class="full-width" />
        </el-form-item>

        <el-form-item>
          <template #label>
            <el-tooltip
              effect="dark"
              content="土壤完全饱和后干燥时间，单位 天，默认7.0，影响入渗恢复速度"
              placement="left"
            >
              <span>干燥时间</span>
            </el-tooltip>
          </template>
          <el-input-number v-model="form.time_dry" :step="0.1" :min="0" class="full-width" />
        </el-form-item>

        <el-form-item>
          <template #label>
            <el-tooltip
              effect="dark"
              content="最大入渗体积，单位 mm，默认0，表示无限制"
              placement="left"
            >
              <span>最大入渗体积</span>
            </el-tooltip>
          </template>
          <el-input-number v-model="form.volume_max" :step="0.1" :min="0" class="full-width" />
        </el-form-item>
      </el-form>
    </div>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" @click="onSubmit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref } from 'vue'
import { getInfiltrationAxios, updateInfiltrationAxios } from '@/apis/subcatchment'

const visible = defineModel('visible')
const subcatchmentName = defineModel('subcatchmentName')
const form = ref({
  subcatchment: subcatchmentName.value,
  rate_max: 3.0,
  rate_min: 0.5,
  decay: 4.0,
  time_dry: 7.0,
  volume_max: 0,
})

const getInfiltrationData = async (subcatchment_name) => {
  const response = await getInfiltrationAxios(subcatchment_name)
  form.value = response.data
}
getInfiltrationData(subcatchmentName.value)

const onSubmit = async () => {
  const response = await updateInfiltrationAxios(form.value)
  if (response.code === 200) {
    ElMessage.success('下渗参数更新成功')
    visible.value = false
  }
}
</script>

<style scoped>
.full-width {
  width: 100%;
}
.form-container {
  padding: 0 16px;
}
</style>
