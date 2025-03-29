<template>
  <div class="layout-container">
    <div class="left-menu"><LeftMenu></LeftMenu></div>
    <div class="cesium-container"><CesiumContainer></CesiumContainer></div>
  </div>
</template>

<script setup>
import LeftMenu from '@/components/LeftMenu.vue'
import CesiumContainer from '@/components/CesiumContainer.vue'
</script>

<style scoped>
.layout-container {
  display: flex; /* 使用 Flexbox 实现水平布局 */
  height: 100vh; /* 设置布局容器的高度为视口高度 */
}

.left-menu {
  width: 200px; /* 左侧菜单栏的宽度 */
  background-color: #fefefe; /* 背景色，可以根据需要调整 */
}

.cesium-container {
  flex-grow: 1; /* 右侧容器自适应剩余宽度 */
  background-color: #ffffff; /* 背景色，可以根据需要调整 */
}
</style>
