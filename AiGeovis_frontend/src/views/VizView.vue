<template>
  <div class="viz-view" :class="{ embedded }">
    <el-empty
      v-if="!hasDataSource"
      image-size="120"
    >
      <template v-if="embedded" #description>
        <span :style="{ fontSize: '14px', color: isDark ? '#ffffff' : '' }">{{ tLabel('请上传 WoS 数据 / 自定义数据，或', 'Upload WoS or custom data, or ') }}</span>
        <button
          style="font-size: 14px;margin-left: 3px;"
          type="button"
          class="empty-demo-link-btn"
          @click="openDemo"
        >{{ tLabel('打开案例', 'open a demo') }}</button>
        <span>{{ tLabel('。', '.') }}</span>
      </template>
      <template v-else #description>
        <span>请先在「数据加载」页上传 WoS 数据或自定义地址数据</span>
      </template>
      <el-button v-if="!embedded" type="primary" @click="$router.push('/home')">去首页</el-button>
    </el-empty>

    <template v-else>
      <!-- ── 页面标题 + 控制栏 ── -->
      <div v-if="!embedded" class="viz-header">
        <div class="viz-title">
          <el-icon size="22" color="#3949ab"><TrendCharts /></el-icon>
          <h2>地理可视化</h2>
        </div>

        <div class="viz-controls">
          <!-- 字段选择 -->
          <el-radio-group v-model="vizField" size="small" @change="loadData">
            <el-radio-button label="C1">C1（作者地址）</el-radio-button>
            <el-radio-button label="C3">C3（全文地址）</el-radio-button>
          </el-radio-group>

          <!-- 可视化类型 -->
          <el-segmented
            v-model="vizType"
            :options="vizOptions"
            size="small"
            style="margin-left:12px"
          />

          <el-button
            type="primary"
            size="small"
            :loading="loading"
            style="margin-left:8px"
            @click="loadData"
          >
            <el-icon><Refresh /></el-icon> 刷新数据
          </el-button>

          <!-- 解析进度角标 -->
          <el-tag
            v-if="parseStats.total > 0"
            :type="parseStats.complete ? 'success' : 'warning'"
            size="small"
            style="margin-left:8px"
          >
            {{ vizField }}:
            {{ parseStats.parsed }}/{{ parseStats.total }}
            {{ parseStats.complete ? '✓ 完成' : `(${parseStats.percent}%)` }}
          </el-tag>
        </div>
      </div>

      <!-- ── 未解析 / 等待中 提示 ── -->
      <el-alert
        v-if="!embedded && !loading && !parsed"
        type="warning"
        show-icon
        :closable="false"
        style="margin-bottom:16px"
      >
        <template #title>
          <span>{{ vizField }} 字段尚未解析，或解析任务正在进行中</span>
        </template>
        <template #default>
          <div style="display:flex;align-items:center;gap:10px;margin-top:6px">
            <span style="font-size:12px;color:#999">
              正在自动检测（每 4 秒），解析完成后将自动显示
            </span>
            <el-button size="small" @click="$router.push('/home')">去首页解析</el-button>
            <el-button size="small" type="primary" :loading="loading" @click="loadData">立即刷新</el-button>
          </div>
        </template>
      </el-alert>

      <!-- ── 部分解析提示 ── -->
      <el-alert
        v-if="!embedded && parsed && !parseStats.complete && parseStats.total > 0"
        type="warning"
        show-icon
        :closable="false"
        style="margin-bottom:12px"
      >
        <template #title>
          {{ vizField }} 仅完成部分解析（{{ parseStats.parsed }}/{{ parseStats.total }} 个唯一地址）
        </template>
        <template #default>
          <div style="display:flex;align-items:center;gap:10px;margin-top:6px">
            <span style="font-size:12px;color:#888">点击「继续解析」可对剩余地址进行增量补充，已解析的不会重复处理</span>
            <el-button size="small" type="warning" @click="$router.push('/home')">
              继续解析
            </el-button>
          </div>
        </template>
      </el-alert>

      <!-- ── 主内容区 ── -->
      <div v-if="parsed" class="viz-body">

        <!-- 世界地图 -->
        <template v-if="vizType === 'map' || vizType === 'heatmap'">
          <div v-if="embedded" class="embedded-map-wrap">
            <div v-if="geocodeItems.length === 0" class="empty-tip">
              <el-empty description="AI 解析结果中无经纬度数据" image-size="120" />
            </div>
            <div v-else ref="mapChartEl" class="map-container embedded-map" />
          </div>
          <el-card v-else shadow="always" class="viz-card">
            <template #header>
              <div class="card-hd-row">
              <span class="card-hd"><el-icon><Location /></el-icon>{{ vizType === 'heatmap' ? '地理热力密度图' : '地理分布地图' }}</span>
                <el-tag v-if="geocodeItems.length" type="success" size="small">
                  {{ geocodeItems.length }} 个地点有坐标
                </el-tag>
                <el-tag v-else type="info" size="small">解析结果中暂无坐标（AI 未返回）</el-tag>
              </div>
            </template>
            <div v-if="geocodeItems.length === 0" class="empty-tip">
              <el-empty description="AI 解析结果中无经纬度数据" image-size="120">
                <p style="font-size:12px;color:#888;margin-top:4px">
                  切换到「国家」「机构」「城市」可查看已解析数据
                </p>
              </el-empty>
            </div>
            <div v-else ref="mapChartEl" class="map-container" />
          </el-card>
        </template>

        <!-- 国家 / 地区 -->
        <template v-else-if="vizType === 'country'">
          <el-card shadow="always" class="viz-card">
            <template #header>
              <span class="card-hd"><el-icon><Location /></el-icon> 国家 / 地区 Top {{ topNCount(countryData.length) }}</span>
            </template>
            <div ref="countryChartEl" class="chart-container tall" />
          </el-card>
        </template>

        <!-- 机构 -->
        <template v-else-if="vizType === 'org'">
          <el-card shadow="always" class="viz-card">
            <template #header>
              <span class="card-hd"><el-icon><School /></el-icon> 机构 Top {{ topNCount(orgData.length) }}</span>
            </template>
            <div ref="orgChartEl" class="chart-container tall" />
          </el-card>
        </template>

        <!-- 城市 -->
        <template v-else-if="vizType === 'city'">
          <el-card shadow="always" class="viz-card">
            <template #header>
              <span class="card-hd"><el-icon><Place /></el-icon> 城市 Top {{ topNCount(cityData.length) }}</span>
            </template>
            <div ref="cityChartEl" class="chart-container tall" />
          </el-card>
        </template>

      </div>
      <el-empty
        v-else-if="embedded && !loading"
        description="当前解析字段暂无可视化数据"
        image-size="90"
      />
    </template>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, onMounted, onBeforeUnmount, onActivated } from 'vue'
import { ElMessage } from 'element-plus'
import { getTierStats, getVizData, getDemoData, getDemoMatrix, getEntityMatrix } from '../api/index.js'
import { edgeWeightRange, edgeWeightToBaseWidth } from '../utils/edgeWidth.js'
import world from '../utils/json/world.json'

const props = defineProps({
  sessionId:   { type: String, default: '' },
  recordCount: { type: Number, default: 0 },
  embedded:    { type: Boolean, default: false },
  fixedField:  { type: String, default: '' },
  fixedType:   { type: String, default: '' },
  fixedTier:   { type: String, default: 'country' },
  langZh: { type: Boolean, default: true },
  demoMode: { type: Boolean, default: false },
  autoLoadViz: { type: Boolean, default: true },  // 是否自动加载 viz 数据
  mapNodeSize: { type: Number, default: 100 },
  mapLabelVisible: { type: Boolean, default: false },
  mapNodeOpacity: { type: Number, default: 70 },
  mapSizeMode: { type: String, default: 'scaled' },
  mapNodeColor: { type: String, default: '#0f9f94' },
  mapEdgeColor: { type: String, default: '#334155' },
  mapEdgeWidth: { type: Number, default: 8 },
  mapEdgeOpacity: { type: Number, default: 88 },
  showEdges: { type: Boolean, default: false },
  reloadKey:   { type: Number, default: 0 },
})
const emit = defineEmits(['stats-meta', 'open-demo', 'viz-loading'])

function tLabel(zh, en) {
  return props.langZh ? zh : en
}

// ── 状态 ─────────────────────────────────────
const vizField = ref(props.fixedField || 'C1')
const vizType  = ref(props.fixedType || 'map')
const vizTier  = ref(props.fixedTier || 'country')
const hasDataSource = ref(Boolean(props.sessionId || props.demoMode))
const loading  = ref(false)
const parsed   = ref(false)
let skipNextVizApiCall = false  // 跳过下次 viz-data API 调用（上传后首次）

const countryData  = ref([])
const orgData      = ref([])
const cityData     = ref([])
const geocodeItems = ref([])
const entityEdges = ref([])
const entityNodeAliasMap = ref(new Map())
const edgeVisibleState = ref(props.showEdges)
const selectedMapNodeName = ref('')
const parseStats   = ref({ total: 0, parsed: 0, percent: 0, complete: false })
const isDark = ref(false)
const BAR_TOP_N = 30
const FULL_TOP_N = 10000

