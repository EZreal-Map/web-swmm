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
        <!-- 右侧内容区域 -->
        <div class="content">
          <div class="content-left">
            <div class="content-left-top">
              <el-form
                :inline="false"
                :model="calculateOpertions"
                label-width="120px"
                class="content-left-top-form"
              >
                <el-row :gutter="10">
                  <!-- 设置行间距 -->
                  <el-col :span="8">
                    <el-form-item label="开始计算时间">
                      <el-date-picker
                        v-model="calculateOpertions.start_datetime"
                        type="datetime"
                        placeholder="请选择开始计算时间"
                        :format="DATETIME_FORMAT"
                        :clearable="false"
                        style="width: 100%"
                        @change="updateCalculateOptions"
                      />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="开始报告时间">
                      <el-date-picker
                        v-model="calculateOpertions.start_report_datetime"
                        type="datetime"
                        placeholder="请选择开始报告时间"
                        :format="DATETIME_FORMAT"
                        :clearable="false"
                        style="width: 100%"
                        @change="updateCalculateOptions"
                      />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="结束计算时间">
                      <el-date-picker
                        v-model="calculateOpertions.end_datetime"
                        type="datetime"
                        placeholder="请选择结束计算时间"
                        :format="DATETIME_FORMAT"
                        :clearable="false"
                        style="width: 100%"
                        @change="updateCalculateOptions"
                      />
                    </el-form-item>
                  </el-col>
                </el-row>
                <el-row :gutter="10">
                  <!-- 设置行间距 -->
                  <el-col :span="8">
                    <el-form-item label="计算间隔时间">
                      <el-time-picker
                        v-model="calculateOpertions.report_step"
                        placeholder="请选择计算间隔时间"
                        :clearable="false"
                        style="width: 100%"
                        @change="updateCalculateOptions"
                      />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="演算模型">
                      <el-select
                        v-model="calculateOpertions.flow_routing"
                        type="string"
                        placeholder="请选择演算模型"
                        @change="updateCalculateOptions"
                      >
                        <el-option
                          v-for="item in FlowRoutingSelect"
                          :key="item.value"
                          :label="item.label"
                          :value="item.value"
                        ></el-option
                      ></el-select>
                    </el-form-item>
                  </el-col>
                  <!-- 按钮靠右 -->
                  <el-col :span="8" class="button-right">
                    <el-button type="primary" @click="startCalculateFunction">开始计算</el-button>
                  </el-col>
                </el-row>
              </el-form>
            </div>
            <div class="content-left-bottom">
              <div class="content-left-bottom-select">
                <el-form
                  :inline="false"
                  :model="calculateOpertions"
                  label-width="120px"
                  class="content-left-top-form"
                >
                  <el-row :gutter="10">
                    <!-- 设置行间距 -->
                    <el-col :span="8">
                      <el-form-item label="查询实体名称">
                        <el-input
                          v-model="getQueryEntityName"
                          type="string"
                          placeholder="请输入查询实体名称"
                          @change="getQueryEntityKindSelect"
                        >
                        </el-input>
                      </el-form-item>
                    </el-col>

                    <el-col :span="8">
                      <el-form-item label="查询实体属性">
                        <el-select
                          v-model="variableSelect"
                          type="string"
                          no-data-text="请先输入正确的实体名称"
                          placeholder="请选择查询实体属性"
                        >
                          <el-option
                            v-for="item in variableSelectList"
                            :key="item.value"
                            :label="item.label"
                            :value="item.value"
                          ></el-option
                        ></el-select>
                      </el-form-item>
                    </el-col>
                    <!-- 占位作用 -->
                    <el-col :span="8" class="button-right">
                      <el-button type="primary" @click="getQueryEntityResult"> 结果查询</el-button>
                    </el-col>
                  </el-row>
                </el-form>
              </div>
              <div class="content-left-bottom-chart" ref="refChartDom"></div>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import {
  getCalculateOptionsAxios,
  updateCalculateOptionsAxios,
  getQueryEntityKindSelectAxios,
  getQueryEntityResultAxios,
  calculateAxios,
} from '@/apis/calculate'
import dayjs from 'dayjs'
import * as echarts from 'echarts' // TODO: 这里是全部导入，功能完善以后，修改为按需导入

const showDialog = defineModel('showDialog')

const calculateOpertions = ref({}) // 计算选项数据 重要

const FlowRoutingSelect = [
  { value: 'STEADY', label: '恒定流' },
  { value: 'KINWAVE', label: '运动波' },
  { value: 'DYNWAVE', label: '动态波' },
]

const startCalculateFunction = () => {
  // 这里可以添加开始计算的逻辑
  calculateAxios().then((res) => {
    if (res.code == 200) {
      ElMessage.success(res.message)
    } else {
      ElMessage.error(res.message)
    }
  })
}

const initCalculateOpertions = () => {
  getCalculateOptionsAxios().then((res) => {
    // 使用 1970-01-01 作为默认日期，并拼接时间（因为前端el-time-picker需要时间格式，日期在这里无所谓）
    // 并且一定要加上时区，否则会出现时间错位的问题
    res.data.report_step = new Date(`1970-01-01T${res.data.report_step}+08:00`)
    // 这里需要将时间格式转换为 Date 对象
    res.data.start_datetime = new Date(res.data.start_datetime)
    res.data.start_report_datetime = new Date(res.data.start_report_datetime)
    res.data.end_datetime = new Date(res.data.end_datetime)
    // 赋值给计算选项（前端）
    calculateOpertions.value = res.data
  })
}
initCalculateOpertions()

