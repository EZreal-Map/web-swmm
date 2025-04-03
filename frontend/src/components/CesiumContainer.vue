<template>
  <div id="cesiumContainer"></div>
  <!-- 节点信息弹窗 -->
  <JunctionDialog
    v-if="showJunctionDialog"
    v-model:show-dialog="showJunctionDialog"
    v-model:junction-entity="viewerStore.clickedEntityDict"
  />

  <!-- 出口信息弹窗 -->
  <OutfallDialog
    v-if="showOutfallDialog"
    v-model:show-dialog="showOutfallDialog"
    v-model:outfall-entity="viewerStore.clickedEntityDict"
  />

  <!-- 管道信息弹窗 -->
  <ConduitDialog
    v-if="showConduitDialog"
    v-model:show-dialog="showConduitDialog"
    v-model:conduit-entity="viewerStore.clickedEntityDict"
  />
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { initCesium } from '@/utils/useCesium'
import JunctionDialog from '@/components/JunctionDialog.vue'
import OutfallDialog from '@/components/OutfallDialog.vue'
import ConduitDialog from '@/components/ConduitDialog.vue'
import { useViewerStore } from '@/stores/viewer'
import { highlightClickedEntityColor } from '@/utils/entity'

const viewerStore = useViewerStore()

const showJunctionDialog = ref(false)
const showOutfallDialog = ref(false)
const showConduitDialog = ref(false)

onMounted(async () => {
  initCesium('cesiumContainer')

  watch(
    () => viewerStore.clickedEntityDict,
    (newEntityDict, oldEntityDict) => {
      // 高亮变红选择实体
      highlightClickedEntityColor(viewerStore.viewer, oldEntityDict, true)
      highlightClickedEntityColor(viewerStore.viewer, newEntityDict, false)

      // 弹窗处理
      if (newEntityDict?.type) {
        if (newEntityDict.type === 'junction') {
          showJunctionDialog.value = true
          showOutfallDialog.value = false
          showConduitDialog.value = false
        }
        if (newEntityDict.type === 'outfall') {
          showJunctionDialog.value = false
          showOutfallDialog.value = true
          showConduitDialog.value = false
        }
        if (newEntityDict.type === 'conduit') {
          showJunctionDialog.value = false
          showOutfallDialog.value = false
          showConduitDialog.value = true
        }
      } else {
        showJunctionDialog.value = false
        showOutfallDialog.value = false
        showConduitDialog.value = false
      }
    },
  )
})
</script>

<style>
#cesiumContainer {
  width: 100%;
  height: 100%;
  padding: 0;
  margin: 0;
  overflow: hidden;
}

.cesium-widget-credits {
  display: none !important;
}
</style>
