import { findEntityByName, flyToEntity } from '@/utils/entity.js'
import { initEntities } from '@/utils/useCesium.js'
import { useViewerStore } from '@/stores/viewer'

export const flyToEntityByNameTool = async ({ entity_name: entityName }) => {
  const viewerStore = useViewerStore()
  const { entity, cartesian, typeMessageName } = findEntityByName(viewerStore.viewer, entityName)

  if (entity && cartesian) {
    flyToEntity(viewerStore, entity, cartesian)
    console.log('已找到实体：', entityName, '类型：', typeMessageName)
    ElMessage.success('已找到' + typeMessageName + '：' + entityName)
  } else {
    throw new Error('未找到实体：' + entityName)
  }
}

export const initEntitiesTool = async () => {
  const viewerStore = useViewerStore()
  await initEntities(viewerStore)
  ElMessage.success('刷新实体信息成功')
}
