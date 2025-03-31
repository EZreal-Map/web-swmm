import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useViewerStore = defineStore('viewer', () => {
  const viewer = null
  const clickedEntityDict = ref({}) // 用于存储点击的实体信息
  return { viewer, clickedEntityDict }
})
