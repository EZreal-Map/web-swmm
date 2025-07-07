<template>
  <div class="popup-container" v-show="!viewerStore.extractFlag">
    <el-card class="popup-card">
      <div class="popup-header">
        <span class="popup-title">子汇水区 信息详情</span>
        <el-icon @click="closeDialog"><CloseBold /></el-icon>
      </div>

      <el-form
        label-position="left"
        class="popup-form"
        label-width="70px"
        style="max-width: 268px"
        :size="'default'"
        v-model="subcatchmentEntity"
      >
        <el-form-item label="名字">
          <el-input v-model="subcatchmentEntity.name" type="string"></el-input>
        </el-form-item>
        <el-form-item label="雨量">
          <el-input
            v-model="subcatchmentEntity.timeseriesName"
            type="string"
            class="el-form-length"
          ></el-input>
          <el-button @click="showTimeSeriesDialog = true" class="el-form-length-button"
            >更多</el-button
          >
        </el-form-item>
        <el-form-item label="出水口">
          <el-input v-model="subcatchmentEntity.outlet" type="string"></el-input>
        </el-form-item>
        <el-form-item label="面积">
          <el-input v-model.number="subcatchmentEntity.area" type="number" class="el-form-length">
          </el-input>
          <el-button @click="calculateArea" class="el-form-length-button">计算</el-button>
        </el-form-item>
        <el-form-item>
          <template #label>
            <el-tooltip effect="dark" content="水流横向的有效流宽" placement="left">
              <span>宽度</span>
            </el-tooltip>
          </template>
          <el-input v-model.number="subcatchmentEntity.width" type="number" class="el-form-length">
          </el-input>
          <el-button @click="calculateWidth" class="el-form-length-button">
            <el-tooltip
              effect="dark"
              content="通过面积 ÷ 子汇水区顶点到出水点的最大距离估算得出"
              placement="top"
            >
              <span>估算</span>
            </el-tooltip></el-button
          >
        </el-form-item>
        <el-form-item>
          <template #label>
            <el-tooltip effect="dark" content="百分比 (%)" placement="left">
              <span>不透水率</span>
            </el-tooltip>
          </template>
          <el-input v-model="subcatchmentEntity.imperviousness" type="number"></el-input>
        </el-form-item>
        <el-form-item>
          <template #label>
            <el-tooltip effect="dark" content="百分比 (%)" placement="left">
              <span>坡度</span>
            </el-tooltip>
          </template>
          <el-input v-model.number="subcatchmentEntity.slope" type="number" class="el-form-length">
          </el-input>
          <el-button @click="calculateSlope" class="el-form-length-button">
            <el-tooltip
              effect="dark"
              content="根据子汇水区内最高高程点与出水口的高程差与水平距离，估算得出代表性坡度"
              placement="top"
            >
              <span>估算</span>
            </el-tooltip></el-button
          >
        </el-form-item>
        <!-- 使用额外 div 包裹，使其不换行 -->
        <div style="display: flex; flex-wrap: wrap; column-gap: 8px; row-gap: 0px; width: 100%">
          <el-form-item label="汇流参数" style="margin-right: 0">
            <el-button @click="showSubareaDialog = true">更多</el-button>
          </el-form-item>
          <el-form-item label="下渗参数" style="margin-right: 0">
            <el-button @click="showInfiltrationDialog = true">更多</el-button>
          </el-form-item>
          <el-form-item label="多边形" style="margin-right: 0">
            <el-button @click="startPolygonEdit" v-if="!polygonEditing">编辑</el-button>
            <div v-else>
              <el-button @click="finishEdit">保存</el-button>
              <el-button @click="cancelEdit">取消</el-button>
            </div>
          </el-form-item>
        </div>
      </el-form>
      <div class="popup-footer">
        <el-button type="danger" @click="deleteConduitEntity">删除</el-button>
        <el-button type="primary" @click="saveSubcatchment">保存</el-button>
      </div>
    </el-card>
  </div>

  <!-- 引入子区域产流弹窗组件 -->
  <SubareaDialog
    v-if="showSubareaDialog"
    v-model:visible="showSubareaDialog"
    v-model:subcatchmentName="subcatchmentEntity.name"
  />
  <!-- 引入子区域渗透弹窗组件 -->
  <InfiltrationDialog
    v-if="showInfiltrationDialog"
    v-model:visible="showInfiltrationDialog"
    v-model:subcatchmentName="subcatchmentEntity.name"
  />

  <!-- 引入雨量计选择弹窗组件 -->
  <TimeSeriesDialog
    v-if="showTimeSeriesDialog"
    v-model:show-dialog="showTimeSeriesDialog"
    :timeseriesName="subcatchmentEntity.timeseriesName"
    timeseriesType="RAINGAGE"
  ></TimeSeriesDialog>
