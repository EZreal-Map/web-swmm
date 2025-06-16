<template>
  <div class="popup-container" v-show="!viewerStore.extractFlag">
    <el-card class="popup-card">
      <div class="popup-header">
        <span class="popup-title">子汇水区 信息详情</span>
        <el-icon @click="closeDialog"><CloseBold /></el-icon>
      </div>

      <el-form
        label-position="left"
        class="popup-form"
        label-width="70px"
        style="max-width: 268px"
        :size="'default'"
        v-model="subcatchmentEntity"
      >
        <el-form-item label="名字">
          <el-input v-model="subcatchmentEntity.name" type="string"></el-input>
        </el-form-item>
        <el-form-item label="雨量">
          <el-input
            v-model="subcatchmentEntity.rainGage"
            type="string"
            class="el-form-length"
          ></el-input>
          <el-button @click="calculateLength" class="el-form-length-button">更多</el-button>
        </el-form-item>
        <el-form-item label="出水口">
          <el-input v-model="subcatchmentEntity.outlet" type="string"></el-input>
        </el-form-item>
        <el-form-item label="面积">
          <el-input v-model.number="subcatchmentEntity.area" type="number" class="el-form-length">
          </el-input>
          <el-button @click="calculateLength" class="el-form-length-button">计算</el-button>
        </el-form-item>
        <el-form-item label="宽度">
          <el-input v-model.number="subcatchmentEntity.width" type="number" class="el-form-length">
          </el-input>
          <el-button @click="calculateLength" class="el-form-length-button">计算</el-button>
        </el-form-item>
        <el-form-item>
          <template #label>
            <el-tooltip effect="dark" content="百分比 (%)" placement="top">
              <span>不透水率</span>
            </el-tooltip>
          </template>
          <el-input v-model="subcatchmentEntity.imperviousness" type="number"></el-input>
        </el-form-item>
        <el-form-item label="坡度">
          <el-input v-model.number="subcatchmentEntity.slope" type="number" class="el-form-length">
          </el-input>
          <el-button @click="calculateLength" class="el-form-length-button">计算</el-button>
        </el-form-item>
        <!-- <el-form-item label="多边形">
          <el-button @click="calculateLength">更多</el-button>
        </el-form-item>
        <el-form-item label="汇流参数">
          <el-button @click="calculateLength">更多</el-button>
        </el-form-item>
        <el-form-item label="下渗参数">
          <el-button @click="calculateLength">更多</el-button>
        </el-form-item> -->
        <!-- 使用额外 div 包裹，使其不换行 -->
        <div style="display: flex; flex-wrap: wrap; column-gap: 8px; row-gap: 0px; width: 100%">
          <el-form-item label="汇流参数" style="margin-right: 0">
            <el-button @click="calculateLength">更多</el-button>
          </el-form-item>
          <el-form-item label="下渗参数" style="margin-right: 0">
            <el-button @click="calculateLength">更多</el-button>
          </el-form-item>
          <el-form-item label="多边形" style="margin-right: 0">
            <el-button @click="startPolygonEdit" v-if="!polygonEditing">编辑</el-button>
            <div v-else>
              <el-button @click="finishEdit">保存</el-button>
              <el-button @click="cancelEdit">取消</el-button>
            </div>
          </el-form-item>
        </div>
      </el-form>
      <div class="popup-footer">
        <el-button type="danger" @click="deleteConduitEntity">删除</el-button>
        <el-button type="primary" @click="saveSubcatchment">保存</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { CloseBold } from '@element-plus/icons-vue'
import { convertKeysToKebabCase } from '@/utils/convert'
import {
  updateSubcatchmentByIdAxios,
  deleteSubcatchmentByIdAxios,
  saveSubcatchmentPolygonAxios,
} from '@/apis/subcatchment'
import { useViewerStore } from '@/stores/viewer'
import { initEntities } from '@/utils/useCesium'
import { POINTPREFIX, POLYGONPREFIX } from '@/utils/constant'
import * as Cesium from 'cesium'
import { ref } from 'vue'
import { addTempSubcatchmentConnectionLine } from '@/utils/entity'

const viewerStore = useViewerStore()

const showDialog = defineModel('showDialog')
const subcatchmentEntity = defineModel('subcatchmentEntity')

