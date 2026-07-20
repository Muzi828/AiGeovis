<template>
  <div class="data-view" :class="{ 'is-embedded': embedded }">
    <!-- 无数据提示 -->
    <el-empty
      v-if="!hasDataSource"
      :description="embedded ? tLabel('请先上传 WoS 文件', 'Please upload WoS files first') : tLabel('请先在「数据加载」页上传 WoS 文件', 'Please upload WoS files in Data Prep first')"
      image-size="120"
    >
      <el-button v-if="!embedded" type="primary" @click="$router.push('/home')">{{ tLabel('去首页', 'Go Home') }}</el-button>
    </el-empty>

    <template v-else>
      <!-- 顶部操作栏 -->
      <div class="toolbar">
        <span class="toolbar-count">{{ importCountText }}</span>
        <div class="toolbar-right">
          <el-button size="medium" class="toolbar-btn" @click="openFieldDialog">
            <el-icon style="margin-right: 10px;"><Grid /></el-icon>
            {{ tLabel('显示字段', 'Fields') }}
          </el-button>
          <el-button v-if="!hideExport" size="medium" type="primary" class="toolbar-btn export-btn" @click="doExport">
            <el-icon><Download /></el-icon>
            {{ tLabel('导出 CSV', 'Export CSV') }}
          </el-button>
        </div>
      </div>

      <!-- 数据表格 -->
<!--      <el-card shadow="always" class="table-card">-->
        <div ref="tableWrapRef" class="table-scroll-wrap">
          <el-table
            v-loading="loading"
            class="data-table"
            :data="records"
            border
            stripe
            size="small"
            :height="tableHeight"
          >
          <el-table-column
            v-for="col in visibleCols"
            :key="col"
            :prop="col"
            :label="col"
            :min-width="colWidth(col)"
            :align="['POS', 'PY', 'TC', 'count', 'lat', 'lng', 'Latitude', 'Longitude'].includes(col) ? 'center' : 'left'"
            :header-align="['POS', 'PY', 'TC', 'count', 'lat', 'lng', 'Latitude', 'Longitude'].includes(col) ? 'center' : 'left'"
          />
          </el-table>
        </div>

        <div class="pagination">
          <div class="page-size-left">
            <el-select v-model="pageSize" size="medium" style="width:110px;" @change="onPageSizeChange">
              <el-option :value="20" :label="tLabel('20 条/页', '20 / page')" />
              <el-option :value="50" :label="tLabel('50 条/页', '50 / page')" />
              <el-option :value="100" :label="tLabel('100 条/页', '100 / page')" />
            </el-select>
          </div>
          <el-pagination
            v-model:current-page="currentPage"
            :page-size="pageSize"
            :total="total"
            layout="prev, pager, next, jumper"
            @current-change="loadPage"
          />
        </div>