</template>

<script setup>
import { CloseBold } from '@element-plus/icons-vue'
import { convertKeysToKebabCase } from '@/utils/convert'
import {
  updateSubcatchmentByIdAxios,
  deleteSubcatchmentByIdAxios,
  saveSubcatchmentPolygonAxios,
} from '@/apis/subcatchment'
import { useViewerStore } from '@/stores/viewer'
import { initEntities } from '@/utils/useCesium'
import { POINTPREFIX, POLYGONPREFIX, HEIGHT_GEOID_OFFSET } from '@/utils/constant'
import * as Cesium from 'cesium'
import { ref } from 'vue'
import { addTempSubcatchmentConnectionLine } from '@/utils/entity'
import * as turf from '@turf/turf'

const viewerStore = useViewerStore()

const showDialog = defineModel('showDialog')
const subcatchmentEntity = defineModel('subcatchmentEntity')

const closeDialog = () => {
  if (polygonEditing.value) {
    ElMessage.warning('请先结束多边形编辑')
    return
  }
  showDialog.value = false
  viewerStore.clickedEntityDict = {}
}

const saveSubcatchment = () => {
  if (polygonEditing.value) {
    ElMessage.warning('请先结束多边形编辑')
    return
  }
  updateSubcatchmentByIdAxios(
    subcatchmentEntity.value.id,
    convertKeysToKebabCase(subcatchmentEntity.value),
  )
    .then((res) => {
      ElMessage.success(res.message)
      // 更新 Cesium 中的实体数据
      initEntities(viewerStore.viewer)
      const id = POLYGONPREFIX + res.data.id
      // 更新 id，解决不关闭弹窗时候，重复保存时，selectedEntity的id还是原来旧id的问题
      subcatchmentEntity.value.id = id
    })
    .catch((error) => {
      console.log(error)
    })
}

const deleteConduitEntity = () => {
  if (polygonEditing.value) {
    ElMessage.warning('请先结束多边形编辑')
    return
  }
  deleteSubcatchmentByIdAxios(subcatchmentEntity.value.id)
    // TODO: 添加所以删除 dialog 再确定
    .then((res) => {
      ElMessage.success(res.message)
      // 更新 Cesium 中的实体数据
      initEntities(viewerStore.viewer)
      // 删除结束后，关闭弹窗
      showDialog.value = false
    })
    .catch((error) => {
      console.log(error)
    })
}

const calculateArea = () => {
  const polygonEntity = viewerStore.viewer.entities.getById(subcatchmentEntity.value.id)
  if (!polygonEntity) {
    ElMessage.error('计算失败，子汇水区多边形实体获取失败')
    return
  }
  const positions = polygonEntity.polygon.hierarchy.getValue().positions
  if (positions.length < 3) {
    ElMessage.error('计算失败，子汇水区多边形顶点数不足')
    return
  }
  // 转换为经纬度数组
  const cartographics = positions.map((pos) => Cesium.Cartographic.fromCartesian(pos))
  const coordinates = cartographics.map((c) => [
    Cesium.Math.toDegrees(c.longitude),
    Cesium.Math.toDegrees(c.latitude),
  ])
  // turf 多边形坐标需首尾闭合
  if (
    coordinates.length > 0 &&
    (coordinates[0][0] !== coordinates[coordinates.length - 1][0] ||
      coordinates[0][1] !== coordinates[coordinates.length - 1][1])
  ) {
    coordinates.push(coordinates[0])
  }
  // 构造 turf polygon
  const polygon = turf.polygon([coordinates])
  const area = turf.area(polygon) // 返回平方米
  subcatchmentEntity.value.area = Math.round(area)
  ElMessage.success('面积计算成功')
}

