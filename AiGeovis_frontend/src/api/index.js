import axios from 'axios'

const BACKEND_PORT = 35696
const PROD_API_BASE = 'https://smartdata.las.ac.cn/AiGeovis/AiGeovis/AiGeovis_api/api'

/**
 * 局域网/本机：跟随页面 hostname，保证用 10.x / 192.168.x 打开前端时 API 也打到同一台机器。
 * 可用 VITE_API_BASE_URL 强制覆盖；生产域名走线上地址。
 */
function resolveApiBaseUrl() {
  const envUrl = (import.meta.env.VITE_API_BASE_URL || '').trim()
  if (typeof window !== 'undefined') {
    const host = window.location.hostname || ''
    const isLocalOrLan =
      host === 'localhost'
      || host === '127.0.0.1'
      || /^\d{1,3}(?:\.\d{1,3}){3}$/.test(host)
    if (isLocalOrLan) {
      return `http://${host}:${BACKEND_PORT}/api`
    }
  }
  if (envUrl) return envUrl
  return PROD_API_BASE
}

const api = axios.create({
  baseURL: resolveApiBaseUrl(),
  timeout: 120000,
})

export function checkHealth() {
  return api.get('/health')
}

/** 验证 session 是否仍有效，并返回基本信息（含已解析字段统计） */
export function getSessionInfo(sessionId) {
  return api.get('/data/session-info', { params: { session_id: sessionId } })
}

/** 删除 session（清除后端内存 + 磁盘缓存） */
export function deleteSession(sessionId) {
  return api.delete('/data/session', { params: { session_id: sessionId } })
}

// ─── 数据 ─────────────────────────────────────
export function uploadWos(formData) {
  return api.post('/data/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export function getRecords(sessionId, page = 1, pageSize = 50) {
  return api.get('/data/records', {
    params: { session_id: sessionId, page, page_size: pageSize }
  })
}

export function getSummary(sessionId) {
  return api.get('/data/summary', { params: { session_id: sessionId } })
}

export function exportCsv(sessionId) {
  return api.get('/data/export', {
    params: { session_id: sessionId },
    responseType: 'blob'
  })
}

export function getDemoData(name) {
  return api.get(`/demo/data/${name}`)
}

export function getDemoMatrix(name) {
  return api.get(`/demo/data/${name}`)
}

/** 自定义数据案例：后端加载内置示例地址表并创建真实会话 */
export function createCustomDemoSession() {
  return api.post('/demo/custom-session')
}

// ─── 地理解析 ─────────────────────────────────
/** aiConfigs: 模型配置数组，支持多模型；field: "C1" 或 "C3" */
export function startParseC1(sessionId, aiConfigs, batchSize = 30, field = 'C1', skipCache = false, lang = 'zh') {
  return api.post('/geo/parse-c1', {
    session_id: sessionId,
    ai_configs: aiConfigs,
    batch_size: batchSize,
    field,
    skip_cache: skipCache,
    lang,
  })
}

export function startParseTier(sessionId, aiConfigs, batchSize = 30, field = 'C1', tier = 'country', lang = 'zh') {
  return api.post('/geo/parse-tier', {
    session_id: sessionId,
    ai_configs: aiConfigs,
    batch_size: batchSize,
    field,
    tier,
    lang,
  })
}

/** C1 分层批量解析：tiers 可传任意组合，如 ["country"]、["country","city","org"] */
export function startParseBatchTiers(sessionId, aiConfigs, batchSize = 30, field = 'C1', tiers = ['country'], skipCache = false, lang = 'zh') {
  return api.post('/geo/parse-batch-tiers', {
    session_id: sessionId,
    ai_configs: aiConfigs,
    batch_size: batchSize,
    field,
    tiers,
    skip_cache: skipCache,
    lang,
  })
}

export function stopParseC1(sessionId, lang = 'zh') {
  return api.post('/geo/stop-parse', null, { params: { session_id: sessionId, lang } })
}

/** 仅列出模型 ID（无测速） */
export function listModels(cfg) {
  return api.post('/models/list', cfg)
}

/**
 * 列出模型 + 实际测速 + 按响应时间排序
 * @param {object} cfg  { type, provider, api_key, base_url, timeout?, max_workers? }
 */
export function benchmarkModels(cfg) {
  return api.post('/models/benchmark', cfg, { timeout: 300000 })
}

export function getParseProgress(sessionId) {
  return api.get('/geo/parse-progress', { params: { session_id: sessionId } })
}

export function getTierProgress(sessionId) {
  return api.get('/geo/tier-progress', { params: { session_id: sessionId } })
}

export function getGeoResults(sessionId, page = 1, pageSize = 50, field = 'C1') {
  return api.get('/geo/results', {
    params: { session_id: sessionId, page, page_size: pageSize, field }
  })
}

export function getTierResults(sessionId, field = 'C1', tier = 'country', page = 1, pageSize = 50) {
  return api.get('/geo/tier-results', {
    params: { session_id: sessionId, field, tier, page, page_size: pageSize }
  })
}

/**
 * 确定性地理编码兜底（Nominatim / 高德）：
 * 对解析后仍缺坐标的条目补齐经纬度并回填结果表。
 * tier 传 'country'|'city'|'org' 时作用于分层解析表；affiliation 会话无需传 field/tier。
 */
export function runGeocode(sessionId, amapKey = '', useNominatim = true, field = 'C1', tier = '') {
  return api.post('/geo/geocode', {
    session_id: sessionId,
    amap_key: amapKey,
    use_nominatim: useNominatim,
    field,
    tier,
  }, { timeout: 600000 })
}

/** 获取聚合可视化数据（国家/机构/城市排名 + 地理编码点） */
export function getVizData(sessionId, field = 'C1', topN = 30) {
  return api.get('/geo/viz-data', {
    params: { session_id: sessionId, field, top_n: topN }
  })
}

export function getTierStats(sessionId, field = 'C1', tier = 'country', topN = 30) {
  return api.get('/geo/stats', {
    params: { session_id: sessionId, field, tier, top_n: topN }
  })
}

export function getEntityMatrix(sessionId, field = 'C1', tier = 'org', topN = 50, threshold = 0) {
  return api.get('/geo/entity-matrix', {
    params: { session_id: sessionId, field, tier, top_n: topN, threshold }
  })
}

export function exportEntityMatrixGml(
  sessionId,
  field = 'C1',
  tier = 'country',
  topN = 10000,
  threshold = 0,
  coordType = 'normalized',
  includeMatrix = false,
) {
  return api.get('/geo/entity-matrix/export', {
    params: {
      session_id: sessionId,
      field,
      tier,
      top_n: topN,
      threshold,
      coord_type: coordType,
      include_matrix: includeMatrix,
    },
    responseType: 'blob'
  })
}

/** Affiliation 类型 AI 解析（国家/机构/城市列表） */
export function startParseAffiliation(sessionId, aiConfigs, batchSize = 30, skipCache = false, lang = 'zh') {
  return api.post('/geo/parse-affiliation', {
    session_id: sessionId,
    ai_configs: aiConfigs,
    batch_size: batchSize,
    skip_cache: Boolean(skipCache),
    lang,
  })
}
