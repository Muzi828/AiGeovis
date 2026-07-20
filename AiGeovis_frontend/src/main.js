import { createApp } from 'vue'
import axios from 'axios'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'

const app = createApp(App)
app.use(ElementPlus)
app.use(router)

// Keep compatibility for legacy Options API pages (e.g. userManage.vue)
// that call this.request.get/post directly.
app.config.globalProperties.request = axios.create({
  baseURL: 'https://smartdata.las.ac.cn/knowledgex/knowledgex_api',
  timeout: 120000,
})

for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.mount('#app')
