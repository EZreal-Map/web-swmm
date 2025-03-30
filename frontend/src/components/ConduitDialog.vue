<template>
  <div v-if="showDialog" class="popup-container">
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
          <el-input v-model="conduitEntity.length" type="number"></el-input>
        </el-form-item>
        <el-form-item label="断面形状">
          <el-select v-model="conduitEntity.shape" type="string">
            <el-option
              v-for="item in CrossSectionShape"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            ></el-option
          ></el-select>
        </el-form-item>
        <div v-if="conduitEntity.shape === 'TRAPEZOIDAL'">
          <el-form-item label="最大高度">
            <el-input v-model="conduitEntity.height" type="number"></el-input>
          </el-form-item>
          <el-form-item label="底宽">
            <el-input v-model="conduitEntity.parameter_2" type="number"></el-input>
          </el-form-item>
          <el-form-item label="左侧边坡">
            <el-input v-model="conduitEntity.parameter_3" type="number"></el-input>
          </el-form-item>
          <el-form-item label="右侧边坡">
            <el-input v-model="conduitEntity.parameter_4" type="number"></el-input>
          </el-form-item>
        </div>
        <div v-else>
          <!-- TODO 不规则断面的弹窗 -->
          <el-form-item label="待完成...">
            <el-input v-model="conduitEntity.roughness" type="number"></el-input>
          </el-form-item>
        </div>
      </el-form>
      <div class="popup-footer">
        <!-- TODO 删除功能 -->
        <el-button type="danger" @click="deleteConduitEntity">删除</el-button>
        <el-button type="primary" @click="saveConduitEntity">保存</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { CloseBold } from '@element-plus/icons-vue'
import { convertKeysToKebabCase } from '@/utils/convert'
import { updateConduitByIdAxios, deleteConduitByIdAxios } from '@/apis/conduit'
import { useViewerStore } from '@/stores/viewer'

const viewerStore = useViewerStore()

const showDialog = defineModel('showDialog')
const conduitEntity = defineModel('conduitEntity')

import { ref } from 'vue'

const CrossSectionShape = ref([
  { value: 'TRAPEZOIDAL', label: '梯形断面' },
  { value: 'IRREGULAR', label: '不规则断面' },
])

const closeDialog = () => {
  showDialog.value = false
}

const saveConduitEntity = () => {
  updateConduitByIdAxios(conduitEntity.value.id, convertKeysToKebabCase(conduitEntity.value))
    .then((res) => {
      console.log(res)
      ElMessage.success(res.message)
      // 更新 Cesium 中的实体数据
      viewerStore.viewer.entities.removeAll()
      viewerStore.initData(viewerStore.viewer)
      // 更新 id，解决不关闭弹窗时候，重复保存时，selectedEntity的id还是原来旧id的问题
      conduitEntity.value.id = '#' + conduitEntity.value.name
    })
    .catch((error) => {
      console.log(error)
    })
}

const deleteConduitEntity = () => {
  // TODO 删除功能
  deleteConduitByIdAxios(conduitEntity.value.id)
    .then((res) => {
      ElMessage.success(res.message)
      // 更新 Cesium 中的实体数据
      viewerStore.viewer.entities.removeAll()
      viewerStore.initData(viewerStore.viewer)
      // 删除结束后，关闭弹窗
      showDialog.value = false
    })
    .catch((error) => {
      console.log(error)
    })
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
</style>
