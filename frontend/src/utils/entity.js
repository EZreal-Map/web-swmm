import * as Cesium from 'cesium'

// 默认实体颜色变量
const JUNCTION_DEFAULT_COLOR = Cesium.Color.YELLOW
const OUTFALL_DEFAULT_COLOR = Cesium.Color.BLUE
const CONDUIT_DEFAULT_COLOR = Cesium.Color.BLUE.withAlpha(0.5)
// 选中高亮颜色
const HIGHLIGHT_COLOR = Cesium.Color.RED

// 创建统一节点实体
export const createJunctionEntity = (
  viewer,
  name,
  lon,
  lat,
  elevation,
  type = 'junction',
  depthMax = 0,
  depthInit = 0,
  depthSurcharge = 0,
  areaPonded = 0,
) => {
  // 先创建对象
  const junctionObject = {
    id: 'junction#' + name,
    name: name,
    position: Cesium.Cartesian3.fromDegrees(lon, lat, elevation),
    point: {
      color: JUNCTION_DEFAULT_COLOR,
      pixelSize: 10,
      outlineColor: Cesium.Color.WHITE,
      outlineWidth: 2,
      heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
    },
    properties: {
      type,
      depthMax,
      depthInit,
      depthSurcharge,
      areaPonded,
    },
  }
  // 添加到 Cesium Viewer
  viewer.entities.add(junctionObject)
}

export const createOutfallEntity = (
  viewer,
  name,
  lon,
  lat,
  elevation,
  type = 'outfall',
  kind = 'FREE',
  data = null,
) => {
  // 先创建对象
  const outfallObject = {
    // outfall 也用 junction# 命名，这样方便后续通过 junction# 进行查找
    id: 'junction#' + name,
    name: name,
    position: Cesium.Cartesian3.fromDegrees(lon, lat, elevation),
    point: {
      color: OUTFALL_DEFAULT_COLOR,
      pixelSize: 10,
      outlineColor: Cesium.Color.WHITE,
      outlineWidth: 2,
      heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
    },
    properties: {
      type,
      kind,
      data,
    },
  }
  // 添加到 Cesium Viewer
  viewer.entities.add(outfallObject)
}

// 创建统一管道实体
export const createConduitEntity = (
  viewer,
  name,
  fromNodeId,
  toNodeId,
  type = 'conduit',
  length = 100,
  roughness = 0.01,
  transect = null,
  shape = 'TRAPEZOIDAL',
  height = 10,
  parameter_2 = 20,
  parameter_3 = 0.5,
  parameter_4 = 0.5,
) => {
  console.log('createConduitEntity', name, fromNodeId, toNodeId)
  // 创建管道对象
  const fromNode = viewer.entities.getById('junction#' + fromNodeId)
  const toNode = viewer.entities.getById('junction#' + toNodeId)

  if (!fromNode || !toNode) {
    ElMessage.error(`无法找到连接管道的节点: [${fromNodeId}] → [${toNodeId}]`)
    return null // 不继续往下执行 创建管道对象
  }
  const conduitObject = {
    id: 'conduit#' + name,
    name: name,
    polyline: {
      positions: new Cesium.CallbackProperty(() => {
        const fromNode = viewer.entities.getById('junction#' + fromNodeId)
        const toNode = viewer.entities.getById('junction#' + toNodeId)

        if (!fromNode || !toNode) {
          console.error(`CallbackProperty:无法找到连接管道的节点: ${fromNodeId} 或 ${toNodeId}`)
          return [] // 重要：返回空数组，避免 Cesium 报错
        }

        const fromPosition = fromNode?.position?.getValue()
        const toPosition = toNode?.position?.getValue()

        if (!fromPosition || !toPosition) return []

        return [fromPosition, toPosition]
      }, false), // false 表示不会每一帧都强制更新，节省性能
      width: 10,
      material: CONDUIT_DEFAULT_COLOR,
      clampToGround: true, // 让线贴地
      arcType: Cesium.ArcType.GEODESIC, // 让线自动跟随地形曲率
    },
    properties: {
      type: type,
      fromNode: fromNodeId,
      toNode: toNodeId,
      length,
      roughness,
      transect,
      shape,
      height,
      parameter_2,
      parameter_3,
      parameter_4,
    },
  }

  // 添加到 Cesium Viewer
  return viewer.entities.add(conduitObject)
}

// 更新填充 clickedEntity 数据，clickedEntity 为了存储和显示弹窗信息
export const fillClickedEntityDict = (pickedObject) => {
  let clickedEntityDict = {}
  if (Cesium.defined(pickedObject) && pickedObject.id) {
    // 如果是点（Node）
    if (pickedObject.id.point) {
      const cartesianPosition = pickedObject.id.position.getValue()
      const cartographic = Cesium.Cartographic.fromCartesian(cartesianPosition)
      const lon = Cesium.Math.toDegrees(cartographic.longitude)
      const lat = Cesium.Math.toDegrees(cartographic.latitude)
      const height = cartographic.height
      const type = pickedObject.id.properties.type.getValue()
      // 如果是节点（Junction）
      if (type === 'junction') {
        clickedEntityDict = {
          type,
          id: pickedObject.id.id,
          name: pickedObject.id.name,
          lon,
          lat,
          elevation: height,
          depthMax: pickedObject.id.properties.depthMax.getValue(),
          depthInit: pickedObject.id.properties.depthInit.getValue(),
          depthSurcharge: pickedObject.id.properties.depthSurcharge.getValue(),
          areaPonded: pickedObject.id.properties.areaPonded.getValue(),
        }
      }
      // 如果是出口（Outfall）
      else if (type === 'outfall') {
        clickedEntityDict = {
          id: pickedObject.id.id,
          name: pickedObject.id.name,
          lon: lon,
          lat: lat,
          elevation: height,
          type,
          kind: pickedObject.id.properties.kind.getValue(),
          data: pickedObject.id.properties.data.getValue(),
        }
      }
    }
    // 如果是渠道（Conduit）
    else if (pickedObject.id.polyline) {
      clickedEntityDict = {
        id: pickedObject.id.id,
        name: pickedObject.id.name,
        type: pickedObject.id.properties.type.getValue(),
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
  return clickedEntityDict
}

export const highlightClickedEntityColor = (viewer, entityDict, reverse = false) => {
  if (!entityDict?.id) return

  const entity = viewer.entities.getById(entityDict.id)
  if (!entity) return

  // 使用更高效的条件判断
  switch (entityDict.type) {
    case 'junction':
      if (entity.point) {
        entity.point.color = reverse ? JUNCTION_DEFAULT_COLOR : HIGHLIGHT_COLOR
      }
      break

    case 'outfall':
      if (entity.point) {
        entity.point.color = reverse ? OUTFALL_DEFAULT_COLOR : HIGHLIGHT_COLOR
      }
      break

    case 'conduit':
      if (entity.polyline) {
        entity.polyline.material = reverse
          ? new Cesium.ColorMaterialProperty(CONDUIT_DEFAULT_COLOR)
          : new Cesium.ColorMaterialProperty(HIGHLIGHT_COLOR)
      }
      break
  }
}
