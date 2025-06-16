import * as Cesium from 'cesium'
import { useViewerStore } from '@/stores/viewer'
import { getAllJunctionsAxios } from '@/apis/junction'
import { getAllConduitsAxios } from '@/apis/conduit'
import { getAllOutfallsAxios } from '@/apis/outfall'
import { getSubcatchmentsAxios } from '@/apis/subcatchment'
import {
  createJunctionEntity,
  createConduitEntity,
  createOutfallEntity,
  createSubcatchmentEntity,
  fillClickedEntityDict,
  highlightClickedEntityColor,
} from '@/utils/entity'

import { createSystemCustomLeftClickHandler } from '@/utils/entity'
import { getBoundaryAxios } from '@/apis/boundary'

export const initCesium = async (containerId) => {
  Cesium.Ion.defaultAccessToken =
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJkNjQ5ODdiMy02NTIxLTQ2YWYtODJkNC0yYmIzMDdhNTRjYTkiLCJpZCI6MTU1ODM0LCJpYXQiOjE2OTMyNzIwNDh9.7oNx5xlOUJNC9qfJJ_csPvDWFXqmqFce-gxF2qFu-18'
  const viewer = new Cesium.Viewer(containerId, {
    geocoder: false, //隐藏查找控件
    homeButton: false, //隐藏视角返回初始位置按钮
    sceneModePicker: false, //隐藏视角模式3D 2D CV
    baseLayerPicker: false, //隐藏图层选择
    navigationHelpButton: false, //隐藏帮助
    animation: false, //隐藏动画控件
    timeline: false, //隐藏时间线控件
    fullscreenButton: false, //隐藏全屏
  })

  // 数据共享
  const viewerStore = useViewerStore() // 获取 Pinia store 实例
  viewerStore.viewer = viewer // 将 viewer 实例存储到 Pinia 中

  // 初始化地形数据（这里链接的是自己上传的乐山的地形数据  Cesium Ion 编号）
  viewer.scene.setTerrain(new Cesium.Terrain(Cesium.CesiumTerrainProvider.fromIonAssetId(3263550)))

  // 开始时设置相机位置
  viewer.camera.setView({
    destination: Cesium.Cartesian3.fromDegrees(103.77346807693011, 29.5048309132203, 200000),
    orientation: {
      heading: Cesium.Math.toRadians(0),
      pitch: Cesium.Math.toRadians(-90),
      roll: Cesium.Math.toRadians(0),
    },
  })

  // 清除默认鼠标左键点击事件
  viewer.screenSpaceEventHandler.removeInputAction(Cesium.ScreenSpaceEventType.LEFT_CLICK)
  viewer.screenSpaceEventHandler.removeInputAction(Cesium.ScreenSpaceEventType.LEFT_DOUBLE_CLICK)

  // 监听鼠标点击事件
  const systemCustomLeftClickManager = createSystemCustomLeftClickHandler(viewerStore)
  // 启动点击事件
  systemCustomLeftClickManager.start()
  // 将自定义的鼠标左键点击事件管理器存储到 Pinia 中，方便其他地方使用
  viewerStore.systemCustomLeftClickManager = systemCustomLeftClickManager
  // 初始化数据
  initEntities(viewer)
}

// 开启鼠标拖动事件
export const startDragHandlers = (viewer) => {
  let draggedEntity = null
  let isDragging = false
  const dragHandler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas)

  dragHandler.setInputAction((movement) => {
    const pickedObject = viewer.scene.pick(movement.position)
    if (Cesium.defined(pickedObject) && pickedObject.id && pickedObject.id.point) {
      draggedEntity = pickedObject
      isDragging = true
      viewer.scene.screenSpaceCameraController.enableRotate = false
    }
  }, Cesium.ScreenSpaceEventType.LEFT_DOWN)

  dragHandler.setInputAction((movement) => {
    if (!isDragging || !draggedEntity.id) return

    const ray = viewer.camera.getPickRay(movement.endPosition)
    const cartesian = viewer.scene.globe.pick(ray, viewer.scene)

    if (cartesian) {
      // 更新实体位置
      draggedEntity.id.position = cartesian
      // 更新填充 clickedEntityDict 数据，为了存储和显示弹窗信息
      const viewerStore = useViewerStore()
      viewerStore.clickedEntityDict = fillClickedEntityDict(draggedEntity.id)
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
export const stopDragHandlers = (dragHandler) => {
  dragHandler.removeInputAction(Cesium.ScreenSpaceEventType.LEFT_DOWN)
  dragHandler.removeInputAction(Cesium.ScreenSpaceEventType.MOUSE_MOVE)
  dragHandler.removeInputAction(Cesium.ScreenSpaceEventType.LEFT_UP)
}

// 节点初始化
const junctionsInit = async (viewer) => {
  const { data: junctionDatas } = await getAllJunctionsAxios()
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
      junctionData.has_inflow,
      junctionData.timeseries_name,
    )
  })
}

