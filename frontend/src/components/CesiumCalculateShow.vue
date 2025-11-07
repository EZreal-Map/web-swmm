<template>
  <div id="cesiumCalculateContainer"></div>

  <div class="time-overlay">
    <select v-model="selectedTime" @change="onTimeChange">
      <option v-for="(time, index) in timeList" :key="index" :value="time">
        {{ time }}
      </option>
    </select>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import * as Cesium from 'cesium'
import { getCalculateShowAxios } from '@/apis/show'

// 当前时间步标签
const selectedTime = ref('')
const timeList = ref([])

const currentIndex = ref(0)
const conduitEntities = [] // 存储所有 polyline 实体

const onTimeChange = () => {
  const index = timeList.value.indexOf(selectedTime.value)
  console.log('index:', index)
  if (index !== -1) {
    currentIndex.value = index
    updateEntityColors()
  }
}

// 更新实体颜色 (重要)
const updateEntityColors = () => {
  selectedTime.value = timeList.value[currentIndex.value]
  conduitEntities.forEach((entity) => {
    const flow = entity.properties.flow.getValue()
    const flowValue = flow.data?.[currentIndex.value] ?? 0
    const minFlow = flow.min
    const maxFlow = flow.max
    const color = getColorByValue(flowValue, minFlow, maxFlow)
    entity.polyline.material = color
  })
}

const getColorByValue = (value, min, max) => {
  // 归一化
  let normalizedValue = (value - min) / (max - min)
  normalizedValue = Math.min(Math.max(normalizedValue, 0.0), 1.0)

  // const colorStart = Cesium.Color.LIGHTBLUE
  const colorStart = new Cesium.Color(0.2, 0.6, 0.8, 1.0) // 浅蓝
  const colorEnd = Cesium.Color.BLUE

  // 创建一个空的 Cesium.Color 对象作为 result
  const result = new Cesium.Color()
  Cesium.Color.lerp(colorStart, colorEnd, normalizedValue, result)

  return result.withAlpha(0.8)
}

