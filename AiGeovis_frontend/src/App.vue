<template>
  <el-container class="app-root" :class="{ 'app-dark': appDark }">
    <!-- 顶部导航 -->
    <el-header class="app-header" height="70px">
      <div class="header-inner">
        <img class="logo-img" src="./assets/img/logo.png" alt="AiGeovis logo" />

        <div class="header-right" v-if="!authDisabled">
          <template v-if="userName">
            <el-dropdown
              ref="userDropdownRef"
              trigger="click"
              :popper-class="appDark ? 'user-menu-dropdown user-menu-dropdown-dark' : 'user-menu-dropdown'"
              @command="onUserMenuCommand"
            >
              <div class="user-pill">
                <span class="user-text">
                  <span class="user-avatar" aria-hidden="true">
                    <svg t="1776851927062" class="icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="47685" width="20" height="20"><path d="M501.937582 545.097053c147.891962 0 268.231366-118.534055 268.223274-264.288929 0-145.746783-120.330301-264.28994-268.222263-264.28994-147.890951 0-268.221252 118.584625-268.221252 264.28994C233.71633 426.520519 354.046631 545.097053 501.937582 545.097053zM612.471463 570.546911 411.497184 570.546911c-186.760063 0-338.664249 149.569875-338.664249 333.472733l0 19.794109c0 96.139636 149.47278 96.139636 338.664249 96.139636l200.974278 0c181.747565 0 338.694591 0 338.694591-96.139636l0-19.794109C951.164031 720.158252 799.235571 570.546911 612.471463 570.546911z" fill="#429488" p-id="47686"></path></svg>
                  </span>
                  {{ userName }}
                </span>
              </div>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="user-manage">用户管理</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <span class="center-icon"> | </span>
            <span class="logout-btn" @click="logout">Logout</span>
          </template>
<!--          <el-button v-else type="primary" @click="authVisible = true">登录</el-button>-->
          <span v-else class="login" @click="authVisible = true" style="cursor: pointer;">Login / Register</span>
        </div>
      </div>
    </el-header>

    <!-- 主内容 -->
    <div class="app-main">
      <router-view
        :key="route.fullPath"
        :session-id="sessionId"
        :record-count="recordCount"
        @session-created="onSessionCreated"
        @session-cleared="onSessionCleared"
      />
    </div>

    <AuthModal
      v-if="!authDisabled"
      :visible="authVisible"
      Lang="CN"
      @close="authVisible = false"
      @login-success="onLoginSuccess"
    />
  </el-container>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { checkHealth, getSessionInfo } from './api/index.js'
import AuthModal from './components/AuthModal.vue'

const router = useRouter()
const route = useRoute()
const userDropdownRef = ref(null)
const sessionId = ref('')
const recordCount = ref(0)
const apiOk = ref(false)
// 本地开发可通过 VITE_DISABLE_AUTH=true 隐藏登录入口（.env.development.local）
const authDisabled = import.meta.env.VITE_DISABLE_AUTH === 'true'
const authVisible = ref(false)
const userName = ref('')
const appDark = ref(false)

watch(appDark, (v) => {
  document.body.classList.toggle('app-dark', v)
}, { immediate: true })

function onSessionCreated({ sessionId: sid, recordCount: cnt }) {
  sessionId.value = sid
  recordCount.value = cnt
}

function onSessionCleared() {
  sessionId.value = ''
  recordCount.value = 0
  localStorage.removeItem('geo_session_id')
  localStorage.removeItem('geo_record_count')
}

function extractUserName(user) {
  if (!user || typeof user !== 'object') return ''
  const keys = ['username', 'name', 'userName', 'nickName', 'nickname', 'realName', 'realname']
  for (const key of keys) {
    const value = user[key]
    if (typeof value === 'string' && value.trim()) return value.trim()
  }
  return ''
}

function syncUserNameFromStorage() {
  const cachedName = localStorage.getItem('app_user_name')
  if (cachedName && cachedName.trim()) {
    userName.value = cachedName.trim()
    return
  }

  const userRaw = localStorage.getItem('userInfoAiGeovis')
    || localStorage.getItem('userInfoAigeovis')
    || localStorage.getItem('userInfoAI')
    || localStorage.getItem('userInfoCast')
  if (!userRaw) {
    userName.value = ''
    return
  }

  try {
    const user = JSON.parse(userRaw)
    userName.value = extractUserName(user)
  } catch {
    userName.value = ''
  }
}

function onLoginSuccess() {
  const cachedName = localStorage.getItem('app_user_name')
  if (cachedName && cachedName.trim()) {
    userName.value = cachedName.trim()
  }
  syncUserNameFromStorage()
  authVisible.value = false
}

function logout() {
  localStorage.removeItem('userInfoAiGeovis')
  localStorage.removeItem('userInfoAigeovis')
  localStorage.removeItem('userInfoAI')
  localStorage.removeItem('userInfoCast')
  localStorage.removeItem('mssIsLogin')
  localStorage.removeItem('mssLogin')
  localStorage.removeItem('app_user_name')
  localStorage.removeItem('geo_record_count')
  localStorage.removeItem('geo_session_id')
  localStorage.removeItem('home_lang_switch')
  localStorage.removeItem('home_theme_switch')
  localStorage.removeItem('home_model_cfg')
  window.dispatchEvent(new Event('app-logout'))
  userName.value = ''
  appDark.value = false
}

