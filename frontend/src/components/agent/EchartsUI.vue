<template>
  <div class="echarts-ui">
    <div class="content-top-select">
      <el-row :gutter="10">
        <el-col :span="12">
          <el-form-item label="查询名称">
            <el-input
              v-model="queryEntityName"
              type="string"
              placeholder="请输入查询实体名称"
              @change="getQueryEntityKindSelect"
            >
            </el-input>
          </el-form-item>
        </el-col>

        <el-col :span="12">
          <el-form-item label="查询属性">
            <el-select
              v-model="variableSelect"
              type="string"
              no-data-text="请先输入正确的实体名称"
              placeholder="请选择查询实体属性"
              append-to=".message-content"
              @change="getQueryEntityResult"
            >
              <el-option
                v-for="item in variableSelectList"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              ></el-option>
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>
    </div>
    <div class="content-bottom-echart" ref="refChartDom"></div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import dayjs from 'dayjs'
import * as echarts from 'echarts'
import { getQueryEntityKindSelectAxios, getQueryEntityResultAxios } from '@/apis/calculate'

const entityKind = defineModel('entityKind')
const queryEntityName = defineModel('queryEntityName')
const variableSelect = defineModel('variableSelect')

const variableSelectList = ref([])
const resultData = ref([])

// 获取查询实体选项（查询属性）
const getQueryEntityKindSelect = async () => {
  const res = await getQueryEntityKindSelectAxios(queryEntityName.value)
  entityKind.value = res.data?.kind
  variableSelectList.value = res.data?.select
  if (!variableSelectList.value) {
    ElMessage.warning(`未找到 ${queryEntityName.value} 查询属性，请检查实体名称是否正确`)
    variableSelect.value = '' // 清空查询属性
    resultData.value = [] // 清空查询结果
  } else {
    // 查找是否有匹配查询属性，有则直接查询，无则用第一个属性作为默认值
    const found = variableSelectList.value.find((item) => item.value === variableSelect.value)
    if (found) {
      getQueryEntityResult()
    } else {
      variableSelect.value = variableSelectList.value[0]?.value || ''
      getQueryEntityResult()
    }
  }
}

// 获取查询结果
const getQueryEntityResult = async () => {
  const res = await getQueryEntityResultAxios(
    entityKind.value,
    queryEntityName.value,
    variableSelect.value,
  )
  resultData.value = res.data
}

const refChartDom = ref(null)
let myChart = null
let resizeObserver = null
const DATETIME_FORMAT = 'YYYY/MM/DD HH:mm'
const DATETIME_FORMAT_WITHOUT_YEAR = 'MM-DD HH:mm'

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
            padding: [20, 0, 0, 0],
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

// 初始化图表
watch(
  () => refChartDom.value,
  () => {
    myChart = echarts.init(refChartDom.value)
    // 使用 ResizeObserver 监听容器尺寸变化
    if (resizeObserver) resizeObserver.disconnect()
    resizeObserver = new ResizeObserver(() => {
      myChart && myChart.resize()
    })
    resizeObserver.observe(refChartDom.value)
    updateChart()
  },
  { once: true },
)

onBeforeUnmount(() => {
  if (resizeObserver) resizeObserver.disconnect()
})

onMounted(async () => {
  // 监听数据变化
  watch(
    () => resultData.value,
    () => {
      updateChart()
    },
  )
  // 初始数据
  await getQueryEntityKindSelect()
  await getQueryEntityResult()
})
</script>

<style scoped>
.echarts-ui {
  display: flex;
  flex-direction: column;
  height: 400px;
}

.content-top-select {
  padding: 10px 10px 0;
  margin-bottom: 8px;
}
.content-bottom-echart {
  flex: 1;
}
.button-right {
  text-align: right;
}
</style>