const vizOptions = [
  { label: '世界地图', value: 'map' },
  { label: '热力密度图', value: 'heatmap' },
  { label: '国家', value: 'country' },
  { label: '机构', value: 'org' },
  { label: '城市', value: 'city' },
]

const DEMO_MATRIX_API_MAP = {
  C1: { country: 'C1CountryMatrix', city: 'C1CityMatrix', org: 'C1OrgMatrix' },
  C3: { org: 'C3OrgMatrix' },
}

// ── 图表 DOM refs ─────────────────────────────
const countryChartEl = ref(null)
const orgChartEl     = ref(null)
const cityChartEl    = ref(null)
const mapChartEl     = ref(null)

let chartInstances = []
let pollTimer      = null   // 未解析时轮询计时器
let edgeHideTimer  = null
let dataLoadSeq = 0
let edgeLoadSeq = 0
const vizDataCache = new Map()
const entityEdgeCache = new Map()
let worldRegistered = false
let resizeObserver = null
const MAP_BASE_ZOOM = 1.6
const MAP_MAX_ZOOM = 10000
const MAP_MIN_ZOOM = 1
const MAP_CLUSTER_THRESHOLD = 1200
const MAP_GRID_SIZE = 1.8
const MAP_HEAVY_THRESHOLD = 1800
const EDGE_TOGGLE_DURATION = 320
let mapRoamState = {
  zoom: MAP_BASE_ZOOM,
  center: null,
}
let lastRenderedMapZoom = MAP_BASE_ZOOM

function openDemo() {
  emit('open-demo')
}

function getVizContextKey() {
  return JSON.stringify({
    sessionId: props.sessionId || '',
    demoMode: props.demoMode,
    field: vizField.value,
    type: vizType.value,
    tier: vizTier.value,
    showEdges: props.showEdges,
  })
}

function getVizDataCacheKey() {
  const tier = (vizType.value === 'map' || vizType.value === 'heatmap') ? vizTier.value : vizType.value
  return JSON.stringify({
    sessionId: props.sessionId || '',
    demoMode: props.demoMode,
    field: vizField.value,
    tier,
    topN: requestTopNByVizType(),
    autoLoadViz: props.autoLoadViz,
  })
}

function getEntityEdgeCacheKey() {
  if (!shouldLoadEntityEdges()) return ''
  return JSON.stringify({
    sessionId: props.sessionId || '',
    demoMode: props.demoMode,
    field: vizField.value,
    tier: getActiveEdgeTier(),
    topN: requestTopNByVizType(),
  })
}

function cloneMap(obj) {
  return new Map(Array.from((obj instanceof Map ? obj : new Map()).entries()).map(([key, value]) => [key, new Set(Array.from(value || []))]))
}

function buildVizSnapshot() {
  return {
    parsed: Boolean(parsed.value),
    parseStats: { ...parseStats.value },
    geocodeItems: Array.isArray(geocodeItems.value) ? geocodeItems.value.map(item => ({ ...item })) : [],
    countryData: Array.isArray(countryData.value) ? countryData.value.map(item => ({ ...item })) : [],
    orgData: Array.isArray(orgData.value) ? orgData.value.map(item => ({ ...item })) : [],
    cityData: Array.isArray(cityData.value) ? cityData.value.map(item => ({ ...item })) : [],
  }
}

function applyVizSnapshot(snapshot) {
  parsed.value = Boolean(snapshot?.parsed)
  parseStats.value = snapshot?.parseStats ? { ...snapshot.parseStats } : { total: 0, parsed: 0, percent: 0, complete: false }
  geocodeItems.value = Array.isArray(snapshot?.geocodeItems) ? snapshot.geocodeItems.map(item => ({ ...item })) : []
  countryData.value = Array.isArray(snapshot?.countryData) ? snapshot.countryData.map(item => ({ ...item })) : []
  orgData.value = Array.isArray(snapshot?.orgData) ? snapshot.orgData.map(item => ({ ...item })) : []
  cityData.value = Array.isArray(snapshot?.cityData) ? snapshot.cityData.map(item => ({ ...item })) : []
}

function cacheCurrentVizSnapshot(cacheKey = getVizDataCacheKey()) {
  if (!cacheKey || !parsed.value) return
  vizDataCache.set(cacheKey, buildVizSnapshot())
}

function emitStatsMetaFromState(source = 'cache') {
  const tier = (vizType.value === 'map' || vizType.value === 'heatmap') ? vizTier.value : vizType.value
  const displayCount = (
    tier === 'country' ? countryData.value.length
      : tier === 'org' ? orgData.value.length
        : tier === 'city' ? cityData.value.length
          : geocodeItems.value.length
  )
  emit('stats-meta', {
    source,
    field: vizField.value,
    tier,
    total: Number(parseStats.value?.total) || 0,
    display_count: displayCount,
  })
}

function resetViewport() {
  mapRoamState = {
    zoom: MAP_BASE_ZOOM,
    center: null,
  }
  if (vizType.value === 'map' || vizType.value === 'heatmap') {
    renderMap(true)
  }
}

defineExpose({
  resetViewport,
})

function syncTheme() {
  isDark.value = localStorage.getItem('home_theme_switch') === 'dark'
}

function waitForNextPaint() {
  return new Promise((resolve) => {
    requestAnimationFrame(() => {
      requestAnimationFrame(resolve)
    })
  })
}

function waitForChartRendered(chart, timeout = 1500) {
  if (!chart?.on || !chart?.off) return Promise.resolve()
  return new Promise((resolve) => {
    let settled = false
    let timer = null
    const cleanup = () => {
      if (timer) {
        clearTimeout(timer)
        timer = null
      }
      chart.off('rendered', handleRendered)
      chart.off('finished', handleFinished)
    }
    const handleRendered = () => {
      if (settled) return
      settled = true
      cleanup()
      resolve()
    }
    const handleFinished = () => {
      if (settled) return
      settled = true
      cleanup()
      resolve()
    }
    chart.on('rendered', handleRendered)
    chart.on('finished', handleFinished)
    timer = window.setTimeout(() => {
      if (settled) return
      settled = true
      cleanup()
      resolve()
    }, timeout)
  })
}

function createChartRenderTask(chart, timeout = 4000) {
  return {
    chart,
    done: waitForChartRendered(chart, timeout),
  }
}

function isC1TierMode() {
  if (vizField.value !== 'C1') return false
  if (['country', 'org', 'city'].includes(vizType.value)) return true
  return ['map', 'heatmap'].includes(vizType.value) && ['country', 'org', 'city'].includes(vizTier.value)
}

// ── 加载 ECharts ──────────────────────────────
let _echartsLoaded = false
async function loadECharts() {
  if (window.echarts || _echartsLoaded) return
  await loadScript('https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js')
  _echartsLoaded = true
}

function loadScript(src) {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) { resolve(); return }
    const s = document.createElement('script')
    s.src = src; s.onload = resolve; s.onerror = reject
    document.head.appendChild(s)
  })
}

function buildCountsFromGeocode(items, fieldKey) {
  const list = Array.isArray(items) ? items : []
  const map = new Map()
  for (const it of list) {
    const name = String(it?.[fieldKey] || '').trim()
    if (!name) continue
    const prev = map.get(name) || 0
    map.set(name, prev + (Number(it?.count) || 0))
  }
  return Array.from(map.entries())
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
}

/** 统一 affiliation / 本地案例字段别名，保证条形图、地图、热力同源可读 */
function normalizeGeocodeItems(items) {
  const list = Array.isArray(items) ? items : []
  return list.map((item) => {
    const org = String(item?.organization || item?.org || item?.name || '').trim()
    const city = String(item?.City1 || item?.city || '').trim()
    const country = String(item?.country || item?.['Country/Region'] || '').trim()
    return {
      ...item,
      org,
      organization: org,
      name: org || city || country || String(item?.name || '').trim(),
      city,
      City1: city,
      country,
      lat: item?.lat,
      lng: item?.lng,
      count: Number(item?.count ?? item?.value) || 0,
    }
  })
}

/**
 * 仅对几乎重合的点做极小散开（真实近邻如清华/北大靠放大地图分辨，不人为拉开几十公里）
 */
function applyAffiliationCoordJitter(items) {
  const list = normalizeGeocodeItems(items)
  const groups = new Map()
  list.forEach((item, idx) => {
    const lat = Number(item.lat)
    const lng = Number(item.lng)
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) return
    const key = `${lat.toFixed(4)}_${lng.toFixed(4)}`
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key).push(idx)
  })

  return list.map((item, idx) => {
    const lat = Number(item.lat)
    const lng = Number(item.lng)
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) return item
    const key = `${lat.toFixed(4)}_${lng.toFixed(4)}`
    const group = groups.get(key) || [idx]
    if (group.length <= 1) return item
    const pos = group.indexOf(idx)
    const angle = (2 * Math.PI * pos) / group.length
    const radius = 0.002 + 0.001 * Math.floor(pos / 6)
    return {
      ...item,
      lat: lat + radius * Math.sin(angle),
      lng: lng + radius * Math.cos(angle),
    }
  })
}

