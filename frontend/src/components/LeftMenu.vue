<template>
  <h5>工具</h5>
  <el-menu background-color="#fefefe">
    <el-menu-item index="1" @click="queryEntityByName">
      <span>查找</span>
    </el-menu-item>
    <el-sub-menu index="2">
      <template #title>
        <span>新增</span>
      </template>

      <el-menu-item
        index="2-1"
        @click="createJunction"
        :disabled="createConduitHandler !== null || createOutfallHandler !== null"
      >
        节点</el-menu-item
      >
      <el-menu-item
        index="2-2"
        @click="selectTwoJunctions"
        :disabled="createJunctionHandler !== null || createOutfallHandler !== null"
        >渠道</el-menu-item
      >

      <el-menu-item
        index="2-3"
        @click="createOutfall"
        :disabled="createJunctionHandler !== null || createConduitHandler !== null"
        >出口</el-menu-item
      >
      <el-menu-item
        index="2-4"
        @click="startDrawingPolygon"
        :disabled="createJunctionHandler !== null || createConduitHandler !== null"
        >子汇水区</el-menu-item
      >
    </el-sub-menu>
    <el-sub-menu index="3">
      <template #title>拖拽</template>
      <el-menu-item index="3-1" @click="startDrag" :disabled="draggable">开始拖拽</el-menu-item>
      <el-menu-item index="3-2" @click="restoreDrag">还原未保存</el-menu-item>
      <el-menu-item index="3-3" @click="stopDrag" :disabled="!draggable">停止拖拽</el-menu-item>
    </el-sub-menu>
    <el-menu-item index="4" @click="showCalculateDialog = true">
      <span>计算</span>
    </el-menu-item>
    <el-menu-item index="5" @click="showAgentChatDialog = !showAgentChatDialog">
      <span>Agent</span>
    </el-menu-item>
  </el-menu>
  <!-- 计算选项和计算结果查看弹窗 -->
  <CalculateDialog
    v-if="showCalculateDialog"
    v-model:show-dialog="showCalculateDialog"
  ></CalculateDialog>

  <AgentChatDialog
    v-if="showAgentChatDialog"
    v-model:show-dialog="showAgentChatDialog"
  ></AgentChatDialog>
</template>

<script setup>
import { useViewerStore } from '@/stores/viewer'
import {
  createJunctionEntity,
  createConduitEntity,
  createOutfallEntity,
  createSubcatchmentEntity,
} from '@/utils/entity'
import { createJunctionAxios } from '@/apis/junction'
import { createConduitAxios } from '@/apis/conduit'
import { createOutfallAxios } from '@/apis/outfall'
import { createSubcatchmentAxios } from '@/apis/subcatchment'
import * as Cesium from 'cesium'
import { ref } from 'vue'
import { getStringAfterFirstDash } from '@/utils/convert'
import { startDragHandlers, stopDragHandlers, initEntities } from '@/utils/useCesium'
import { ElMessage } from 'element-plus'
import CalculateDialog from '@/components/CalculateDialog.vue'
import { findEntityByName, flyToEntity } from '@/utils/entity'
import AgentChatDialog from '@/components/agent/AgentChatDialog.vue'

const viewerStore = useViewerStore()

// 1. 查找事件
const queryEntityByName = async () => {
  await ElMessageBox.prompt('请输入要查找的实体名称', '查找', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    inputPattern: /^(?!\s*$).+/,
    inputErrorMessage: '不能为空',
    beforeClose: (action, instance, done) => {
      if (action === 'confirm') {
        const { entity } = findEntityByName(viewerStore.viewer, instance.inputValue)
        if (!entity) {
          ElMessage.error('未找到实体名为 ' + instance.inputValue)
          return // 阻止关闭
        }
        done()
      } else {
        done()
      }
    },
  })
    .then(({ value }) => {
      const { entity, cartesian, typeMessageName } = findEntityByName(viewerStore.viewer, value)
      if (entity && cartesian) {
        flyToEntity(viewerStore, entity, cartesian)
        ElMessage.success('已找到' + typeMessageName + '：' + value)
      }
    })
    .catch((error) => {
      if (error === 'cancel') {
        ElMessage.info('已取消查找')
      } else {
        console.error('发生错误:', error)
        ElMessage.error('查找发生错误')
      }
    })
}
// 3. 拖拽事件
// 记录拖拽处理器
let dragHandler = null
// 记录可以拖拽
const draggable = ref(false)

