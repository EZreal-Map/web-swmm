import { createApp } from 'vue'
import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
// 导入 highlight.js 样式
// import 'highlight.js/styles/atom-one-dark.css'  // TODO：目前 markdown 代码样式没有
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