function clearMapSelection() {
  selectedMapNodeName.value = ''
}

function normalizeMapNodeToken(value) {
  return typeof value === 'string' ? value.trim().toLowerCase() : ''
}

function registerEntityNodeAlias(aliasMap, alias, canonical) {
  const aliasKey = normalizeMapNodeToken(alias)
  const canonicalKey = normalizeMapNodeToken(canonical)
  if (!aliasKey || !canonicalKey) return
  const existing = aliasMap.get(aliasKey)
  if (existing) {
    existing.add(canonicalKey)
    return
  }
  aliasMap.set(aliasKey, new Set([canonicalKey]))
}

function getEntityNodeAliases(name, tier) {
  const text = typeof name === 'string' ? name.trim() : ''
  if (!text) return []
  const aliases = new Set([text])
  if (tier === 'city' && text.includes(' > ')) {
    const parts = text.split(' > ').map((item) => item.trim()).filter(Boolean)
    const leaf = parts[parts.length - 1]
    if (leaf) aliases.add(leaf)
  }
  return Array.from(aliases)
}

function resolveEntityNodeKeys(names) {
  const aliasMap = entityNodeAliasMap.value instanceof Map ? entityNodeAliasMap.value : new Map()
  const resolved = new Set()
  for (const name of Array.isArray(names) ? names : []) {
    const directKey = normalizeMapNodeToken(name)
    if (!directKey) continue
    const matchedKeys = aliasMap.get(directKey)
    if (matchedKeys?.size) {
      matchedKeys.forEach((key) => resolved.add(key))
      continue
    }
    resolved.add(directKey)
  }
  return Array.from(resolved)
}

function getMapTierKey() {
  return vizType.value === 'map' || vizType.value === 'heatmap' ? vizTier.value : vizType.value
}

function getMapNodePrimaryName(item = {}) {
  const source = item?._meta || item || {}
  const tier = getMapTierKey()
  return getMapNodeNameByTier(source, tier)
}

function getMapNodeNameByTier(source = {}, tier = getMapTierKey()) {
  if (tier === 'country') {
    return String(source?.['Country/Region'] || source?.country || source?.name || '').trim()
  }
  if (tier === 'org') {
    return String(source?.Organization || source?.organization || source?.org || source?.name || '').trim()
  }
  if (tier === 'city') {
    return String(source?.City1 || source?.city || source?.name || '').trim()
  }
  return String(source?.name || '').trim()
}

function sameMapCoord(a, b) {
  if (!a || !b) return false
  return Math.abs(Number(a.lng) - Number(b.lng)) < 1e-7 && Math.abs(Number(a.lat) - Number(b.lat)) < 1e-7
}

function buildVisibleMapNodeCoordIndex(tier) {
  const coordMap = new Map()
  const ambiguousKeys = new Set()
  for (const item of Array.isArray(geocodeItems.value) ? geocodeItems.value : []) {
    const name = formatEntityNameByTier(getMapNodeNameByTier(item, tier), tier)
    const key = normalizeMapNodeToken(name)
    const lng = Number(item?.lng)
    const lat = Number(item?.lat)
    if (!key || !Number.isFinite(lng) || !Number.isFinite(lat)) continue
    const next = { lng, lat }
    const prev = coordMap.get(key)
    if (prev && !sameMapCoord(prev, next)) {
      ambiguousKeys.add(key)
      continue
    }
    if (!ambiguousKeys.has(key)) coordMap.set(key, next)
  }
  ambiguousKeys.forEach((key) => coordMap.delete(key))
  return { coordMap, ambiguousKeys }
}

function getMapSelectionState() {
  const activeName = typeof selectedMapNodeName.value === 'string' ? selectedMapNodeName.value.trim() : ''
  const activeNames = activeName
    .split(' || ')
    .map((item) => item.trim())
    .filter(Boolean)
  const activeKeys = resolveEntityNodeKeys(activeNames)
  const activeKey = activeKeys[0] || ''
  const relatedNodeKeys = new Set()
  const relatedEdgeKeys = new Set()
  if (activeKeys.length === 0) {
    return {
      activeName: '',
      activeKey: '',
      activeKeys: [],
      relatedNodeKeys,
      relatedEdgeKeys,
      hasSelection: false,
    }
  }
  activeKeys.forEach((key) => relatedNodeKeys.add(key))
  for (const edge of Array.isArray(entityEdges.value) ? entityEdges.value : []) {
    const source = typeof edge?.fromName === 'string' ? edge.fromName.trim() : ''
    const target = typeof edge?.toName === 'string' ? edge.toName.trim() : ''
    const sourceKey = normalizeMapNodeToken(source)
    const targetKey = normalizeMapNodeToken(target)
    if (!sourceKey || !targetKey) continue
    if (!activeKeys.includes(sourceKey) && !activeKeys.includes(targetKey)) continue
    relatedNodeKeys.add(sourceKey)
    relatedNodeKeys.add(targetKey)
    relatedEdgeKeys.add(`${source}__${target}`)
    relatedEdgeKeys.add(`${target}__${source}`)
  }
  return {
    activeName,
    activeKey,
    activeKeys,
    relatedNodeKeys,
    relatedEdgeKeys,
    hasSelection: true,
  }
}

function getSelectedNodeStyle(baseColor, baseOpacity, item, selectionState, isHeatNode = false) {
  const memberNames = Array.isArray(item?._memberNames) && item._memberNames.length > 0
    ? item._memberNames
    : [getMapNodePrimaryName(item)]
  const memberKeys = resolveEntityNodeKeys(memberNames)
  const isActive = selectionState.hasSelection && memberKeys.some((key) => selectionState.activeKeys.includes(key))
  const isRelated = selectionState.hasSelection && memberKeys.some((key) => selectionState.relatedNodeKeys.has(key))
  if (!selectionState.hasSelection) {
    return {
      color: isHeatNode ? '#111111' : baseColor,
      opacity: baseOpacity,
      borderWidth: 0,
      borderColor: 'transparent',
    }
  }
  if (isActive) {
    return {
      color: '#f97316',
      opacity: 1,
      borderWidth: 2,
      borderColor: isDark.value ? '#fff7ed' : '#7c2d12',
    }
  }
  if (isRelated) {
    return {
      color: isHeatNode ? '#111111' : baseColor,
      opacity: Math.min(1, baseOpacity + 0.2),
      borderWidth: 1.5,
      borderColor: isDark.value ? '#e2e8f0' : '#334155',
    }
  }
  return {
    color: isHeatNode ? '#111111' : baseColor,
    opacity: Math.max(0.08, baseOpacity * 0.18),
    borderWidth: 0,
    borderColor: 'transparent',
  }
}

function topNCount(n) {
  return Math.min(Number(n) || 0, BAR_TOP_N)
}

function requestTopNByVizType() {
  // 本地地址 / affiliation：四个图与解析表格共用全量，保证统计一致
  if (typeof vizField.value === 'string' && vizField.value.startsWith('affiliation_')) {
    return FULL_TOP_N
  }
  return (vizType.value === 'map' || vizType.value === 'heatmap') ? FULL_TOP_N : BAR_TOP_N
}

function getActiveEdgeTier() {
  return (vizType.value === 'map' || vizType.value === 'heatmap') ? vizTier.value : vizType.value
}

function formatEntityNameByTier(name, tier) {
  const text = typeof name === 'string' ? name.trim() : ''
  if (!text) return ''
  if (tier === 'city' && text.includes(' > ')) {
    const parts = text.split(' > ').map((item) => item.trim()).filter(Boolean)
    return parts[parts.length - 1] || text
  }
  return text
}

function shouldLoadEntityEdges() {
  const activeTier = getActiveEdgeTier()
  const isAffiliationField = typeof vizField.value === 'string' && vizField.value.startsWith('affiliation_')
  const isC1TierSupported = vizField.value === 'C1' && ['country', 'org', 'city'].includes(activeTier)
  const isC3OrgSupported = vizField.value === 'C3' && activeTier === 'org'
  return Boolean(
    props.showEdges
    && !isAffiliationField
    && (isC1TierSupported || isC3OrgSupported)
    && vizType.value === 'map'
    && (
      (props.demoMode && DEMO_MATRIX_API_MAP[vizField.value === 'C3' ? 'C3' : 'C1']?.[activeTier])
      || (!props.demoMode && props.sessionId)
    )
  )
}

function syncEdgeVisibleState(visible) {
  edgeVisibleState.value = Boolean(visible)
}