// 3.1 开始拖拽
const startDrag = () => {
  if (draggable.value) {
    return
  }
  ElMessage.success('已开启拖拽功能，同时注意手动保存拖拽之后的实体')
  draggable.value = true
  dragHandler = startDragHandlers(viewerStore.viewer)
}

// 3.2 停止拖拽
const stopDrag = () => {
  draggable.value = false
  restoreDrag() // 还原未保存的拖拽
  if (dragHandler) {
    stopDragHandlers(dragHandler)
    dragHandler.destroy()
    dragHandler = null
  } else {
    console.error('没有拖拽处理器')
  }
  ElMessage.warning('已停止拖拽功能')
}

// 3.3 还原未保存拖拽
const restoreDrag = () => {
  initEntities(viewerStore.viewer)
}

// 2. 新增事件
// 2.1 创建节点
const createJunctionHandler = ref(null)
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
    createJunctionAxios({ name, lon, lat, elevation }).then((res) => {
      ElMessage.success(res.message)
      // 前端创建节点实体
      createJunctionEntity(viewer, name, lon, lat, elevation)
    })

    // 移除监听器，防止继续添加
    createJunctionHandler.value.removeInputAction(Cesium.ScreenSpaceEventType.LEFT_CLICK)
    // 销毁 handler，防止继续监听
    createJunctionHandler.value.destroy()
    createJunctionHandler.value = null
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK)
}

// 2.3 创建出口
const createOutfallHandler = ref(null)
const createOutfall = () => {
  // 如果已经有 handler，说明已经在创建出口了
  if (createOutfallHandler.value) {
    ElMessage.warning('已取消出口创建')
    createOutfallHandler.value.removeInputAction(Cesium.ScreenSpaceEventType.LEFT_CLICK)
    createOutfallHandler.value.destroy()
    createOutfallHandler.value = null
    return
  } else {
    ElMessage.success('请点击地图选择出口位置')
  }
  const viewer = viewerStore.viewer
  // 创建点击事件监听器
  createOutfallHandler.value = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas)
  createOutfallHandler.value.setInputAction((click) => {
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
    // 创建出口实体
    const name = '出口_' + Date.now() // 用时间戳作为出口名称
    createOutfallAxios({ name, lon, lat, elevation }).then((res) => {
      ElMessage.success(res.message)
      // 前端创建出口实体
      createOutfallEntity(viewer, name, lon, lat, elevation)
    })

    // 移除监听器，防止继续添加
    createOutfallHandler.value.removeInputAction(Cesium.ScreenSpaceEventType.LEFT_CLICK)
    // 销毁 handler，防止继续监听
    createOutfallHandler.value.destroy()
    createOutfallHandler.value = null
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK)
}

// 2.2. 创建渠道 - 选择两个节点（仅获取 ID）
const createConduitHandler = ref(null)
let selectedNodes = []

const selectTwoJunctions = () => {
  if (createConduitHandler.value) {
    ElMessage.warning('已取消渠道创建')
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
      ElMessage.warning(`已选中一个节点，请继续选择第二个节点`)
    }

    // 选中两个后停止监听
    if (selectedNodes.length === 2) {
      // 处理选中的两个点，例如创建渠道
      const name = '渠道_' + Date.now() // 用时间戳作为节点名称
      const fromNode = getStringAfterFirstDash(selectedNodes[0])
      const toNode = getStringAfterFirstDash(selectedNodes[1])
      createConduitAxios({ name, from_node: fromNode, to_node: toNode }).then((res) => {
        ElMessage.success(res.message)
        createConduitEntity(viewer, name, fromNode, toNode) // 前端创建渠道实体
      })

      // 移除监听
      createConduitHandler.value.removeInputAction(Cesium.ScreenSpaceEventType.LEFT_CLICK)
      createConduitHandler.value.destroy()
      createConduitHandler.value = null
      selectedNodes = [] // 重置已选节点
    }
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK)
}

