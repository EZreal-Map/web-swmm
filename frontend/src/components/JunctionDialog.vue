<template>
  <div class="popup-container">
    <el-card class="popup-card">
      <div class="popup-header">
        <span class="popup-title">信息详情</span>
        <el-icon @click="closeDialog"><CloseBold /></el-icon>
      </div>

      <el-form
        label-position="left"
        class="popup-form"
        label-width="70px"
        style="max-width: 300px"
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
        <el-form-item label="最大水深">
          <el-input v-model.number="junctionEntity.depthMax" type="number"></el-input>
        </el-form-item>
        <el-form-item label="初始水深">
          <el-input v-model.number="junctionEntity.depthInit" type="number"></el-input>
        </el-form-item>
        <el-form-item label="超额水深">
          <el-input v-model.number="junctionEntity.depthSurcharge" type="number"></el-input>
        </el-form-item>
        <el-form-item label="积水面积">
          <el-input v-model.number="junctionEntity.areaPonded" type="number"></el-input>
        </el-form-item>
      </el-form>
      <div class="popup-footer">
        <el-button type="danger" @click="deleteJunctionEntity">删除</el-button>
        <el-button type="primary" @click="saveJunctionEntity">保存</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { CloseBold } from '@element-plus/icons-vue'
import { updateJunctionByIdAxios, deleteJunctionByIdAxios } from '@/apis/junction'
import { convertKeysToKebabCase } from '@/utils/convert'
import { useViewerStore } from '@/stores/viewer'
import { initEntities } from '@/utils/useCesium'
import * as Cesium from 'cesium'

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
    const id = res.data.type + '#' + res.data.id
    junctionEntity.value.id = id
    // 更新 Cesium 中的实体数据
    initEntities(viewerStore.viewer)
    ElMessage.success(res.message)
  })
}

const deleteJunctionEntity = () => {
  deleteJunctionByIdAxios(junctionEntity.value.id)
    .then((res) => {
      // 更新 Cesium 中的实体数据
      initEntities(viewerStore.viewer)
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
    junctionEntity.value.elevation = height
    ElMessage.success('高程计算成功')
  } catch (error) {
    ElMessage.error(`计算失败，请检查经纬度坐标`)
    console.error('计算高程时发生错误:', error)
  }
}
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