async function loadEntityEdges() {
  const seq = ++edgeLoadSeq
  const contextKey = getVizContextKey()
  if (!shouldLoadEntityEdges()) {
    entityEdges.value = []
    entityNodeAliasMap.value = new Map()
    return
  }

  const edgeCacheKey = getEntityEdgeCacheKey()
  const cachedEdges = edgeCacheKey ? entityEdgeCache.get(edgeCacheKey) : null
  if (cachedEdges) {
    entityEdges.value = Array.isArray(cachedEdges.entityEdges)
      ? cachedEdges.entityEdges.map(item => ({ ...item, coords: Array.isArray(item?.coords) ? item.coords.map(coord => Array.isArray(coord) ? [...coord] : coord) : [] }))
      : []
    entityNodeAliasMap.value = cloneMap(cachedEdges.entityNodeAliasMap)
    return
  }

  try {
    const activeTier = getActiveEdgeTier()
    const edgeField = vizField.value === 'C3' ? 'C3' : 'C1'
    const { coordMap: visibleCoordMap, ambiguousKeys } = buildVisibleMapNodeCoordIndex(activeTier)
    const res = props.demoMode
      ? await getDemoMatrix(DEMO_MATRIX_API_MAP[edgeField]?.[activeTier])
      : await getEntityMatrix(props.sessionId, edgeField, activeTier, requestTopNByVizType(), 0)
    if (seq !== edgeLoadSeq || contextKey !== getVizContextKey()) return
    const nodes = Array.isArray(res.data?.nodes) ? res.data.nodes : []
    const aliasMap = new Map()
    nodes.forEach((node) => {
      const canonicalName = formatEntityNameByTier(node?.name, activeTier)
      getEntityNodeAliases(canonicalName, activeTier).forEach((alias) => {
        registerEntityNodeAlias(aliasMap, alias, canonicalName)
      })
    })
    entityNodeAliasMap.value = aliasMap
    const matrixNodeMap = new Map(
      nodes
        .filter(node => Number.isFinite(Number(node?.lng)) && Number.isFinite(Number(node?.lat)))
        .map(node => [
          formatEntityNameByTier(node?.name, activeTier),
          { lng: Number(node.lng), lat: Number(node.lat) },
        ])
    )
    const rawEdges = (Array.isArray(res.data?.edges) ? res.data.edges : [])
      .filter(edge => Number(edge?.weight) > 0)
    const { minW, maxW } = edgeWeightRange(rawEdges)
    entityEdges.value = rawEdges.map(edge => {
        const sourceName = formatEntityNameByTier(edge?.source, activeTier)
        const targetName = formatEntityNameByTier(edge?.target, activeTier)
        const sourceKey = normalizeMapNodeToken(sourceName)
        const targetKey = normalizeMapNodeToken(targetName)
        if (!sourceKey || !targetKey) return null
        if (ambiguousKeys.has(sourceKey) || ambiguousKeys.has(targetKey)) return null
        const source = visibleCoordMap.get(sourceKey) || matrixNodeMap.get(sourceName)
        const target = visibleCoordMap.get(targetKey) || matrixNodeMap.get(targetName)
        if (!source || !target) return null
        const weight = Number(edge.weight) || 0
        const baseWidth = edgeWeightToBaseWidth(weight, minW, maxW, {
          minPx: 0.85,
          maxPx: 4.2,
          power: 0.55,
        })
        return {
          fromName: sourceName,
          toName: targetName,
          coords: [
            [source.lng, source.lat],
            [target.lng, target.lat],
          ],
          value: weight,
          baseWidth,
        }
      })
      .filter(Boolean)
    if (edgeCacheKey) {
      entityEdgeCache.set(edgeCacheKey, {
        entityEdges: entityEdges.value.map(item => ({ ...item, coords: Array.isArray(item?.coords) ? item.coords.map(coord => Array.isArray(coord) ? [...coord] : coord) : [] })),
        entityNodeAliasMap: cloneMap(entityNodeAliasMap.value),
      })
    }
  } catch (_) {
    if (seq !== edgeLoadSeq || contextKey !== getVizContextKey()) return
    entityEdges.value = []
    entityNodeAliasMap.value = new Map()
  }
}

function clearVizDisplayState() {
  stopPoll()
  destroyCharts()
  clearMapSelection()
  geocodeItems.value = []
  countryData.value = []
  orgData.value = []
  cityData.value = []
  entityEdges.value = []
  entityNodeAliasMap.value = new Map()
  parsed.value = false
  parseStats.value = { total: 0, parsed: 0, percent: 0, complete: false }
}

// ── 加载数据 ──────────────────────────────────
async function loadData() {
  const seq = ++dataLoadSeq
  const contextKey = getVizContextKey()
  const dataCacheKey = getVizDataCacheKey()
  hasDataSource.value = Boolean(props.sessionId || props.demoMode)
  if (!hasDataSource.value) {
    clearVizDisplayState()
    loading.value = false
    return
  }

  const cachedSnapshot = dataCacheKey ? vizDataCache.get(dataCacheKey) : null
  const needsNetworkFetch = !cachedSnapshot && !props.demoMode && !props.autoLoadViz
  if (needsNetworkFetch) {
    // 新会话尚未允许自动拉取：清空旧图画布，避免残留上一会话画面
    clearVizDisplayState()
    loading.value = false
    return
  }

  loading.value = true
  let rendered = false
  stopPoll()
  destroyCharts()
  clearMapSelection()

  try {
    if (cachedSnapshot) {
      applyVizSnapshot(cachedSnapshot)
      geocodeItems.value = normalizeGeocodeItems(geocodeItems.value)
      await loadEntityEdges()
      if (seq !== dataLoadSeq || contextKey !== getVizContextKey()) return
      await nextTick()
      await renderViz()
      rendered = true
      emitStatsMetaFromState('cache')
      return
    }

    entityEdges.value = []
    entityNodeAliasMap.value = new Map()

    if (props.demoMode) {
      const tier = (vizType.value === 'map' || vizType.value === 'heatmap') ? vizTier.value : vizType.value
      const demoName = vizField.value === 'C3'
        ? 'demoC3Count'
        : (tier === 'org' ? 'demoC1OrgCount' : tier === 'city' ? 'demoC1CityCount' : 'demoC1CountryCount')
      const res = await getDemoData(demoName)
      if (seq !== dataLoadSeq || contextKey !== getVizContextKey()) return
      if (vizField.value === 'C3') {
        const geocodes = Array.isArray(res.data?.geocode_items) ? res.data.geocode_items : []
        const mappedGeocodes = geocodes.map((it) => ({
          country: it?.country || '',
          city: it?.city || '',
          City1: it?.City1 || it?.city || '',
          organization: it?.organization || it?.org || '',
          lat: it?.lat ?? it?.latitude ?? null,
          lng: it?.lng ?? it?.longitude ?? null,
          count: Number(it?.count ?? it?.value ?? 0) || 0,
        }))
        const c3Country = buildCountsFromGeocode(mappedGeocodes, 'country')
        const c3Org = buildCountsFromGeocode(mappedGeocodes, 'organization')
        const c3City = buildCountsFromGeocode(mappedGeocodes, 'city')

        parsed.value = mappedGeocodes.length > 0
        parseStats.value = {
          total: Number(res.data?.parse_stats?.total) || mappedGeocodes.length,
          parsed: Number(res.data?.parse_stats?.parsed) || mappedGeocodes.length,
          percent: parsed.value ? 100 : 0,
          complete: parsed.value,
        }
        emit('stats-meta', {
          source: 'demo',
          field: 'C3',
          tier,
          total: parseStats.value.total,
          display_count: mappedGeocodes.length,
        })
        geocodeItems.value = mappedGeocodes
        countryData.value = c3Country
        orgData.value = c3Org
        cityData.value = c3City
        cacheCurrentVizSnapshot(dataCacheKey)
        await loadEntityEdges()
        if (parsed.value) {
          await nextTick()
          await renderViz()
          rendered = true
        }
        return
      }

      const items = normalizeDemoItems(res.data, vizField.value, tier)
      parsed.value = items.length > 0
      parseStats.value = {
        total: items.length,
        parsed: items.length,
        percent: parsed.value ? 100 : 0,
        complete: parsed.value,
      }
      emit('stats-meta', {
        source: 'demo',
        field: vizField.value,
        tier,
        total: items.length,
        display_count: items.length,
      })
      countryData.value = tier === 'country' ? items : []
      orgData.value = tier === 'org' ? items : []
      cityData.value = tier === 'city' ? items : []
      geocodeItems.value = items.map((it) => ({
        country: tier === 'country' ? it.name : '',
        city: tier === 'city' ? it.name : '',
        City1: tier === 'city' ? it.name : '',
        organization: tier === 'org' ? it.name : '',
        lat: it.lat,
        lng: it.lng,
        count: Number(it.value) || 0,
      }))
      cacheCurrentVizSnapshot(dataCacheKey)
      await loadEntityEdges()
      if (parsed.value) {
        await nextTick()
        await renderViz()
        rendered = true
      }
      return
    }

    if (isC1TierMode()) {
      const tier = (vizType.value === 'map' || vizType.value === 'heatmap') ? vizTier.value : vizType.value
      const res = await getTierStats(props.sessionId, 'C1', tier, requestTopNByVizType())
      if (seq !== dataLoadSeq || contextKey !== getVizContextKey()) return
      const items = Array.isArray(res.data?.items) ? res.data.items : []
      parsed.value = Boolean(res.data?.parsed) || items.length > 0
      parseStats.value = {
        total: Number(res.data?.total) || 0,
        parsed: Number(res.data?.total) || 0,
        percent: parsed.value ? 100 : 0,
        complete: parsed.value,
      }
      emit('stats-meta', {
        source: 'stats',
        field: 'C1',
        tier,
        total: Number(res.data?.total) || 0,
        display_count: items.length,
      })
      countryData.value = tier === 'country'
        ? items.map((it) => ({ name: it?.name || '-', value: Number(it?.count) || 0 }))
        : []
      orgData.value = tier === 'org'
        ? items.map((it) => ({ name: it?.name || '-', value: Number(it?.count) || 0 }))
        : []
      cityData.value = tier === 'city'
        ? items.map((it) => ({ name: it?.name || '-', value: Number(it?.count) || 0 }))
        : []
      geocodeItems.value = items.map((it) => ({
        country: tier === 'country' ? it?.name : (it?.country || ''),
        city: tier === 'city' ? it?.name : '',
        City1: tier === 'city' ? (it?.City1 || it?.name || '') : (it?.City1 || ''),
        organization: tier === 'org' ? it?.name : (it?.organization || it?.org || ''),
        org: tier === 'org' ? it?.name : (it?.org || it?.organization || ''),
        name: it?.name || it?.organization || it?.org || it?.country || it?.city || '',
        lat: it?.lat,
        lng: it?.lng,
        count: Number(it?.count) || 0,
      }))
      cacheCurrentVizSnapshot(dataCacheKey)
      await loadEntityEdges()
      if (parsed.value) {
        await nextTick()
        await renderViz()
        rendered = true
      }
      return
    }

    const res = await getVizData(props.sessionId, vizField.value, requestTopNByVizType())
    if (seq !== dataLoadSeq || contextKey !== getVizContextKey()) return
    const d = res.data
    // C3 各层排名直接采用后端「整体计数」结果（每篇每实体去重，与共现矩阵一致），
    // 不再从 geocode_items 反推——否则按机构点求和会把国家/城市层重复放大。
    const c3Country = d.country_counts || []
    const c3Org = d.org_counts || []
    const c3City = d.city_counts || []
    parsed.value = d.parsed
    parseStats.value = d.parse_stats || { total: 0, parsed: 0, percent: 0, complete: false }

    // Affiliation 模式：统一从 geocode_items 获取数据
    const isAffiliationMode = vizField.value?.startsWith('affiliation_')
    const geocodeItemsData = d.geocode_items || []
    const normalizedGeocode = normalizeGeocodeItems(geocodeItemsData)

    // 根据 vizType 提取对应的 country/org/city 数据
    let countryCounts = []
    let orgCounts = []
    let cityCounts = []

    if (isAffiliationMode) {
      // 条形图与地图同源：一律从规范化后的 geocode_items 聚合
      countryCounts = buildCountsFromGeocode(normalizedGeocode, 'country')
      orgCounts = buildCountsFromGeocode(normalizedGeocode, 'org')
      cityCounts = buildCountsFromGeocode(normalizedGeocode, 'city')
    } else if (vizField.value === 'C3') {
      // C3 模式
      countryCounts = c3Country
      orgCounts = c3Org
      cityCounts = c3City
    } else {
      // C1 模式：使用原有字段
      countryCounts = d.country_counts || []
      orgCounts = d.org_counts || []
      cityCounts = d.city_counts || []
    }

    emit('stats-meta', {
      source: 'viz-data',
      field: vizField.value,
      tier: vizType.value === 'map' ? vizTier.value : vizType.value,
      total: Number(d.parse_stats?.total) || 0,
      display_count: (
        vizType.value === 'country' ? countryCounts.length
          : vizType.value === 'org' ? orgCounts.length
            : vizType.value === 'city' ? cityCounts.length
              : normalizedGeocode.length
      ),
    })
    geocodeItems.value = normalizedGeocode
    countryData.value = countryCounts
    orgData.value = orgCounts
    cityData.value = cityCounts
    cacheCurrentVizSnapshot(dataCacheKey)
    await loadEntityEdges()

    if (d.parsed) {
      await nextTick()
      await renderViz()
      rendered = true
    } else {
      startPoll()
    }
  } catch (e) {
    if (seq !== dataLoadSeq || contextKey !== getVizContextKey()) return
    ElMessage.error('加载数据失败：' + (e.response?.data?.detail || e.message))
  } finally {
    // 被更新的请求取代时，把 loading 交给最新请求；完成后再次核对序号再关闭
    if (seq !== dataLoadSeq || contextKey !== getVizContextKey()) return
    if (rendered) {
      await nextTick()
      await waitForNextPaint()
    }
    if (seq === dataLoadSeq) {
      loading.value = false
    }
  }
}

