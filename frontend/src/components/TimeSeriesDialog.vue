<template>
  <div>
    <el-dialog
      v-model="showDialog"
      :modal="false"
      :lock-scroll="false"
      width="70%"
      draggable
      overflow
    >
      <div class="dialog-container">
        <!-- 左侧菜单 -->
        <el-aside class="sidebar">
          <div
            v-for="(item, index) in timeseriesNames"
            :key="index"
            :class="['menu-item', { active: selectedTimeseriesName === item }]"
            @click="updateTimeseries(item)"
          >
            {{ item }}
          </div>
        </el-aside>

        <!-- 右侧内容区域 -->
        <div class="content">
          <div class="content-left">
            <div class="content-left-top">
              <el-form
                :inline="false"
                :model="timeseriesDatas"
                label-width="80px"
                class="content-left-top-form"
              >
                <el-form-item label="时间序列名称" label-width="100px">
                  <el-input v-model="timeseriesDatas.name" placeholder="请输入时间序列名称" />
                </el-form-item>
              </el-form>
            </div>
            <div class="content-left-bottom" ref="refChartDom"></div>
          </div>
          <div class="content-right">
            <el-table :data="timeseriesDatas.data" border>
              <el-table-column label="时间">
                <template #default="{ row }">
                  <el-date-picker
                    v-model="row[0]"
                    type="datetime"
                    placeholder="请选择日期时间"
                    :format="DATETIME_FORMAT"
                    style="width: 100%"
                    @change="checkLastRow"
                  />
                </template>
              </el-table-column>
              <el-table-column :label="TIMESERIESTYPEP[props.timeseriesType]" width="100">
                <template #default="{ row }">
                  <el-input
                    v-model.number="row[1]"
                    placeholder="Y 坐标"
                    type="number"
                    @mousewheel.prevent
                    @input="checkLastRow"
                  />
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <div>
            <el-button type="success" @click="createTimeseries">新建</el-button>
          </div>
          <div>
            <el-button type="danger" @click="deleteTimeseries">删除</el-button>
            <el-button type="primary" @click="saveTimeseries">保存</el-button>
          </div>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import {
  getAllTimeSeriesNameAxios,
  getTimeseriesByIdAxios,
  updateTimeseriesByIdAxios,
  createTimeseriesAxios,
  deleteTimeseriesByIdAxios,
} from '@/apis/timeseries'
import * as echarts from 'echarts' // TODO: 这里是全部导入，功能完善以后，修改为按需导入
import { useViewerStore } from '@/stores/viewer'
import dayjs from 'dayjs'
import { POINTPREFIX, POLYGONPREFIX } from '@/utils/constant'

const viewerStore = useViewerStore()
const showDialog = defineModel('showDialog')
const timeseriesNames = ref([]) // 时间序列列表
// 接收父组件传入的时间序列名称
const props = defineProps({
  timeseriesName: {
    type: String,
    default: '',
  },
  timeseriesType: {
    type: String,
    default: 'INFLOW', // 默认是流量
  },
})

const TIMESERIESTYPEP = {
  INFLOW: '流量',
  RAINGAGE: '雨量',
}
// 创建 雨量时间序列的同时，绑定一个雨量计 （删除，更新时，雨量计也会更新）

// 检查 timeseriesType 是否在 TIMESERIESTYPEP 中
if (!Object.keys(TIMESERIESTYPEP).includes(props.timeseriesType)) {
  ElMessage.error(`timeseriesType "${props.timeseriesType}" 不在 TIMESERIESTYPEP 中，请检查！`)
}

const selectedTimeseriesName = ref(props.timeseriesName) // 选中的时间序列名称
const timeseriesDatas = ref({}) // 时间序列数据 重要！

// echarts 实例
let myChart = null
const refChartDom = ref(null)
const DATETIME_FORMAT = 'YYYY/MM/DD HH:mm' // 时间格式常量
const DATETIME_FORMAT_WITHOUT_YEAR = 'MM-DD HH:mm' // 时间格式常量

const timeseriesInit = async () => {
  // 这里分成2个接口，一个是获取所有时间序列name，
  // 另一个是通过name获取时间序列数据，每次menu点击时，获取时间序列数据，
  // 同时 selectedMenuName 需要通过父组件传递，如果不传递，就是默认的第一个时间序列，去获取时间序列数据
  await updateTimeseriesNames() // 获取所有时间序列名称
  // 如果没有传入时间序列名称或者传入的时间序列名错误（不存在在timeseriesNames里），则默认选中第一个时间序列
  if (
    !selectedTimeseriesName.value ||
    timeseriesNames.value.includes(selectedTimeseriesName.value) === false
  ) {
    if (timeseriesNames.value.length > 0) {
      selectedTimeseriesName.value = timeseriesNames.value[0]
    } else {
      ElMessage.warning(
        `没有${TIMESERIESTYPEP[props.timeseriesType]}时间序列数据，请新建${TIMESERIESTYPEP[props.timeseriesType]}时间序列吧！`,
      )
      timeseriesDatas.value = {} // 清空时间序列数据
      return // 没有时间序列名称，直接返回
    }
  }
  await updateTimeseries(selectedTimeseriesName.value) // 默认选中第一个时间序列
}