// 出口初始化
const outfallsInit = async (viewer) => {
  const { data: outletDatas } = await getAllOutfallsAxios()
  outletDatas.forEach((outfall) => {
    createOutfallEntity(
      viewer,
      outfall.name,
      outfall.lon,
      outfall.lat,
      outfall.elevation,
      outfall.type,
      outfall.kind,
      outfall.data,
    )
  })
}

// 渠道初始化
const conduitsInit = async (viewer) => {
  const { data: conduitDatas } = await getAllConduitsAxios()
  // 遍历每个渠道数据，创建对应的实体
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

// 子汇水区初始化
const subcatchmentsInit = async (viewer) => {
  const { data: subcatchmentDatas } = await getSubcatchmentsAxios()
  subcatchmentDatas.forEach((subcatchmentData) => {
    createSubcatchmentEntity(
      viewer,
      subcatchmentData.name,
      subcatchmentData.rain_gage,
      subcatchmentData.outlet,
      subcatchmentData.area,
      subcatchmentData.imperviousness,
      subcatchmentData.width,
      subcatchmentData.slope,
      subcatchmentData.polygon,
    )
  })
}

export const initEntities = async (viewer) => {
  // 清除所有实体
  viewer.entities.removeAll()
  // 创建所有实体
  await junctionsInit(viewer) // 先加载节点
  await outfallsInit(viewer) // 再加载出口
  await conduitsInit(viewer) // 最后加载渠道
  await subcatchmentsInit(viewer) // 加载子汇水区
  await initBasinBoundary(viewer) // 初始化流域边界 (这个是常量)
  // 设置默认高亮颜色
  const viewerStore = useViewerStore() // 获取 Pinia store 实例
  highlightClickedEntityColor(viewer, viewerStore.clickedEntityDict)
}

// 初始化流域边界 (这个是常量)
const initBasinBoundary = async (viewer) => {
  const response = await getBoundaryAxios()
  try {
    if (response.code !== 200) {
      ElMessage.error(response.message || '边界数据加载失败')
      return
    }

    const geojson = response.data
    if (!geojson || !geojson.features || !Array.isArray(geojson.features)) {
      ElMessage.error('边界数据格式错误')
      return
    }

    geojson.features.forEach((feature) => {
      if (!feature.geometry || !feature.geometry.type || !feature.geometry.coordinates) return

      const geom = feature.geometry
      if (geom.type === 'Polygon') {
        drawPolygonBoundary(viewer, geom.coordinates)
      } else if (geom.type === 'MultiPolygon') {
        geom.coordinates.forEach((polygonCoords) => {
          drawPolygonBoundary(viewer, polygonCoords)
        })
      }
    })
  } catch (e) {
    console.error('加载边界数据异常', e)
    ElMessage.error('加载边界数据异常')
  }
}

// 初始化流域边界的辅助函数：绘制多边形边界线（含外环和内环）
// (了解就行，gpt生成的，不保证正确性，没有测试过MultiPolygon)
const drawPolygonBoundary = (viewer, polygonCoords) => {
  if (!Array.isArray(polygonCoords) || polygonCoords.length === 0) return

  // 外环 coords 是 polygonCoords[0]，内环是后续的坐标环
  polygonCoords.forEach((ring) => {
    if (!Array.isArray(ring) || ring.length === 0) return

    // 转换坐标为 Cesium.Cartesian3 数组
    const positions = ring
      .map((coord) => {
        if (!Array.isArray(coord) || coord.length < 2) return null
        return Cesium.Cartesian3.fromDegrees(coord[0], coord[1])
      })
      .filter((pos) => pos !== null)

    if (positions.length < 2) return

    // 保证闭合（首尾坐标相同）
    const first = positions[0]
    const last = positions[positions.length - 1]
    if (!Cesium.Cartesian3.equalsEpsilon(first, last, Cesium.Math.EPSILON6)) {
      positions.push(first)
    }

    viewer.entities.add({
      polyline: {
        positions: positions,
        width: 2,
        material: Cesium.Color.SKYBLUE.withAlpha(0.6),
        clampToGround: true,
      },
    })
  })
}
