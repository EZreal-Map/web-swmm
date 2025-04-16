import * as Cesium from 'cesium'

// 默认实体颜色常量
const JUNCTION_DEFAULT_COLOR = Cesium.Color.YELLOW
const OUTFALL_DEFAULT_COLOR = Cesium.Color.BLUE
const CONDUIT_DEFAULT_COLOR = Cesium.Color.BLUE.withAlpha(0.5)
// 选中高亮颜色常量
const HIGHLIGHT_COLOR = Cesium.Color.RED
// 默认点大小常量
const DEFAULT_POINT_SIZE = 8

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
  hasInflow = false,
  timeseriesName = '',
) => {
  // 先创建对象
  const junctionObject = {
    id: 'junction#' + name,
    name: name,
    position: Cesium.Cartesian3.fromDegrees(lon, lat, elevation),
    point: {
      color: JUNCTION_DEFAULT_COLOR,
      pixelSize: DEFAULT_POINT_SIZE,
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
      hasInflow,
      timeseriesName,
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
      pixelSize: DEFAULT_POINT_SIZE,
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

// 创建统一渠道实体
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
  // 创建渠道对象
  const fromNode = viewer.entities.getById('junction#' + fromNodeId)
  const toNode = viewer.entities.getById('junction#' + toNodeId)

  if (!fromNode || !toNode) {
    ElMessage.error(`无法找到连接渠道的节点: [${fromNodeId}] → [${toNodeId}]`)
    return null // 不继续往下执行 创建渠道对象
  }
  const conduitObject = {
    id: 'conduit#' + name,
    name: name,
    polyline: {
      positions: new Cesium.CallbackProperty(() => {
        const fromNode = viewer.entities.getById('junction#' + fromNodeId)
        const toNode = viewer.entities.getById('junction#' + toNodeId)

        if (!fromNode || !toNode) {
          console.error(`CallbackProperty:无法找到连接渠道的节点: ${fromNodeId} 或 ${toNodeId}`)
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
// pickedObject 是实体
export const fillClickedEntityDict = (pickedObject, cartesianPosition = null) => {
  let clickedEntityDict = {}
  if (Cesium.defined(pickedObject) && pickedObject) {
    // 如果是点（Node）
    if (pickedObject.point) {
      const cartesianPosition = pickedObject.position.getValue()
      const cartographic = Cesium.Cartographic.fromCartesian(cartesianPosition)
      const lon = Cesium.Math.toDegrees(cartographic.longitude)
      const lat = Cesium.Math.toDegrees(cartographic.latitude)
      const height = Number(cartographic.height.toFixed(2)) // 保留两位小数
      const type = pickedObject.properties.type.getValue()
      // 如果是节点（Junction）
      if (type === 'junction') {
        clickedEntityDict = {
          type,
          id: pickedObject.id,
          name: pickedObject.name,
          lon,
          lat,
          elevation: height,
          depthMax: pickedObject.properties.depthMax.getValue(),
          depthInit: pickedObject.properties.depthInit.getValue(),
          depthSurcharge: pickedObject.properties.depthSurcharge.getValue(),
          areaPonded: pickedObject.properties.areaPonded.getValue(),
          hasInflow: pickedObject.properties.hasInflow.getValue(),
          timeseriesName: pickedObject.properties.timeseriesName.getValue(),
        }
      }
      // 如果是出口（Outfall）
      else if (type === 'outfall') {
        clickedEntityDict = {
          id: pickedObject.id,
          name: pickedObject.name,
          lon: lon,
          lat: lat,
          elevation: height,
          type,
          kind: pickedObject.properties.kind.getValue(),
          data: pickedObject.properties.data.getValue(),
        }
      }
    }
    // 如果是渠道（Conduit）
    else if (pickedObject.polyline) {
      clickedEntityDict = {
        id: pickedObject.id,
        name: pickedObject.name,
        type: pickedObject.properties.type.getValue(),
        fromNode: pickedObject.properties.fromNode.getValue(),
        toNode: pickedObject.properties.toNode.getValue(),
        length: pickedObject.properties.length.getValue(),
        roughness: pickedObject.properties.roughness.getValue(),
        transect: pickedObject.properties.transect.getValue(),
        shape: pickedObject.properties.shape.getValue(),
        height: pickedObject.properties.height.getValue(),
        parameter_2: pickedObject.properties.parameter_2.getValue(),
        parameter_3: pickedObject.properties.parameter_3.getValue(),
        parameter_4: pickedObject.properties.parameter_4.getValue(),
      }
    }
  }
  // 如果没有点击到任何对象，且有传入的 cartesianPosition
  // 则根据 cartesianPosition 获取经纬度
  if ((!clickedEntityDict?.lon || !clickedEntityDict?.lat) && cartesianPosition) {
    const cartographic = Cesium.Cartographic.fromCartesian(cartesianPosition)
    const lon = Cesium.Math.toDegrees(cartographic.longitude)
    const lat = Cesium.Math.toDegrees(cartographic.latitude)
    clickedEntityDict.lon = lon
    clickedEntityDict.lat = lat
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

// 通过传入2个经纬度坐标点，获取高程剖面过程线数据（提取不规则断面）
export const getElevationProfile = async (
  viewer,
  startCartographic,
  endCartographic,
  sampleCount = 20,
) => {
  const positions = []
  // 传入的 startCartographic 和 endCartographic 是度制，经纬度要先转换为弧度
  const startLon = Cesium.Math.toRadians(startCartographic.lon)
  const startLat = Cesium.Math.toRadians(startCartographic.lat)
  const endLon = Cesium.Math.toRadians(endCartographic.lon)
  const endLat = Cesium.Math.toRadians(endCartographic.lat)

  for (let i = 0; i <= sampleCount; i++) {
    const lon = Cesium.Math.lerp(startLon, endLon, i / sampleCount)
    const lat = Cesium.Math.lerp(startLat, endLat, i / sampleCount)
    const point = new Cesium.Cartographic(lon, lat)
    positions.push(point)
  }

  const terrainProvider = viewer.terrainProvider
  const updatedPositions = await Cesium.sampleTerrainMostDetailed(terrainProvider, positions)

  // 计算地面距离，先将 Cartographic 转换为 Cartesian3，然后再计算与起点的距离
  const cartesianPoints = updatedPositions.map((p) =>
    Cesium.Cartesian3.fromRadians(p.longitude, p.latitude, p.height),
  )
  const startPoint = cartesianPoints[0]

  const result = cartesianPoints.map((point, index) => {
    const distance = Cesium.Cartesian3.distance(startPoint, point)
    let height = parseFloat(updatedPositions[index].height.toFixed(2))
    // Cesium 默认用的是 WGS84 椭球高度，而平常使用的 DEM 数据则通常是以平均海平面为基准的正交高程
    // 在乐山这个地方，WGS84 椭球高度和正交高程的差值大概是 +44 米
    height += 44
    return [height, parseFloat(distance.toFixed(2))] // 保留两位小数
  })

  return result
}