function normalizeDemoItems(payload, field, tier) {
  const pickArray = (obj, key) => (Array.isArray(obj?.[key]) ? obj[key] : [])
  const src = Array.isArray(payload)
    ? payload
    : (() => {
      const keyByTier = tier === 'org' ? 'org_counts' : tier === 'city' ? 'city_counts' : 'country_counts'
      const preferred = pickArray(payload, keyByTier)
      if (preferred.length > 0) return preferred
      const fallbackKeys = field === 'C3'
        ? ['org_counts', 'country_counts', 'city_counts', 'items', 'records', 'data']
        : ['country_counts', 'org_counts', 'city_counts', 'items', 'records', 'data']
      for (const key of fallbackKeys) {
        const arr = pickArray(payload, key)
        if (arr.length > 0) return arr
      }
      return []
    })()
  return src.map((item) => ({
    name: item?.name || item?.country || item?.city || item?.organization || item?.org || '-',
    value: Number(item?.count ?? item?.value ?? item?.num ?? 0) || 0,
    lat: item?.lat ?? item?.latitude ?? item?.Latitude ?? null,
    lng: item?.lng ?? item?.longitude ?? item?.Longitude ?? null,
  }))
}

function startPoll() {
  if (isC1TierMode()) return
  stopPoll()
  pollTimer = setInterval(async () => {
    if (!props.sessionId) return stopPoll()
    try {
      const res = await getVizData(props.sessionId, vizField.value, requestTopNByVizType())
      const d = res.data
      if (d.parsed) {
        stopPoll()
        parsed.value       = true
        parseStats.value   = d.parse_stats || parseStats.value
        geocodeItems.value = normalizeGeocodeItems(d.geocode_items || [])
        if (vizField.value === 'C3' || (typeof vizField.value === 'string' && vizField.value.startsWith('affiliation_'))) {
          countryData.value = buildCountsFromGeocode(geocodeItems.value, 'country')
          orgData.value = buildCountsFromGeocode(geocodeItems.value, 'org')
          cityData.value = buildCountsFromGeocode(geocodeItems.value, 'city')
        } else {
          countryData.value  = d.country_counts || []
          orgData.value      = d.org_counts || []
          cityData.value     = d.city_counts || []
        }
        cacheCurrentVizSnapshot()
        await loadEntityEdges()
        await nextTick()
        renderViz()
      }
    } catch (_) {}
  }, 4000)
}

function stopPoll() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

// ── 渲染分发 ──────────────────────────────────
async function renderViz() {
  if (!parsed.value) return
  let renderTask = null
  if (vizType.value === 'map' || vizType.value === 'heatmap') {
    await loadECharts()
    renderTask = renderMap()
  } else {
    await loadECharts()
    if (vizType.value === 'country') renderTask = renderCountryCharts()
    else if (vizType.value === 'org') renderTask = renderBarChart(orgChartEl, orgData.value, tLabel('发文量', 'Publications'), '#009688')
    else if (vizType.value === 'city') renderTask = renderBarChart(cityChartEl, cityData.value, tLabel('出现次数', 'Occurrences'), '#009688')
  }
  await nextTick()
  await (renderTask?.done || Promise.resolve())
  await waitForNextPaint()
}

function bindMapSelection(chart) {
  if (!chart) return
  if (!chart.__vizMapClickBound) {
    chart.__vizMapClickBound = true
    chart.on('click', (params) => {
      const isNodeSeries = params?.seriesId === 'map-points' || params?.seriesId === 'map-nodes'
      if (!isNodeSeries) return
      const nextName = typeof params?.name === 'string' ? params.name.trim() : ''
      if (!nextName) return
      selectedMapNodeName.value = selectedMapNodeName.value === nextName ? '' : nextName
      if (vizType.value === 'map' || vizType.value === 'heatmap') {
        renderMap()
      }
    })
  }
  if (!chart.__vizMapBlankClickBound) {
    chart.__vizMapBlankClickBound = true
    chart.getZr().on('click', (event) => {
      if (event?.target) return
      if (!selectedMapNodeName.value) return
      clearMapSelection()
      if (vizType.value === 'map' || vizType.value === 'heatmap') {
        renderMap()
      }
    })
  }
}