function onUserMenuCommand(command) {
  if (command === 'user-manage') {
    userDropdownRef.value?.handleClose?.()
    router.push({ name: 'user-manage', query: { theme: appDark.value ? 'dark' : 'light' } })
    return
  }
}

function syncThemeFromStorage() {
  appDark.value = localStorage.getItem('home_theme_switch') === 'dark'
}

// localStorage 持久化
watch(sessionId, (v) => {
  if (v) localStorage.setItem('geo_session_id', v)
  else localStorage.removeItem('geo_session_id')
})
watch(recordCount, (v) => {
  localStorage.setItem('geo_record_count', String(v))
})
watch(() => route.fullPath, () => {
  syncUserNameFromStorage()
  syncThemeFromStorage()
})

onMounted(async () => {
  // 1. 先检查 API 健康
  try {
    await checkHealth()
    apiOk.value = true
  } catch {
    apiOk.value = false
  }

  // 2. 尝试从 localStorage 恢复上次 session
  const savedId = localStorage.getItem('geo_session_id')
  if (savedId && !sessionId.value) {
    try {
      const res = await getSessionInfo(savedId)
      sessionId.value = savedId
      recordCount.value = res.data.record_count
    } catch {
      // session 已失效，清除
      localStorage.removeItem('geo_session_id')
      localStorage.removeItem('geo_record_count')
    }
  }

  syncUserNameFromStorage()
  syncThemeFromStorage()
  window.addEventListener('app-theme-change', syncThemeFromStorage)
})

onBeforeUnmount(() => {
  window.removeEventListener('app-theme-change', syncThemeFromStorage)
})
</script>

<style>
* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  background: #f0f2f5;
}

* {
  scrollbar-width: thin;
  scrollbar-color: #bcc4d1 transparent;
}

*::-webkit-scrollbar {
  width: 6px;
  height: 6px;
  background: transparent;
}

*::-webkit-scrollbar-track {
  background: transparent;
  border: none;
  box-shadow: none;
}

*::-webkit-scrollbar-thumb {
  background: #bcc4d1;
  border-radius: 999px;
  border: none;
}

*::-webkit-scrollbar-corner {
  background: transparent;
}

.app-root {
  min-height: 100vh;
  background:#f5f8fc;
}

.app-header {
  background: transparent;
  /*border-bottom: 1px solid #e3ebf5;*/
  /*box-shadow: 0 1px 6px rgba(35, 61, 92, 0.08);*/
  padding: 0;
  /*border: 1px solid red;*/
}

.header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 100%;
  padding: 0 30px;
  gap: 16px;
}

.logo-img {
  height: 45px;
  width: auto;
  flex-shrink: 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.user-pill {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #212020;
  font-size: 16px;
  cursor: pointer;
  /*border: 1px solid red;*/
  /*font-weight: 600;*/
}
.user-text{
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-avatar {

  width: 35px;
  height: 35px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  background: #e6e7ea;
}

.app-main {
  padding: 0 24px 24px;
  height: calc(100vh - 70px);
  /*border: 1px solid red;*/
}

.app-root.app-dark {
  background: #101729;
}

.app-root.app-dark .app-header {
  background: #101729;
}

.app-root.app-dark .user-pill {
  color: #dbe3ef;
}

.app-root.app-dark .login {
  color: #dbe3ef;
}

.app-root.app-dark .user-avatar {
  background: #223149;
}

.app-root.app-dark .app-main {
  background: #101729;
}

.logout-btn {
  border: none;
  background: transparent;
  color: #212020;
  font-size: 16px;
  cursor: pointer;
}

.logout-btn:hover {
  color: #0f3b67;
}

.app-root.app-dark .logout-btn {
  color: #dbe3ef;
}
.app-root.app-dark .center-icon {
  color: #dbe3ef;
}
.user-menu-dropdown {
  border: 1px solid #e7ecf3 !important;
  border-radius: 10px !important;
  padding: 6px !important;
  background: #ffffff !important;
}

.user-menu-dropdown .el-dropdown-menu__item {
  border-radius: 8px;
  color: #1f2937;
}

.user-menu-dropdown .el-dropdown-menu__item:not(.is-disabled):hover {
  background: #e6f7f4;
  color: #0b8f83;
}

.user-menu-dropdown .el-dropdown-menu__item:focus {
  background: transparent;
  color: #1f2937;
}

.user-menu-dropdown-dark {
  background: #182235 !important;
  border: 1px solid #2d3e58 !important;
  box-shadow: 0 10px 30px rgba(2, 6, 23, 0.45) !important;
}

.user-menu-dropdown-dark .el-dropdown-menu {
  background: #182235 !important;
}

.user-menu-dropdown-dark .el-dropdown-menu__item {
  color: #dbe3ef !important;
}

.user-menu-dropdown-dark .el-popper__arrow::before {
  background: #182235 !important;
  border-color: #2d3e58 !important;
}

.user-menu-dropdown-dark .el-dropdown-menu__item:not(.is-disabled):hover {
  background: #1f3d36 !important;
  color: #34d399 !important;
}

.user-menu-dropdown-dark .el-dropdown-menu__item:focus {
  background: transparent !important;
  color: #dbe3ef !important;
}
</style>
