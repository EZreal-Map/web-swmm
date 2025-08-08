import { findEntityByName, flyToEntity } from '@/utils/entity'

export const flyToEntityByNameTool = (viewerStore, name) => {
  const { entity, cartesian, typeMessageName } = findEntityByName(viewerStore.viewer, name)

  if (entity && cartesian) {
    flyToEntity(viewerStore, entity, cartesian)
    console.log('已找到实体：', name, '类型：', typeMessageName)
    // ElMessage.success('已找到' + typeMessageName + '：' + name)
  } else {
    throw new Error('未找到实体：' + name)
  }
}