// ── ECharts 世界地图 ───────────────────────────
function renderMap(resetRoam = false) {
  if (!mapChartEl.value || !window.echarts) return null
  if (geocodeItems.value.length === 0) return null

  const mapNameByTier = (item = {}) => {
    if (vizTier.value === 'org' || vizType.value === 'org') {
      return item.organization || item.org || item.name || ''
    }
    if (vizTier.value === 'city' || vizType.value === 'city') {
      return item.City1 || item.city || item.name || ''
    }
    return item.country || item.name || ''
  }

  if (!worldRegistered) {
    window.echarts.registerMap('world', world)
    worldRegistered = true
  }

  const chart = makeChart(mapChartEl)
  if (!chart) return null
  const renderTask = createChartRenderTask(chart)

  const isAffiliationField = typeof vizField.value === 'string' && vizField.value.startsWith('affiliation_')
  const plotItems = isAffiliationField ? applyAffiliationCoordJitter(geocodeItems.value) : geocodeItems.value
  const rawScatterData = plotItems
    .map(item => {
      const lng = Number(item.lng)
      const lat = Number(item.lat)
      const val = Number(item.count) || 0
      if (Number.isNaN(lng) || Number.isNaN(lat)) return null
      return {
        name: mapNameByTier(item),
        value: [lng, lat, val],
        _meta: item,
      }
    })
    .filter(Boolean)
  const currentZoom = resetRoam ? MAP_BASE_ZOOM : getMapCurrentZoom(chart)
  const currentCenter = resetRoam ? null : mapRoamState.center
  // affiliation / 本地数据：不做网格聚合，保证与表格逐条对应
  const scatterData = buildMapScatterData(rawScatterData, currentZoom, true)
  const maxCount = scatterData.reduce((m, item) => Math.max(m, Number(item?.value?.[2]) || 0), 0)
  const safeMax = Math.max(maxCount, 1)
  const nodeSizeValue = Math.min(100, Math.max(1, Number(props.mapNodeSize || 100)))
  const sizeScale = 0.18 + (nodeSizeValue / 100) * 1.45
  // 放大后缩小节点，避免近邻机构圆点重叠
  const zoomShrink = Math.max(0.22, Math.min(1, Math.pow(MAP_BASE_ZOOM / Math.max(currentZoom, MAP_BASE_ZOOM), 0.55)))
  const minSize = 4 * sizeScale * zoomShrink
  const maxSize = 38 * sizeScale * zoomShrink
  const isFixedNodeSize = props.mapSizeMode === 'fixed'
  const opacityValue = Math.min(100, Math.max(1, Number(props.mapNodeOpacity || 70)))
  const nodeOpacity = Math.max(0, 1 - opacityValue / 100)
  const nodeColor = props.mapNodeColor || '#0f9f94'
  const mapLabelColor = isDark.value ? '#ffffff' : '#111827'
  const isHeatmapMode = vizType.value === 'heatmap'
  const selectionState = getMapSelectionState()
  const useLargeScatter = !isHeatmapMode && !isAffiliationField && scatterData.length > 800
  const isHeavyScatter = scatterData.length > MAP_HEAVY_THRESHOLD && !isHeatmapMode
  const mapScatterData = isHeatmapMode
    ? scatterData
    : scatterData.map((item) => {
      const count = Math.max(0, Number(item?.value?.[2]) || 0)
      const ratio = Math.pow(count / safeMax, 0.65)
      const size = isFixedNodeSize
        ? Math.max(4, (minSize + maxSize) / 2)
        : Math.max(4, minSize + ratio * (maxSize - minSize))
      return { ...item, size }
    })
  const heatScatterData = scatterData.map((item) => {
    const count = Math.max(0, Number(item?.value?.[2]) || 0)
    const ratio = Math.pow(count / safeMax, 0.65)
    const size = isFixedNodeSize
      ? Math.max(4, (minSize + maxSize) / 2)
      : Math.max(4, minSize + ratio * (maxSize - minSize))
    return {
      ...item,
      size,
      itemStyle: getSelectedNodeStyle('#111111', nodeOpacity, item, selectionState, true),
    }
  })
  const heatPointSize = Math.max(5, Math.round(getHeatPointSize(currentZoom, scatterData.length) * 0.75))
  const heatBlurSize = Math.max(8, Math.round(getHeatBlurSize(currentZoom, scatterData.length) * 0.72))
  const heatData = scatterData.map((item) => {
    const lng = Number(item?.value?.[0]) || 0
    const lat = Number(item?.value?.[1]) || 0
    const val = Number(item?.value?.[2]) || 0
    // 压缩极端值，避免单点过亮导致整图失真
    const weight = Math.log1p(Math.max(0, val))
    return [lng, lat, weight]
  })
  const heatValues = heatData.map(item => Number(item?.[2]) || 0).sort((a, b) => a - b)
  const heatMax = heatValues[heatValues.length - 1] || 1
  const p80Index = Math.max(0, Math.floor(heatValues.length * 0.8) - 1)
  const heatP80 = heatValues[p80Index] || heatMax
  const safeHeatMax = Math.max(heatP80, 1)
  const edgeColor = props.mapEdgeColor || '#334155'
  const edgeData = entityEdges.value
  const edgeWidthValue = Math.min(20, Math.max(1, Number(props.mapEdgeWidth || 8)))
  const edgeWidthRatio = Math.pow(edgeWidthValue / 20, 1.08)
  const edgeWidthScale = 0.22 + edgeWidthRatio * 5.6
  const edgeOpacityValue = Math.min(100, Math.max(1, Number(props.mapEdgeOpacity || 40)))
  const edgeOpacity = edgeVisibleState.value ? Math.max(0, 1 - edgeOpacityValue / 100) : 0
  const renderedEdgeData = edgeData.map((item) => {
    const baseWidth = Math.max(0.5, Number(item?.baseWidth) || 0.85)
    const width = Math.max(0.35, baseWidth * edgeWidthScale)
    const source = typeof item?.fromName === 'string' ? item.fromName.trim() : ''
    const target = typeof item?.toName === 'string' ? item.toName.trim() : ''
    const edgeKey = `${source}__${target}`
    const isRelated = !selectionState.hasSelection || selectionState.relatedEdgeKeys.has(edgeKey)
    return {
      ...item,
      isRelated,
        lineStyle: {
          width,
          color: edgeColor,
        opacity: selectionState.hasSelection
          ? (isRelated ? Math.min(1, edgeOpacity + 0.2) : Math.max(0.02, edgeOpacity * 0.12))
          : edgeOpacity,
      },
      emphasis: {
        lineStyle: {
          width: width * 1.12,
        },
      },
    }
  })
  const edgeSeries = renderedEdgeData.length > 0
    ? [{
      id: 'map-edges',
      name: 'Edges',
      type: 'lines',
      coordinateSystem: 'geo',
      data: renderedEdgeData,
      animation: false,
      progressive: 0,
      large: false,
      zlevel: 0,
      z: 1,
      silent: !edgeVisibleState.value,
      symbol: ['none', 'none'],
      symbolSize: 5,
      lineStyle: {
        color: edgeColor,
        opacity: edgeOpacity,
        type: 'solid',
        curveness: 0.3,
        cap: 'round',
        join: 'round',
      },
      emphasis: {
        lineStyle: {
          color: edgeColor,
          opacity: edgeVisibleState.value ? Math.min(1, edgeOpacity + 0.18) : 0,
          cap: 'round',
          join: 'round',
        },
      },
      tooltip: {
        show: edgeVisibleState.value,
        formatter: (params) => {
          const weight = Number(params?.data?.value) || 0
          return `${params?.data?.fromName || '-'} - ${params?.data?.toName || '-'}: ${weight}`
        },
      },
    }]
    : []

  chart.setOption({
    animation: false,
    animationDuration: 0,
    backgroundColor: isDark.value ? '#161f31' : '#fff',
    tooltip: {
      show: true,
      trigger: 'item',
      enterable: false,
      backgroundColor: isDark.value ? 'rgba(15, 23, 42, 0.96)' : '#fff',
      borderColor: isDark.value ? '#334155' : '#d1d5db',
      textStyle: { color: isDark.value ? '#e5e7eb' : '#111827' },
      formatter: (params) => {
        const meta = params?.data?._meta || {}
        const title = mapNameByTier(meta) || params?.name || '-'
        if (params.componentSubType === 'heatmap') {
          const val = Number(params?.value?.[2]) || 0
          return [
            `<b>${title}</b>`,
            `${tLabel('热度', 'Heat')}: ${val.toFixed(2)}`,
          ].filter(Boolean).join('<br/>')
        }
        return [
          `<b>${title}</b>`,
          `${tLabel('记录数', 'Records')}: ${meta.count ?? 0}`,
        ].filter(Boolean).join('<br/>')
      },
    },
    geo: {
      map: 'world',
      roam: true,
      zoom: currentZoom,
      center: currentCenter || undefined,
      scaleLimit: { min: MAP_MIN_ZOOM, max: MAP_MAX_ZOOM },
      layoutCenter: ['50%', '50%'],
      layoutSize: '100%',
      selectedMode: false,
      itemStyle: {
        areaColor: isDark.value ? '#3c465a' : '#e3e3e3b0',
        borderColor: isDark.value ? 'transparent' : '#e2e8f0',
        borderWidth: isDark.value ? 0 : 0.6,
      },
      emphasis: {
        disabled: true,
        itemStyle: { areaColor: isDark.value ? '#5b677f' : '#e3e3e3b0' },
      },
    },
    series: isHeatmapMode
      ? [
        ...edgeSeries,
        {
          id: 'map-heat',
          name: 'Density',
          type: 'heatmap',
          coordinateSystem: 'geo',
          data: heatData,
          animation: false,
          progressive: 0,
          silent: true,
          pointSize: heatPointSize,
          blurSize: heatBlurSize,
          minOpacity: 0,
          maxOpacity: 0.92,
          itemStyle: { opacity: 1 },
          emphasis: { itemStyle: { opacity: 1 } },
          legendHoverLink: false,
          zlevel: 0,
          z: 2,
        },
        {
          id: 'map-nodes',
          name: 'Nodes',
          type: 'scatter',
          coordinateSystem: 'geo',
          data: heatScatterData,
          animation: false,
          silent: isHeavyScatter,
          symbolSize: (value, params) => params?.data?.size || 5,
          itemStyle: {
            color: '#111111',
            opacity: nodeOpacity,
            borderWidth: 0,
          },
          label: {
            show: Boolean(props.mapLabelVisible),
            position: 'right',
            formatter: '{b}',
            color: mapLabelColor,
            opacity: 1,
            fontSize: 11,
          },
          legendHoverLink: false,
          zlevel: 0,
          z: 3,
        },
  ]
      : [
        ...edgeSeries,
        {
          id: 'map-points',
          name: 'Points',
          type: 'scatter',
          coordinateSystem: 'geo',
          data: mapScatterData.map((item) => ({
            ...item,
            itemStyle: getSelectedNodeStyle(nodeColor, nodeOpacity, item, selectionState, false),
          })),
          animation: false,
          animationDurationUpdate: 0,
          progressive: 0,
          progressiveThreshold: 0,
          large: false,
          symbolSize: (value, params) => params?.data?.size || 7,
          silent: false,
          itemStyle: {
            color: nodeColor,
            opacity: nodeOpacity,
          },
          label: {
            show: Boolean(props.mapLabelVisible),
            position: 'right',
            formatter: '{b}',
            color: mapLabelColor,
            opacity: 1,
            fontSize: 11,
          },
          emphasis: {
            disabled: true,
          },
          zlevel: 0,
          z: 3,
        },
      ],
    visualMap: isHeatmapMode
      ? {
        show: false,
        min: 0,
        max: safeHeatMax,
        seriesIndex: [edgeSeries.length],
        calculable: true,
        type: 'continuous',
        inRange: {
          color: ['#cfd6ff', '#8fd694', '#ffe85a', '#ff9f2a', '#ff4d2d'],
        },
      }
      : null,
  }, { notMerge: false, lazyUpdate: true })
  lastRenderedMapZoom = currentZoom
  bindMapRoam(chart)
  bindMapSelection(chart)
  return renderTask
}

