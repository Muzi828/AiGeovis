import { createRouter, createWebHashHistory } from 'vue-router'

import HomeView from '../views/HomeView.vue'
import DataView from '../views/DataView.vue'
import VizView from '../views/VizView.vue'
import UserManage from '../views/userManage.vue'

const router = createRouter({
  history: createWebHashHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: { name: 'home' } },
    { path: '/home', name: 'home', component: HomeView, meta: { title: '首页' } },
    { path: '/data', name: 'data', component: DataView, meta: { title: '数据浏览' } },
    { path: '/viz', name: 'viz', component: VizView, meta: { title: '地理可视化' } },
    { path: '/user-manage', name: 'user-manage', component: UserManage, meta: { title: '用户管理' } },
  ]
})

export default router
