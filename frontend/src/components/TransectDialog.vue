<template>
  <div v-show="!viewerStore.extractFlag">
    <el-dialog
      v-model="showDialog"
      :modal="false"
      :lock-scroll="false"
      width="70%"
      draggable
      overflow
      :before-close="beforeClose"
      :close-on-click-modal="!viewerStore.extractFlag"
    >
      <div class="dialog-container">
        <!-- 左侧菜单 -->
        <el-aside class="sidebar">
          <div
            v-for="(item, index) in transectNames"
            :key="index"
            :class="['menu-item', { active: selectedTransectName === item }]"
            @click="updateTransect(item)"
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
                :model="transectDatas"
                label-width="80px"
                class="content-left-top-form"
              >
                <el-row :gutter="10">
                  <!-- 设置行间距 -->
                  <el-col :span="8">
                    <el-form-item label="断面名称">
                      <el-input v-model="transectDatas.name" placeholder="请输入断面名称" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="左岸编号">
                      <el-input
                        v-model="transectDatas.bank_station_left"
                        placeholder="请输入左岸编号"
                        type="number"
                        @blur="
                          transectDatas.bank_station_left = parseFloat(
                            transectDatas.bank_station_left,
                          )
                        "
                      />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="右岸编号">
                      <el-input
                        v-model="transectDatas.bank_station_right"
                        placeholder="请输入右岸编号"
                        type="number"
                        @blur="
                          transectDatas.bank_station_right = parseFloat(
                            transectDatas.bank_station_right,
                          )
                        "
                      />
                    </el-form-item>
                  </el-col>
                </el-row>

                <el-row :gutter="10">
                  <el-col :span="8">
                    <el-form-item label="渠道糙率">
                      <el-input
                        v-model="transectDatas.roughness_channel"
                        placeholder="请输入渠道糙率"
                        type="number"
                        @blur="
                          transectDatas.roughness_channel = parseFloat(
                            transectDatas.roughness_channel,
                          )
                        "
                      />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="左岸糙率">
                      <el-input
                        v-model="transectDatas.roughness_left"
                        placeholder="请输入左岸糙率"
                        type="number"
                        @blur="
                          transectDatas.roughness_left = parseFloat(transectDatas.roughness_left)
                        "
                      />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="右岸糙率">
                      <el-input
                        v-model="transectDatas.roughness_right"
                        placeholder="请输入右岸糙率"
                        type="number"
                        @blur="
                          transectDatas.roughness_right = parseFloat(transectDatas.roughness_right)
                        "
                      />
                    </el-form-item>
                  </el-col>
                </el-row>
              </el-form>
            </div>
            <div class="content-left-bottom" ref="refChartDom"></div>
          </div>
          <div class="content-right">
            <el-table :data="transectDatas.station_elevations" border>
              <el-table-column label="X 坐标">
                <template #default="{ row }">
                  <el-input
                    v-model.number="row[1]"
                    placeholder="X 坐标"
                    type="number"
                    @mousewheel.prevent
                    @input="checkLastRow"
                  />
                </template>
              </el-table-column>
              <el-table-column label="Y 坐标">
                <template #default="{ row }">
                  <el-input
                    v-model.number="row[0]"
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
            <el-button type="success" @click="createTransect">新建</el-button>
            <el-button type="warning" @click="extractTransect">提取</el-button>
          </div>
          <div>
            <el-button type="danger" @click="deleteTransect">删除</el-button>
            <el-button type="primary" @click="saveTransect">保存</el-button>
          </div>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, onUnmounted } from 'vue'
import {
  getAllTransectsNameAxios,
  getTransectByIdAxios,
  updateTransectByIdAxios,
  createTransectAxios,
  deleteTransectByIdAxios,
} from '@/apis/transect'
import { getElevationProfile } from '@/utils/entity'
import { useViewerStore } from '@/stores/viewer'
import * as echarts from 'echarts' // TODO: 这里是全部导入，功能完善以后，修改为按需导入
import { ElMessage } from 'element-plus'
import { POLYLINEPREFIX } from '@/utils/constant'

const viewerStore = useViewerStore()
const showDialog = defineModel('showDialog')
const transectNames = ref([]) // 断面列表
// 接收父组件传入的断面名称
const props = defineProps({
  transectName: {
    type: String,
    default: '',
  },
})
const selectedTransectName = ref(props.transectName) // 选中的断面名称

const transectDatas = ref({}) // 断面数据 重要！
const refChartDom = ref(null)

// echarts 实例
let myChart = null
const transectInit = async () => {
  // 这里分成2个接口，一个是获取所有断面name，
  // 另一个是通过name获取断面数据，每次menu点击时，获取断面数据，
  // 同时 selectedMenuName 需要通过父组件传递，如果不传递，就是默认的第一个断面，去获取断面数据
  await updateTransectNames() // 获取所有断面名称
  // 如果没有传入断面名称或者传入的断面名错误（不存在在transectNames里），则默认选中第一个断面
  if (
    !selectedTransectName.value ||
    transectNames.value.includes(selectedTransectName.value) === false
  ) {
    if (transectNames.value.length > 0) {
      selectedTransectName.value = transectNames.value[0]
    } else {
      ElMessage.warning('没有断面数据，请新建断面吧！')
      transectDatas.value = {} // 清空断面数据
      return // 没有断面名称，直接返回
    }
  }
  await updateTransect(selectedTransectName.value) // 默认选中第一个断面
}

