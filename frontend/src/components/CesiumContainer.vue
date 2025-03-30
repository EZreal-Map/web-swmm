<template>
  <div id="cesiumContainer"></div>
  <div v-if="showJunctionDialog">
    <JunctionDialog
      v-model:show-dialog="showJunctionDialog"
      v-model:junction-entity="clickedEntity"
    />
  </div>
  <div v-if="showConduitDialog">
    <ConduitDialog v-model:show-dialog="showConduitDialog" v-model:conduit-entity="clickedEntity" />
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import useCesium from '@/utils/useCesium'
import JunctionDialog from '@/components/JunctionDialog.vue'
import ConduitDialog from '@/components/ConduitDialog.vue'

// TODO: 解决默认导出/命名导出的问题，useCesium.js 默认导出的机制，重复加载initViewer，会不会浪费不必要的内存
const { initViewer, clickedEntity } = useCesium()
const showJunctionDialog = ref(false)
const showConduitDialog = ref(false)

watch(
  () => clickedEntity.value,
  (newEntity) => {
    if (newEntity) {
      if (newEntity.type === 'junction') {
        showJunctionDialog.value = true
        showConduitDialog.value = false
      }
      if (newEntity.type === 'conduit') {
        showJunctionDialog.value = false
        showConduitDialog.value = true
      }
    }
  },
)

onMounted(() => {
  initViewer('cesiumContainer')
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