const calculateWidth = () => {
  const polygonEntity = viewerStore.viewer.entities.getById(subcatchmentEntity.value.id)
  if (!polygonEntity) {
    ElMessage.error('计算失败：子汇水区多边形实体不存在')
    return
  }
  const outletEntity = viewerStore.viewer.entities.getById(
    POINTPREFIX + subcatchmentEntity.value.outlet,
  )
  if (!outletEntity) {
    ElMessage.error('计算失败：出水口实体不存在')
    return
  }
  const positions = polygonEntity.polygon.hierarchy.getValue().positions
  const outletPosition = outletEntity.position.getValue()
  if (positions.length < 3 || !outletPosition) {
    ElMessage.error('计算失败：顶点或出水口坐标无效')
    return
  }
  // 转换为经纬度
  const outletCarto = Cesium.Cartographic.fromCartesian(outletPosition)
  const outletLonLat = [
    Cesium.Math.toDegrees(outletCarto.longitude),
    Cesium.Math.toDegrees(outletCarto.latitude),
  ]
  const coordinates = positions.map((p) => {
    const c = Cesium.Cartographic.fromCartesian(p)
    return [Cesium.Math.toDegrees(c.longitude), Cesium.Math.toDegrees(c.latitude)]
  })
  // 计算最大路径长度（单位：米）
  let maxDistance = 0
  for (const coord of coordinates) {
    const from = turf.point(coord)
    const to = turf.point(outletLonLat)
    const dist = turf.distance(from, to, { units: 'meters' })
    if (dist > maxDistance) {
      maxDistance = dist
    }
  }
  if (maxDistance === 0) {
    ElMessage.error('计算失败：最大路径长度为0')
    return
  }
  // 用面积 / 最大路径长度 来估算代表性宽度
  const area = subcatchmentEntity.value.area
  const estimatedWidth = Math.round(area / maxDistance)
  subcatchmentEntity.value.width = Math.round(estimatedWidth)
  ElMessage.success(
    `宽度估算成功：S = ${area}㎡，L = ${Math.round(maxDistance)}m，W = ${estimatedWidth}m`,
  )
}

const calculateSlope = async () => {
  const polygonEntity = viewerStore.viewer.entities.getById(subcatchmentEntity.value.id)
  if (!polygonEntity) {
    ElMessage.error('计算失败：子汇水区多边形实体不存在')
    return
  }
  const outletEntity = viewerStore.viewer.entities.getById(
    POINTPREFIX + subcatchmentEntity.value.outlet,
  )
  if (!outletEntity) {
    ElMessage.error('计算失败：出水口实体不存在')
    return
  }

  const positions = polygonEntity.polygon.hierarchy.getValue().positions
  const outletPosition = outletEntity.position.getValue()
  if (positions.length < 3 || !outletPosition) {
    ElMessage.error('计算失败：顶点或出水口坐标无效')
    return
  }
  // 1. 转换多边形为经纬度坐标数组
  const coordinates = positions.map((p) => {
    const c = Cesium.Cartographic.fromCartesian(p)
    return [Cesium.Math.toDegrees(c.longitude), Cesium.Math.toDegrees(c.latitude)]
  })
  // 闭合多边形
  if (
    coordinates.length > 0 &&
    (coordinates[0][0] !== coordinates.at(-1)[0] || coordinates[0][1] !== coordinates.at(-1)[1])
  ) {
    coordinates.push(coordinates[0])
  }
  // 2. 生成内部点进行高程采样
  const turfPolygon = turf.polygon([coordinates])
  const grid = turf.pointGrid(turf.bbox(turfPolygon), 100, {
    units: 'meters',
    mask: turfPolygon,
  })
  const cartographicPoints = grid.features.map((pt) => {
    const [lon, lat] = pt.geometry.coordinates
    return Cesium.Cartographic.fromDegrees(lon, lat)
  })

  if (cartographicPoints.length === 0) {
    ElMessage.error('计算失败：未采样到多边形内部高程点')
    return
  }
  // 3. 使用 Cesium 地形服务采样高程
  const sampledPoints = await Cesium.sampleTerrainMostDetailed(
    viewerStore.viewer.terrainProvider,
    cartographicPoints,
  )
  // 4. 找出最高点
  let maxPoint = null
  let maxHeight = -Infinity
  for (const pt of sampledPoints) {
    if (pt.height > maxHeight) {
      maxHeight = pt.height
      maxPoint = pt
    }
  }
  // 补充高程误差
  maxHeight += HEIGHT_GEOID_OFFSET
  if (!maxPoint) {
    ElMessage.error('计算失败：最高点获取失败')
    return
  }
  // 5. 获取出水口高程
  const outletCarto = Cesium.Cartographic.fromCartesian(outletPosition)
  const deltaH = maxHeight - outletCarto.height
  const from = turf.point([
    Cesium.Math.toDegrees(maxPoint.longitude),
    Cesium.Math.toDegrees(maxPoint.latitude),
  ])
  const to = turf.point([
    Cesium.Math.toDegrees(outletCarto.longitude),
    Cesium.Math.toDegrees(outletCarto.latitude),
  ])
  const maxDistance = turf.distance(from, to, { units: 'meters' })
  if (maxDistance === 0) {
    ElMessage.error('计算失败：最大距离为0')
    return
  }

  // 6. 坡度 = Δh / L × 100
  const slopePercent = (deltaH / maxDistance) * 100
  const rounded = Math.round(slopePercent * 100) / 100
  subcatchmentEntity.value.slope = rounded
  if (rounded > 0) {
    ElMessage.success(
      `坡度估算成功：Δh = ${deltaH.toFixed(2)}m，L = ${maxDistance.toFixed(2)}m，坡度 = ${rounded}%`,
    )
  } else {
    ElMessage.warning(
      `坡度估算完成，但结果为负值：Δh = ${deltaH.toFixed(2)}m，L = ${maxDistance.toFixed(
        2,
      )}m，坡度 = ${rounded}%。可能由于出水口点高程较高`,
    )
  }
}