const updateTransectNames = async () => {
  const res = await getAllTransectsNameAxios()
  // 按照字符串排序
  res.data.sort((a, b) => a.localeCompare(b))
  // 更新断面名称列表
  transectNames.value = res.data
}

const updateTransect = (transectName) => {
  // menu 点击时，获取断面数据
  selectedTransectName.value = transectName
  getTransectByIdAxios(transectName).then((res) => {
    transectDatas.value = res.data
    transectDatas.value.station_elevations.push([]) // 初始时：为每个断面的 station_elevations 添加一行空数据
  })
}

const updateChart = () => {
  try {
    if (myChart && transectDatas.value) {
      const selectedTransect = transectDatas.value
      const leftThreshold = selectedTransect.bank_station_left
      const rightThreshold = selectedTransect.bank_station_right
      // 此处的 stationElevations 已做了处理，1. yx -> xy 2. 去除无效值 3.排序
      const stationElevations = selectedTransect.station_elevations
        .map(([y, x]) => [x, y]) // 交换坐标
        .filter(([x, y]) => x && y) // 排除 undefined / '' / null 的数据
        .sort((a, b) => a[0] - b[0]) // 按照 X 坐标升序排序
      // 为设置y坐标刻度
      const yData = stationElevations.map((xy) => xy[1])

      const leftBankData = stationElevations.filter((xy) => xy[0] <= leftThreshold)

      const rightBankData = stationElevations.filter((xy) => xy[0] >= rightThreshold)

      const channelData = stationElevations.filter(
        (xy) => xy[0] >= leftThreshold && xy[0] <= rightThreshold,
      )
      if (stationElevations.length === 0) {
        myChart.clear()
        myChart.setOption({
          title: {
            text: '暂无断面数据',
            left: 'center',
            top: 'center',
            textStyle: { fontSize: 20, color: '#999' },
          },
        })
        return
      }
      const option = {
        title: { text: '' },
        tooltip: {
          trigger: 'axis',
          backgroundColor: 'rgba(50, 50, 50, 0.8)',
          borderRadius: 8,
          textStyle: { color: '#fff' },
        },
        legend: {
          data: ['左岸', '渠道', '右岸'],
          textStyle: { fontSize: 14, color: '#333' },
        },
        xAxis: {
          type: 'value', // 直接用数值型 x 轴
          name: 'X',
          min: stationElevations[0][0],
          max: stationElevations[stationElevations.length - 1][0],
        },
        yAxis: {
          type: 'value',
          name: 'Y',
          min: Math.floor(Math.min(...yData)),
          max: Math.ceil(Math.max(...yData)),
          splitLine: { lineStyle: { type: 'dashed', color: '#ddd' } },
        },
        series: [
          {
            name: '左岸',
            type: 'line',
            data: leftBankData, // 这里直接用 [x, y] 格式
            symbol: 'circle', // 可选：点状显示数据
            symbolSize: 9,
            lineStyle: { width: 3, color: 'red' },
            itemStyle: { color: 'red' },
            areaStyle: {
              // 蓝色渐变填充
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(255, 0, 0, 0.5)' },
                { offset: 1, color: 'rgba(255, 0, 0, 0.2)' },
              ]),
            },
          },

          {
            name: '右岸',
            type: 'line',
            data: rightBankData, // 这里直接用 [x, y] 格式
            symbol: 'circle',
            symbolSize: 9,
            lineStyle: { width: 3, color: 'red' },
            itemStyle: { color: 'green' },
            areaStyle: {
              // 红色渐变填充
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(255, 0, 0, 0.5)' },
                { offset: 1, color: 'rgba(255, 0, 0, 0.2)' },
              ]),
            },
          },
          {
            name: '渠道',
            type: 'line',
            data: channelData, // 这里直接用 [x, y] 格式
            symbol: 'circle',
            symbolSize: 9,
            lineStyle: { width: 3, color: 'blue' },
            itemStyle: { color: 'blue' },
            areaStyle: {
              // 绿色渐变填充
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(0, 0, 255, 0.8)' },
                { offset: 1, color: 'rgba(0, 0, 255, 0.4)' },
              ]),
            },
          },
        ],
      }

      myChart.setOption(option)
    }
  } catch (error) {
    console.error('Error updating chart:', error)
  }
}

// 检查最后一行是否为空，如果为空，则添加一行
const checkLastRow = () => {
  const lastRow =
    transectDatas.value.station_elevations[transectDatas.value.station_elevations.length - 1]
  if (lastRow[0] && lastRow[1]) {
    transectDatas.value.station_elevations.push([]) // 新增一行空数据
  }
}

