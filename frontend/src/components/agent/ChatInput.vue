<template>
  <div class="chat-input-container">
    <div class="input-actions">
      <div class="input-row" style="position: relative">
        <!-- 聊天输入框 -->
        <textarea
          ref="textareaRef"
          v-model="inputText"
          placeholder="请输入您的问题..."
          :disabled="disabled"
          @keydown="handleKeydown"
          @input="onInput"
          rows="1"
          class="chat-input"
        ></textarea>
        <!-- 发送按钮 -->
        <button @click="handleSend" :disabled="disabled || !inputText.trim()" class="send-btn">
          <svg viewBox="0 0 24 24" width="16" height="16">
            <path fill="currentColor" d="M2,21L23,12L2,3V10L17,12L2,14V21Z" />
          </svg>
        </button>
        <!-- 工具下拉框，仅支持鼠标 hover 高亮 -->
        <ul v-if="showToolDropdown" class="tool-dropdown">
          <li v-for="tool in toolList" :key="tool.key" @mousedown.prevent="selectTool(tool)">
            {{ tool.label }}
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { useViewerStore } from '@/stores/viewer'
import * as Cesium from 'cesium'

// ========== 基础数据与响应式 ========== //
const viewerStore = useViewerStore() // 地图 viewer store
const textareaRef = ref(null) // 输入框 DOM 引用
const inputText = defineModel({ type: String, default: '' }) // 聊天输入内容
const showToolDropdown = ref(false) // 是否显示工具下拉
const toolList = [
  // 工具列表
  { key: 'pick-coord', label: '拾取地图坐标' },
  { key: 'get-bounds', label: '拾取地图边界' },
]

const props = defineProps({
  disabled: {
    type: Boolean,
    default: false,
  },
})
const emit = defineEmits(['send', 'tool']) // 组件事件

// ========== 输入框与下拉逻辑 ========== //

// 输入框高度自适应
function adjustHeight() {
  nextTick(() => {
    const textarea = textareaRef.value
    if (textarea) {
      textarea.style.height = 'auto'
      const maxHeight = 120
      const scrollHeight = textarea.scrollHeight
      textarea.style.height = Math.min(scrollHeight, maxHeight) + 'px'
      textarea.style.overflowY = scrollHeight > maxHeight ? 'auto' : 'hidden'
    }
  })
}

// 监听输入@，唤起工具下拉
function onInput() {
  adjustHeight()
  const val = inputText.value.trimEnd() // 去除末尾空格和换行
  showToolDropdown.value = val.endsWith('@')
}