// 编辑多边形
const polygonEditing = ref(false)
let editingController = null

const startPolygonEdit = () => {
  polygonEditing.value = true
  const polygonEntity = viewerStore.viewer.entities.getById(subcatchmentEntity.value.id)
  viewerStore.systemCustomLeftClickManager.stop()
  editingController = enablePolygonEditing(viewerStore.viewer, polygonEntity)
  ElMessage.info('编辑提示：①拖动顶点  ②右键插入顶点  ③双击删除顶点')
}

const enablePolygonEditing = (viewer, originalPolygonEntity) => {
  originalPolygonEntity.show = false
  const positions = [...originalPolygonEntity.polygon.hierarchy.getValue().positions]

  const editablePolygonEntity = viewer.entities.add({
    polygon: {
      hierarchy: new Cesium.CallbackProperty(() => new Cesium.PolygonHierarchy(positions), false),
      material: Cesium.Color.YELLOW.withAlpha(0.5),
      clampToGround: true,
    },
  })

  const controlPoints = []

  const createControlPoint = (pos, index) => {
    return viewer.entities.add({
      position: pos,
      point: {
        color: Cesium.Color.RED,
        pixelSize: 10,
        heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
      },
      properties: {
        index,
        isControlPoint: true,
      },
    })
  }

  // 初始化控制点
  positions.forEach((pos, i) => {
    controlPoints[i] = createControlPoint(pos, i)
  })

  const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas)
  let draggingPoint = null

  // 拖拽开始
  handler.setInputAction((click) => {
    const picked = viewer.scene.pick(click.position)
    if (
      Cesium.defined(picked) &&
      picked.id &&
      picked.id.point &&
      picked.id.properties?.isControlPoint
    ) {
      draggingPoint = picked.id
      viewer.scene.screenSpaceCameraController.enableRotate = false
    }
  }, Cesium.ScreenSpaceEventType.LEFT_DOWN)

  // 拖拽中
  handler.setInputAction((movement) => {
    if (draggingPoint) {
      const cartesian = viewer.scene.pickPosition(movement.endPosition)
      if (cartesian) {
        draggingPoint.position = cartesian
        const index = draggingPoint.properties.index
        positions[index] = cartesian
      }
    }
  }, Cesium.ScreenSpaceEventType.MOUSE_MOVE)

  // 拖拽结束
  handler.setInputAction(() => {
    draggingPoint = null
    viewer.scene.screenSpaceCameraController.enableRotate = true
  }, Cesium.ScreenSpaceEventType.LEFT_UP)

  // 区别下面代码另外一种交互思路：
  // 加入删除/增加控制点的功能，可能类似参考swmm，右键出一个menu，有①删除、②插入
  // 右键插入一个多边形顶点
  handler.setInputAction((click) => {
    const picked = viewer.scene.pick(click.position)
    if (
      Cesium.defined(picked) &&
      picked.id &&
      picked.id.point &&
      picked.id.properties?.isControlPoint
    ) {
      const index = picked.id.properties.index

      const current = positions[index]
      const next = positions[(index + 1) % positions.length]
      const mid = Cesium.Cartesian3.midpoint(current, next, new Cesium.Cartesian3())

      // 在数组中插入中间点
      const insertIndex = index + 1
      positions.splice(insertIndex, 0, mid)

      // 重建所有控制点（包括 index 属性）
      controlPoints.forEach((e) => viewer.entities.remove(e))
      controlPoints.length = 0
      positions.forEach((pos, i) => {
        controlPoints[i] = createControlPoint(pos, i)
      })
    }
  }, Cesium.ScreenSpaceEventType.RIGHT_CLICK)

  // 双击左键删除一个多边形顶点
  handler.setInputAction((click) => {
    const picked = viewer.scene.pick(click.position)
    if (
      Cesium.defined(picked) &&
      picked.id &&
      picked.id.point &&
      picked.id.properties?.isControlPoint
    ) {
      if (positions.length <= 3) {
        ElMessage.warning('子区域多边形不能少于 3 个点，删除失败')
        return
      }

      const index = picked.id.properties.index
      positions.splice(index, 1)
      viewer.entities.remove(picked.id)
      controlPoints.splice(index, 1)
    }
  }, Cesium.ScreenSpaceEventType.LEFT_DOUBLE_CLICK)

  return {
    finish: () => {
      const polygonData = positions.map((pos) => {
        const cartographic = Cesium.Cartographic.fromCartesian(pos)
        return [
          Cesium.Math.toDegrees(cartographic.longitude),
          Cesium.Math.toDegrees(cartographic.latitude),
        ]
      })
      const data = {
        subcatchment: subcatchmentEntity.value.name,
        polygon: polygonData,
      }
      saveSubcatchmentPolygonAxios(data)
        .then((res) => {
          ElMessage.success(res.message)
          originalPolygonEntity.polygon.hierarchy = new Cesium.PolygonHierarchy(positions)
          const outletEntity = viewer.entities.getById(
            POINTPREFIX + subcatchmentEntity.value.outlet,
          )
          console.log('out', outletEntity)
          console.log('origin', originalPolygonEntity)
          addTempSubcatchmentConnectionLine(viewer, originalPolygonEntity, outletEntity)
        })
        .finally(() => {
          viewer.entities.remove(editablePolygonEntity)
          controlPoints.forEach((e) => viewer.entities.remove(e))
          handler.destroy()
          originalPolygonEntity.show = true
        })
    },
    cancel: () => {
      originalPolygonEntity.show = true
      viewer.entities.remove(editablePolygonEntity)
      controlPoints.forEach((e) => viewer.entities.remove(e))
      handler.destroy()
    },
  }
}