onMounted(async () => {
  Cesium.Ion.defaultAccessToken =
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJkNjQ5ODdiMy02NTIxLTQ2YWYtODJkNC0yYmIzMDdhNTRjYTkiLCJpZCI6MTU1ODM0LCJpYXQiOjE2OTMyNzIwNDh9.7oNx5xlOUJNC9qfJJ_csPvDWFXqmqFce-gxF2qFu-18'
  const viewer = new Cesium.Viewer('cesiumCalculateContainer', {
    geocoder: false, //隐藏查找控件
    homeButton: false, //隐藏视角返回初始位置按钮
    sceneModePicker: false, //隐藏视角模式3D 2D CV
    baseLayerPicker: false, //隐藏图层选择
    navigationHelpButton: false, //隐藏帮助
    animation: false, //隐藏动画控件
    timeline: false, //隐藏时间线控件
    fullscreenButton: false, //隐藏全屏
  })

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

  const response = await getCalculateShowAxios()

  if (response.code !== 200) {
    console.error('获取数据失败:', response.message)
    ElMessage.error(response.message)
    return
  }

  timeList.value = response.data.time

  const variablesExtremes = response.data.variables_extremes
  // console.log('变量极值:', variablesExtremes)

  const calculateResult = response.data.calculate_result

  // console.log('计算结果:', calculateResult)
  calculateResult.forEach((e) => {
    const fromNode = Cesium.Cartesian3.fromDegrees(e.from_node.lon, e.from_node.lat)
    const toNode = Cesium.Cartesian3.fromDegrees(e.to_node.lon, e.to_node.lat)

    const entity = viewer.entities.add({
      id: 'show-conduit#' + e.name,
      name: e.name,
      polyline: {
        positions: [fromNode, toNode],
        width: 10,
        material: Cesium.Color.BLUE.withAlpha(0.5), // 初始颜色
        arcType: Cesium.ArcType.GEODESIC,
      },
      properties: {
        flow: {
          data: e.flow,
          max: variablesExtremes.flow.max,
          min: variablesExtremes.flow.min,
        },
        depth: {
          data: e.depth,
          max: variablesExtremes.depth.max,
          min: variablesExtremes.depth.min,
        },
        velocity: {
          data: e.velocity,
          max: variablesExtremes.velocity.max,
          min: variablesExtremes.velocity.min,
        },
      },
    })

    // 提示框
    const midPoint = Cesium.Cartesian3.midpoint(fromNode, toNode, new Cesium.Cartesian3())
    const labelEntity = viewer.entities.add({
      position: midPoint,
      label: {
        show: false, // 初始不显示
        text: new Cesium.CallbackProperty(() => {
          const flow = e.flow[currentIndex.value] ?? 0
          const depth = e.depth[currentIndex.value] ?? 0
          const velocity = e.velocity[currentIndex.value] ?? 0
          return `             ${e.name}\n流量：${flow.toFixed(1)} m³/s \n水深：${depth.toFixed(2)}m\n流速：${velocity.toFixed(2)}m/s`
        }, false),
        font: 'bold 12px sans-serif',
        fillColor: Cesium.Color.SKYBLUE,
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 3,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        pixelOffset: new Cesium.Cartesian2(10, 0),
        showBackground: true,
        backgroundColor: new Cesium.Color(0, 0, 0, 0.5),
        backgroundPadding: new Cesium.Cartesian2(8, 6),
        horizontalOrigin: Cesium.HorizontalOrigin.LEFT, // 设置为左对齐
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        scale: 1.2,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
    })

    // 将 labelEntity 附加到 conduit 实体上（假设 entity 是管线实体）
    entity.labelEntity = labelEntity
    entity.isLabelVisible = false

    conduitEntities.push(entity)
  })

  // label 点击事件，显示/隐藏 label
  const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas)

  handler.setInputAction((movement) => {
    const pickedObject = viewer.scene.pick(movement.position)
    if (Cesium.defined(pickedObject) && pickedObject.id) {
      const pickedEntity = pickedObject.id
      if (pickedEntity.labelEntity) {
        pickedEntity.isLabelVisible = !pickedEntity.isLabelVisible
        pickedEntity.labelEntity.label.show = pickedEntity.isLabelVisible
      }
    }
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK)

  // function getColorByFlow(flow) {
  //   if (flow < 10) {
  //     return Cesium.Color.LIGHTBLUE.withAlpha(0.6)
  //   } else if (flow < 50) {
  //     return Cesium.Color.BLUE.withAlpha(0.6)
  //   } else if (flow < 100) {
  //     return Cesium.Color.ORANGE.withAlpha(0.6)
  //   } else {
  //     return Cesium.Color.RED.withAlpha(0.6)
  //   }
  // }

  const totalSteps = response.data.time.length
  setInterval(() => {
    currentIndex.value = (currentIndex.value + 1) % totalSteps
    updateEntityColors()
  }, 1000)
})
</script>

<style scoped>
#cesiumCalculateContainer {
  width: 100%;
  height: 100%;
  padding: 0;
  margin: 0;
  overflow: hidden;
}
.time-overlay {
  position: absolute;
  top: 10px;
  left: 10px;
  background: rgba(30, 30, 30, 0.7);
  color: #fff;
  border-radius: 8px;
  font-size: 14px;
  z-index: 10;
  display: flex;
  align-items: center;
}

.time-overlay label {
  font-size: 16px;
  font-weight: bold;
  margin-right: 12px;
}

.time-overlay select {
  appearance: none; /* 移除默认样式 */
  background-color: transparent;
  color: #fff;
  border: 0px;
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 20px;
  transition: all 0.2s ease;
  cursor: pointer;
  min-width: 100px;
  padding: 8px 16px;
}

/* 鼠标悬停或聚焦时更明显 */
.time-overlay select:hover {
  border-color: #aaa;
  background-color: rgba(255, 255, 255, 0.05);
  box-shadow: 0 0 4px rgba(255, 255, 255, 0.2);
  outline: none;
}

/* 下拉项背景颜色 */
.time-overlay option {
  background-color: #222;
  color: #fff;
}

/* 美化滚动条轨道 */
.time-overlay select::-webkit-scrollbar {
  width: 0px;
}
</style>
