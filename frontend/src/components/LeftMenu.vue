<template>
  <h5 class="mb-2">工具</h5>
  <el-menu background-color="#fefefe">
    <el-sub-menu index="1">
      <template #title>
        <span>显示</span>
      </template>

      <el-menu-item index="1-1">item one</el-menu-item>
      <el-menu-item index="1-2">item two</el-menu-item>

      <el-menu-item index="1-3">item three</el-menu-item>

      <el-sub-menu index="1-4">
        <template #title>item four</template>
        <el-menu-item index="1-4-1">item one</el-menu-item>
      </el-sub-menu>
    </el-sub-menu>
    <el-sub-menu index="2-1">
      <template #title>拖拽</template>
      <el-menu-item index="2-2-1" @click="startDrag" :disabled="draggable">开始拖拽</el-menu-item>
      <el-menu-item index="2-2-2" @click="restoreDrag">还原未保存</el-menu-item>
      <el-menu-item index="2-2-3" @click="stopDrag" :disabled="!draggable">停止拖拽</el-menu-item>
    </el-sub-menu>
    <el-sub-menu index="2">
      <template #title>
        <span>编辑</span>
      </template>

      <el-menu-item index="2-2">item two</el-menu-item>

      <el-menu-item index="2-3">item three</el-menu-item>

      <el-sub-menu index="2-4">
        <template #title>item four</template>
        <el-menu-item index="2-4-1">item one</el-menu-item>
      </el-sub-menu>
    </el-sub-menu>
    <el-menu-item index="3">
      <span>增加</span>
    </el-menu-item>
  </el-menu>
</template>

<script setup>
import { useViewerStore } from '@/stores/viewer'
import { ref } from 'vue'

const viewerStore = useViewerStore()

let handler = null
// 记录可以拖拽
const draggable = ref(false)

const startDrag = () => {
  if (draggable.value) {
    return
  }
  draggable.value = true
  handler = viewerStore.startDragHandlers(viewerStore.viewer)
}

const stopDrag = () => {
  draggable.value = false
  if (handler) {
    viewerStore.stopDragHandlers(handler)
    handler.destroy()
    handler = null
  } else {
    console.error('没有拖拽处理器')
  }
}

// 还原未保存拖拽
const restoreDrag = () => {
  viewerStore.viewer.entities.removeAll()
  viewerStore.initData(viewerStore.viewer)
}
</script>