// ── 国家 横向条形图 ────────────────────────────
function renderCountryCharts() {
  return renderBarChart(countryChartEl, countryData.value, tLabel('记录数', 'Records'), '#009688')
}

function makeChart(elRef) {
  if (!elRef.value || !window.echarts) return null
  let inst = window.echarts.getInstanceByDom(elRef.value)
  if (!inst) {
    inst = window.echarts.init(elRef.value, null, { renderer: 'canvas', useDirtyRect: true })
    chartInstances.push(inst)
  } else if (!chartInstances.includes(inst)) {
    chartInstances.push(inst)
  }
  return inst
}

function buildMapScatterData(points, zoom = MAP_BASE_ZOOM, keepRaw = false) {
  const list = Array.isArray(points) ? points : []
  if (keepRaw || list.length <= MAP_CLUSTER_THRESHOLD || zoom >= 4) {
    return list
  }

  const gridSize = Math.max(0.15, MAP_GRID_SIZE / Math.max(zoom, 1))
  const grouped = new Map()

  for (const item of list) {
    const lng = Number(item?.value?.[0])
    const lat = Number(item?.value?.[1])
    const val = Number(item?.value?.[2]) || 0
    if (Number.isNaN(lng) || Number.isNaN(lat)) continue
    const gx = Math.floor((lng + 180) / gridSize)
    const gy = Math.floor((lat + 90) / gridSize)
    const key = `${gx}_${gy}`
    const prev = grouped.get(key)
    if (!prev) {
      grouped.set(key, {
        lngSum: lng * Math.max(val, 1),
        latSum: lat * Math.max(val, 1),
        weight: Math.max(val, 1),
        count: val,
        names: item.name ? [item.name] : [],
        memberNames: item.name ? [item.name] : [],
        meta: item._meta,
      })
      continue
    }
    prev.lngSum += lng * Math.max(val, 1)
    prev.latSum += lat * Math.max(val, 1)
    prev.weight += Math.max(val, 1)
    prev.count += val
    if (item.name && prev.names.length < 3) prev.names.push(item.name)
    if (item.name && !prev.memberNames.includes(item.name)) prev.memberNames.push(item.name)
  }

  return Array.from(grouped.values()).map((bucket) => {
    const lng = bucket.lngSum / bucket.weight
    const lat = bucket.latSum / bucket.weight
    const count = bucket.count
    const names = bucket.names.filter(Boolean)
    return {
      name: names[0] || bucket.meta?.country || bucket.meta?.city || bucket.meta?.organization || '',
      _memberNames: bucket.memberNames,
      value: [lng, lat, count],
      _meta: {
        ...bucket.meta,
        count,
        country: bucket.meta?.country || names.join(' / '),
        aggregated: true,
      },
    }
  })
}

function getMapCurrentZoom(chart) {
  try {
    const option = chart?.getOption?.()
    const zoom = Number(option?.geo?.[0]?.zoom) || mapRoamState.zoom || MAP_BASE_ZOOM
    const center = option?.geo?.[0]?.center
    mapRoamState = {
      zoom,
      center: Array.isArray(center) ? center : mapRoamState.center,
    }
    return zoom
  } catch (_) {
    return mapRoamState.zoom || MAP_BASE_ZOOM
  }
}

function getMapCurrentCenter(chart) {
  try {
    const option = chart?.getOption?.()
    const center = option?.geo?.[0]?.center
    if (Array.isArray(center) && center.length === 2) return center
    return mapRoamState.center
  } catch (_) {
    return mapRoamState.center
  }
}

function getHeatPointSize(zoom, count) {
  const zoomFactor = Math.max(0.8, Math.min(2.4, zoom / MAP_BASE_ZOOM))
  const densityFactor = count > 3000 ? 0.85 : count > 1500 ? 1 : 1.15
  return Math.round(14 * zoomFactor * densityFactor)
}

function getHeatBlurSize(zoom, count) {
  const zoomFactor = Math.max(0.9, Math.min(2.8, zoom / MAP_BASE_ZOOM))
  const densityFactor = count > 3000 ? 0.9 : count > 1500 ? 1 : 1.1
  return Math.round(20 * zoomFactor * densityFactor)
}

function bindMapRoam(chart) {
  if (!chart || chart.__vizMapRoamBound) return
  chart.__vizMapRoamBound = true
  let roamTimer = null
  chart.on('georoam', () => {
    const prevZoom = mapRoamState.zoom || MAP_BASE_ZOOM
    const nextZoom = getMapCurrentZoom(chart)
    const nextCenter = getMapCurrentCenter(chart)
    mapRoamState.zoom = nextZoom
    mapRoamState.center = nextCenter
    if (roamTimer) clearTimeout(roamTimer)
    roamTimer = setTimeout(() => {
      const zoomChanged = Math.abs(nextZoom - lastRenderedMapZoom) > 0.001
      if (zoomChanged && (vizType.value === 'map' || vizType.value === 'heatmap')) {
        renderMap()
      }
    }, 180)
  })
}

function renderBarChart(elRef, data, unitLabel, color) {
  const chart = makeChart(elRef)
  if (!chart) return null
  const renderTask = createChartRenderTask(chart)
  const isAffiliation = typeof vizField.value === 'string' && vizField.value.startsWith('affiliation_')
  const dataTop = isAffiliation
    ? (Array.isArray(data) ? data : [])
    : (Array.isArray(data) ? data : []).slice(0, BAR_TOP_N)
  const names  = dataTop.map(d => d.name).reverse()
  const values = dataTop.map(d => d.value).reverse()
  const barOpacity = isDark.value ? 0.5 : 1
  const barColor = isDark.value ? '#2dd4bf' : color
  chart.setOption({
    backgroundColor: isDark.value ? '#161f31' : '#ffffff',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: isDark.value ? 'rgba(15, 23, 42, 0.96)' : '#fff',
      borderColor: isDark.value ? '#334155' : '#d1d5db',
      textStyle: { color: isDark.value ? '#e5e7eb' : '#111827' },
    },
    grid: { left: '4%', right: '6%', bottom: '3%', top: '3%', containLabel: true },
    xAxis: {
      type: 'value',
      name: unitLabel,
      nameTextStyle: { color: isDark.value ? '#94a3b8' : '#6b7280' },
      axisLine: { lineStyle: { color: isDark.value ? '#475569' : '#cbd5e1' } },
      splitLine: { lineStyle: { color: isDark.value ? '#334155' : '#e2e8f0' } },
      axisLabel: { color: isDark.value ? '#cbd5e1' : '#6b7280' },
    },
    yAxis: {
      type: 'category', data: names,
      axisLabel: { fontSize: 12, width: 240, overflow: 'truncate', color: isDark.value ? '#cbd5e1' : '#6b7280' },
      axisLine: { lineStyle: { color: isDark.value ? '#475569' : '#cbd5e1' } },
    },
    series: [{
      type: 'bar', data: values,
      itemStyle: { color: barColor, opacity: barOpacity },
      label: { show: true, position: 'right', formatter: '{c}', color: isDark.value ? '#e5e7eb' : '#374151' },
    }],
  })
  return renderTask
}

