import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useViewerStore = defineStore('viewer', () => {
  const viewer = null
  const clickedEntityDict = ref({}) // 用于存储点击的实体信息
  const remeberclickedEntityDict = ref({}) // 用于存储点击的实体信息
  const extractFlag = ref(false) // 用于标记是否提取数据
  const extractPoints = [] // 用于存储提取的点数据
  return { viewer, clickedEntityDict, remeberclickedEntityDict, extractFlag, extractPoints }
})
