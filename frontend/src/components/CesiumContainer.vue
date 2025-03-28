<template>
  <div id="cesiumContainer"></div>
</template>

<script setup>
import * as Cesium from 'cesium'
import { onMounted } from 'vue'
// import { ElMessage } from 'element-plus'
import { getAllNodeCoordinatesAxios } from '@/apis/coordinate'
import { getAllConduitsAxios } from '@/apis/conduit'

onMounted(async () => {
  Cesium.Ion.defaultAccessToken =
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJlODBjMmY1YS00NjZjLTQwZjUtYTVhNy05NDBiODliYWYwMzUiLCJpZCI6MTU1ODM0LCJpYXQiOjE2OTAwOTA4MTN9.s-rWLcdw5_e2j9Fz2l41ydsl23lAVJg2Q3XhThRUeRM'
  const viewer = new Cesium.Viewer('cesiumContainer', {
    geocoder: false, //隐藏查找控件
    homeButton: false, //隐藏视角返回初始位置按钮
    sceneModePicker: false, //隐藏视角模式3D 2D CV
    baseLayerPicker: false, //隐藏图层选择
    navigationHelpButton: false, //隐藏帮助
    animation: false, //隐藏动画控件
    timeline: false, //隐藏时间线控件
    fullscreenButton: false, //隐藏全屏
    terrainProvider: await Cesium.CesiumTerrainProvider.fromIonAssetId(2248627),
  })

  // 调整全局光源
  viewer.scene.light = new Cesium.DirectionalLight({
    color: new Cesium.Color(1.0, 1.0, 1.0, 1),
    direction: new Cesium.Cartesian3(0, -1, 1), // 将方向修改为斜向建筑物
    intensity: 10,
  })
  // 开始时设置相机位置
  viewer.camera.setView({
    destination: Cesium.Cartesian3.fromDegrees(103.76472222222222, 29.552777777777777, 27000),
    orientation: {
      heading: Cesium.Math.toRadians(0),
      pitch: Cesium.Math.toRadians(-90),
      roll: Cesium.Math.toRadians(0),
    },
  })

  // 清除默认鼠标左键点击事件
  viewer.screenSpaceEventHandler.removeInputAction(Cesium.ScreenSpaceEventType.LEFT_CLICK)
  viewer.screenSpaceEventHandler.removeInputAction(Cesium.ScreenSpaceEventType.LEFT_DOUBLE_CLICK)

  let selectedEntity = null // 当前被拖动的实体
  let isDragging = false // 是否正在拖动
  const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas)

  // 按下鼠标：选中可拖拽的点
  handler.setInputAction((movement) => {
    const pickedObject = viewer.scene.pick(movement.position)
    if (Cesium.defined(pickedObject) && pickedObject.id && pickedObject.id.point) {
      selectedEntity = pickedObject.id
      isDragging = true
      viewer.scene.screenSpaceCameraController.enableRotate = false // 禁止旋转地图
    }
  }, Cesium.ScreenSpaceEventType.LEFT_DOWN)

  // 拖动鼠标：更新点的位置
  handler.setInputAction((movement) => {
    if (isDragging && selectedEntity) {
      const ray = viewer.camera.getPickRay(movement.endPosition)
      const cartesian = viewer.scene.globe.pick(ray, viewer.scene)
      if (cartesian) {
        selectedEntity.position = cartesian
      }
    }
  }, Cesium.ScreenSpaceEventType.MOUSE_MOVE)

  // 释放鼠标：停止拖拽
  handler.setInputAction(() => {
    isDragging = false
    selectedEntity = null
    viewer.scene.screenSpaceCameraController.enableRotate = true // 允许旋转地图
  }, Cesium.ScreenSpaceEventType.LEFT_UP)

  // 记录所有节点实体
  let nodeEntities = []
  // 节点初始化
  const nodesInit = async () => {
    const nodeCoordinateDatas = await getAllNodeCoordinatesAxios()
    nodeCoordinateDatas.forEach((nodeCoordinate) => {
      const node = viewer.entities.add({
        id: nodeCoordinate.node,
        name: nodeCoordinate.node,
        position: Cesium.Cartesian3.fromDegrees(nodeCoordinate.x, nodeCoordinate.y, 0), // 经度, 纬度, 高度
        point: {
          color: Cesium.Color.YELLOW,
          pixelSize: 10,
          outlineColor: Cesium.Color.WHITE,
          outlineWidth: 2,
        },
      })

      nodeEntities.push(node)
    })
  }

  let conduitEntities = []
  // 管道初始化
  const conduitsInit = async () => {
    const conduitDatas = await getAllConduitsAxios()
    conduitDatas.forEach((conduitData) => {
      const fromNode = viewer.entities.getById(conduitData.from_node)
      const toNode = viewer.entities.getById(conduitData.to_node)

      if (fromNode && toNode) {
        const conduit = viewer.entities.add({
          id: conduitData.name,
          name: conduitData.name,
          polyline: {
            positions: new Cesium.CallbackProperty(() => {
              // 再次获取节点，防止节点被删除
              const fromNodeUpdated = viewer.entities.getById(conduitData.from_node)
              const toNodeUpdated = viewer.entities.getById(conduitData.to_node)

              if (!fromNodeUpdated || !toNodeUpdated) {
                return [] // 返回空数组，Cesium 会自动移除线
              }

              const fromPosition = fromNodeUpdated.position.getValue(Cesium.JulianDate.now())
              const toPosition = toNodeUpdated.position.getValue(Cesium.JulianDate.now())

              return [fromPosition, toPosition]
            }, false), // false 表示不会每一帧都强制更新，节省性能
            width: 10,
            material: Cesium.Color.BLUE.withAlpha(0.5),
          },
          properties: {
            length: conduitData.length,
            roughness: conduitData.roughness,
          },
        })
        conduitEntities.push(conduit)
      }
    })
  }
  // 初始化顺序控制
  const init = async () => {
    await nodesInit() // 先加载节点
    await conduitsInit() // 再加载管道
    viewer.zoomTo(viewer.entities)
  }
  init()
})
</script>

<style>
#cesiumContainer {
  width: 100%;
  height: 100%;
  padding: 0;
  margin: 0;
  overflow: hidden;
}

.cesium-widget-credits {
  display: none !important;
}
</style>