// 断面操作的4个按钮
// 1. 新建
const createTransect = () => {
  const name = '断面_' + Date.now() // 用时间戳作为断面名称
  // 新建请求
  createTransectAxios({ name }).then((res) => {
    ElMessage.success(res.message)
    transectNames.value.push(res.data.name) // 添加新断面名称
    transectNames.value.sort((a, b) => a.localeCompare(b)) // 排序
    selectedTransectName.value = res.data.name // 更新选中的断面名称
    updateTransect(selectedTransectName.value) // 更新断面数据
  })
}

// 2. 删除
const deleteTransect = async () => {
  // 删除请求
  const res = await deleteTransectByIdAxios(selectedTransectName.value)
  ElMessage.success(res.message)
  selectedTransectName.value = '' // 清空选中的断面名称
  await transectInit() // 更新断面数据
  // 如果有滚动条，就回到顶部
  const sidebarDom = document.querySelector('.sidebar')
  sidebarDom.scrollTop = 0
}

// 3. 保存
const saveTransect = () => {
  updateTransectByIdAxios(selectedTransectName.value, transectDatas.value)
    .then((res) => {
      ElMessage.success(res.message)

      // 1. 更新 viewer 中可能相关联的数据 (容易忽视)
      if (res.data.related_xsections.length > 0) {
        // 渠道弹窗（如果刚好修改的是渠道弹窗的关联 name ） 修改关联的断面名称
        if (viewerStore.clickedEntityDict?.transect === selectedTransectName.value) {
          viewerStore.clickedEntityDict.transect = transectDatas.value.name
        }
        // 更新 viewer 中 entity的 properties 的 transect
        res.data.related_xsections.forEach((item) => {
          const id = POLYLINEPREFIX + item
          const entity = viewerStore.viewer.entities.getById(id)
          if (entity) {
            entity.properties.transect.setValue(transectDatas.value.name)
          }
        })
      }

      // 2.更新弹窗数据
      selectedTransectName.value = transectDatas.value.name // 更新选中的断面名称
      transectInit() // 更新断面数据
    })
    .catch((error) => {
      console.error('Error saving transect:', error)
      transectDatas.value.station_elevations.push([]) // 新增一行空数据
    })
}

// 4. 提取
const showExtractDialog = ref(true)
const extractTransect = () => {
  viewerStore.extractFlag = true // 设置提取模式
  showExtractDialog.value = false
}

const beforeClose = (done) => {
  // 如果是提取模式，则不关闭弹窗
  if (!viewerStore.extractFlag) {
    showDialog.value = false
    done()
  }
  return
}

// 监听 refChartDom 的变化，如果从null -> 有值，就是dom装载好了，可以初始化图表，并且只监听一次
// 需要放在 onMounted 的外面，要不然refChartDom.value 已经装载好了，没有监听到从 null 到有值的变化
watch(
  () => refChartDom.value,
  () => {
    console.log('refChartDom.value', refChartDom.value)
    myChart = echarts.init(refChartDom.value)
    window.onresize = () => {
      myChart.resize()
    }
  },
  { once: true }, // 监听一次
)

// 记录异步watch监听，因为异步监听需要主动在销毁之前取消
let extractWatch

onMounted(async () => {
  await transectInit()

  // 监听 transectDatas 的变化，更新图表
  watch(
    () => transectDatas.value,
    () => {
      updateChart()
    },
    { deep: true }, // 深度监听 transectDatas
  )

  // 监听提取成功的事件
  // 同步语句创建的侦听器，会自动绑定到宿主组件实例上，并且会在宿主组件卸载时自动停止
  // 如果用异步回调创建一个侦听器，那么它不会绑定到当前组件上，你必须手动停止它，以防内存泄漏
  extractWatch = watch(
    () => viewerStore.extractPoints.length,
    async (newValue) => {
      if (newValue === 1) {
        ElMessage.warning('已经选中一个点，请再选中另外一个点')
      }
      if (newValue >= 2) {
        try {
          // 提取成功，关闭弹窗
          const result = await getElevationProfile(
            viewerStore.viewer,
            viewerStore.extractPoints[0],
            viewerStore.extractPoints[1],
          )
          transectDatas.value.station_elevations = result // 更新断面数据
          ElMessage.success('断面提取成功！')
        } catch (error) {
          console.error('提取失败', error)
          ElMessage.error('提取失败，请试着刷新页面，重新提取')
        } finally {
          viewerStore.extractPoints = [] // 清空提取点
          viewerStore.extractFlag = false // 关闭提取模式
          viewerStore.clickedEntityDict = viewerStore.remeberclickedEntityDict // 恢复之前的点击实体
          viewerStore.remeberclickedEntityDict = {} // 清空之前的点击实体
        }
      }
    },
  )
})

onUnmounted(() => {
  extractWatch() // 需要主动取消异步监听事件
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
  height: 100px; /* 上部固定高度 */
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 10px 10px 0;
  margin-bottom: 8px;
}

.content-left-bottom {
  flex: 1; /* 占据剩余空间 */
  border: 1px solid #dcdfe6;
  border-radius: 4px;
}

.content-right {
  display: flex;
  width: 210px;
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
