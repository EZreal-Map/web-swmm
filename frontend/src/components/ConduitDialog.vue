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
        <el-form-item label="曼宁系数">
          <el-input v-model="conduitEntity.roughness" type="number"></el-input>
        </el-form-item>
      </el-form>
      <div class="popup-footer">
        <el-button type="primary" @click="saveConduitEntity">保存</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { CloseBold } from '@element-plus/icons-vue'
import { convertKeysToKebabCase } from '@/utils/convert'
import { updateConduitByIdAxios } from '@/apis/conduit'
import { useViewerStore } from '@/stores/viewer'

const viewerStore = useViewerStore()

const showDialog = defineModel('showDialog')
const conduitEntity = defineModel('conduitEntity')

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