// 2.4 创建子汇水区
let drawing = false
let positions = []
let tempMousePos = null
let handler = null
let tempLine = null
let polygonEntity = null

const startDrawingPolygon = () => {
  ElMessage.success('请在地图上依次点击子汇水区顶点，右键完成绘制')
  drawing = true
  positions = []
  tempMousePos = null

  const viewer = viewerStore.viewer
  const scene = viewer.scene
  const canvas = scene.canvas

  handler = new Cesium.ScreenSpaceEventHandler(canvas)

  // 添加 polygon 实体（始终存在，只是动态更新点）
  polygonEntity = viewer.entities.add({
    polygon: {
      hierarchy: new Cesium.CallbackProperty(() => {
        if (positions.length < 2 || !tempMousePos) return null
        return new Cesium.PolygonHierarchy([...positions, tempMousePos])
      }, false),
      material: Cesium.Color.LIGHTSKYBLUE.withAlpha(0.4),
    },
  })

  // 左键点击添加点
  handler.setInputAction((click) => {
    const cartesian = viewer.scene.pickPosition(click.position)
    if (!cartesian) return
    positions.push(cartesian)

    // 添加红点标记
    // viewer.entities.add({
    //   position: cartesian,
    //   point: {
    //     pixelSize: 1,
    //     color: Cesium.Color.RED,
    //     heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
    //   },
    // })
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK)

  // 鼠标移动，更新临时线 & 多边形边缘
  handler.setInputAction((movement) => {
    if (!drawing || positions.length < 1) return

    const currentPos = viewer.scene.pickPosition(movement.endPosition)
    if (!currentPos) return
    tempMousePos = currentPos

    // 动态连线
    if (!tempLine) {
      tempLine = viewer.entities.add({
        polyline: {
          positions: new Cesium.CallbackProperty(() => {
            return [...positions, tempMousePos]
          }, false),
          width: 2,
          material: Cesium.Color.YELLOW,
          clampToGround: true,
        },
      })
    }
  }, Cesium.ScreenSpaceEventType.MOUSE_MOVE)

  // 右键点击完成
  handler.setInputAction(() => {
    if (positions.length < 3) {
      ElMessage.warning('至少需要三个点来绘制多边形')
      return
    }

    // 最终闭合 polygon（不再使用鼠标位置）
    polygonEntity.polygon.hierarchy = new Cesium.PolygonHierarchy(positions)
    // 转换为经纬度
    const ellipsoid = Cesium.Ellipsoid.WGS84
    const polygon = positions.map((pos) => {
      const cartographic = ellipsoid.cartesianToCartographic(pos)
      return [
        Cesium.Math.toDegrees(cartographic.longitude),
        Cesium.Math.toDegrees(cartographic.latitude),
      ]
    })
    const subcatchment = '子汇水区_' + Date.now() // 用时间戳作为出口名称
    createSubcatchmentAxios({ subcatchment, polygon }).then((res) => {
      ElMessage.success(res.message)
      const data = res.data
      createSubcatchmentEntity(
        viewer,
        data.name,
        data.rain_gage,
        data.outlet,
        data.area,
        data.imperviousness,
        data.width,
        data.slope,
        polygon,
      )
    })

    clearDrawing()
  }, Cesium.ScreenSpaceEventType.RIGHT_CLICK)
}

// 可复用清理函数
const clearDrawing = () => {
  drawing = false
  tempMousePos = null

  if (handler) {
    handler.destroy()
    handler = null
  }

  if (tempLine) {
    viewerStore.viewer.entities.remove(tempLine)
    tempLine = null
  }
  if (polygonEntity) {
    viewerStore.viewer.entities.remove(polygonEntity)
    polygonEntity = null
  }
}

// 4. 计算事件
const showCalculateDialog = ref(false)

// 5. Agent 聊天事件
const showAgentChatDialog = ref(false)
</script>
