<template>
  <el-dialog
    v-model="visible"
    title="编辑子汇水区汇流参数"
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
              content="不透水区域的地表粗糙程度，默认值 0.01；建议依据地表覆盖类型调整"
              placement="left"
            >
              <span>不透水曼宁系数</span>
            </el-tooltip>
          </template>
          <el-input-number v-model="form.n_imperv" :step="0.01" :min="0" class="full-width" />
        </el-form-item>

        <el-form-item>
          <template #label>
            <el-tooltip
              effect="dark"
              content="渗透区域的地表糙率，默认 0.1，建议依据地表覆盖类型调整"
              placement="left"
            >
              <span>渗透曼宁系数</span>
            </el-tooltip>
          </template>
          <el-input-number v-model="form.n_perv" :step="0.01" :min="0" class="full-width" />
        </el-form-item>

        <el-form-item>
          <template #label>
            <el-tooltip
              effect="dark"
              content="不透水区的初始存水量，单位 mm，一般为 1～3mm，可依据实际情况调整"
              placement="left"
            >
              <span>不透水凹陷储存</span>
            </el-tooltip>
          </template>
          <el-input-number v-model="form.storage_imperv" :step="0.01" :min="0" class="full-width" />
        </el-form-item>

        <el-form-item>
          <template #label>
            <el-tooltip
              effect="dark"
              content="渗透区的初始存水量，单位 mm，建议与不透水一致或更大"
              placement="left"
            >
              <span>渗透凹陷储存</span>
            </el-tooltip>
          </template>
          <el-input-number v-model="form.storage_perv" :step="0.01" :min="0" class="full-width" />
        </el-form-item>

        <el-form-item>
          <template #label>
            <el-tooltip
              effect="dark"
              content="无凹陷储存的不透水面积占比 (%)，默认25，可依据地面硬化情况调整"
              placement="left"
            >
              <span>无储存面积百分比</span>
            </el-tooltip>
          </template>
          <el-input-number
            v-model="form.pct_zero"
            :step="1"
            :min="0"
            :max="100"
            class="full-width"
          />
        </el-form-item>

        <el-form-item>
          <template #label>
            <el-tooltip
              effect="dark"
              content="控制子区径流流向；一般选择 直接出流"
              placement="left"
            >
              <span>径流路径</span>
            </el-tooltip>
          </template>
          <el-select v-model="form.route_to" placeholder="请选择路径" class="full-width">
            <el-option label="流向不透水区" value="IMPERVIOUS" />
            <el-option label="流向渗透区" value="PERVIOUS" />
            <el-option label="直接出流" value="OUTLET" />
          </el-select>
        </el-form-item>

        <el-form-item>
          <template #label>
            <el-tooltip
              effect="dark"
              content="设置有多少比例的径流进入目标区域，一般为100%；需要分流时再修改"
              placement="left"
            >
              <span>流向比例</span>
            </el-tooltip>
          </template>
          <el-input-number
            v-model="form.pct_routed"
            :step="1"
            :min="0"
            :max="100"
            class="full-width"
          />
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
import { getSubareaAxios, updateSubareaAxios } from '@/apis/subcatchment'
import { ref } from 'vue'

const visible = defineModel('visible')
const subcatchmentName = defineModel('subcatchmentName')
const form = ref({
  subcatchment: subcatchmentName.value,
  n_imperv: 0.01,
  n_perv: 0.1,
  storage_imperv: 1,
  storage_perv: 1,
  pct_zero: 25,
  route_to: 'OUTLET',
  pct_routed: 100,
})

const getInfiltrationData = async (subcatchmentName) => {
  const response = await getSubareaAxios(subcatchmentName)
  form.value = response.data
}
getInfiltrationData(subcatchmentName.value)

const onSubmit = async () => {
  const response = await updateSubareaAxios(form.value)
  if (response.code === 200) {
    ElMessage.success('汇流参数更新成功')
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
