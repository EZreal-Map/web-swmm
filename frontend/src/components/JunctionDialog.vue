<template>
  <div class="popup-container">
    <el-card class="popup-card">
      <div class="popup-header">
        <span class="popup-title">节点 信息详情</span>
        <el-icon @click="closeDialog"><CloseBold /></el-icon>
      </div>

      <el-form
        label-position="left"
        class="popup-form"
        label-width="70px"
        style="max-width: 268px"
        :size="'default'"
        v-model="junctionEntity"
      >
        <el-form-item label="名字">
          <el-input v-model="junctionEntity.name" type="string"></el-input>
        </el-form-item>
        <el-form-item label="经度">
          <el-input v-model.number="junctionEntity.lon" type="number"></el-input>
        </el-form-item>
        <el-form-item label="纬度">
          <el-input v-model.number="junctionEntity.lat" type="number"></el-input>
        </el-form-item>
        <el-form-item label="高程">
          <el-input
            v-model.number="junctionEntity.elevation"
            type="number"
            class="el-form-length"
          ></el-input>
          <el-button @click="calculateElevation" class="el-form-length-button">计算</el-button>
        </el-form-item>
        <el-form-item label="初始水深">
          <el-input v-model.number="junctionEntity.depthInit" type="number"></el-input>
        </el-form-item>
        <el-form-item>
          <template #label>
            <el-tooltip effect="dark" content="不考虑节点溢流时，推荐设置为 9999" placement="left">
              <span>最大水深</span>
            </el-tooltip>
          </template>
          <el-input v-model.number="junctionEntity.depthMax" type="number"></el-input>
        </el-form-item>
        <el-form-item>
          <template #label>
            <el-tooltip effect="dark" content="不考虑节点溢流时，推荐设置为 9999" placement="left">
              <span>超额水深</span>
            </el-tooltip>
          </template>
          <el-input v-model.number="junctionEntity.depthSurcharge" type="number"></el-input>
        </el-form-item>
        <el-form-item>
          <template #label>
            <el-tooltip effect="dark" content="不考虑节点溢流时，推荐设置为 0" placement="left">
              <span>积水面积</span>
            </el-tooltip>
          </template>
          <el-input v-model.number="junctionEntity.areaPonded" type="number"></el-input>
        </el-form-item>
        <el-form-item label="输入流量">
          <el-select
            v-model="junctionEntity.hasInflow"
            type="string"
            placeholder="请选择输入流量的时间序列"
          >
            <el-option
              v-for="item in hasInflowSelect"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            ></el-option
          ></el-select>
        </el-form-item>
        <div v-if="junctionEntity.hasInflow">
          <el-form-item label="流量选择">
            <el-input
              v-model="junctionEntity.timeseriesName"
              type="string"
              class="el-form-length"
            ></el-input>
            <el-button @click="showTimeSeriesDialog = true" class="el-form-length-button"
              >更多</el-button
            >
            <TimeSeriesDialog
              v-if="showTimeSeriesDialog"
              v-model:show-dialog="showTimeSeriesDialog"
              :timeseriesName="junctionEntity.timeseriesName"
              timeseriesType="INFLOW"
            ></TimeSeriesDialog>
          </el-form-item>
        </div>
      </el-form>
      <div class="popup-footer">
        <el-button type="danger" @click="deleteJunctionEntity">删除</el-button>
        <el-button type="primary" @click="saveJunctionEntity">保存</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { CloseBold } from '@element-plus/icons-vue'
import { updateJunctionByIdAxios, deleteJunctionByIdAxios } from '@/apis/junction'
import { convertKeysToKebabCase } from '@/utils/convert'
import { useViewerStore } from '@/stores/viewer'
import { initEntities } from '@/utils/useCesium'
import TimeSeriesDialog from '@/components/TimeSeriesDialog.vue'
import * as Cesium from 'cesium'
import { POINTPREFIX } from '@/utils/constant'

const viewerStore = useViewerStore()

const showDialog = defineModel('showDialog')
const junctionEntity = defineModel('junctionEntity')

const closeDialog = () => {
  showDialog.value = false
  viewerStore.clickedEntityDict = {}
}

const saveJunctionEntity = () => {
  updateJunctionByIdAxios(
    junctionEntity.value.id,
    convertKeysToKebabCase(junctionEntity.value),
  ).then((res) => {
    // 更新 id，解决不关闭弹窗时候，重复保存时，selectedEntity的id还是原来旧id的问题
    const id = POINTPREFIX + res.data.id
    junctionEntity.value.id = id
    // 更新 Cesium 中的实体数据
    initEntities(viewerStore)
    ElMessage.success(res.message)
  })
}

const deleteJunctionEntity = () => {
  deleteJunctionByIdAxios(junctionEntity.value.id)
    .then((res) => {
      // 更新 Cesium 中的实体数据
      initEntities(viewerStore)
      // 删除结束后，关闭弹窗
      showDialog.value = false
      ElMessage.success(res.message)
    })
    .catch((error) => {
      console.log(error)
    })
}

const calculateElevation = async () => {
  const { lon, lat } = junctionEntity.value
  const terrainProvider = viewerStore.viewer.terrainProvider

  const positions = [Cesium.Cartographic.fromDegrees(lon, lat)]

  try {
    const updatedPositions = await Cesium.sampleTerrainMostDetailed(terrainProvider, positions)
    const height = Number(updatedPositions[0].height.toFixed(2))
    // Cesium 默认用的是 WGS84 椭球高度，而平常使用的 DEM 数据则通常是以平均海平面为基准的正交高程
    // 在乐山这个地方，WGS84 椭球高度和正交高程的差值大概是 +44 米
    junctionEntity.value.elevation = height + 44
    ElMessage.success('高程计算成功')
  } catch (error) {
    ElMessage.error(`计算失败，请检查经纬度坐标`)
    console.error('计算高程时发生错误:', error)
  }
}

// 流量选择
const hasInflowSelect = [
  { value: true, label: '有' },
  { value: false, label: '无' },
]
const showTimeSeriesDialog = ref(false)
</script>

<style scoped>
.popup-container {
  position: fixed;
  top: 10px;
  right: 10px;
  z-index: 1000;
  height: 10px;
}

.popup-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 5px;
  font-weight: bold;
  border-bottom: 1px solid #ebeef5;
}
.popup-title {
  font-size: 16px;
}
.popup-form {
  display: flex;
  flex-direction: column;
  padding: 10px 0;
}
.popup-footer {
  display: flex;
  justify-content: flex-end;
  padding-top: 10px;
  border-top: 1px solid #ebeef5;
}

.popup-form .el-form-length {
  --el-input-width: 128px;
}
.popup-form .el-form-length-button {
  margin-left: 10px;
}
</style>
