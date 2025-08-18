<template>
  <div class="popup-container" v-show="!viewerStore.extractFlag">
    <el-card class="popup-card">
      <div class="popup-header">
        <span class="popup-title">渠道 信息详情</span>
        <el-icon @click="closeDialog"><CloseBold /></el-icon>
      </div>

      <el-form
        label-position="left"
        class="popup-form"
        label-width="70px"
        style="max-width: 268px"
        :size="'default'"
        v-model="conduitEntity"
      >
        <el-form-item label="名字">
          <el-input v-model="conduitEntity.name" type="string"></el-input>
        </el-form-item>
        <el-form-item label="进水节点">
          <el-input v-model="conduitEntity.fromNode" type="string"></el-input>
        </el-form-item>
        <el-form-item label="出水节点">
          <el-input v-model="conduitEntity.toNode" type="string"></el-input>
        </el-form-item>
        <el-form-item label="长度">
          <el-input v-model.number="conduitEntity.length" type="number" class="el-form-length">
          </el-input>
          <el-button @click="calculateLength" class="el-form-length-button">计算</el-button>
        </el-form-item>
        <el-form-item label="粗糙度">
          <el-input
            v-model="conduitEntity.roughness"
            type="number"
            @blur="conduitEntity.roughness = parseFloat(conduitEntity.roughness)"
          ></el-input>
        </el-form-item>
        <el-form-item label="断面形状">
          <el-select v-model="conduitEntity.shape" type="string" placeholder="请选择断面形状">
            <el-option
              v-for="item in CrossSectionShapeSelect"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            ></el-option
          ></el-select>
        </el-form-item>
        <div v-if="conduitEntity.shape !== 'IRREGULAR'">
          <el-form-item label="断面高度">
            <el-input v-model.number="conduitEntity.height" type="number"></el-input>
          </el-form-item>
        </div>
        <div v-if="conduitEntity.shape === 'TRAPEZOIDAL'">
          <el-form-item label="断面底宽">
            <el-input v-model.number="conduitEntity.parameter_2" type="number"></el-input>
          </el-form-item>
          <el-form-item label="左侧边坡">
            <el-input v-model.number="conduitEntity.parameter_3" type="number"></el-input>
          </el-form-item>
          <el-form-item label="右侧边坡">
            <el-input v-model.number="conduitEntity.parameter_4" type="number"></el-input>
          </el-form-item>
        </div>
        <div v-if="conduitEntity.shape === 'IRREGULAR'">
          <el-form-item label="断面选择">
            <el-input
              v-model="conduitEntity.transect"
              type="string"
              class="el-form-length"
            ></el-input>
            <el-button @click="showXsectionDialog = true" class="el-form-length-button"
              >更多</el-button
            >
          </el-form-item>
        </div>
      </el-form>
      <div class="popup-footer">
        <el-button type="danger" @click="deleteConduitEntity">删除</el-button>
        <el-button type="primary" @click="saveConduitEntity">保存</el-button>
      </div>
    </el-card>
    <TransectDialog
      v-if="showXsectionDialog"
      v-model:show-dialog="showXsectionDialog"
      :transectName="conduitEntity.transect"
    ></TransectDialog>
  </div>
</template>

<script setup>
import { CloseBold } from '@element-plus/icons-vue'
import { convertKeysToKebabCase } from '@/utils/convert'
import { updateConduitByIdAxios, deleteConduitByIdAxios } from '@/apis/conduit'
import { useViewerStore } from '@/stores/viewer'
import { initEntities } from '@/utils/useCesium'
import * as Cesium from 'cesium'
import TransectDialog from '@/components/TransectDialog.vue'
import { POINTPREFIX, POLYLINEPREFIX } from '@/utils/constant'
import { ref } from 'vue'

const viewerStore = useViewerStore()

const showDialog = defineModel('showDialog')
const conduitEntity = defineModel('conduitEntity')

const CrossSectionShapeSelect = [
  { value: 'CIRCULAR', label: '圆形断面' },
  { value: 'TRAPEZOIDAL', label: '梯形断面' },
  { value: 'IRREGULAR', label: '不规则断面' },
]

const closeDialog = () => {
  showDialog.value = false
  viewerStore.clickedEntityDict = {}
}

const saveConduitEntity = () => {
  updateConduitByIdAxios(conduitEntity.value.id, convertKeysToKebabCase(conduitEntity.value))
    .then((res) => {
      ElMessage.success(res.message)
      // 更新 Cesium 中的实体数据
      initEntities(viewerStore)
      const id = POLYLINEPREFIX + res.data.id
      // 更新 id，解决不关闭弹窗时候，重复保存时，selectedEntity的id还是原来旧id的问题
      conduitEntity.value.id = id
    })
    .catch((error) => {
      console.log(error)
    })
}

const deleteConduitEntity = () => {
  deleteConduitByIdAxios(conduitEntity.value.id)
    .then((res) => {
      ElMessage.success(res.message)
      // 更新 Cesium 中的实体数据
      initEntities(viewerStore)
      // 删除结束后，关闭弹窗
      showDialog.value = false
    })
    .catch((error) => {
      console.log(error)
    })
}

// 计算长度的函数
const calculateLength = () => {
  // 获取渠道的起点和终点坐标
  const fromNodePostion = viewerStore.viewer.entities
    .getById(POINTPREFIX + conduitEntity.value.fromNode)
    ?.position.getValue()
  if (!fromNodePostion) {
    ElMessage.error(`计算失败，${conduitEntity.value.fromNode} 坐标获取失败`)
    return
  }
  const toNodePostion = viewerStore.viewer.entities
    .getById(POINTPREFIX + conduitEntity.value.toNode)
    ?.position.getValue()
  if (!toNodePostion) {
    ElMessage.error(`计算失败，${conduitEntity.value.toNode} 坐标获取失败`)
    return
  }
  // 计算两点的直线距离
  const distance = Cesium.Cartesian3.distance(fromNodePostion, toNodePostion)
  // 节点保留2位小数
  conduitEntity.value.length = Number(distance.toFixed(2))
  ElMessage.success('长度计算成功')
}

const showXsectionDialog = ref(false)
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
