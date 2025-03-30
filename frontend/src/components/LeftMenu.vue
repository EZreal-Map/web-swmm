<template>
  <h5 class="mb-2">工具</h5>
  <el-menu background-color="#fefefe">
    <el-sub-menu index="1">
      <template #title>
        <span>新增</span>
      </template>

      <el-menu-item index="1-1" @click="createJunction" :disabled="createConduitHandler !== null"
        >节点</el-menu-item
      >
      <el-menu-item
        index="1-2"
        @click="selectTwoJunctions"
        :disabled="createJunctionHandler !== null"
        >管道</el-menu-item
      >

      <el-menu-item index="1-3">出口</el-menu-item>
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
import { createJunctionEntity, createConduitEntity } from '@/utils/entity'
import { createJunctionAxios } from '@/apis/junction'
import { createConduitAxios } from '@/apis/conduit'
import * as Cesium from 'cesium'
import { ref } from 'vue'
import { getStringAfterFirstDash } from '@/utils/convert'

const viewerStore = useViewerStore()

// 2. 拖拽事件
// 记录拖拽处理器
let dragHandler = null
// 记录可以拖拽
const draggable = ref(false)

// 2.1 开始拖拽
const startDrag = () => {
  if (draggable.value) {
    return
  }
  draggable.value = true
  dragHandler = viewerStore.startDragHandlers(viewerStore.viewer)
}

// 2.2 停止拖拽
const stopDrag = () => {
  draggable.value = false
  if (dragHandler) {
    viewerStore.stopDragHandlers(dragHandler)
    dragHandler.destroy()
    dragHandler = null
  } else {
    console.error('没有拖拽处理器')
  }
}

// 2.3 还原未保存拖拽
const restoreDrag = () => {
  viewerStore.viewer.entities.removeAll()
  viewerStore.initData(viewerStore.viewer)
}

// 1. 新增事件
const createJunctionHandler = ref(null)
// 1.1 创建节点
const createJunction = () => {
  // 如果已经有 handler，说明已经在创建节点了
  if (createJunctionHandler.value) {
    ElMessage.warning('已取消节点创建')
    createJunctionHandler.value.removeInputAction(Cesium.ScreenSpaceEventType.LEFT_CLICK)
    createJunctionHandler.value.destroy()
    createJunctionHandler.value = null
    return
  } else {
    ElMessage.success('请点击地图选择节点位置')
  }
  const viewer = viewerStore.viewer
  // 创建点击事件监听器
  createJunctionHandler.value = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas)
  createJunctionHandler.value.setInputAction((click) => {
    // 获取点击的坐标
    const cartesian = viewer.scene.pickPosition(click.position)
    if (!cartesian) {
      console.log('未能拾取坐标')
      return
    }

    // 将 Cartesian3 转换为 Cartographic（弧度单位）
    const cartographic = Cesium.Cartographic.fromCartesian(cartesian)
    // 转换为度数
    const lon = Cesium.Math.toDegrees(cartographic.longitude)
    const lat = Cesium.Math.toDegrees(cartographic.latitude)
    const elevation = cartographic.height
    // 创建节点实体
    const name = '节点_' + Date.now() // 用时间戳作为节点名称

    // TODO: 要完成后端的节点添加
    createJunctionAxios({ name, lon, lat, elevation })
      .then((res) => {
        ElMessage.success(res.message)
        // 前端创建节点实体
        createJunctionEntity(viewer, name, lon, lat, elevation)
      })
      .catch((err) => {
        // TODO: 重新更新地图 调用 initData
        ElMessage.error(err.message)
      })

    // 移除监听器，防止继续添加
    createJunctionHandler.value.removeInputAction(Cesium.ScreenSpaceEventType.LEFT_CLICK)
    // 销毁 handler，防止继续监听
    createJunctionHandler.value.destroy()
    createJunctionHandler.value = null
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK)
}

// 2. 选择两个节点（仅获取 ID）
const createConduitHandler = ref(null)
let selectedNodes = []

const selectTwoJunctions = () => {
  if (createConduitHandler.value) {
    ElMessage.warning('已取消管道创建')
    createConduitHandler.value.removeInputAction(Cesium.ScreenSpaceEventType.LEFT_CLICK)
    createConduitHandler.value.destroy()
    createConduitHandler.value = null
    selectedNodes = [] // 重置已选节点
    return
  } else {
    ElMessage.success('请点击地图选择两个节点')
  }
  const viewer = viewerStore.viewer

  createConduitHandler.value = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas)

  createConduitHandler.value.setInputAction((click) => {
    const pickedObject = viewer.scene.pick(click.position)

    if (!pickedObject || !pickedObject.id || !pickedObject.id.point) {
      ElMessage.warning('请选择有效的点实体')
      return
    }

    const entity = pickedObject.id

    // 记录选中的节点 ID
    selectedNodes.push(entity.id)

    // 提示已选中
    if (selectedNodes.length === 1) {
      ElMessage.success(`已选中一个节点，请继续选择第二个节点`)
    }

    // 选中两个后停止监听
    if (selectedNodes.length === 2) {
      // 处理选中的两个点，例如创建管道
      // TODO: 调用后端接口创建管道
      const name = '管道_' + Date.now() // 用时间戳作为节点名称
      const fromNode = getStringAfterFirstDash(selectedNodes[0])
      const toNode = getStringAfterFirstDash(selectedNodes[1])
      createConduitAxios({ name, from_node: fromNode, to_node: toNode })
        .then((res) => {
          ElMessage.success(res.message)
          createConduitEntity(viewer, name, fromNode, toNode) // 前端创建管道实体
        })
        .catch((err) => {
          ElMessage.error(err.message)
        })
      // 移除监听
      createConduitHandler.value.removeInputAction(Cesium.ScreenSpaceEventType.LEFT_CLICK)
      createConduitHandler.value.destroy()
      createConduitHandler.value = null
      selectedNodes = [] // 重置已选节点
    }
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK)
}
</script>