// 结束编辑，应用修改
const finishEdit = () => {
  if (editingController) {
    editingController.finish()
    editingController = null
  }
  polygonEditing.value = false
  viewerStore.systemCustomLeftClickManager.start()
}

// 取消编辑，不保存修改
const cancelEdit = () => {
  if (editingController) {
    editingController.cancel()
    editingController = null
  }
  polygonEditing.value = false
  viewerStore.systemCustomLeftClickManager.start()
  ElMessage.info('多边形编辑已取消')
}

// 产流对话框
const showSubareaDialog = ref(false)

// 渗透对话框
const showInfiltrationDialog = ref(false)

// 雨量计选择对话框
const showTimeSeriesDialog = ref(false)
</script>

<style scoped>
.popup-container {
  position: fixed;
  top: 10px;
  right: 10px;
  z-index: 1000;
  height: 10px;
}

.popup-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 5px;
  font-weight: bold;
  border-bottom: 1px solid #ebeef5;
}
.popup-title {
  font-size: 16px;
}
.popup-form {
  display: flex;
  flex-direction: column;
  padding: 10px 0;
}
.popup-footer {
  display: flex;
  justify-content: flex-end;
  padding-top: 10px;
  border-top: 1px solid #ebeef5;
}

.popup-form .el-form-length {
  --el-input-width: 128px;
}
.popup-form .el-form-length-button {
  margin-left: 10px;
}
</style>
