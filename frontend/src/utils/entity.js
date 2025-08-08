import * as Cesium from 'cesium'
import {
  POINTPREFIX,
  POLYLINEPREFIX,
  POLYGONPREFIX,
  HEIGHT_GEOID_OFFSET,
} from '@/utils/constant.js'

// 默认实体颜色常量
const JUNCTION_DEFAULT_COLOR = Cesium.Color.YELLOW
const OUTFALL_DEFAULT_COLOR = Cesium.Color.BLUE
const CONDUIT_DEFAULT_COLOR = Cesium.Color.BLUE.withAlpha(0.5)
const SUBCATCHMENT_DEFAULT_COLOR = Cesium.Color.LIGHTSKYBLUE.withAlpha(0.5)

// 选中高亮颜色常量
const HIGHLIGHT_COLOR = Cesium.Color.RED
const SUBCATCHMENT_HIGHLISHT_COLOR = Cesium.Color.RED.withAlpha(0.5)
// 默认点大小常量
const DEFAULT_POINT_SIZE = 8

// 临时连接线 ID
const TEMP_SUBCATCHMENT_CONNECTION_LINE_ID = 'temp_subcatchment_connection_line'

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
    id: POINTPREFIX + name,
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

// 创建统一出水口实体
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
    // outfall 也用 POINT# 命名，这样方便后续通过 POINT# 进行查找
    // 因为管道初始化的起始点和终点，不分出水口和节点
    id: POINTPREFIX + name,
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
  const fromNode = viewer.entities.getById(POINTPREFIX + fromNodeId)
  const toNode = viewer.entities.getById(POINTPREFIX + toNodeId)

  if (!fromNode || !toNode) {
    ElMessage.error(`无法找到连接渠道的节点: [${fromNodeId}] → [${toNodeId}]`)
    return null // 不继续往下执行 创建渠道对象
  }
  const conduitObject = {
    id: POLYLINEPREFIX + name,
    name: name,
    polyline: {
      positions: new Cesium.CallbackProperty(() => {
        const fromNode = viewer.entities.getById(POINTPREFIX + fromNodeId)
        const toNode = viewer.entities.getById(POINTPREFIX + toNodeId)

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

export const createSubcatchmentEntity = (
  viewer,
  name,
  rainGage,
  outlet,
  area,
  imperviousness,
  width,
  slope,
  polygon, // polygon 是数组，例如 [[x1, y1], [x2, y2], ...]
) => {
  if (!polygon || polygon.length < 3) {
    console.error(`子汇水区 ${name} 的 polygon 数据无效，无法创建实体`)
    return null
  }

  const positions = polygon.map(([x, y]) => Cesium.Cartesian3.fromDegrees(x, y))

  const subcatchmentObject = {
    id: POLYGONPREFIX + name,
    name: name,
    polygon: {
      hierarchy: new Cesium.PolygonHierarchy(positions),
      material: Cesium.Color.LIGHTSKYBLUE.withAlpha(0.5), // 设置填充颜色
      clampToGround: true,
      // 贴地就不能设置outline
      // height: 0,
      // outline: true,
      // outlineColor: Cesium.Color.SKYBLUE,
    },
    properties: {
      type: 'subcatchment',
      timeseriesName: rainGage, // 这里用 timeseriesName 字段存储雨量计名称 （方便前端Junction和Subcatchment统一处理timeseriesName）
      outlet,
      area,
      imperviousness,
      width,
      slope,
      polygon, // 存储原始的多边形数据（经纬度数组）
    },
  }

  return viewer.entities.add(subcatchmentObject)
}

// 控制系统自定义点击事件启动和停止的管理器
export const createSystemCustomLeftClickHandler = (viewerStore) => {
  let clickHandler = null
  const viewer = viewerStore.viewer
  return {
    start: () => {
      if (!clickHandler) {
        clickHandler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas)
        clickHandler.setInputAction((movement) => {
          const worldPosition = viewer.scene.pickPosition(movement.position)
          const pickedObject = viewer.scene.pick(movement.position)
          viewerStore.clickedEntityDict = fillClickedEntityDict(pickedObject?.id, worldPosition)
        }, Cesium.ScreenSpaceEventType.LEFT_CLICK)
      }
    },

    stop: () => {
      if (clickHandler) {
        clickHandler.destroy()
        clickHandler = null
      }
    },
  }
}
// 更新填充 clickedEntity 数据，clickedEntity 为了存储和显示弹窗信息
// pickedObject 是实体
export const fillClickedEntityDict = (pickedObject, cartesianPosition = null) => {
  let clickedEntityDict = {}
  // pickedObject.properties?.type?.getValue() 代表是有 type 属性的实体
  if (Cesium.defined(pickedObject) && pickedObject && pickedObject.properties?.type?.getValue()) {
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
    // 如果是子汇水区（Subcatchment）
    else if (pickedObject.polygon) {
      clickedEntityDict = {
        id: pickedObject.id,
        name: pickedObject.name,
        type: pickedObject.properties.type.getValue(),
        timeseriesName: pickedObject.properties.timeseriesName.getValue(), // 这里用 timeseriesName 字段存储雨量计名称 （方便前端Junction和Subcatchment统一处理timeseriesName）
        outlet: pickedObject.properties.outlet.getValue(),
        area: pickedObject.properties.area.getValue(),
        imperviousness: pickedObject.properties.imperviousness.getValue(),
        width: pickedObject.properties.width.getValue(),
        slope: pickedObject.properties.slope.getValue(),
        polygon: pickedObject.properties.polygon.getValue(), // 存储原始的多边形数据（经纬度数组）
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
          : new Cesium.ColorMaterialProperty(HIGHLIGHT_COLOR.withAlpha(0.7))
      }
      break

    case 'subcatchment': {
      // 子汇水区的高亮颜色处理
      if (entity.polygon) {
        entity.polygon.material = reverse
          ? SUBCATCHMENT_DEFAULT_COLOR
          : SUBCATCHMENT_HIGHLISHT_COLOR

        // 子汇水区出口连接
        // 如果有出口节点，找到出口节点，然后找到子汇水区与出口节点最近的连接
        const outletId = entity.properties.outlet.getValue()
        const outletEntity = viewer.entities.getById(POINTPREFIX + outletId)
        addTempSubcatchmentConnectionLine(viewer, entity, outletEntity, reverse)
      }

      break
    }
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
    height += HEIGHT_GEOID_OFFSET
    return [height, parseFloat(distance.toFixed(2))] // 保留两位小数
  })

  return result
}

/**
 * 计算多边形中心点（通过平均经纬度）
 * @param {Cesium.Cartesian3[]} cartesianPositions - Polygon 顶点（笛卡尔坐标数组）
 * @returns {Cesium.Cartesian3} - 中心点笛卡尔坐标
 */
export const getPolygonCenter = (cartesianPositions) => {
  if (!cartesianPositions || cartesianPositions.length === 0) return null

  // 1. 转为 Cartographic
  const cartographicPositions = cartesianPositions.map((pos) =>
    Cesium.Ellipsoid.WGS84.cartesianToCartographic(pos),
  )

  // 2. 计算平均经纬度
  let lonSum = 0
  let latSum = 0
  for (const pos of cartographicPositions) {
    lonSum += Cesium.Math.toDegrees(pos.longitude)
    latSum += Cesium.Math.toDegrees(pos.latitude)
  }
  const lon = lonSum / cartographicPositions.length
  const lat = latSum / cartographicPositions.length

  // 3. 转回 Cartesian3，设置高程为 0
  return Cesium.Cartesian3.fromDegrees(lon, lat, 0)
}

// 添加临时连接线
export const addTempSubcatchmentConnectionLine = (
  viewer,
  subcatchmentEntity,
  outletEntity,
  reverse = false,
) => {
  if (outletEntity) {
    //  1.先删除已有的连接线（如果存在）
    const existingLine = viewer.entities.getById(TEMP_SUBCATCHMENT_CONNECTION_LINE_ID)
    if (existingLine) {
      viewer.entities.remove(existingLine)
    }
    // 2.如果是反选操作，直接返回，不添加连接线
    if (reverse) {
      return
    }
    // 3.如果是选中操作，添加连接线
    // 获取子汇水区中心点
    const hierarchy = subcatchmentEntity.polygon.hierarchy.getValue()
    const centerCartesian = getPolygonCenter(hierarchy.positions)
    // 获取出口节点位置
    const outletCartesian = outletEntity.position.getValue(Cesium.JulianDate.now())
    // 添加新的连接线
    viewer.entities.add({
      id: TEMP_SUBCATCHMENT_CONNECTION_LINE_ID,
      name: '子汇水区-出口',
      polyline: {
        positions: [centerCartesian, outletCartesian],
        width: 4,
        material: Cesium.Color.YELLOW.withAlpha(0.5),
        clampToGround: true,
      },
    })
  }
}

// 查找函数
// 1. 查找实体
export const findEntityByName = (viewer, name) => {
  const entityJunction = viewer.entities.getById(POINTPREFIX + name)
  const entityConduit = viewer.entities.getById(POLYLINEPREFIX + name)
  const entitySubcatchment = viewer.entities.getById(POLYGONPREFIX + name)

  let entity = null
  let cartesian = null
  let typeMessageName = null

  if (entityJunction) {
    typeMessageName = '节点'
    entity = entityJunction
    cartesian = entity.position.getValue()
  } else if (entityConduit) {
    typeMessageName = '渠道'
    entity = entityConduit
    // 渠道用第一个点坐标
    cartesian = entity.polyline.positions.getValue()[0]
  } else if (entitySubcatchment) {
    typeMessageName = '汇水区'
    entity = entitySubcatchment
    const hierarchy = entity.polygon.hierarchy.getValue()
    // 获取多边形中心点
    cartesian = getPolygonCenter(hierarchy.positions)
  }

  return { entity, cartesian, typeMessageName }
}

// 2. 飞行到实体
export const flyToEntity = (viewerStore, entity, cartesian) => {
  // 显示飞到的实体弹窗和高亮实体（类似左键点击事件）
  viewerStore.clickedEntityDict = fillClickedEntityDict(entity)

  const cartographic = Cesium.Cartographic.fromCartesian(cartesian)
  const longitude = Cesium.Math.toDegrees(cartographic.longitude)
  const latitude = Cesium.Math.toDegrees(cartographic.latitude)
  const customHeight = 20000
  const destination = Cesium.Cartesian3.fromDegrees(longitude, latitude, customHeight)

  viewerStore.viewer.camera.flyTo({
    destination,
    duration: 2,
  })
}