const updateTimeseriesNames = async () => {
  const res = await getAllTimeSeriesNameAxios(props.timeseriesType)
  // 按照字符串排序
  res.data.sort((a, b) => a.localeCompare(b))
  // 更新时间序列名称列表
  timeseriesNames.value = res.data
}

const updateTimeseries = (timeseriesName) => {
  // menu 点击时，获取时间序列数据
  selectedTimeseriesName.value = timeseriesName
  getTimeseriesByIdAxios(timeseriesName, props.timeseriesType).then((res) => {
    // 把时间字符串转换位时间对象
    res.data.data = res.data.data.map((item) => {
      return [new Date(item[0]), item[1]]
    })
    timeseriesDatas.value = res.data
    timeseriesDatas.value.data.push([]) // 初始时：为每个时间序列的 station_elevations 添加一行空数据
  })
}

const updateChart = () => {
  try {
    if (myChart && timeseriesDatas.value.data) {
      if (timeseriesDatas.value.data.length === 0) {
        myChart.clear()
        myChart.setOption({
          title: {
            text: '暂无时间序列数据',
            left: 'center',
            top: 'center',
            textStyle: { fontSize: 20, color: '#999' },
          },
        })
        return
      }
      // 清除无效的数据
      const data = timeseriesDatas.value.data
        .filter((item) => item[0] && item[1])
        .sort((a, b) => a[0] - b[0]) // 按照 X 坐标升序排序

      const option = {
        title: {
          text: `时间${TIMESERIESTYPEP[props.timeseriesType]}图`,
          top: '20px',
          left: 'center',
          textStyle: {
            fontSize: 18,
            color: '#333',
          },
        },
        tooltip: {
          trigger: 'axis',
          formatter: function (params) {
            const date = params[0].value[0]
            const formattedDate = dayjs(date).format(DATETIME_FORMAT)
            return `${formattedDate}<br />${TIMESERIESTYPEP[props.timeseriesType]}: ${params[0].value[1]}`
          },
        },
        xAxis: {
          type: 'time',
          name: '时间',
          nameTextStyle: {
            fontSize: 14,
            padding: [20, 0, 0, 0], // 增加与轴线的距离
            color: '#666',
          },
          axisLine: {
            show: true,
            lineStyle: {
              color: '#666',
            },
          },
          splitLine: {
            show: true,
            lineStyle: {
              type: 'dashed',
              color: '#ccc',
            },
          },
          axisLabel: {
            formatter: (xValue) => dayjs(xValue).format(DATETIME_FORMAT_WITHOUT_YEAR),
            interval: 'auto',
            fontSize: 12,
            rotate: 45,
            color: '#666',
          },
        },
        yAxis: {
          type: 'value',
          name: TIMESERIESTYPEP[props.timeseriesType],
          nameTextStyle: {
            fontSize: 14,
            padding: [0, 0, 10, 0],
            color: '#666',
          },
          axisLine: {
            show: true,
            lineStyle: {
              color: '#666',
            },
          },
          splitLine: {
            show: true,
            lineStyle: {
              type: 'dashed',
              color: '#ccc',
            },
          },
          axisLabel: {
            color: '#666',
            fontSize: 12,
          },
        },
        series: [
          {
            name: TIMESERIESTYPEP[props.timeseriesType],
            type: 'line',
            data,
            smooth: true,
            symbol: 'circle',
            symbolSize: 6,
            lineStyle: {
              color: '#5470C6',
            },
            itemStyle: {
              color: '#5470C6',
            },
          },
        ],
        grid: {
          top: 100, // 控制图整体下移，避免标题和图表贴太近
          bottom: 100, // 保证 x 轴文字旋转后不被遮挡
          left: 60,
          right: 60,
        },
      }

      myChart.setOption(option)
    }
  } catch (error) {
    console.error('Error updating chart:', error)
  }
}

// 检查最后一行是否为空，如果为空，则添加一行
const checkLastRow = () => {
  const lastRow = timeseriesDatas.value.data[timeseriesDatas.value.data.length - 1]
  if (lastRow[0] && lastRow[1]) {
    timeseriesDatas.value.data.push([]) // 新增一行空数据
  }
}

// 时间序列操作的4个按钮
// 1. 新建
const createTimeseries = () => {
  const name = `${TIMESERIESTYPEP[props.timeseriesType]}_${Date.now()}` // 用时间戳作为时间序列名称
  // // 新建请求
  createTimeseriesAxios({ name }, props.timeseriesType).then((res) => {
    ElMessage.success(res.message)
    timeseriesNames.value.push(res.data.name) // 添加新时间序列名称
    timeseriesNames.value.sort((a, b) => a.localeCompare(b)) // 排序
    selectedTimeseriesName.value = res.data.name // 更新选中的时间序列名称
    updateTimeseries(selectedTimeseriesName.value) // 更新时间序列数据
  })
}