// 输入框键盘事件处理
// Esc 关闭下拉/取消地图工具，Enter 发送
function handleKeydown(e) {
  if (showToolDropdown.value && e.key === 'Escape') {
    showToolDropdown.value = false
    return
  }
  if (e.key === 'Escape') {
    cancelPickCoord() // 取消地图点拾取
    cancelDrawBounds() // 取消地图边界绘制
    return
  }
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

// 发送消息到父组件
function handleSend() {
  const message = inputText.value.trim()
  if (message && !props.disabled) {
    emit('send', message)
    inputText.value = ''
    nextTick(adjustHeight)
  }
}

// 选择工具（下拉点击）
function selectTool(tool) {
  showToolDropdown.value = false
  // 删除@符号
  if (inputText.value.endsWith('@')) {
    inputText.value = inputText.value.slice(0, -1)
  }
  if (tool.key === 'pick-coord') {
    ElMessage.info('请在地图上点击要拾取的点')
    startPickCoord()
  } else if (tool.key === 'get-bounds') {
    ElMessage.info('请在地图上依次点击边界点，右键结束，自动闭合')
    startDrawBounds()
  }
  emit('tool', tool.key)
  nextTick(adjustHeight)
}

// ========== 地图拾取/绘制工具 ========== //

// --- 单点拾取 ---
let pickHandler = null // 地图点拾取事件句柄
/**
 * 启动地图单点拾取模式，点击地图插入经纬度
 */
function startPickCoord() {
  const viewer = viewerStore.viewer
  if (!viewer || !viewer.scene) {
    ElMessage.error('地图未初始化')
    return
  }
  viewer._container.style.cursor = 'crosshair'
  if (pickHandler) {
    pickHandler.destroy()
    pickHandler = null
  }
  pickHandler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas)
  pickHandler.setInputAction((click) => {
    const cartesian = viewer.scene.pickPosition(click.position)
    if (!cartesian) {
      ElMessage.warning('未能拾取坐标')
      return
    }
    const cartographic = Cesium.Cartographic.fromCartesian(cartesian)
    const lon = Cesium.Math.toDegrees(cartographic.longitude)
    const lat = Cesium.Math.toDegrees(cartographic.latitude)
    insertCoordToInput(lon, lat)
    viewer._container.style.cursor = ''
    pickHandler.destroy()
    pickHandler = null
    ElMessage.success(`已拾取坐标: (${lon.toFixed(6)}, ${lat.toFixed(6)})`)
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK)
}
/**
 * 取消地图点拾取
 */
function cancelPickCoord() {
  const viewer = viewerStore.viewer
  if (pickHandler) {
    pickHandler.destroy()
    pickHandler = null
    if (viewer && viewer._container) viewer._container.style.cursor = ''
    ElMessage.info('已取消拾取坐标')
  }
}

// --- 多点边界绘制 ---
let boundsHandler = null // 边界绘制事件句柄
let boundsPositions = [] // 边界点数组
let boundsPolygonEntity = null // 多边形实体
let boundsTempLine = null // 临时线实体
let boundsTempMousePos = null // 鼠标当前点
let boundsPointEntities = [] // 红点实体数组
let boundsEscListener = null // Esc 监听器

/**
 * 启动地图边界绘制模式，左键添加点，右键结束，动态显示多边形和线
 */
function startDrawBounds() {
  const viewer = viewerStore.viewer
  if (!viewer || !viewer.scene) {
    ElMessage.error('地图未初始化')
    return
  }
  // 清理旧 handler/entity
  if (boundsHandler) boundsHandler.destroy()
  if (boundsPolygonEntity) viewer.entities.remove(boundsPolygonEntity)
  if (boundsTempLine) viewer.entities.remove(boundsTempLine)
  boundsPointEntities.forEach((e) => viewer.entities.remove(e))
  boundsHandler = null
  boundsPolygonEntity = null
  boundsTempLine = null
  boundsPointEntities = []
  boundsPositions = []
  boundsTempMousePos = null
  viewer._container.style.cursor = 'crosshair'
  boundsHandler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas)
  // 多边形实体
  boundsPolygonEntity = viewer.entities.add({
    polygon: {
      hierarchy: new Cesium.CallbackProperty(() => {
        if (boundsPositions.length === 0) return null
        if (boundsPositions.length === 1 && !boundsTempMousePos) return null
        if (boundsTempMousePos) {
          return new Cesium.PolygonHierarchy([...boundsPositions, boundsTempMousePos])
        } else {
          return new Cesium.PolygonHierarchy([...boundsPositions])
        }
      }, false),
      material: Cesium.Color.LIGHTSKYBLUE.withAlpha(0.3),
    },
  })
  // 鼠标移动，动态线
  boundsHandler.setInputAction((movement) => {
    if (boundsPositions.length === 0) return
    const currentPos = viewer.scene.pickPosition(movement.endPosition)
    if (!currentPos) return
    boundsTempMousePos = currentPos
    if (!boundsTempLine) {
      boundsTempLine = viewer.entities.add({
        polyline: {
          positions: new Cesium.CallbackProperty(() => {
            if (boundsPositions.length === 0) return []
            if (boundsTempMousePos) {
              return [...boundsPositions, boundsTempMousePos]
            } else {
              return [...boundsPositions]
            }
          }, false),
          width: 2,
          material: Cesium.Color.YELLOW,
          clampToGround: true,
        },
      })
    }
  }, Cesium.ScreenSpaceEventType.MOUSE_MOVE)
  // 左键添加点
  boundsHandler.setInputAction((click) => {
    const cartesian = viewer.scene.pickPosition(click.position)
    if (!cartesian) return
    boundsPositions.push(cartesian)
    // 红点标记
    const pt = viewer.entities.add({
      position: cartesian,
      point: {
        pixelSize: 8,
        color: Cesium.Color.RED,
        heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
      },
    })
    boundsPointEntities.push(pt)
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK)
  // 右键结束
  boundsHandler.setInputAction(() => {
    if (boundsPositions.length < 3) {
      ElMessage.warning('至少需要三个点')
      return
    }
    // 转经纬度
    const ellipsoid = Cesium.Ellipsoid.WGS84
    const coords = boundsPositions.map((pos) => {
      const carto = ellipsoid.cartesianToCartographic(pos)
      return [Cesium.Math.toDegrees(carto.longitude), Cesium.Math.toDegrees(carto.latitude)]
    })
    // 自动闭合
    if (
      coords.length > 2 &&
      (coords[0][0] !== coords[coords.length - 1][0] ||
        coords[0][1] !== coords[coords.length - 1][1])
    ) {
      coords.push([coords[0][0], coords[0][1]])
    }
    // 格式：[(),(),()]
    const str = '[' + coords.map((c) => `(${c[0].toFixed(6)},${c[1].toFixed(6)})`).join(',') + ']'
    insertCoordToInput(str)
    ElMessage.success('已获取边界')
    viewer._container.style.cursor = ''
    boundsHandler.destroy()
    boundsHandler = null
    if (boundsPolygonEntity) viewer.entities.remove(boundsPolygonEntity)
    if (boundsTempLine) viewer.entities.remove(boundsTempLine)
    boundsPointEntities.forEach((e) => viewer.entities.remove(e))
    boundsPolygonEntity = null
    boundsTempLine = null
    boundsPointEntities = []
    boundsTempMousePos = null
    // 移除全局 Esc 监听
    if (boundsEscListener) {
      window.removeEventListener('keydown', boundsEscListener)
      boundsEscListener = null
    }
  }, Cesium.ScreenSpaceEventType.RIGHT_CLICK)
  // Esc 取消监听
  boundsEscListener = function (e) {
    if (e.key === 'Escape') {
      cancelDrawBounds()
      window.removeEventListener('keydown', boundsEscListener)
      boundsEscListener = null
    }
  }
  window.addEventListener('keydown', boundsEscListener)
}
/**
 * 取消地图边界绘制
 */
function cancelDrawBounds() {
  const viewer = viewerStore.viewer
  if (boundsHandler) {
    boundsHandler.destroy()
    boundsHandler = null
    if (viewer && viewer._container) viewer._container.style.cursor = ''
    if (boundsPolygonEntity) viewer.entities.remove(boundsPolygonEntity)
    if (boundsTempLine) viewer.entities.remove(boundsTempLine)
    boundsPointEntities.forEach((e) => viewer.entities.remove(e))
    boundsPolygonEntity = null
    boundsTempLine = null
    boundsPointEntities = []
    boundsTempMousePos = null
    boundsPositions = []
    ElMessage.info('已取消边界绘制')
  }
  if (boundsEscListener) {
    window.removeEventListener('keydown', boundsEscListener)
    boundsEscListener = null
  }
}

// ========== 工具函数 ========== //

/**
 * 插入经纬度或边界到输入框光标处
 * @param {number|string} lonOrStr - 经度或边界字符串
 * @param {number} [lat] - 纬度
 */
function insertCoordToInput(lonOrStr, lat) {
  const textarea = textareaRef.value
  if (!textarea) return
  let coordStr = ''
  if (typeof lonOrStr === 'string') {
    coordStr = lonOrStr
  } else {
    coordStr = `(${lonOrStr.toFixed(6)},${lat.toFixed(6)})`
  }
  const start = textarea.selectionStart
  const end = textarea.selectionEnd
  const val = inputText.value
  inputText.value = val.slice(0, start) + coordStr + val.slice(end)
  nextTick(() => {
    textarea.setSelectionRange(start + coordStr.length, start + coordStr.length)
    textarea.focus()
    adjustHeight()
  })
}

// 初始化输入框高度
nextTick(adjustHeight)
</script>

<style scoped>
.chat-input-container {
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  padding: 12px;
  background: #fff;
  z-index: 9999; /* 确保input在最上层 */
}

.input-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.input-row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}