<!--      </el-card>-->

      <el-dialog
        v-model="fieldDialogVisible"
        class="field-select-dialog"
        :title="tLabel('显示字段', 'Fields')"
        width="700px"
        align-center
        append-to-body
        destroy-on-close
      >
        <div class="field-dialog-tools">
          <div class="field-dialog-actions">
            <el-button size="small" @click="selectAllFields">{{ tLabel('全选', 'Select All') }}</el-button>
            <el-button size="small" @click="resetDefaultFields">{{ tLabel('默认字段', 'Default') }}</el-button>
          </div>
          <span class="field-dialog-count">{{ tLabel('已选', 'Selected') }} {{ tempVisibleCols.length }} {{ tLabel('个', '') }}</span>
        </div>
        <el-checkbox-group v-model="tempVisibleCols" class="field-dialog-group">
          <el-checkbox
            v-for="col in allCols"
            :key="col"
            class="field-dialog-item"
            :label="col"
          >{{ col }}</el-checkbox>
        </el-checkbox-group>
        <template #footer>
          <el-button @click="fieldDialogVisible = false">{{ tLabel('取消', 'Cancel') }}</el-button>
          <el-button type="primary" @click="applyVisibleFields">{{ tLabel('确定', 'Confirm') }}</el-button>
        </template>
      </el-dialog>

      <!-- 统计摘要抽屉 -->
      <el-drawer v-model="summaryVisible" :title="tLabel('数据统计摘要', 'Data Summary')" size="480px" direction="rtl">
        <div v-if="summary" class="summary-drawer">
          <el-statistic label="记录总数" :value="summary.record_count" class="stat-item" />

          <div class="chart-block">
            <h4>发文年份分布</h4>
            <div class="year-bars">
              <div
                v-for="item in summary.year_distribution"
                :key="item.year"
                class="year-bar-wrap"
              >
                <div
                  class="year-bar"
                  :style="{ height: barHeight(item.count, summary.year_distribution) + 'px' }"
                  :title="`${item.year}: ${item.count} 篇`"
                />
                <span class="year-label">{{ item.year }}</span>
              </div>
            </div>
          </div>

          <div class="list-block">
            <h4>Top 来源期刊</h4>
            <div
              v-for="item in summary.top_sources"
              :key="item.name"
              class="list-item"
            >
              <span class="list-name" :title="item.name">{{ item.name }}</span>
              <el-progress
                :percentage="pct(item.value, summary.top_sources)"
                :stroke-width="12"
                class="list-bar"
              />
              <span class="list-val">{{ item.value }}</span>
            </div>
          </div>

          <div class="list-block">
            <h4>文献类型</h4>
            <div
              v-for="item in summary.document_types"
              :key="item.name"
              class="list-item"
            >
              <span class="list-name">{{ item.name }}</span>
              <el-progress :percentage="pct(item.value, summary.document_types)" :stroke-width="12" class="list-bar" />
              <span class="list-val">{{ item.value }}</span>
            </div>
          </div>

          <div class="list-block">
            <h4>高频关键词 (Top 15)</h4>
            <el-space wrap>
              <el-tag
                v-for="item in summary.top_keywords"
                :key="item.name"
                size="small"
                type="info"
              >{{ item.name }} ({{ item.value }})</el-tag>
            </el-space>
          </div>
        </div>
        <div v-else v-loading="true" style="height:200px" />
      </el-drawer>
    </template>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { getRecords, getSummary, exportCsv } from '../api/index.js'

const props = defineProps({
  sessionId:   { type: String, default: '' },
  recordCount: { type: Number, default: 0 },
  embedded:    { type: Boolean, default: false },
  langZh:      { type: Boolean, default: true },
  useExternalData: { type: Boolean, default: false },
  externalRecords: { type: Array, default: () => [] },
  externalLoading: { type: Boolean, default: false },
  hideExport: { type: Boolean, default: false },
})

const DEFAULT_COLS = ['POS', 'TI', 'AU', 'SO', 'PY', 'TC', 'DI', 'C1', 'C3']

const loading       = ref(false)
const records       = ref([])
const total         = ref(0)
const currentPage   = ref(1)
const pageSize      = ref(50)
const allCols       = ref([...DEFAULT_COLS])
const visibleCols   = ref([...DEFAULT_COLS])
const fieldDialogVisible = ref(false)
const tempVisibleCols = ref([...DEFAULT_COLS])
const summaryVisible = ref(false)
const summary       = ref(null)
const tableHeight = computed(() => (props.embedded ? '100%' : 560))
const viewportWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1440)
const tableWrapRef = ref(null)
const tableWrapWidth = ref(0)
const externalMode = computed(() => Boolean(props.useExternalData))
const hasDataSource = computed(() => Boolean(props.sessionId || externalMode.value))
let resizeHandler = null
let tableResizeObserver = null

function tLabel(zh, en) {
  return props.langZh ? zh : en
}

