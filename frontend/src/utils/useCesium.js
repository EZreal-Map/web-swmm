import * as Cesium from 'cesium'
import { useViewerStore } from '@/stores/viewer'
import { getAllJunctionsAxios } from '@/apis/junction'
import { getAllConduitsAxios } from '@/apis/conduit'
import { createJunctionEntity, createConduitEntity } from '@/utils/entity'
import { ref } from 'vue'

const useCesium = () => {
  let viewer = null
  const clickedEntity = ref(null)

  const initViewer = async (containerId) => {
    Cesium.Ion.defaultAccessToken =
      'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJkNjQ5ODdiMy02NTIxLTQ2YWYtODJkNC0yYmIzMDdhNTRjYTkiLCJpZCI6MTU1ODM0LCJpYXQiOjE2OTMyNzIwNDh9.7oNx5xlOUJNC9qfJJ_csPvDWFXqmqFce-gxF2qFu-18'
    viewer = new Cesium.Viewer(containerId, {
      geocoder: false, //隐藏查找控件
      homeButton: false, //隐藏视角返回初始位置按钮
      sceneModePicker: false, //隐藏视角模式3D 2D CV
      baseLayerPicker: false, //隐藏图层选择
      navigationHelpButton: false, //隐藏帮助
      animation: false, //隐藏动画控件
      timeline: false, //隐藏时间线控件
      fullscreenButton: false, //隐藏全屏
      terrainProvider: Cesium.CesiumTerrainProvider.fromIonAssetId(3263550),
    })
    // 调整全局光源
    viewer.scene.light = new Cesium.DirectionalLight({
      color: new Cesium.Color(1.0, 1.0, 1.0, 1),
      direction: new Cesium.Cartesian3(0, -1, 1), // 将方向修改为斜向建筑物
      intensity: 10,
    })

    viewer.scene.setTerrain(
      new Cesium.Terrain(Cesium.CesiumTerrainProvider.fromIonAssetId(3263550)),
    )

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

    let clickHandler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas)
    // 监听鼠标点击事件

    clickHandler.setInputAction((movement) => {
      const pickedObject = viewer.scene.pick(movement.position)
      if (Cesium.defined(pickedObject) && pickedObject.id) {
        // 如果是点（Node）
        if (pickedObject.id.point) {
          const cartesianPosition = pickedObject.id.position.getValue()
          const cartographic = Cesium.Cartographic.fromCartesian(cartesianPosition)
          const lon = Cesium.Math.toDegrees(cartographic.longitude)
          const lat = Cesium.Math.toDegrees(cartographic.latitude)
          const height = cartographic.height
          clickedEntity.value = {
            type: pickedObject.id.properties.type.getValue(),
            id: pickedObject.id.id,
            name: pickedObject.id.name,
            lon: lon,
            lat: lat,
            elevation: height,
            depthMax: pickedObject.id.properties.depthMax.getValue(),
            depthInit: pickedObject.id.properties.depthInit.getValue(),
            depthSurcharge: pickedObject.id.properties.depthSurcharge.getValue(),
            areaPonded: pickedObject.id.properties.areaPonded.getValue(),
          }
        }
        // 如果是渠道（Conduit）
        else if (pickedObject.id.polyline) {
          clickedEntity.value = {
            type: pickedObject.id.properties.type.getValue(),
            id: pickedObject.id.id,
            name: pickedObject.id.name,
            fromNode: pickedObject.id.properties.fromNode.getValue(),
            toNode: pickedObject.id.properties.toNode.getValue(),
            length: pickedObject.id.properties.length.getValue(),
            roughness: pickedObject.id.properties.roughness.getValue(),
            transect: pickedObject.id.properties.transect.getValue(),
            shape: pickedObject.id.properties.shape.getValue(),
            height: pickedObject.id.properties.height.getValue(),
            parameter_2: pickedObject.id.properties.parameter_2.getValue(),
            parameter_3: pickedObject.id.properties.parameter_3.getValue(),
            parameter_4: pickedObject.id.properties.parameter_4.getValue(),
          }
        }
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK)

    initData(viewer) // 初始化数据

    // 数据共享
    const viewerStore = useViewerStore() // 获取 Pinia store 实例
    viewerStore.viewer = viewer // 将 viewer 实例存储到 Pinia 中
    viewerStore.startDragHandlers = startDragHandlers // 将开始拖动事件存储到 Pinia 中
    viewerStore.stopDragHandlers = stopDragHandlers // 将结束拖动事件存储到 Pinia 中
    viewerStore.initData = initData // 将初始化数据存储到 Pinia 中
  }

  // 开启鼠标拖动事件
  const startDragHandlers = (viewer) => {
    let draggedEntity = null
    let isDragging = false
    const dragHandler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas)

    dragHandler.setInputAction((movement) => {
      const pickedObject = viewer.scene.pick(movement.position)
      if (Cesium.defined(pickedObject) && pickedObject.id && pickedObject.id.point) {
        draggedEntity = pickedObject.id
        isDragging = true
        viewer.scene.screenSpaceCameraController.enableRotate = false
      }
    }, Cesium.ScreenSpaceEventType.LEFT_DOWN)

    dragHandler.setInputAction((movement) => {
      if (!isDragging || !draggedEntity) return

      const ray = viewer.camera.getPickRay(movement.endPosition)
      const cartesian = viewer.scene.globe.pick(ray, viewer.scene)

      if (cartesian) {
        // 更新实体位置
        draggedEntity.position = cartesian

        // 从 cartesian 位置计算经纬度和高度
        const cartographic = Cesium.Cartographic.fromCartesian(cartesian)
        const lon = Cesium.Math.toDegrees(cartographic.longitude)
        const lat = Cesium.Math.toDegrees(cartographic.latitude)
        const height = cartographic.height

        // 更新 clickedEntity 的数据
        clickedEntity.value = {
          type: draggedEntity.properties.type.getValue(),
          id: draggedEntity.id,
          name: draggedEntity.name,
          lon: lon,
          lat: lat,
          elevation: height,
          depthMax: draggedEntity.properties.depthMax.getValue(),
          depthInit: draggedEntity.properties.depthInit.getValue(),
          depthSurcharge: draggedEntity.properties.depthSurcharge.getValue(),
          areaPonded: draggedEntity.properties.areaPonded.getValue(),
        }
      }
    }, Cesium.ScreenSpaceEventType.MOUSE_MOVE)

    dragHandler.setInputAction(() => {
      isDragging = false
      draggedEntity = null
      viewer.scene.screenSpaceCameraController.enableRotate = true
    }, Cesium.ScreenSpaceEventType.LEFT_UP)

    return dragHandler
  }

  // 清除鼠标拖动事件
  const stopDragHandlers = (dragHandler) => {
    dragHandler.removeInputAction(Cesium.ScreenSpaceEventType.LEFT_DOWN)
    dragHandler.removeInputAction(Cesium.ScreenSpaceEventType.MOUSE_MOVE)
    dragHandler.removeInputAction(Cesium.ScreenSpaceEventType.LEFT_UP)
  }

  // 节点初始化
  const junctionsInit = async (viewer) => {
    const junctionDatas = await getAllJunctionsAxios()

    junctionDatas.forEach((junctionData) => {
      createJunctionEntity(
        viewer,
        junctionData.name,
        junctionData.lon,
        junctionData.lat,
        junctionData.elevation,
        junctionData.type,
        junctionData.depth_max,
        junctionData.depth_init,
        junctionData.depth_surcharge,
        junctionData.area_ponded,
      )
    })
  }

  // 管道初始化
  const conduitsInit = async () => {
    const conduitDatas = await getAllConduitsAxios()
    conduitDatas.forEach((conduitData) => {
      createConduitEntity(
        viewer,
        conduitData.name,
        conduitData.from_node,
        conduitData.to_node,
        conduitData.type,
        conduitData.length,
        conduitData.roughness,
        conduitData.transect,
        conduitData.shape,
        conduitData.height,
        conduitData.parameter_2,
        conduitData.parameter_3,
        conduitData.parameter_4,
      )
    })
  }

  const initData = async (viewer) => {
    await junctionsInit(viewer) // 先加载节点
    await conduitsInit(viewer) // 再加载管道
  }

  return {
    initViewer,
    initData,
    startDragHandlers,
    clickedEntity,
  }
}

// 默认导出 useCesium 工具函数
// 该函数用于初始化 Cesium Viewer、初始化数据、初始化处理鼠标事件
export default useCesium