function destroyCharts({ preserveRoam = false } = {}) {
  if (preserveRoam && mapChartEl.value && window.echarts) {
    const live = window.echarts.getInstanceByDom(mapChartEl.value)
    if (live) getMapCurrentZoom(live)
  }
  const savedRoam = preserveRoam
    ? {
      zoom: mapRoamState.zoom || MAP_BASE_ZOOM,
      center: Array.isArray(mapRoamState.center) ? [...mapRoamState.center] : null,
    }
    : null

  chartInstances.forEach(c => c.dispose())
  chartInstances = []

  if (savedRoam) {
    mapRoamState = savedRoam
    lastRenderedMapZoom = savedRoam.zoom
  } else {
    mapRoamState = {
      zoom: MAP_BASE_ZOOM,
      center: null,
    }
    lastRenderedMapZoom = MAP_BASE_ZOOM
  }
}

function resizeCharts() {
  chartInstances.forEach((chart) => {
    try {
      chart.resize()
    } catch (_) {}
  })
}

// ── 监听切换 ──────────────────────────────────
watch(vizType, async () => {
  destroyCharts()
  await nextTick()
  renderViz()
})

watch(() => props.sessionId, (v, oldV) => {
  hasDataSource.value = Boolean(v || props.demoMode)
  if (v !== oldV) {
    vizDataCache.clear()
    entityEdgeCache.clear()
    if (!v) clearVizDisplayState()
  }
  if (!v || v === oldV) return
  loadData()
})

watch(vizField, async () => {
  edgeLoadSeq += 1
  await loadData()
})

watch(() => props.fixedField, (v) => {
  if (!v || v === vizField.value) return
  vizField.value = v
})

watch(() => props.fixedType, (v) => {
  if (!v || v === vizType.value) return
  edgeLoadSeq += 1
  vizType.value = v
  if (props.sessionId || props.demoMode) loadData()
})

watch(() => props.fixedTier, (v) => {
  if (!v || v === vizTier.value) return
  edgeLoadSeq += 1
  vizTier.value = v
  if (props.sessionId || props.demoMode) loadData()
})

watch(() => props.reloadKey, () => {
  vizDataCache.clear()
  entityEdgeCache.clear()
  if (props.sessionId || props.demoMode) loadData()
})

watch(() => props.demoMode, () => {
  hasDataSource.value = Boolean(props.sessionId || props.demoMode)
  vizDataCache.clear()
  entityEdgeCache.clear()
  loadData()
})

watch(() => [props.mapNodeSize, props.mapLabelVisible, props.mapNodeOpacity, props.mapSizeMode, props.mapNodeColor, props.mapEdgeColor, props.mapEdgeWidth, props.mapEdgeOpacity], async () => {
  if (vizType.value !== 'map' && vizType.value !== 'heatmap') return
  await nextTick()
  // 在用户当前漫游视图上刷新节点样式，不重置底图位置
  if (mapChartEl.value && window.echarts) {
    const live = window.echarts.getInstanceByDom(mapChartEl.value)
    if (live) getMapCurrentZoom(live)
  }
  renderMap(false)
})

watch(() => props.showEdges, async (visible) => {
  if (vizType.value !== 'map' && vizType.value !== 'heatmap') return
  loading.value = true
  if (edgeHideTimer) {
    clearTimeout(edgeHideTimer)
    edgeHideTimer = null
  }
  try {
    if (mapChartEl.value && window.echarts) {
      const live = window.echarts.getInstanceByDom(mapChartEl.value)
      if (live) getMapCurrentZoom(live)
    }
    if (visible) {
      await loadEntityEdges()
      syncEdgeVisibleState(true)
    } else {
      syncEdgeVisibleState(false)
      await nextTick()
      const renderTask = renderMap(false)
      await (renderTask?.done || Promise.resolve())
      await waitForNextPaint()
      if (entityEdges.value.length > 0) {
        edgeHideTimer = window.setTimeout(() => {
          edgeHideTimer = null
          if (props.showEdges) return
          entityEdges.value = []
          if (vizType.value === 'map' || vizType.value === 'heatmap') {
            renderMap(false)
          }
        }, EDGE_TOGGLE_DURATION)
      }
      return
    }
    await nextTick()
    const renderTask = renderMap(false)
    await (renderTask?.done || Promise.resolve())
    await waitForNextPaint()
  } finally {
    loading.value = false
  }
})

watch(isDark, async () => {
  await nextTick()
  destroyCharts({ preserveRoam: true })
  renderViz()
})

watch(loading, (value) => {
  emit('viz-loading', value)
}, { immediate: true })

onMounted(() => {
  syncTheme()
  window.addEventListener('app-theme-change', syncTheme)
  window.addEventListener('resize', resizeCharts)
  if (window.ResizeObserver) {
    resizeObserver = new ResizeObserver(() => {
      resizeCharts()
    })
    if (mapChartEl.value) resizeObserver.observe(mapChartEl.value)
    if (countryChartEl.value) resizeObserver.observe(countryChartEl.value)
    if (orgChartEl.value) resizeObserver.observe(orgChartEl.value)
    if (cityChartEl.value) resizeObserver.observe(cityChartEl.value)
  }
  if (props.autoLoadViz && (props.sessionId || props.demoMode)) loadData()
})

onActivated(async () => {
  await nextTick()
  resizeCharts()
  if (parsed.value) {
    destroyCharts()
    await nextTick()
    await renderViz()
  }
})

onBeforeUnmount(() => {
  stopPoll()
  if (edgeHideTimer) {
    clearTimeout(edgeHideTimer)
    edgeHideTimer = null
  }
  destroyCharts()
  window.removeEventListener('app-theme-change', syncTheme)
  window.removeEventListener('resize', resizeCharts)
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
})
</script>

<style scoped>
.viz-view { min-height: 100%;display: flex;justify-content: center;align-items: center; }
.viz-view.embedded {
  height: 100%;
  width: 100%;
  min-height: 0;
  overflow: hidden;
}

.empty-demo-link-btn {
  border: 0;
  background: transparent;
  color: #009688;
  padding: 0 2px;
  margin: 0;
  font-size: inherit;
  line-height: inherit;
  cursor: pointer;
  &:hover{
    text-decoration: underline;
  }
}

.viz-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
  flex-wrap: wrap;
  gap: 10px;
}
.viz-title {
  display: flex;
  align-items: center;
  gap: 8px;
}
.viz-title h2 { font-size: 18px; color: #1a237e; }

.viz-controls {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}

.viz-body { display: flex; flex-direction: column; gap: 16px; }
.viz-view.embedded .viz-body {
  height: 100%;
  width: 100%;
  min-height: 0;
  gap: 10px;
}

.viz-card { height: 100%; }
.viz-view.embedded .viz-card {
  box-shadow: none;
  border: 1px solid #e3eaf6;
}

.card-hd {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  /*color: #3949ab;*/
  font-size: 13px;
}
.card-hd-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.map-container {
  height: 500px;
  width: 100%;
  border-radius: 4px;
}

.embedded-map-wrap {
  height: 100%;
  min-height: 0;
}

.embedded-map {
  height: 100% !important;
  min-height: 0;
  border-radius: 8px;
}

.viz-view.embedded .map-container {
  height: 100%;
  min-height: 0;
}

.chart-container {
  height: 440px;
  width: 100%;
}
.chart-container.tall {
  height: 600px;
}
.viz-view.embedded .chart-container,
.viz-view.embedded .chart-container.tall {
  height: 100%;
}

.viz-view.embedded :deep(.el-row),
.viz-view.embedded :deep(.el-col) {
  height: 100%;
}

.viz-view.embedded :deep(.el-card__body) {
  height: calc(100% - 56px);
}

.empty-tip {
  height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.home-view.is-dark .viz-view.embedded .viz-card {
  border-color: #334155;
  background: #161f31;
}

.home-view.is-dark .viz-view .card-hd {
  color: #c7cedb;
}

.home-view.is-dark .viz-view :deep(.el-card),
.home-view.is-dark .viz-view :deep(.el-card__header),
.home-view.is-dark .viz-view :deep(.el-card__body) {
  background: #161f31;
  border-color: #334155;
  color: #e5e7eb;
}
</style>