const closeDialog = () => {
  if (polygonEditing.value) {
    ElMessage.warning('请先结束多边形编辑')
    return
  }
  showDialog.value = false
  viewerStore.clickedEntityDict = {}
}

const saveSubcatchment = () => {
  if (polygonEditing.value) {
    ElMessage.warning('请先结束多边形编辑')
    return
  }
  updateSubcatchmentByIdAxios(
    subcatchmentEntity.value.id,
    convertKeysToKebabCase(subcatchmentEntity.value),
  )
    .then((res) => {
      console.log(res)
      ElMessage.success(res.message)
      // 更新 Cesium 中的实体数据
      initEntities(viewerStore.viewer)
      const id = POLYGONPREFIX + res.data.id
      // 更新 id，解决不关闭弹窗时候，重复保存时，selectedEntity的id还是原来旧id的问题
      subcatchmentEntity.value.id = id
    })
    .catch((error) => {
      console.log(error)
    })
}

const deleteConduitEntity = () => {
  if (polygonEditing.value) {
    ElMessage.warning('请先结束多边形编辑')
    return
  }
  deleteSubcatchmentByIdAxios(subcatchmentEntity.value.id)
    // TODO: 添加所以删除 dialog 再确定
    .then((res) => {
      ElMessage.success(res.message)
      // 更新 Cesium 中的实体数据
      initEntities(viewerStore.viewer)
      // 删除结束后，关闭弹窗
      showDialog.value = false
    })
    .catch((error) => {
      console.log(error)
    })
}

// 计算长度的函数
const calculateLength = () => {
  // 获取渠道的起点和终点坐标
  // const fromNodePostion = viewerStore.viewer.entities
  //   .getById('junction#' + subcatchmentEntity.value.fromNode)
  //   ?.position.getValue()
  // if (!fromNodePostion) {
  //   ElMessage.error(`计算失败，${subcatchmentEntity.value.fromNode} 坐标获取失败`)
  //   return
  // }
  // const toNodePostion = viewerStore.viewer.entities
  //   .getById('junction#' + subcatchmentEntity.value.toNode)
  //   ?.position.getValue()
  // if (!toNodePostion) {
  //   ElMessage.error(`计算失败，${subcatchmentEntity.value.toNode} 坐标获取失败`)
  //   return
  // }
  // // 计算两点的直线距离
  // const distance = Cesium.Cartesian3.distance(fromNodePostion, toNodePostion)
  // // 节点保留2位小数
  // subcatchmentEntity.value.length = Number(distance.toFixed(2))
  // ElMessage.success('长度计算成功')
  ElMessage.warning('功能尚未实现')
}

// 编辑多边形
const polygonEditing = ref(false)
let editingController = null

const startPolygonEdit = () => {
  polygonEditing.value = true
  const polygonEntity = viewerStore.viewer.entities.getById(subcatchmentEntity.value.id)
  viewerStore.systemCustomLeftClickManager.stop()
  editingController = enablePolygonEditing(viewerStore.viewer, polygonEntity)
}

