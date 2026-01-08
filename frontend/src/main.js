import { createApp } from 'vue'
import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
// 导入 highlight.js 样式（蓝调的 Tokyo Night Dark 主题）
import 'highlight.js/styles/tokyo-night-dark.css'
// 导入 自定义markdown样式
import '@/assets/markdown.css'

import App from './App.vue'
import router from './router'

const pinia = createPinia()
// pinia 持久化插件
pinia.use(piniaPluginPersistedstate)

const app = createApp(App)

app.use(pinia)
app.use(router)

app.mount('#app')