const updateCalculateOptions = () => {
  // 检查所有的计算选项是否存在空值，如果存在，就提示并终止请求
  for (const key in calculateOpertions.value) {
    const val = calculateOpertions.value[key]
    if (!val) {
      ElMessage.warning('计算选项不能为空')
      return // 中断请求
    }
  }

  // 所有字段都校验通过，发送请求
  updateCalculateOptionsAxios(calculateOpertions.value).then((res) => {
    ElMessage.success(res.message)
  })
}

// 结果查询
// 1.查询实体名称
const getQueryEntityName = ref('') // 查询实体名称
const variableSelectList = ref([]) // 查询实体属性列表
const variableSelect = ref('') // 查询实体属性
const entityKind = ref('') // 查询实体类型
// 查询类型和属性
const getQueryEntityKindSelect = () => {
  if (!getQueryEntityName.value) {
    variableSelectList.value = [] // 如果没有选择实体名称，则清空属性选择列表
    variableSelect.value = '' // 清空属性选择
    entityKind.value = '' // 清空实体类型
    return
  }
  getQueryEntityKindSelectAxios(getQueryEntityName.value).then((res) => {
    if (res.code == 200) {
      variableSelectList.value = res.data.select
      variableSelect.value = res.data.select[0].value // 默认选择第一个属性
      entityKind.value = res.data.kind
      resultData.value = [] // 清空结果查询数据
      updateChart() // 更新图表
      ElMessage.success(res.message)
    } else {
      // 处理错误情况
      variableSelectList.value = [] // 清空属性选择
      variableSelect.value = '' // 清空属性选择
      entityKind.value = '' // 清空实体类型
      resultData.value = [] // 清空结果查询数据
      updateChart() // 更新图表
      ElMessage.error(res.message)
    }
  })
}
// 2.查询实体属性
const resultData = ref([]) // 结果查询数据
const getQueryEntityResult = () => {
  if (!getQueryEntityName.value || !variableSelect.value) {
    ElMessage.warning('查询实体名称和属性不能为空')
    return
  }
  getQueryEntityResultAxios(entityKind.value, getQueryEntityName.value, variableSelect.value).then(
    (res) => {
      if (res.code == 200) {
        // 处理结果查询
        resultData.value = res.data
        updateChart() // 更新图表
        ElMessage.success(res.message)
      } else {
        // 处理错误情况
        resultData.value = [] // 清空结果查询数据
        updateChart() // 更新图表
        ElMessage.error(res.message)
      }
    },
  )
}

// echarts 实例
let myChart = null
const refChartDom = ref(null)
const DATETIME_FORMAT = 'YYYY/MM/DD HH:mm' // 时间格式常量
const DATETIME_FORMAT_WITHOUT_YEAR = 'MM-DD HH:mm' // 时间格式常量

const updateChart = () => {
  try {
    if (myChart && resultData.value) {
      myChart.clear()
      if (resultData.value.length === 0) {
        myChart.setOption({
          title: {
            text: '暂无结果查询数据',
            left: 'center',
            top: 'center',
            textStyle: { fontSize: 20, color: '#999' },
          },
        })
        return
      }
      const data = resultData.value.map((item) => {
        return [new Date(item[0]), item[1]]
      })
      const yData = resultData.value.map((item) => item[1])
      // 获取 y 轴名称
      const yAxisName = variableSelectList.value.find(
        (i) => i.value === variableSelect.value,
      )?.label

      const option = {
        tooltip: {
          trigger: 'axis',
          formatter: function (params) {
            const date = params[0].value[0]
            const formattedDate = dayjs(date).format(DATETIME_FORMAT)
            return `${formattedDate}<br />${yAxisName}: ${params[0].value[1]}`
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
          name: yAxisName,
          min: Math.floor(Math.min(...yData)),
          max: Math.ceil(Math.max(...yData)),
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
            name: yAxisName,
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

// 监听 refChartDom 的变化，如果从null -> 有值，就是dom装载好了，可以初始化图表，并且只监听一次
// 需要放在 onMounted 的外面，要不然refChartDom.value 已经装载好了，没有监听到从 null 到有值的变化
watch(
  () => refChartDom.value,
  () => {
    myChart = echarts.init(refChartDom.value)
    window.onresize = () => {
      myChart.resize()
    }
    updateChart() // 第一次更新图表（初始化图表）
  },
  { once: true }, // 监听一次
)

onMounted(() => {
  // 监听 resultData 的变化，更新图表
  watch(
    () => resultData.value,
    () => {
      updateChart()
    },
  )
})
</script>

<style scoped>
.dialog-container {
  display: flex;
  height: 60vh;
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
  display: flex;
  flex-direction: column;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
}

.content-left-bottom-select {
  padding: 10px 10px 0;
  margin-bottom: 8px;
}

.content-left-bottom-chart {
  flex: 1; /* 占据剩余空间 */
}

.button-right {
  text-align: right; /* 按钮靠右 */
}

.dialog-footer {
  display: flex;
  justify-content: space-between; /* 左右靠边 */
  align-items: center; /* 垂直居中 */
}

.el-table th.gutter {
  display: table-cell !important;
}
</style>
