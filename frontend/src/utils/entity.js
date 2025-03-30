import * as Cesium from 'cesium'

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
      color: Cesium.Color.YELLOW,
      pixelSize: 10,
      outlineColor: Cesium.Color.WHITE,
      outlineWidth: 2,
      heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
    },
    properties: {
      type: type,
      depthMax: depthMax,
      depthInit: depthInit,
      depthSurcharge: depthSurcharge,
      areaPonded: areaPonded,
    },
  }
  // 添加到 Cesium Viewer
  viewer.entities.add(junctionObject)
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
      material: Cesium.Color.BLUE.withAlpha(0.5),
      clampToGround: true, // 让线贴地
      arcType: Cesium.ArcType.GEODESIC, // 让线自动跟随地形曲率
    },
    properties: {
      type: type,
      fromNode: fromNodeId,
      toNode: toNodeId,
      length: length,
      roughness: roughness,
      transect: transect,
      shape: shape,
      height: height,
      parameter_2: parameter_2,
      parameter_3: parameter_3,
      parameter_4: parameter_4,
    },
  }

  // 添加到 Cesium Viewer
  return viewer.entities.add(conduitObject)
}
