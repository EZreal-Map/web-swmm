import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useViewerStore = defineStore('viewer', () => {
  const viewer = null
  const clickedEntityDict = ref({}) // 用于存储点击的实体信息
  const remeberclickedEntityDict = ref({}) // 用于存储点击的实体信息
  const extractFlag = ref(false) // 用于标记是否提取数据
  const extractPoints = [] // 用于存储提取的点数据
  const systemCustomLeftClickManager = ref({
    start: () => {},
    stop: () => {},
  }) // 用于存储自定义鼠标左键点击事件管理器
  return {
    viewer,
    clickedEntityDict,
    remeberclickedEntityDict,
    extractFlag,
    extractPoints,
    systemCustomLeftClickManager,
  }
})