// 2. 删除
const deleteTimeseries = async () => {
  // 删除请求
  const res = await deleteTimeseriesByIdAxios(selectedTimeseriesName.value, props.timeseriesType)
  ElMessage.success(res.message)
  selectedTimeseriesName.value = '' // 清空选中的时间序列名称
  await timeseriesInit() // 更新时间序列数据
  // 如果有滚动条，就回到顶部
  const sidebarDom = document.querySelector('.sidebar')
  sidebarDom.scrollTop = 0
}

// 3. 保存
const saveTimeseries = () => {
  updateTimeseriesByIdAxios(
    selectedTimeseriesName.value,
    timeseriesDatas.value,
    props.timeseriesType,
  )
    .then((res) => {
      ElMessage.success(res.message)
      // 1. 更新 viewer 中可能相关联的数据 (容易忽视)
      if (res.data.related_entity_ids.length > 0) {
        // 节点弹窗（如果刚好修改的是节点弹窗的关联 name ） 修改关联的节点 timeseries 名称
        if (viewerStore.clickedEntityDict?.timeseriesName === selectedTimeseriesName.value) {
          viewerStore.clickedEntityDict.timeseriesName = timeseriesDatas.value.name
        }
        // 更新 viewer 中 entity的 properties 的 timeseries
        res.data.related_entity_ids.forEach((item) => {
          let prefix = '' // 前缀
          if (props.timeseriesType === 'INFLOW') {
            prefix = POINTPREFIX
          } else if (props.timeseriesType === 'RAINGAGE') {
            prefix = POLYGONPREFIX
          }
          const id = prefix + item
          const entity = viewerStore.viewer.entities.getById(id)
          if (entity) {
            entity.properties.timeseriesName.setValue(timeseriesDatas.value.name)
          }
        })
      }
      // 2.更新弹窗数据
      selectedTimeseriesName.value = timeseriesDatas.value.name // 更新选中的时间序列名称
      timeseriesInit() // 更新时间序列数据
    })
    .catch((error) => {
      console.error('Error saving timeseries:', error)
      ElMessage.error('保存失败，请刷新重试')
    })
}

// 监听 refChartDom 的变化，如果从null -> 有值，就是dom装载好了，可以初始化图表，并且只监听一次
// 需要放在 onMounted 的外面，要不然refChartDom.value 已经装载好了，没有监听到从 null 到有值的变化
watch(
  () => refChartDom.value,
  () => {
    myChart = echarts.init(refChartDom.value)
    window.onresize = () => {
      myChart.resize()
    }
  },
  { once: true }, // 监听一次
)

onMounted(async () => {
  await timeseriesInit()

  // 监听 timeseriesDatas 的变化，更新图表
  watch(
    () => timeseriesDatas.value,
    () => {
      updateChart()
    },
    { deep: true }, // 深度监听 timeseriesDatas
  )
})
</script>

<style scoped>
.dialog-container {
  display: flex;
  height: 60vh;
}

.sidebar {
  width: 180px;
  font-weight: bold;
  padding: 10px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  overflow-y: auto;
}

.menu-item {
  padding: 4px;
  margin-bottom: 8px;
  cursor: pointer;
  border-radius: 4px;
  transition: 0.3s;
  background: #f5f7fa;
}

/* hover 时的样式 */
.menu-item:hover {
  background: #e5e7ea;
}

/* active 时的样式 */
.menu-item.active {
  background: #409eff; /* 颜色更深 */
  color: white;
  box-shadow: 0 0 5px rgba(64, 158, 255, 0.6); /* 添加阴影提升层次感 */
}

.content {
  flex: 1; /* 占据剩余空间 */
  display: flex;
  height: 100%;
}

.content-left {
  flex: 1; /* 占据剩余空间 */
  display: flex;
  flex-direction: column; /* 让子元素垂直排列 */
  width: 100%;
  margin: 0px 8px;
}

.content-left-top {
  height: 40px; /* 上部固定高度 */
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 10px 10px 0;
  margin-bottom: 8px;
}

/* .content-left-top-form {
  display: flex;
  flex-wrap: wrap;
} */

.content-left-bottom {
  flex: 1; /* 占据剩余空间 */
  border: 1px solid #dcdfe6;
  border-radius: 4px;
}

.content-right {
  display: flex;
  width: 305px;
  height: 100%;
  border-left: 1px solid #dcdfe6;
  overflow-y: auto;
  overflow-x: hidden;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
}

.dialog-footer {
  display: flex;
  justify-content: space-between; /* 左右靠边 */
  align-items: center; /* 垂直居中 */
}

.el-table th.gutter {
  display: table-cell !important;
}

/* 美化滚动条 */
::-webkit-scrollbar {
  width: 4px;
}

::-webkit-scrollbar-thumb {
  background: #c0c4cc;
  border-radius: 2px;
}

::-webkit-scrollbar-thumb:hover {
  background: #a6a9ad;
}

::-webkit-scrollbar-track {
  background: #f5f7fa;
}

::v-deep(input::-webkit-inner-spin-button) {
  -webkit-appearance: none;
}
</style>
