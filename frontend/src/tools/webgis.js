import { findEntityByName, flyToEntity } from '@/utils/entity.js'
import { initEntities } from '@/utils/useCesium.js'
import { useViewerStore } from '@/stores/viewer'
import { ElMessage } from 'element-plus'

export const flyToEntityByNameTool = async (name) => {
  const viewerStore = useViewerStore()
  const { entity, cartesian, typeMessageName } = findEntityByName(viewerStore.viewer, name)

  if (entity && cartesian) {
    flyToEntity(viewerStore, entity, cartesian)
    console.log('已找到实体：', name, '类型：', typeMessageName)
    ElMessage.success('已找到' + typeMessageName + '：' + name)
  } else {
    throw new Error('未找到实体：' + name)
  }
}

export const initEntitiesTool = async () => {
  const viewerStore = useViewerStore()
  await initEntities(viewerStore)
  ElMessage.success('刷新实体信息成功')
}