const enablePolygonEditing = (viewer, originalPolygonEntity) => {
  originalPolygonEntity.show = false
  const positions = [...originalPolygonEntity.polygon.hierarchy.getValue().positions]

  const editablePolygonEntity = viewer.entities.add({
    polygon: {
      hierarchy: new Cesium.CallbackProperty(() => new Cesium.PolygonHierarchy(positions), false),
      material: Cesium.Color.YELLOW.withAlpha(0.5),
      clampToGround: true,
    },
  })

  const controlPoints = []

  const createControlPoint = (pos, index) => {
    return viewer.entities.add({
      position: pos,
      point: {
        color: Cesium.Color.RED,
        pixelSize: 10,
        heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
      },
      properties: {
        index,
        isControlPoint: true,
      },
    })
  }

  // 初始化控制点
  positions.forEach((pos, i) => {
    controlPoints[i] = createControlPoint(pos, i)
  })

  const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas)
  let draggingPoint = null

  // 拖拽开始
  handler.setInputAction((click) => {
    const picked = viewer.scene.pick(click.position)
    if (
      Cesium.defined(picked) &&
      picked.id &&
      picked.id.point &&
      picked.id.properties?.isControlPoint
    ) {
      draggingPoint = picked.id
      viewer.scene.screenSpaceCameraController.enableRotate = false
    }
  }, Cesium.ScreenSpaceEventType.LEFT_DOWN)

  // 拖拽中
  handler.setInputAction((movement) => {
    if (draggingPoint) {
      const cartesian = viewer.scene.pickPosition(movement.endPosition)
      if (cartesian) {
        draggingPoint.position = cartesian
        const index = draggingPoint.properties.index
        positions[index] = cartesian
      }
    }
  }, Cesium.ScreenSpaceEventType.MOUSE_MOVE)

  // 拖拽结束
  handler.setInputAction(() => {
    draggingPoint = null
    viewer.scene.screenSpaceCameraController.enableRotate = true
  }, Cesium.ScreenSpaceEventType.LEFT_UP)

  // TODO：想办法，加入删除控制点的功能，可能类似参考swmm，右键出一个menu，有①删除、②插入
  // 右键插入顶点
  handler.setInputAction((click) => {
    const picked = viewer.scene.pick(click.position)
    if (
      Cesium.defined(picked) &&
      picked.id &&
      picked.id.point &&
      picked.id.properties?.isControlPoint
    ) {
      const index = picked.id.properties.index

      const current = positions[index]
      const next = positions[(index + 1) % positions.length]
      const mid = Cesium.Cartesian3.midpoint(current, next, new Cesium.Cartesian3())

      // 在数组中插入中间点
      const insertIndex = index + 1
      positions.splice(insertIndex, 0, mid)

      // 重建所有控制点（包括 index 属性）
      controlPoints.forEach((e) => viewer.entities.remove(e))
      controlPoints.length = 0
      positions.forEach((pos, i) => {
        controlPoints[i] = createControlPoint(pos, i)
      })
    }
  }, Cesium.ScreenSpaceEventType.RIGHT_CLICK)

  return {
    finish: () => {
      const polygonData = positions.map((pos) => {
        const cartographic = Cesium.Cartographic.fromCartesian(pos)
        return [
          Cesium.Math.toDegrees(cartographic.longitude),
          Cesium.Math.toDegrees(cartographic.latitude),
        ]
      })
      const data = {
        subcatchment: subcatchmentEntity.value.name,
        polygon: polygonData,
      }
      saveSubcatchmentPolygonAxios(data)
        .then((res) => {
          ElMessage.success(res.message)
          originalPolygonEntity.polygon.hierarchy = new Cesium.PolygonHierarchy(positions)
          const outletEntity = viewer.entities.getById(
            POINTPREFIX + subcatchmentEntity.value.outlet,
          )
          console.log('out', outletEntity)
          console.log('origin', originalPolygonEntity)
          addTempSubcatchmentConnectionLine(viewer, originalPolygonEntity, outletEntity)
        })
        .finally(() => {
          viewer.entities.remove(editablePolygonEntity)
          controlPoints.forEach((e) => viewer.entities.remove(e))
          handler.destroy()
          originalPolygonEntity.show = true
        })
    },
    cancel: () => {
      originalPolygonEntity.show = true
      viewer.entities.remove(editablePolygonEntity)
      controlPoints.forEach((e) => viewer.entities.remove(e))
      handler.destroy()
    },
  }
}

// 结束编辑，应用修改
const finishEdit = () => {
  if (editingController) {
    editingController.finish()
    editingController = null
  }
  polygonEditing.value = false
  viewerStore.systemCustomLeftClickManager.start()
}

// 取消编辑，不保存修改
const cancelEdit = () => {
  if (editingController) {
    editingController.cancel()
    editingController = null
  }
  polygonEditing.value = false
  viewerStore.systemCustomLeftClickManager.start()
  ElMessage.info('多边形编辑已取消')
}
</script>

<style scoped>
.popup-container {
  position: fixed;
  top: 10px;
  right: 10px;
  z-index: 1000;
  height: 10px;
}

.popup-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 5px;
  font-weight: bold;
  border-bottom: 1px solid #ebeef5;
}
.popup-title {
  font-size: 16px;
}
.popup-form {
  display: flex;
  flex-direction: column;
  padding: 10px 0;
}
.popup-footer {
  display: flex;
  justify-content: flex-end;
  padding-top: 10px;
  border-top: 1px solid #ebeef5;
}

.popup-form .el-form-length {
  --el-input-width: 128px;
}
.popup-form .el-form-length-button {
  margin-left: 10px;
}
</style>