const importCountText = computed(() => {
  const n = Number(total.value) || 0
  // 自定义地址表 / affiliation：用“记录”；WoS 文献：用“论文”
  const looksLikeAddress = allCols.value.some((c) =>
    ['Organization', 'unit-name', 'name', '_affiliation_type', 'ParseSrc'].includes(c)
  ) && !allCols.value.includes('TI')
  if (looksLikeAddress) {
    return tLabel(`共导入 ${n} 条记录`, `Imported ${n} records`)
  }
  return tLabel(`共导入 ${n} 篇论文`, `Imported ${n} papers`)
})

async function loadPage(page = 1) {
  if (externalMode.value) {
    currentPage.value = page
    const all = Array.isArray(props.externalRecords) ? props.externalRecords : []
    total.value = all.length
    const start = (page - 1) * pageSize.value
    const end = start + pageSize.value
    records.value = all.slice(start, end)
    if (all.length > 0) {
      const keys = Object.keys(all[0]).filter(k => k !== 'ParseModel')
      allCols.value = keys
      const defaults = keys.filter((c) => DEFAULT_COLS.includes(c))
      if (defaults.length > 0) {
        visibleCols.value = defaults
      } else if (visibleCols.value.every(c => !keys.includes(c))) {
        visibleCols.value = keys.slice(0, 8)
      }
    } else {
      allCols.value = [...DEFAULT_COLS]
      visibleCols.value = [...DEFAULT_COLS]
    }
    loading.value = Boolean(props.externalLoading)
    return
  }
  if (!props.sessionId) return
  loading.value = true
  currentPage.value = page
  try {
    const res = await getRecords(props.sessionId, page, pageSize.value)
    records.value = res.data.records
    total.value   = res.data.total

    // 动态更新列（过滤掉 ParseModel）
    if (res.data.records.length > 0) {
      const keys = Object.keys(res.data.records[0]).filter(k => k !== 'ParseModel')
      allCols.value = keys
      // 初始化只显示默认列（与实际列取交集）
      if (visibleCols.value.every(c => !keys.includes(c))) {
        visibleCols.value = keys.slice(0, 8)
      }
    }
  } catch (e) {
    ElMessage.error('加载数据失败：' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

function onPageSizeChange() {
  loadPage(1)
}

function openFieldDialog() {
  tempVisibleCols.value = [...visibleCols.value]
  fieldDialogVisible.value = true
}

function selectAllFields() {
  tempVisibleCols.value = [...allCols.value]
}

function resetDefaultFields() {
  const defaults = allCols.value.filter((c) => DEFAULT_COLS.includes(c))
  tempVisibleCols.value = defaults.length > 0 ? defaults : allCols.value.slice(0, 8)
}

function applyVisibleFields() {
  if (tempVisibleCols.value.length === 0) {
    ElMessage.warning('至少选择一个字段')
    return
  }
  visibleCols.value = [...tempVisibleCols.value]
  fieldDialogVisible.value = false
}

async function loadSummary() {
  summaryVisible.value = true
  if (summary.value) return
  try {
    const res = await getSummary(props.sessionId)
    summary.value = res.data
  } catch (e) {
    ElMessage.error('获取统计失败')
  }
}

async function doExport() {
  try {
    if (externalMode.value) {
      const rows = Array.isArray(props.externalRecords) ? props.externalRecords : []
      if (rows.length === 0) {
        ElMessage.warning(tLabel('暂无可导出的数据', 'No data to export'))
        return
      }
      const cols = allCols.value.length > 0
        ? allCols.value
        : Object.keys(rows[0] || {}).filter((k) => k !== 'ParseModel')
      const escapeCell = (val) => {
        const text = val == null ? '' : String(val)
        if (/[",\n\r]/.test(text)) return `"${text.replace(/"/g, '""')}"`
        return text
      }
      const lines = [
        cols.map(escapeCell).join(','),
        ...rows.map((row) => cols.map((col) => escapeCell(row?.[col])).join(',')),
      ]
      const blob = new Blob([`\uFEFF${lines.join('\n')}`], { type: 'text/csv;charset=utf-8;' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'wos_data.csv'
      a.click()
      URL.revokeObjectURL(url)
      return
    }
    if (props.hideExport) return
    if (!props.sessionId) {
      ElMessage.warning(tLabel('请先上传数据', 'Please upload data first'))
      return
    }
    const res = await exportCsv(props.sessionId)
    const url = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = url
    a.download = 'wos_data.csv'
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    ElMessage.error(tLabel('导出失败', 'Export failed'))
  }
}

function colWidth(col) {
  if (['POS', 'PY', 'TC'].includes(col)) return 70
  const wide = ['TI', 'AB', 'C1', 'AU', 'AF', 'CR', 'DE', 'ID']
  if (props.embedded) {
    const colCount = Math.max(visibleCols.value.length, 1)
    const widthBase = tableWrapWidth.value || Math.floor(viewportWidth.value * 0.66)
    const available = Math.max(widthBase - 12, 280)
    const totalWeight = visibleCols.value.reduce((sum, c) => sum + (wide.includes(c) ? 1.45 : 1), 0) || colCount
    const unit = Math.max(22, Math.floor(available / totalWeight))
    return wide.includes(col) ? Math.floor(unit * 1.45) : unit
  }
  return wide.includes(col) ? 240 : 100
}

function barHeight(val, arr) {
  const max = Math.max(...arr.map(i => i.count))
  return max ? Math.round((val / max) * 80) + 4 : 4
}

function pct(val, arr) {
  const max = Math.max(...arr.map(i => i.value))
  return max ? Math.round((val / max) * 100) : 0
}

watch(() => props.sessionId, (v) => {
  if (v) {
    summary.value = null
    loadPage(1)
  }
})

watch(() => props.externalRecords, () => {
  if (!externalMode.value) return
  loadPage(1)
}, { deep: true })

watch(() => props.externalLoading, (v) => {
  if (!externalMode.value) return
  loading.value = Boolean(v)
})

onMounted(() => {
  if (typeof window !== 'undefined') {
    resizeHandler = () => { viewportWidth.value = window.innerWidth }
    window.addEventListener('resize', resizeHandler)
  }
  if (tableWrapRef.value) {
    tableWrapWidth.value = tableWrapRef.value.clientWidth || 0
    if (typeof ResizeObserver !== 'undefined') {
      tableResizeObserver = new ResizeObserver((entries) => {
        const entry = entries?.[0]
        if (!entry) return
        tableWrapWidth.value = Math.floor(entry.contentRect.width)
      })
      tableResizeObserver.observe(tableWrapRef.value)
    }
  }
  if (props.sessionId || externalMode.value) loadPage(1)
})

onBeforeUnmount(() => {
  if (typeof window !== 'undefined' && resizeHandler) {
    window.removeEventListener('resize', resizeHandler)
    resizeHandler = null
  }
  if (tableResizeObserver) {
    tableResizeObserver.disconnect()
    tableResizeObserver = null
  }
})
</script>

<style scoped>
.data-view {
  height: 100%;
  width: 100%;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 0 10px;
  /*border: 1px solid red;*/
}

.data-view.is-embedded {
  padding: 0;
  --theme-color: #009688;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-shrink: 0;
}
.toolbar-count {
  font-size: 15px;
  color: inherit;
}
.toolbar-right {
  display: flex;
  align-items: center;
  /*gap: 10px;*/
}

.data-table {
  flex: 1;
}

.data-view.is-embedded :deep(.data-table .el-table__body td.el-table__cell .cell) {
  user-select: text;
  cursor: text;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.table-scroll-wrap {
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: hidden;
}

.table-scroll-wrap .data-table {
  height: 100%;
}

.pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0 4px;
  flex-shrink: 0;
  /*border: 1px solid red;*/
}

.page-size-left {
  display: flex;
  align-items: center;
}

.field-dialog-tools {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.field-dialog-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.field-dialog-count {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  white-space: nowrap;
  writing-mode: horizontal-tb;
  font-size: 13px;
  color: #6b7280;
}

.field-dialog-group {
  max-height: 360px;
  overflow: auto;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(92px, 1fr));
  gap: 10px 14px;
  align-items: center;
}

.field-dialog-item {
  margin-right: 0;
}

.summary-drawer { padding: 8px 16px; }
.stat-item { margin-bottom: 24px; }
.chart-block, .list-block { margin-bottom: 28px; }
.chart-block h4, .list-block h4 {
  font-size: 14px;
  color: #3949ab;
  margin-bottom: 12px;
  font-weight: 600;
}

.year-bars {
  display: flex;
  align-items: flex-end;
  gap: 4px;
  height: 100px;
  overflow-x: auto;
  padding-bottom: 20px;
}
.year-bar-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 28px;
}
.year-bar {
  width: 20px;
  background: #7986cb;
  border-radius: 2px 2px 0 0;
  transition: height 0.3s;
  cursor: pointer;
}
.year-bar:hover { background: #3949ab; }
.year-label { font-size: 10px; color: #888; margin-top: 4px; transform: rotate(-45deg); }

.list-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.list-name {
  width: 160px;
  font-size: 12px;
  color: #444;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex-shrink: 0;
}
.list-bar { flex: 1; }
.list-val {
  width: 36px;
  font-size: 12px;
  color: #3949ab;
  font-weight: 600;
  text-align: right;
}

.data-view.is-embedded .toolbar {
  margin-bottom: 20px;
}

.data-view.is-embedded .toolbar-right {
  gap: 12px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.data-view.is-embedded .toolbar-right :deep(.toolbar-btn) {
  --el-button-hover-text-color: #009688;
  --el-button-hover-border-color: #8fcfc7;
  --el-button-hover-bg-color: #e8f6f4;
  --el-button-active-text-color: #009688;
  --el-button-active-border-color: #7cc2b9;
  --el-button-active-bg-color: #def2ef;
  height: 30px;
  min-height: 30px;
  padding: 0 14px;
  border-radius: 10px;
  border-color: #d8dde7;
  color: #575c65;
  font-size: 12px;
}

.data-view.is-embedded .toolbar-right :deep(.toolbar-btn .el-icon) {
  margin-right: 10px;
}

.data-view.is-embedded .toolbar-right :deep(.export-btn) {
  --el-button-hover-border-color: #007f73;
  --el-button-hover-bg-color: #007f73;
  --el-button-active-border-color: #006e64;
  --el-button-active-bg-color: #006e64;
  border-color: var(--theme-color);
  background: var(--theme-color);
  color: #ffffff;
}

.data-view.is-embedded :deep(.el-table) {
  --el-table-border-color: #d9dee7;
  --el-table-header-bg-color: #f8fafc;
  --el-table-tr-bg-color: #ffffff;
}

.data-view.is-embedded :deep(.el-table th.el-table__cell) {
  height: 46px;
  padding: 0 8px;
  font-size: 14px;
  color: #8a8f98;
  font-weight: 700;
}

.data-view.is-embedded :deep(.el-table td.el-table__cell) {
  height: 46px;
  max-height: 46px;
  padding: 0 8px;
  font-size: 13px;
  color: #5f646d;
}

.data-view.is-embedded :deep(.el-table th.el-table__cell .cell),
.data-view.is-embedded :deep(.el-table td.el-table__cell .cell) {
  height: 46px;
  line-height: 46px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  word-break: keep-all;
}

.data-view.is-embedded .pagination {
  padding: 20px 0 6px;
  gap: 12px;
  flex-wrap: wrap;
}

.data-view.is-embedded .page-size-left :deep(.el-input__wrapper) {
  min-height: 42px;
  padding: 0 16px;
  border-radius: 10px;
  box-shadow: 0 0 0 1px #d6dbe5 inset;
}

.data-view.is-embedded .page-size-left :deep(.el-select__selected-item) {
  font-size: 14px;
  color: #5f646d;
}

.data-view.is-embedded :deep(.el-pagination) {
  font-size: 14px;
  color: #60656e;
}

.data-view.is-embedded :deep(.el-pagination .el-pager li.is-active) {
  color: var(--theme-color);
}

.data-view.is-embedded :deep(.el-pagination .el-pager li),
.data-view.is-embedded :deep(.el-pagination .btn-prev),
.data-view.is-embedded :deep(.el-pagination .btn-next),
.data-view.is-embedded :deep(.el-pagination .el-pagination__jump) {
  min-width: 34px;
  height: 34px;
  line-height: 34px;
}

:deep(.field-select-dialog) {
  width: 700px !important;
  max-width: 700px;
  margin: 0 auto !important;
  border-radius: 15px;
}

:deep(.field-select-dialog .el-dialog) {
  /*border-radius: 15px;*/
  overflow: hidden;
  --el-color-primary: #009688;
  --el-color-primary-light-3: #33b5a9;
  --el-color-primary-light-5: #66cbc2;
  --el-color-primary-light-7: #99e1db;
  --el-color-primary-light-8: #b8ebe6;
  --el-color-primary-light-9: #d8f5f2;
  --el-color-primary-dark-2: #007f73;
}

:deep(.field-select-dialog .el-dialog__header) {
  padding: 10px 10px 6px;
  border-bottom: none;
}

:deep(.field-select-dialog .el-dialog__title) {
  font-size: 16px;
  line-height: 1.2;
  font-weight: 700;
  color: #2f3136;
}

:deep(.field-select-dialog .el-dialog__headerbtn) {
  top: 10px;
  right: 10px;
}

:deep(.field-select-dialog .el-dialog__close) {
  font-size: 16px;
  color: #000;
  font-weight: bold;
}

:deep(.field-select-dialog .el-dialog__body) {
  padding: 16px 20px 10px;
  border-top: none;
  display: block !important;
}

:deep(.field-select-dialog .el-dialog__footer) {
  padding: 8px 20px 16px;
  border-top: none;
}

:deep(.field-select-dialog .el-checkbox) {
  margin-right: 0;
  min-height: 32px;
}

:deep(.field-select-dialog .el-checkbox__label) {
  font-size: 14px;
  color: #4b5563;
}

:deep(.field-select-dialog .el-checkbox__input.is-checked .el-checkbox__inner),
:deep(.field-select-dialog .el-checkbox__input.is-indeterminate .el-checkbox__inner) {
  background: #009688 !important;
  border-color: #009688 !important;
}

:deep(.field-select-dialog .el-checkbox__input.is-checked + .el-checkbox__label) {
  color: #009688;
}

:deep(.field-select-dialog .el-button--primary) {
  --el-button-bg-color: #009688;
  --el-button-border-color: #009688;
  --el-button-hover-bg-color: #007f73;
  --el-button-hover-border-color: #007f73;
  --el-button-active-bg-color: #006e64;
  --el-button-active-border-color: #006e64;
}

@media (max-width: 1100px) {
  .data-view.is-embedded .toolbar {
    margin-bottom: 12px;
  }

  .data-view.is-embedded .toolbar-right :deep(.toolbar-btn) {
    height: 30px;
    min-height: 30px;
    padding: 0 12px;
    font-size: 12px;
  }

  .data-view.is-embedded .pagination {
    padding: 12px 0 4px;
  }

  .data-view.is-embedded :deep(.el-pagination) {
    margin-left: auto;
  }

  .field-dialog-tools {
    flex-wrap: wrap;
    row-gap: 8px;
  }

  .field-dialog-count {
    margin-left: auto;
  }

  .field-dialog-group {
    grid-template-columns: repeat(auto-fill, minmax(84px, 1fr));
    gap: 8px 10px;
  }
}
</style>

<style>
.field-select-dialog .el-dialog {
  width: 700px !important;
  max-width: 700px !important;
  border-radius: 15px;
  overflow: hidden;
  --el-color-primary: #009688;
  --el-color-primary-light-3: #33b5a9;
  --el-color-primary-light-5: #66cbc2;
  --el-color-primary-light-7: #99e1db;
  --el-color-primary-light-8: #b8ebe6;
  --el-color-primary-light-9: #d8f5f2;
  --el-color-primary-dark-2: #007f73;
}

.field-select-dialog .el-dialog__header {
  padding: 10px 10px 6px !important;
}

.field-select-dialog .el-dialog__title {
  font-size: 16px !important;
  line-height: 1.2;
  font-weight: 700;
  color: #2f3136;
}

.field-select-dialog .el-dialog__headerbtn {
  top: 10px !important;
  right: 10px !important;
}

.field-select-dialog .el-dialog__close {
  font-size: 16px !important;
  color: #000 !important;
  font-weight: bold;
}

.field-select-dialog .el-dialog__body {
  padding: 16px 20px 10px !important;
}

.field-select-dialog .el-dialog__footer {
  padding: 8px 20px 16px !important;
}

.field-select-dialog .el-checkbox__input.is-checked .el-checkbox__inner,
.field-select-dialog .el-checkbox__input.is-indeterminate .el-checkbox__inner {
  background: #009688 !important;
  border-color: #009688 !important;
}

.field-select-dialog .el-checkbox__input.is-checked + .el-checkbox__label {
  color: #009688 !important;
}

.field-select-dialog .el-button--primary {
  background: #009688 !important;
  border-color: #009688 !important;
  color: #fff !important;
}

.field-select-dialog .el-button--primary:hover,
.field-select-dialog .el-button--primary:focus {
  background: #007f73 !important;
  border-color: #007f73 !important;
}

.field-select-dialog .el-button--primary:active {
  background: #006e64 !important;
  border-color: #006e64 !important;
}

body.app-dark .field-select-dialog .el-dialog {
  --el-dialog-bg-color: #101729 !important;
  background: #101729 !important;
  background-color: #101729 !important;
  border: 1px solid #334155;
  box-shadow: none !important;
}

body.app-dark .field-select-dialog {
  --el-dialog-bg-color: #101729 !important;
  border: 1px solid #334155 !important;
}

body.app-dark .field-select-dialog .el-dialog__content,
body.app-dark .field-select-dialog .el-dialog__header,
body.app-dark .field-select-dialog .el-dialog__body,
body.app-dark .field-select-dialog .el-dialog__footer {
  background: #101729 !important;
}

body.app-dark .field-select-dialog .el-dialog__title,
body.app-dark .field-select-dialog .field-dialog-count,
body.app-dark .field-select-dialog .el-checkbox__label {
  color: #e5e7eb !important;
}

body.app-dark .field-select-dialog .el-dialog__close {
  color: #c7cedb !important;
}

body.app-dark .field-select-dialog .el-button:not(.el-button--primary) {
  background: #1a2333 !important;
  border-color: transparent !important;
  color: #ffffff !important;
}

body.app-dark .field-select-dialog .el-checkbox__inner {
  background: #1a2333 !important;
  border-color: #475569 !important;
}

body.app-dark .field-select-dialog .el-checkbox__input.is-checked .el-checkbox__inner,
body.app-dark .field-select-dialog .el-checkbox__input.is-indeterminate .el-checkbox__inner {
  background: #009688 !important;
  border-color: #009688 !important;
}

.home-view.is-dark .data-view.is-embedded .toolbar-count,
body.app-dark .data-view.is-embedded .toolbar-count {
  color: #e2e8f0;
}

.home-view.is-dark .data-view.is-embedded .toolbar-right .toolbar-btn:not(.export-btn),
body.app-dark .data-view.is-embedded .toolbar-right .toolbar-btn:not(.export-btn) {
  background: #1a2333 !important;
  border-color: transparent !important;
  color: #ffffff !important;
}

.home-view.is-dark .data-view.is-embedded .toolbar-right .toolbar-btn:not(.export-btn) .el-icon,
body.app-dark .data-view.is-embedded .toolbar-right .toolbar-btn:not(.export-btn) .el-icon {
  color: #c7cedb !important;
}

.home-view.is-dark .data-view.is-embedded .toolbar-right .export-btn,
body.app-dark .data-view.is-embedded .toolbar-right .export-btn {
  background: #1a2333 !important;
  border-color: #00897b !important;
  color: #19b3a6 !important;
}

.home-view.is-dark .data-view.is-embedded .toolbar-right .export-btn:hover,
.home-view.is-dark .data-view.is-embedded .toolbar-right .export-btn:focus,
.home-view.is-dark .data-view.is-embedded .toolbar-right .export-btn:active,
body.app-dark .data-view.is-embedded .toolbar-right .export-btn:hover,
body.app-dark .data-view.is-embedded .toolbar-right .export-btn:focus,
body.app-dark .data-view.is-embedded .toolbar-right .export-btn:active {
  background: #223149 !important;
  border-color: #19b3a6 !important;
  color: #31c3b6 !important;
}

.home-view.is-dark .data-view.is-embedded .page-size-left .el-input__wrapper,
.home-view.is-dark .data-view.is-embedded .page-size-left .el-select__wrapper,
body.app-dark .data-view.is-embedded .page-size-left .el-input__wrapper,
body.app-dark .data-view.is-embedded .page-size-left .el-select__wrapper {
  background: #1a2333 !important;
  box-shadow: 0 0 0 1px #334155 inset !important;
}

.home-view.is-dark .data-view.is-embedded .page-size-left .el-select__selected-item,
.home-view.is-dark .data-view.is-embedded .page-size-left .el-input__inner,
body.app-dark .data-view.is-embedded .page-size-left .el-select__selected-item,
body.app-dark .data-view.is-embedded .page-size-left .el-input__inner {
  color: #ffffff !important;
}

.home-view.is-dark .data-view.is-embedded .el-pagination__jump,
body.app-dark .data-view.is-embedded .el-pagination__jump {
  background: transparent !important;
}

.home-view.is-dark .data-view.is-embedded .el-pagination__total,
body.app-dark .data-view.is-embedded .el-pagination__total {
  color: #ffffff !important;
}

.home-view.is-dark .data-view.is-embedded .el-table,
body.app-dark .data-view.is-embedded .el-table {
  --el-table-border-color: #334155 !important;
  --el-table-header-bg-color: #1a2333 !important;
  --el-table-tr-bg-color: #1a2333 !important;
  --el-table-row-hover-bg-color: #223149 !important;
  --el-table-text-color: #ffffff !important;
  --el-table-header-text-color: #e5e7eb !important;
  --el-fill-color-lighter: #1a2333 !important;
  background: #1a2333 !important;
}

.home-view.is-dark .data-view.is-embedded .el-table th.el-table__cell,
body.app-dark .data-view.is-embedded .el-table th.el-table__cell {
  color: #e5e7eb !important;
  background: #1a2333 !important;
}

.home-view.is-dark .data-view.is-embedded .el-table td.el-table__cell,
body.app-dark .data-view.is-embedded .el-table td.el-table__cell {
  color: #ffffff !important;
  background: #1a2333 !important;
}

body.app-dark .data-view.is-embedded .el-table--striped .el-table__body tr.el-table__row--striped td.el-table__cell {
  background: #162033 !important;
}

body.app-dark .data-view.is-embedded .table-scroll-wrap,
body.app-dark .data-view.is-embedded .el-loading-mask {
  background: #101729 !important;
}
</style>
