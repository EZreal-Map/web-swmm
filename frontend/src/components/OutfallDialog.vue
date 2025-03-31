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
        v-model="outfallEntity"
      >
        <el-form-item label="名字">
          <el-input v-model="outfallEntity.name" type="string"></el-input>
        </el-form-item>
        <el-form-item label="经度">
          <el-input v-model="outfallEntity.lon" type="number"></el-input>
        </el-form-item>
        <el-form-item label="纬度">
          <el-input v-model="outfallEntity.lat" type="number"></el-input>
        </el-form-item>
        <el-form-item label="高度">
          <el-input v-model="outfallEntity.elevation" type="number"></el-input>
        </el-form-item>
        <el-form-item label="出口类型">
          <el-select v-model="outfallEntity.kind" type="string">
            <el-option
              v-for="item in OutfallKind"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            ></el-option
          ></el-select>
        </el-form-item>

        <el-form-item label="出口水位" v-if="outfallEntity.kind === 'FIXED'">
          <el-input v-model="outfallEntity.data" type="number"></el-input>
        </el-form-item>
      </el-form>
      <div class="popup-footer">
        <el-button type="danger" @click="deleteOutfallEntity">删除</el-button>
        <el-button type="primary" @click="saveOutfallEntity">保存</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { CloseBold } from '@element-plus/icons-vue'
import { updateOutfallByIdAxios, deleteOutfallByIdAxios } from '@/apis/outfall'
import { convertKeysToKebabCase } from '@/utils/convert'
import { useViewerStore } from '@/stores/viewer'
import { initEntities } from '@/utils/useCesium'

import { ref } from 'vue'

const OutfallKind = ref([
  { value: 'FREE', label: '自由出流' },
  { value: 'NORMAL', label: '正常水力控制' },
  { value: 'FIXED', label: '固定水位' },
])

const viewerStore = useViewerStore()

const showDialog = defineModel('showDialog')
const outfallEntity = defineModel('outfallEntity')

const closeDialog = () => {
  showDialog.value = false
  viewerStore.clickedEntityDict = {}
}

const saveOutfallEntity = () => {
  updateOutfallByIdAxios(outfallEntity.value.id, convertKeysToKebabCase(outfallEntity.value)).then(
    (res) => {
      ElMessage.success(res.message)
      // 更新 Cesium 中的实体数据
      viewerStore.viewer.entities.removeAll()
      initEntities(viewerStore.viewer)
      // 更新 id，解决不关闭弹窗时候，重复保存时，selectedEntity的id还是原来旧id的问题
      const id = res.data.type + '#' + res.data.id
      outfallEntity.value.id = id
      // 解决保存后，窗口任然没关闭，继续保持实体高亮
      viewerStore.clickedEntityDict = { id: id, type: res.data.type }
    },
  )
}

const deleteOutfallEntity = () => {
  deleteOutfallByIdAxios(outfallEntity.value.id)
    .then((res) => {
      ElMessage.success(res.message)
      // 更新 Cesium 中的实体数据
      viewerStore.viewer.entities.removeAll()
      initEntities(viewerStore.viewer)
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