.chat-input {
  flex: 1;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 14px;
  line-height: 20px;
  resize: none;
  outline: none;
  transition: border-color 0.2s;
  height: 36px;
  max-height: 120px;
  font-family: inherit;
  box-sizing: border-box;
  overflow-y: auto;
}

.chat-input:focus {
  border-color: #667eea;
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.1);
}

.chat-input:disabled {
  background-color: #f8f9fa;
  cursor: not-allowed;
  opacity: 0.7;
}

.chat-input::placeholder {
  color: #94a3b8;
}

.send-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 6px;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.send-btn:disabled {
  background: #e2e8f0;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.send-btn:active:not(:disabled) {
  transform: translateY(0);
}

.send-btn svg {
  transition: transform 0.2s;
}

.send-btn:hover:not(:disabled) svg {
  transform: scale(1.1);
}
.tool-dropdown {
  position: absolute;
  left: 0;
  bottom: 44px;
  z-index: 10000;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(102, 126, 234, 0.1);
  min-width: 160px;
  padding: 4px 0;
  list-style: none;
  margin: 0;
  font-size: 15px;
  color: #333;
  overflow: hidden;
}
.tool-dropdown li {
  padding: 8px 18px;
  cursor: pointer;
  transition:
    background 0.18s,
    color 0.18s;
  user-select: none;
}
.tool-dropdown li:hover {
  background: #e6f0ff;
  color: #3366cc;
}
</style>
