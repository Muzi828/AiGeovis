<template>
  <div class="home-view" :class="{ 'is-dark': themeSwitch }">
    <div v-if="demoLoading" class="demo-loading-mask">
      <div class="demo-loading-card">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>{{ tLabel('正在加载案例数据...', 'Loading demo data...') }}</span>
      </div>
    </div>
    <div class="home-layout">
      <section class="left-panel">

        <section class="section-card data-prepare-card">
<!--          <img class="logo-img" src="../assets/img/logo.png" alt="AiGeovis logo" />-->
          <div class="section-title">
            <span class="section-icon">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M5 6c0-1.7 3.1-3 7-3s7 1.3 7 3-3.1 3-7 3-7-1.3-7-3zm0 0v6c0 1.7 3.1 3 7 3s7-1.3 7-3V6m-14 6v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6" />
              </svg>
            </span>
            {{ tLabel('数据准备', 'Data Preprocessing') }}
            <el-button
              v-if="displayedUploadFiles.length > 0"
              class="clear-icon-btn"
              text
              circle
              aria-label="清空上传列"
              @click="clearUploads"
            >
              <svg class="btn-icon" viewBox="0 0 24 24" aria-hidden="true" style="width: 20px;height: 20px;">
                <path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3" />
              </svg>
            </el-button>
          </div>
          <div
            class="upload-box"
            :class="{ 'upload-box-has-files': displayedUploadFiles.length > 0 }"
            @click="handleUploadBoxClick"
          >
            <el-upload
              ref="uploadRef"
              v-model:file-list="fileList"
              drag
              multiple
              accept=".txt,.csv,.xlsx,.xls"
              :auto-upload="false"
              :show-file-list="false"
              :on-change="handleUploadChange"
              class="home-upload"
            >
              <div v-if="displayedUploadFiles.length === 0" class="upload-empty">
                <svg class="upload-icon" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M12 16V4m0 0 4 4m-4-4-4 4M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" />
                </svg>
                <p class="upload-title">{{ tLabel('请上传 WoS 数据 / 自定义数据，或打开案例。', 'Upload WoS or custom data, or open a demo.') }}</p>
                <p class="upload-desc">{{ uploadDisplayName }} · {{ tLabel('WoS 纯文本 .txt / 自定义地址表 .csv .xlsx', 'WoS .txt / custom address table .csv .xlsx') }}</p>
              </div>
              <div v-else class="upload-empty-placeholder"></div>
            </el-upload>
            <div v-if="displayedUploadFiles.length > 0" class="upload-file-block">
              <div class="upload-file-list">
                <div
                  v-for="file in displayedUploadFiles"
                  :key="file.uid || file.name"
                  class="upload-file-item"
                >
                  <svg class="upload-file-icon" viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M7 3h7l5 5v13H7zM14 3v5h5M9.5 13h7M9.5 17h7" />
                  </svg>
                  <span class="upload-file-name">{{ file.name }}</span>
                  <button
                    type="button"
                    class="upload-file-remove"
                    aria-label="删除文件"
                    @mousedown.stop
                    @click.stop="removeUpload(file)"
                  >
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                      <path d="M6 6l12 12M18 6 6 18" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </div>
          <div class="button-grid button-grid-top">
            <div class="button-group button-group-left">
              <el-button
                class="control-btn open-demo-text-btn"
                :disabled="loading || demoLoading"
                @click="openDemo"
              >
                <svg class="btn-icon" viewBox="0 0 1024 1024" aria-hidden="true" style="margin-right: 5px;">
                  <path d="M922.8 497.1H184.5c-26.7 0-50.4 17.3-58.6 42.7L61.5 738.2V203.5h307.7c0 68 55 123 122.9 123h307.6V419c0.2 16.8 13.8 30.4 30.7 30.4 17 0 30.7-13.8 30.7-30.7h0.2v-91.8c0-34-27.5-61.5-61.5-61.6H492.1c-34 0-61.5-27.5-61.5-61.5 0-16.3-6.5-31.9-18-43.4s-27.2-18-43.4-18H61.5C27.6 142 0.1 169.5 0 203.4v724.2c0.1 34 27.6 61.4 61.6 61.4h738.1c26.8 0 50.5-17.2 58.7-42.7l125.9-387.7c-0.1-33.9-27.5-61.4-61.5-61.5zM983.5 173c-38.2-74-158.9-228.5-457-67.5 0 0 328.2-81.3 367.9 99.8l-54.4 1.3 134.4 84.5 49.4-150.8-40.3 32.7z" />
                </svg>
                {{ tLabel(' 打开案例', ' Open Demo') }}
              </el-button>
            </div>
            <div class="button-group button-group-right">
              <el-button
                type="primary"
                :loading="loading"
                :disabled="!canStartUpload"
                @click="doUpload"
                class="control-btn"
              >
                <svg class="btn-icon" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M8 5v14l11-7z" />
                </svg>
                {{ tLabel('开始加载', 'Load Data') }}
              </el-button>
              <el-button
                v-if="effectiveSessionId || demoMode"
                @click="openRawDataDialog"
                class="control-btn"
              >
                <svg class="btn-icon" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M4 5h16v14H4zM4 10h16M10 5v14" />
                </svg>
                {{ tLabel('打开表格', 'Open Table') }}
              </el-button>
            </div>
          </div>
          <el-progress
            v-if="loading"
            class="upload-progress"
            :percentage="uploadProgress"
            status="striped"
            striped-flow
          />
        </section>

        <section class="section-card parse-config-card">
          <div class="section-title">
            <span class="section-icon">
              <svg class="section-fill-icon" viewBox="0 0 1024 1024" aria-hidden="true">
                <path d="M114.11 276.65h474.9c13.49 54.81 63.05 95.59 121.96 95.59s108.47-40.78 121.96-95.59h76.86c16.57 0 30-13.43 30-30s-13.43-30-30-30h-76.86c-13.49-54.81-63.05-95.59-121.96-95.59s-108.47 40.78-121.96 95.59h-474.9c-16.57 0-30 13.43-30 30s13.43 30 30 30z m596.85-95.59c36.17 0 65.59 29.42 65.59 65.59s-29.42 65.59-65.59 65.59-65.59-29.42-65.59-65.59 29.42-65.59 65.59-65.59zM114.11 542h97.06c13.49 54.81 63.04 95.59 121.96 95.59S441.6 596.81 455.09 542h454.8c16.57 0 30-13.43 30-30s-13.43-30-30-30h-454.8c-13.49-54.81-63.04-95.59-121.96-95.59S224.66 427.19 211.17 482h-97.06c-16.57 0-30 13.43-30 30s13.43 30 30 30z m219.02-95.59c36.17 0 65.59 29.42 65.59 65.59s-29.42 65.59-65.59 65.59-65.59-29.42-65.59-65.59 29.42-65.59 65.59-65.59z m576.75 300.94H737.33c-13.49-54.81-63.05-95.59-121.96-95.59s-108.47 40.78-121.96 95.59h-379.3c-16.57 0-30 13.43-30 30s13.43 30 30 30h379.31c13.49 54.81 63.04 95.59 121.96 95.59s108.47-40.78 121.96-95.59h172.55c16.57 0 30-13.43 30-30s-13.43-30-30-30z m-294.51 95.59c-36.17 0-65.59-29.42-65.59-65.59s29.42-65.59 65.59-65.59 65.59 29.42 65.59 65.59-29.42 65.59-65.59 65.59z" />
              </svg>
            </span>
            {{ tLabel('地理解析配置', 'Geo Parse Config') }}
          </div>
          <div class="parse-tabs parse-field-tabs" role="tablist" aria-label="解析字段切换" v-if="!affiliationMode">
            <button
              type="button"
              class="parse-tab-btn"
              :class="{ 'parse-tab-btn-active': parseField === 'C1' }"
              role="tab"
              :aria-selected="parseField === 'C1'"
              :disabled="parseRunning"
              @click="selectParseField('C1')"
            >
              {{ tLabel('地址列表（C1）', 'Address List (C1)') }}
            </button>
            <button
              type="button"
              class="parse-tab-btn"
              :class="{ 'parse-tab-btn-active': parseField === 'C3' }"
              role="tab"
              :aria-selected="parseField === 'C3'"
              :disabled="parseRunning"
              @click="selectParseField('C3')"
            >
              {{ tLabel('机构列表（C3）', 'Org List (C3)') }}
            </button>
          </div>

          <template v-if="parseField === 'C1' && !affiliationMode">
            <label class="field-label">{{ tLabel('解析字段', 'Parse Fields') }}</label>
            <div class="tier-checkboxes" :class="langSwitch ? 'tier-checkboxes-zh' : 'tier-checkboxes-en'">
              <el-checkbox v-model="c1TierChecks.country" :disabled="parseRunning">
                {{ tLabel('国家 / 地区', 'Country / Region') }}
              </el-checkbox>
              <el-checkbox v-model="c1TierChecks.org" :disabled="parseRunning">
                {{ tLabel('机构', 'Organization') }}
              </el-checkbox>
              <el-checkbox v-model="c1TierChecks.city" :disabled="parseRunning">
                {{ tLabel('城市', 'City') }}
              </el-checkbox>
              <el-checkbox
                :model-value="c1AllChecked"
                :indeterminate="c1AllIndeterminate"
                :disabled="parseRunning"
                @change="toggleAllC1Tiers"
              >
                {{ tLabel('全选', 'Select All') }}
              </el-checkbox>
            </div>
          </template>

          <!-- Affiliation 模式提示 -->
<!--          <div v-if="affiliationMode" class="affiliation-hint">-->
<!--            {{ tLabel('点击启动解析开始处理国家/机构数据', 'Click Start Parse to process country/org data') }}-->
<!--          </div>-->
          <label class="field-label">{{ tLabel('批次数量', 'Batch Size') }}</label>
          <div class="parse-control-row">
            <el-input-number
              v-model="batchSize"
              class="parse-counter"
              :min="1"
              :max="500"
              :step="1"
              :controls="false"
            />

            <div class="parse-actions">
              <el-button
                v-if="!parseRunning"
                type="primary"
                class="full-width parse-button control-btn"
                @click="doParse"
              >
                <svg class="btn-icon" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M8 5v14l11-7z" />
                </svg>
                {{ tLabel('启动解析', 'Start Parse') }}
              </el-button>
              <el-button
                v-else
                type="danger"
                class="full-width parse-button control-btn"
                @click="doStop"
              >
                {{ tLabel('停止', 'Stop') }}
              </el-button>
              <button
                v-if="parseRunning || hasParsedProcess"
                type="button"
                class="progress-icon-btn"
                :class="{ 'progress-icon-btn-active': parseProgressDialogVisible }"
                :aria-label="tLabel('查看解析过程', 'View parse process')"
                :title="tLabel('查看解析过程', 'View parse process')"
                @click="toggleParseProgressDialog"
              >
                <svg viewBox="0 0 1024 1024" aria-hidden="true">
                  <path d="M462 326h72v184h110v72H462V326z m501.712-101.422l-61.622 191.96-209.8-74.216 23.942-67.7 91.924 32.52A358.138 358.138 0 0 0 512 152c-198.504 0-360 161.496-360 360s161.496 360 360 360 360-161.496 360-360h72a432 432 0 0 1-737.47 305.47 432.036 432.036 0 0 1 535.15-671.416 433.508 433.508 0 0 1 130.786 127.872l22.886-71.3z" />
                </svg>
              </button>
            </div>
          </div>
          <div v-if="parseTierSummaries.length" class="parse-summary parse-summary-tiers">
            <div v-if="parseTierSharedTotal != null" class="parse-summary-total">
              {{ tLabel('共处理了', 'Processed') }}
              <b>{{ parseTierSharedTotal }}</b>
              {{ tLabel('条数据', 'records') }}
            </div>
            <div class="parse-summary-grid" :class="{ 'parse-summary-grid-5col': parseTierSharedTotal == null }">
              <template v-for="ts in parseTierSummaries" :key="ts.tier">
                <span class="parse-summary-tier-name">【{{ tierLabel(ts.tier) }}】</span>
                <span v-if="parseTierSharedTotal == null" class="parse-summary-cell"
                      :title="tLabel('共处理', 'Total')">
                  <svg class="parse-summary-icon" viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M4 6h16M4 12h16M4 18h10" />
                  </svg>
                  {{ ts.total }}
                </span>
                <span class="parse-summary-cell parse-summary-accent parse-summary-accent-success"
                      :title="tLabel('成功', 'Success')">
                  <svg class="parse-summary-icon" viewBox="0 0 24 24" aria-hidden="true">
                    <circle cx="12" cy="12" r="9" />
                    <path d="M8 12.5l2.5 2.5L16 9" />
                  </svg>
                  {{ ts.success }} ({{ ts.successRate }}%)
                </span>
                <span class="parse-summary-cell parse-summary-accent parse-summary-accent-failed"
                      :title="tLabel('失败', 'Failed')">
                  <svg class="parse-summary-icon" viewBox="0 0 24 24" aria-hidden="true">
                    <circle cx="12" cy="12" r="9" />
                    <path d="M9 9l6 6M15 9l-6 6" />
                  </svg>
                  {{ ts.failed }} ({{ tierPct(ts.failed, ts.total) }}%)
                </span>
              </template>
            </div>
          </div>
          <div v-else-if="parseSummary" class="parse-summary">
            <span class="parse-summary-segment">
              {{ tLabel('共处理了', 'Processed') }} {{ parseSummary.total }} {{ tLabel('条数据，', 'records,') }}
            </span>
            <span class="parse-summary-segment parse-summary-accent parse-summary-accent-success">
              {{ tLabel('成功', 'Success') }}：{{ parseSummary.success }}，
            </span>
            <span class="parse-summary-segment parse-summary-accent parse-summary-accent-failed">
              {{ tLabel('失败', 'Failed') }}：{{ parseSummary.failed }}，
            </span>
            <span class="parse-summary-segment">
              {{ tLabel('成功率', 'Success Rate') }}：{{ parseSummary.successRate }}%
            </span>
          </div>
        </section>

        <section class="section-card result-view-card">
          <div class="section-title result-view-title-row">
            <div class="result-view-title-left">
              <span class="section-icon">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M4 6l5-2 6 2 5-2v14l-5 2-6-2-5 2V6zm5-2v14m6-12v14" />
                </svg>
              </span>
              {{ tLabel('结果视图', 'Result View') }}
            </div>
            <button type="button" class="result-view-reset-btn" @click="resetCurrentVisualization">
              <svg t="1778046734859" class="icon board-reset-icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="8248" width="200" height="200"><path d="M980.676923 606.523077C953.107692 842.830769 752.246154 1024 512 1024 252.061538 1024 39.384615 811.323077 39.384615 551.384615S252.061538 78.769231 512 78.769231c141.784615 0 263.876923 63.015385 350.523077 157.538461V39.384615c0-19.692308 19.692308-39.384615 39.384615-39.384615s39.384615 19.692308 39.384616 39.384615v275.692308c0 27.569231-11.815385 43.323077-39.384616 39.384615h-275.692307c-19.692308 0-39.384615-19.692308-39.384616-39.384615s19.692308-39.384615 39.384616-39.384615H791.630769c-70.892308-70.892308-169.353846-118.153846-279.630769-118.153846C295.384615 157.538462 118.153846 334.769231 118.153846 551.384615s177.230769 393.846154 393.846154 393.846154c204.8 0 370.215385-153.6 389.907692-354.461538h3.938462c0-23.630769 15.753846-39.384615 39.384615-39.384616s39.384615 15.753846 39.384616 39.384616c0 7.876923 0 11.815385-3.938462 15.753846zM866.461538 236.307692z" p-id="8249"></path></svg>
              <span class="result-view-reset-text">{{ tLabel('恢复默认', 'Default') }}</span>
            </button>
          </div>
          <div class="view-grid" role="radiogroup" aria-label="结果视图切换">
            <button
              v-for="item in viewItems"
              :key="item"
              type="button"
              class="radio-card"
              :class="{ 'radio-card-active': activeView === item && item !== '数据列表' }"
              :aria-checked="activeView === item && item !== '数据列表'"
              :disabled="vizLoading && activeView !== item"
              role="radio"
              @click="onSelectView(item)"
            >
              <svg v-if="item === '数据列表'" class="card-icon-svg" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 5h16v14H4zM4 10h16M10 5v14" />
              </svg>
              <svg v-else-if="item === '平面地图'" class="card-icon-svg" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 6l5-2 6 2 5-2v14l-5 2-6-2-5 2V6zm5-2v14m6-12v14" />
              </svg>
              <svg v-else-if="item === '三维地图'" class="card-icon-svg" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3zm0 9 8-4.5M12 12 4 7.5M12 12v9" />
              </svg>
              <svg v-else-if="item === '热力图'" class="card-icon-svg heatmap-icon-svg" viewBox="0 0 1024 1024" aria-hidden="true">
                <path d="M905.7 588.2C760 439.5 774.8 382.9 796.2 323.6c21.5-59.3-30.6-320.6-223.6-219C379.5 206.2 437 342.1 299.3 336c-137.7-6-306.9 67.8-206 340.2 39.5 106.4 114.5 209.7 230.6 224.6s306.8-23 422.9 34.7c116.2 57.6 304.5-198.6 158.9-347.3zM715.5 867c-98-45.6-258.3-18.8-356.8-29.7S184.3 757.8 152 671.8C69.2 452 229.3 389.9 346.2 393.5 463 397 413.5 260.9 578.3 176.7c164.9-84.2 175.4 133.9 156.6 182.2C713.1 414.7 715 467.7 842.5 592c122.3 119.1-28.9 320.7-127 275z" />
                <path d="M433.4 501c-88.1 41.2-99.5-56.2-207.6 36.8-53 45.6-7.5 153.6 60.8 175.7 68.4 22.2 135.9-2.3 189-48.4 53-46.3 46-205.5-42.2-164.1zM665.8 464.6c-4.3-103.8 47.5-259.5-55.4-233-63.3 16.3-122.9 122.4-97.3 169.7 25.6 47.1 80.7 130.9 62.6 191.6-18 60.6-4.6 134.2 55.7 156 60.4 21.8 189.4 14.5 191.1-49.1 1.6-63.6-152.3-131.3-156.7-235.2z" />
              </svg>
              <svg v-else class="card-icon-svg" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M5 19V9m7 10V5m7 14v-7" />
              </svg>
              <span>{{ viewText(item) }}</span>
<!--              <span class="radio-dot" :class="{ 'radio-dot-active': activeView === item }"></span>-->
            </button>
          </div>
          <div v-if="showMapParamsPanel" class="map-params-panel">
            <div class="map-param-row map-param-row-switch map-param-row-start map-param-row-top-controls">
              <div v-if="showMapLabelControl" class="map-param-chip">
                <div class="map-param-label">{{ mapLabelControlLabel }}</div>
                <div class="map-param-chip-control">
                  <el-switch v-model="mapLabelVisible" class="map-param-switch" />
                </div>
              </div>
              <div v-if="showMapEdgesControl" class="map-param-chip">
                <div class="map-param-label">{{ tLabel('显示 / 隐藏连线', 'Show / hide edges') }}</div>
                <div class="map-param-chip-control">
                  <el-switch v-model="mapEdgeVisible" class="map-param-switch" :disabled="vizLoading" />
                </div>
              </div>
              <div v-if="!showMapEdgesControl && showMapSizeModeControl" class="map-param-chip">
                <div class="map-param-label">{{ tLabel('节点大小', 'Node Size') }}</div>
                <div class="map-param-chip-control">
                  <div class="map-mode-tabs" role="tablist" :aria-label="mapSizeModeControlAriaLabel">
                    <button type="button" class="map-mode-tab" :class="{ 'map-mode-tab-active': mapSizeMode === 'scaled' }" @click="mapSizeMode = 'scaled'">{{ tLabel('比例', 'Scaled') }}</button>
                    <button type="button" class="map-mode-tab" :class="{ 'map-mode-tab-active': mapSizeMode === 'fixed' }" @click="mapSizeMode = 'fixed'">{{ tLabel('固定', 'Fixed') }}</button>
                  </div>
                </div>
              </div>
            </div>
            <div v-if="showThreeDRenderModeControl || showNodeColorControl || showMapEdgesControl" class="map-param-row map-param-row-switch map-param-row-inline-controls map-param-row-start">
              <div v-if="showThreeDRenderModeControl" class="map-param-chip">
                <div class="map-param-label">{{ tLabel('显示模式', 'Display Mode') }}</div>
                <div class="map-param-chip-control">
                  <div class="map-mode-tabs" role="tablist" :aria-label="tLabel('三维显示模式', '3D render mode')">
                    <button type="button" class="map-mode-tab" :class="{ 'map-mode-tab-active': threeDRenderMode === 'bar' }" @click="threeDRenderMode = 'bar'">{{ tLabel('柱体', 'Bars') }}</button>
                    <button type="button" class="map-mode-tab" :class="{ 'map-mode-tab-active': threeDRenderMode === 'point' }" @click="threeDRenderMode = 'point'">{{ tLabel('节点', 'Nodes') }}</button>
                  </div>
                </div>
              </div>
              <div v-if="showNodeColorControl" class="map-param-chip">
                <div class="map-param-label">{{ mapColorControlLabel }}</div>
                <div class="map-param-chip-control">
                  <colorPicker
                    ref="colorPickerNetWorkNode"
                    v-model="activeMapColor"
                    class="copy-picker-hidden"
                    @change="changeNodeColor('label')"
                  />
                </div>
              </div>
              <div v-if="showMapEdgesControl" class="map-param-chip">
                <div class="map-param-label">{{ mapEdgeColorControlLabel }}</div>
                <div class="map-param-chip-control">
                  <colorPicker
                    ref="colorPickerNetWorkEdge"
                    v-model="activeMapEdgeColor"
                    class="copy-picker-hidden"
                    @change="changeEdgeColor('edge')"
                  />
                </div>
              </div>
              <div v-if="showMapEdgesControl" class="map-param-chip">
                <div class="map-param-label">{{ tLabel('节点大小', 'Node Size') }}</div>
                <div class="map-param-chip-control">
                  <div class="map-mode-tabs" role="tablist" :aria-label="mapSizeModeControlAriaLabel">
                    <button type="button" class="map-mode-tab" :class="{ 'map-mode-tab-active': mapSizeMode === 'scaled' }" @click="mapSizeMode = 'scaled'">{{ tLabel('比例', 'Scaled') }}</button>
                    <button type="button" class="map-mode-tab" :class="{ 'map-mode-tab-active': mapSizeMode === 'fixed' }" @click="mapSizeMode = 'fixed'">{{ tLabel('固定', 'Fixed') }}</button>
                  </div>
                </div>
              </div>
            </div>
            <div class="map-param-row map-param-row-sliders">
              <div class="map-param-item map-param-item-slider map-param-item-slider-half">
                <div class="map-param-label">{{ mapSizeControlLabel }}</div>
                <div class="map-param-control">
                  <el-slider v-model="activeMapSize" :min="1" :max="100" :step="1" />
                </div>
              </div>

              <div class="map-param-item map-param-item-slider map-param-item-slider-half">
                <div class="map-param-label">{{ mapOpacityControlLabel }}</div>
                <div class="map-param-control">
                  <el-slider v-model="mapNodeOpacity" :min="1" :max="100" :step="1" />
                </div>
              </div>
            </div>

            <div v-if="showMapEdgesControl && mapEdgeVisible" class="map-param-row map-param-row-sliders map-param-row-inline-controls">
              <div class="map-param-item map-param-item-slider map-param-item-slider-half">
                <div class="map-param-label">{{ mapEdgeWidthControlLabel }}</div>
                <div class="map-param-control">
                  <el-slider v-model="mapEdgeWidth" :min="1" :max="20" :step="1" />
                </div>
              </div>

              <div class="map-param-item map-param-item-slider map-param-item-slider-half">
                <div class="map-param-label">{{ mapEdgeOpacityControlLabel }}</div>
                <div class="map-param-control">
                  <el-slider v-model="mapEdgeOpacity" :min="1" :max="100" :step="1" />
                </div>
              </div>
            </div>
          </div>
        </section>

        <section class="section-card system-settings-card">
          <div class="section-title">
            <span class="section-icon">
              <svg class="section-fill-icon" viewBox="0 0 1024 1024" aria-hidden="true">
                <path d="M448.363 166.827l113.6 0.17a64 64 0 0 1 63.893 63.915l0.043 18.517A301.461 301.461 0 0 1 688 284.31l15.21-8.746a64 64 0 0 1 87.297 23.381l56.938 98.304a64 64 0 0 1-19.989 85.397l-3.477 2.134-15.275 8.81c2.624 24.235 2.304 48.854-1.13 73.323l10.794 6.25a64 64 0 0 1 25.216 84.118l-1.77 3.307-53.334 92.373a64 64 0 0 1-84.117 25.216l-3.328-1.792-14.742-8.533a298.539 298.539 0 0 1-59.626 33.28v25.386a64 64 0 0 1-59.99 63.958l-4.074 0.128-113.6-0.171a64 64 0 0 1-63.894-63.893l-0.064-30.614a302.613 302.613 0 0 1-50.069-29.696l-27.221 15.659a64 64 0 0 1-87.296-23.403l-56.939-98.282a64 64 0 0 1 19.99-85.419l3.477-2.133 27.69-15.936c-2.133-20.267-2.24-40.768-0.192-61.227l-30.741-17.77a64 64 0 0 1-25.237-84.118l1.792-3.307 53.333-92.373a64 64 0 0 1 84.117-25.216l3.307 1.792 26.795 15.467a297.984 297.984 0 0 1 56.426-34.667v-24.363a64 64 0 0 1 59.99-63.978l4.074-0.128z m-0.086 64l0.064 65.066-36.778 17.302a233.577 233.577 0 0 0-44.31 27.221l-34.005 26.539-62.57-36.139-1.6-0.896-53.334 92.373 66.56 38.422-4.139 41.152a235.217 235.217 0 0 0 0.15 48.085l4.394 41.43-63.786 36.735L275.84 726.4l63.339-36.416 33.6 24.597a237.995 237.995 0 0 0 39.466 23.424l36.736 17.259 0.128 71.168 113.579 0.17-0.064-68.16 39.467-16.426a234.539 234.539 0 0 0 46.826-26.112l33.579-24.128 50.56 29.184 53.29-92.395-48.127-27.818 5.973-42.688a234.421 234.421 0 0 0 0.896-57.6l-4.48-41.451 51.456-29.696-56.939-98.283-51.2 29.504-33.621-24.512a238.037 238.037 0 0 0-48.939-27.498l-39.381-16.342-0.128-61.184-113.579-0.17zM575.66 414.549a128.17 128.17 0 0 1 46.89 174.934 127.83 127.83 0 0 1-174.762 46.848 128.17 128.17 0 0 1-46.87-174.934A127.83 127.83 0 0 1 575.66 414.55zM456.34 493.355a64.17 64.17 0 0 0 23.467 87.573 63.83 63.83 0 0 0 87.296-23.403 64.17 64.17 0 0 0-20.267-85.589l-3.2-1.984-3.306-1.77a63.83 63.83 0 0 0-83.99 25.173z" />
              </svg>
            </span>
            {{ tLabel('系统设置', 'System Settings') }}
          </div>
          <div class="settings-head-row">
            <span class="settings-head-item">{{ tLabel('系统语言', 'System Language') }}</span>
            <span class="settings-head-item settings-head-item-model">{{ tLabel('参数设置', 'Parameter Settings') }}</span>
          </div>
          <div class="settings-main-row">
            <div class="settings-left">
              <div class="setting-switch-item">
<!--                <span class="setting-label">{{ tLabel('中英切换', 'Language') }}</span>-->
                <span class="lang-right">
                  <el-switch
                    v-model="langSwitch"
                    class="lang-switch"
                    :active-value="true"
                    :inactive-value="false"
                  />
                  <span class="lang-current">中文/EN</span>
                </span>
              </div>
              <div class="setting-switch-item">

                <el-switch
                  v-model="themeSwitch"
                  class="lang-switch"
                  :active-value="true"
                  :inactive-value="false"
                />
                <span class="setting-label">{{ tLabel('深色/浅色', 'Dark/Light') }}</span>
              </div>
            </div>
            <div class="settings-right">
              <el-button class="model-button control-btn" @click="openModelConfigDialog">
                {{ tLabel('模型选型配置', 'Model Config') }}
              </el-button>
            </div>
          </div>
        </section>
      </section>

      <section class="right-panel" :class="{ 'right-panel-3d': activeView === '三维地图' }">
        <div
          v-if="(effectiveSessionId || demoMode) && showBoardMainTitle"
          class="board-main-title"
        >
          {{ tLabel('科学产出的地理可视化', 'Geospatial Visualization of Scientific Output') }}
        </div>
        <div
          v-if="effectiveSessionId || demoMode"
          class="board-viz-tools"
        >
          <button type="button" class="board-reset-btn" @click="resetCurrentVisualization">
            <svg t="1778046734859" class="icon board-reset-icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="8248" width="200" height="200"><path d="M980.676923 606.523077C953.107692 842.830769 752.246154 1024 512 1024 252.061538 1024 39.384615 811.323077 39.384615 551.384615S252.061538 78.769231 512 78.769231c141.784615 0 263.876923 63.015385 350.523077 157.538461V39.384615c0-19.692308 19.692308-39.384615 39.384615-39.384615s39.384615 19.692308 39.384616 39.384615v275.692308c0 27.569231-11.815385 43.323077-39.384616 39.384615h-275.692307c-19.692308 0-39.384615-19.692308-39.384616-39.384615s19.692308-39.384615 39.384616-39.384615H791.630769c-70.892308-70.892308-169.353846-118.153846-279.630769-118.153846C295.384615 157.538462 118.153846 334.769231 118.153846 551.384615s177.230769 393.846154 393.846154 393.846154c204.8 0 370.215385-153.6 389.907692-354.461538h3.938462c0-23.630769 15.753846-39.384615 39.384615-39.384616s39.384615 15.753846 39.384616 39.384616c0 7.876923 0 11.815385-3.938462 15.753846zM866.461538 236.307692z" p-id="8249"></path></svg>
            <span>{{ tLabel('重置', 'Reset') }}</span>
          </button>
          <button v-if="showExportGmlButton" type="button" class="board-export-btn" @click="doExportGml">
            <svg class="board-export-icon" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M12 3v10m0 0 4-4m-4 4-4-4M5 15v3a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-3" />
            </svg>
            <span>GML</span>
          </button>
          <div
            class="parse-tabs result-viz-tabs main-viz-tabs board-viz-tabs"
            :class="langSwitch ? 'main-viz-tabs-zh' : 'main-viz-tabs-en'"
            role="tablist"
            aria-label="可视化类型切换"
          >
            <button
              v-for="item in vizOptions"
              :key="item.value"
              type="button"
              class="parse-tab-btn result-viz-tab-btn"
              :class="{ 'result-viz-tab-btn-active': vizType === item.value }"
              role="tab"
              :aria-selected="vizType === item.value"
              :disabled="item.disabled || (vizLoading && vizType !== item.value)"
              @click="selectVizType(item.value)"
            >
              {{ item.label }}
            </button>
          </div>
        </div>

        <div class="result-board">

          <div
            class="board-canvas"
            :class="{ 'board-canvas-3d': activeView === '三维地图' }"
          >
            <div v-if="vizLoading" class="board-loading-mask">
              <div class="board-loading-card">
                <el-icon class="is-loading"><Loading /></el-icon>
                <span>{{ tLabel('可视化加载中...', 'Loading visualization...') }} {{ vizLoadingProgress }}%</span>
              </div>
            </div>
            <KeepAlive>
              <VizView
                v-if="activeView === '平面地图' || activeView === '条形图' || activeView === '热力图'"
                ref="vizViewRef"
                embedded
                :session-id="effectiveSessionId"
                :demo-mode="demoMode"
                :record-count="effectiveRecordCount"
                :fixed-field="panelField"
                :fixed-type="panelVizType"
                :fixed-tier="vizType"
                :auto-load-viz="vizAutoLoadEnabled"
                :lang-zh="langSwitch"
                :map-node-size="mapNodeSize"
                :map-label-visible="mapLabelVisible"
                :map-node-opacity="mapNodeOpacity"
                :map-size-mode="mapSizeMode"
                :map-node-color="mapNodeColor"
                :map-edge-color="mapEdgeColor"
                :map-edge-width="mapEdgeWidth"
                :map-edge-opacity="mapEdgeOpacity"
                :show-edges="mapEdgeVisible"
                :reload-key="vizReloadKey"
                @stats-meta="onVizStatsMeta"
                @viz-loading="onVizLoading"
                @open-demo="openDemo"
              />
            </KeepAlive>

            <div
              v-if="activeView === '三维地图'"
              class="three-d-map-wrap"
            >
              <div
                v-if="hasThreeDData"
                ref="threeDMapEl"
                class="three-d-map-chart"
              ></div>
            <el-empty
              v-else
              :description="tLabel('暂无可展示的三维地图数据，请先完成地理解析', 'No 3D data to display yet. Please finish geo parsing first.')"
              image-size="120"
            />
            </div>

            <el-empty
              v-else-if="activeView === '数据列表'"
              :description="tLabel('点击左侧“数据列表”按钮查看解析结果表格', 'Click Data Table on the left to view parsed results.')"
              image-size="120"
            />
          </div>
        </div>
        <div v-if="activeView !== '数据列表' && vizMeta.displayCount != null" class="viz-meta-tip">
          {{ vizMetaText }}
        </div>
      </section>
    </div>

    <el-dialog
      v-model="demoChoiceVisible"
      class="demo-choice-dialog"
      :title="tLabel('选择案例类型', 'Choose Demo Type')"
      width="520px"
      align-center
    >
      <div class="demo-choice-wrap">
        <button type="button" class="demo-choice-card" @click="openWosDemo">
          <svg class="demo-choice-icon" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M4 4h16v16H4zM4 9h16M9 9v11" />
          </svg>
          <span class="demo-choice-name">{{ tLabel('WoS 数据案例', 'WoS Data Demo') }}</span>
          <span class="demo-choice-desc">{{ tLabel('Web of Science 文献数据，展示国家 / 机构 / 城市解析与地图可视化', 'Web of Science records with country / organization / city parsing and maps') }}</span>
        </button>
        <button type="button" class="demo-choice-card" @click="openCustomDemo">
          <svg class="demo-choice-icon" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M7 3h7l5 5v13H7zM14 3v5h5M9.5 13h7M9.5 17h7" />
          </svg>
          <span class="demo-choice-name">{{ tLabel('自定义数据案例', 'Custom Data Demo') }}</span>
          <span class="demo-choice-desc">{{ tLabel('机构地址清单（CSV，已含经纬度），可直接查看地图与解析结果', 'Institution address list (CSV with coordinates) ready for map and results') }}</span>
        </button>
      </div>
    </el-dialog>

    <el-dialog
      v-model="rawDataDialogVisible"
      class="raw-data-dialog"
      :title="tLabel('原始数据表格', 'Raw Data Table')"
      width="70%"
      destroy-on-close
    >
      <DataView
        embedded
        :session-id="demoMode ? '' : effectiveSessionId"
        :record-count="demoMode ? demoRawTableRows.length : effectiveRecordCount"
        :lang-zh="langSwitch"
        :use-external-data="demoMode"
        :external-records="demoMode ? demoRawTableRows : []"
        :external-loading="demoMode ? demoRawTableLoading : false"
      />
    </el-dialog>

    <el-dialog
      v-model="parseResultDialogVisible"
      class="parse-result-dialog"
      :title="parseResultDialogTitle"
      width="70%"
      destroy-on-close
    >
      <div class="parse-result-wrap">
        <div class="result-dialog-toolbar">
          <div
            v-if="parseField === 'C1' || affiliationMode"
            class="parse-tabs result-viz-tabs main-viz-tabs"
            :class="langSwitch ? 'main-viz-tabs-zh' : 'main-viz-tabs-en'"
            role="tablist"
            aria-label="解析结果类型切换"
          >
            <button
              v-for="item in vizOptions"
              :key="item.value"
              type="button"
              class="parse-tab-btn result-viz-tab-btn"
              :class="{ 'result-viz-tab-btn-active': vizType === item.value }"
              role="tab"
              :aria-selected="vizType === item.value"
              :disabled="item.disabled"
              @click="selectVizType(item.value)"
            >
              {{ item.label }}
            </button>
          </div>
          <div class="result-dialog-toolbar-right">
            <el-button
              v-if="!demoMode && effectiveSessionId"
              type="warning"
              plain
              class="result-toolbar-btn result-toolbar-btn-fallback"
              :loading="geocodeFallbackRunning"
              :title="tLabel('对仍缺坐标的条目调用 Nominatim 地理编码补齐', 'Fill missing coordinates via Nominatim geocoding')"
              @click="doGeocodeFallback"
            >
              {{ tLabel('坐标兜底补齐', 'Geocode Fallback') }}
            </el-button>
            <el-button
              type="primary"
              class="result-toolbar-btn result-toolbar-btn-export"
              :disabled="geoTotal === 0"
              @click="doExportParseResults"
            >
              {{ tLabel('导出 CSV', 'Export CSV') }}
            </el-button>
          </div>
        </div>

        <div ref="parseTableWrapRef" class="parse-table-wrap">
          <el-table ref="parseResultTableRef" :data="parseResultRows" border stripe size="small" height="100%" class="parse-result-table">
          <template v-if="parseField === 'C3'">
            <el-table-column label="POS" type="index" :index="parseResultIndex" width="70" align="center" header-align="center" />
            <el-table-column prop="Organization" :label="tLabel('机构', 'Organization')" :width="parseResultColWidth('org')" show-overflow-tooltip />
            <el-table-column :label="tLabel('纬度', 'Latitude')" width="100">
              <template #default="{ row }">
                <span :style="(row.C3_Latitude ?? row.Latitude) ? 'color:#3949ab' : 'color:#bbb'">
                  {{ (row.C3_Latitude ?? row.Latitude) != null ? Number(row.C3_Latitude ?? row.Latitude).toFixed(4) : '-' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column :label="tLabel('经度', 'Longitude')" width="100">
              <template #default="{ row }">
                <span :style="(row.C3_Longitude ?? row.Longitude) ? 'color:#3949ab' : 'color:#bbb'">
                  {{ (row.C3_Longitude ?? row.Longitude) != null ? Number(row.C3_Longitude ?? row.Longitude).toFixed(4) : '-' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="address" :label="tLabel('原始C3列', 'Raw C3')" :min-width="parseResultColWidth('raw')" show-overflow-tooltip />
          </template>

          <!-- Affiliation 模式表格 -->
          <template v-else-if="affiliationMode">
            <el-table-column label="POS" type="index" :index="parseResultIndex" width="70" align="center" header-align="center" />
            <el-table-column :label="affiliationNameLabel" :min-width="parseResultColWidth('rankName')" show-overflow-tooltip>
              <template #default="{ row }">
                {{ row['Country/Region'] || row['Organization'] || row['City1'] || row['name'] || '-' }}
              </template>
            </el-table-column>
            <el-table-column :label="tLabel('纬度', 'Latitude')" :width="parseResultColWidth('lat')">
              <template #default="{ row }">
                <span :style="row.Latitude != null ? 'color:#3949ab' : 'color:#bbb'">
                  {{ row.Latitude != null ? Number(row.Latitude).toFixed(4) : '-' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column :label="tLabel('经度', 'Longitude')" :width="parseResultColWidth('lng')">
              <template #default="{ row }">
                <span :style="row.Longitude != null ? 'color:#3949ab' : 'color:#bbb'">
                  {{ row.Longitude != null ? Number(row.Longitude).toFixed(4) : '-' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column :label="tLabel('模型', 'Model')" :width="parseResultColWidth('raw')" show-overflow-tooltip>
              <template #default="{ row }">
                {{ row.ParseModel || row.ParseSrc || '-' }}
              </template>
            </el-table-column>
          </template>

          <template v-else>
            <el-table-column label="POS" type="index" :index="parseResultIndex" width="70" align="center" header-align="center" />
            <el-table-column prop="name" :label="rankNameLabel" :width="parseResultColWidth('rankName')" show-overflow-tooltip />
            <el-table-column prop="lat" :label="tLabel('纬度', 'Latitude')" :width="parseResultColWidth('lat')">
              <template #default="{ row }">
                <span>{{ row.lat != null ? Number(row.lat).toFixed(4) : '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="lng" :label="tLabel('经度', 'Longitude')" :width="parseResultColWidth('lng')">
              <template #default="{ row }">
                <span>{{ row.lng != null ? Number(row.lng).toFixed(4) : '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="address" :label="tLabel('原始C1', 'Raw C1')" :min-width="parseResultColWidth('raw')" show-overflow-tooltip />
          </template>
          </el-table>
        </div>

        <div class="result-hd parse-result-pagination">
          <div class="parse-result-pagination-left">
            <span class="parse-result-total">
              {{ tLabel(`共 ${geoTotal} 条`, `Total ${geoTotal}`) }}
            </span>
            <div class="page-size-left">
              <el-select v-model="geoPageSize" size="medium" style="width:110px;" @change="onGeoPageSizeChange">
                <el-option :value="20" :label="tLabel('20 条/页', '20 / page')" />
                <el-option :value="50" :label="tLabel('50 条/页', '50 / page')" />
                <el-option :value="100" :label="tLabel('100 条/页', '100 / page')" />
              </el-select>
            </div>
          </div>
          <el-pagination
              v-if="geoTotal > geoPageSize"
              v-model:current-page="geoPage"
              v-model:page-size="geoPageSize"
              :page-size="geoPageSize"
              :total="geoTotal"
              layout="prev, pager, next, jumper"
              medium
              @current-change="affiliationMode ? refreshAffiliationResults($event) : refreshParseResultData($event)"
          />
        </div>
      </div>
    </el-dialog>

    <el-dialog
      v-model="parseProgressDialogVisible"
      class="parse-progress-dialog"
      :title="tLabel('地理解析', 'Geo Parsing')"
      width="70%"
      destroy-on-close
    >
      <div class="parse-progress-wrap parse-progress-dialog-wrap">
        <div class="progress-head">
          <span>{{ tLabel('解析进度', 'Progress') }}</span>
          <span>{{ parseProgress }}%</span>
        </div>
        <el-progress
          :percentage="parseProgress"
          :status="parseProgress === 100 ? 'success' : ''"
          :show-text="false"
          :striped="parseRunning"
          :striped-flow="parseRunning"
          :duration="10"
        />
        <div class="log-box" ref="logBoxRef">
          <p v-for="(line, i) in parseLogs" :key="i" class="log-line">{{ line }}</p>
          <p v-if="parseLogs.length === 0" class="log-placeholder">{{ tLabel('等待解析任务启动...', 'Waiting for the parse task to start...') }}</p>
        </div>
      </div>
    </el-dialog>

    <el-dialog
      v-model="modelConfigDialogVisible"
      class="model-config-dialog"
      :title="tLabel('模型配置', 'Model Settings')"
      width="860px"
      destroy-on-close
    >
      <div class="llm-settings">
        <aside class="llm-provider-nav">
          <button
            v-for="p in PROVIDER_DEFS"
            :key="p.key"
            type="button"
            class="llm-provider-btn"
            :class="{
              active: activeProviderKey === p.key,
              disabled: testingProvider && testingProviderKey !== p.key,
            }"
            @click="selectProvider(p.key)"
          >
            <img class="llm-provider-icon" :src="p.icon" :alt="p.name" />
            <span class="llm-provider-name">{{ p.name }}</span>
            <span class="llm-provider-dot" :class="{ on: providerConfigs[p.key].verified }">●</span>
          </button>
        </aside>
        <section class="llm-provider-panel">
          <h3 class="llm-panel-title">{{ activeProviderDef.name }}</h3>
          <div class="llm-form-row">
            <span class="llm-form-label">API Key</span>
            <el-input
              v-model="activeProviderCfg.api_key"
              class="llm-form-input"
              type="password"
              show-password
              placeholder="Enter your API key"
            />
            <el-button
              class="llm-row-btn llm-test-btn"
              type="primary"
              :loading="testingProvider && testingProviderKey === activeProviderKey"
              @click="testProviderConnection"
            >{{ tLabel('测试', 'Test') }}</el-button>
            <el-button class="llm-row-btn" @click="clearProviderConfig">{{ tLabel('清除', 'Clear') }}</el-button>
          </div>
          <div class="llm-form-row">
            <span class="llm-form-label">Base URL</span>
            <el-input
              v-model="activeProviderCfg.base_url"
              class="llm-form-input"
              :placeholder="activeProviderDef.defaultBaseUrl || 'https://api.example.com/v1'"
            />
          </div>
          <div class="llm-models-header">
            <span class="llm-models-title">{{ tLabel('模型', 'Models') }}</span>
            <span class="llm-models-hint" :class="{ 'is-testing': showProviderTestProgress }">
              <svg
                v-if="showProviderTestProgress"
                class="llm-test-spinner"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <circle
                  class="llm-test-spinner-track"
                  cx="12"
                  cy="12"
                  r="9"
                  fill="none"
                  stroke-width="2.5"
                />
                <circle
                  class="llm-test-spinner-arc"
                  cx="12"
                  cy="12"
                  r="9"
                  fill="none"
                  stroke-width="2.5"
                  stroke-linecap="round"
                />
              </svg>
              <span class="llm-models-hint-text">
                {{ showProviderTestProgress && testProgressText
                  ? testProgressText
                  : (activeProviderCfg.models.length
                    ? tLabel(`${activeProviderCfg.models.length} 个模型`, `${activeProviderCfg.models.length} models`)
                    : tLabel('点击"测试"自动发现并选择可用模型', 'Click Test to discover available models')) }}
              </span>
            </span>
          </div>
          <div class="llm-model-list">
            <div v-for="m in activeProviderCfg.models" :key="m.model" class="llm-model-row">
              <span class="llm-model-name" :title="m.model">{{ m.model }}</span>
              <span v-if="m.elapsed" class="llm-model-time">{{ m.elapsed }}s</span>
              <button
                type="button"
                class="llm-model-del"
                :aria-label="tLabel('移除模型', 'Remove model')"
                @click="removeProviderModel(m.model)"
              >⊖</button>
            </div>
            <p v-if="activeProviderCfg.models.length === 0" class="llm-model-empty">
              {{ tLabel('尚未添加模型', 'No models added yet') }}
            </p>
          </div>
        </section>
      </div>
    </el-dialog>

    <el-dialog
      v-model="modelSelectVisible"
      class="model-select-dialog"
      :title="tLabel('选择模型', 'Select Models')"
      width="520px"
      append-to-body
      :show-close="true"
    >
      <el-input
        v-model="modelSearch"
        class="model-select-search"
        clearable
        :placeholder="tLabel('搜索模型...', 'Search models...')"
      >
        <template #prefix>
          <el-icon class="model-select-search-icon"><Search /></el-icon>
        </template>
      </el-input>
      <div class="model-select-list">
        <label
          v-for="item in filteredFetchedModels"
          :key="item.model"
          class="model-select-item"
          :class="{ 'is-failed': item.passed === false }"
        >
          <el-checkbox v-model="modelSelectChecks[item.model]" />
          <span class="msi-name" :title="item.model">{{ item.model }}</span>
          <span v-if="item.passed === false" class="msi-fail">
            {{ tLabel('未达标', 'Below threshold') }}<template v-if="item.elapsed != null"> · {{ item.elapsed }}s</template>
          </span>
          <span v-else-if="item.elapsed != null" class="msi-time">{{ item.elapsed }}s</span>
        </label>
      </div>
      <template #footer>
        <div class="model-select-toolbar">
          <div class="model-select-actions">
            <el-button class="model-select-action-btn" @click="setAllModelChecks(true)">
              {{ tLabel('全选', 'Select All') }}
            </el-button>
            <el-button class="model-select-action-btn" @click="setAllModelChecks(false)">
              {{ tLabel('清空', 'Clear') }}
            </el-button>
          </div>
          <el-button class="model-select-confirm-btn" type="primary" @click="confirmModelSelect">
            {{ tLabel('添加所选', 'Add Selected') }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElColorPicker, ElMessage, ElMessageBox } from 'element-plus'
import { Loading, Search } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import 'echarts-gl'
import {
  uploadWos,
  startParseC1,
  startParseBatchTiers,
  startParseAffiliation,
  stopParseC1,
  getParseProgress,
  getTierProgress,
  getGeoResults,
  getTierResults,
  getVizData,
  getTierStats,
  getEntityMatrix,
  exportEntityMatrixGml,
  benchmarkModels,
  listModels,
  getDemoData,
  getDemoMatrix,
  createCustomDemoSession,
  runGeocode
} from '../api/index.js'
import world from '../utils/json/world.json'
import { edgeWeightRange, edgeWeightToBaseWidth } from '../utils/edgeWidth.js'
import colorIcon from '../assets/img/color.png'
import deepseekIcon from '../assets/providers/deepseek.svg'
import siliconflowIcon from '../assets/providers/siliconflow.svg'
import qwenIcon from '../assets/providers/qwen.svg'
import openaiIcon from '../assets/providers/openai.svg'
import anthropicIcon from '../assets/providers/anthropic.svg'
import customIcon from '../assets/providers/custom.svg'
import DataView from './DataView.vue'
import VizView from './VizView.vue'

const props = defineProps({
  sessionId:   { type: String, default: '' },
  recordCount: { type: Number, default: 0 },
})
const emit = defineEmits(['session-created'])

// 勿在仓库中写入真实 Key；由用户在「模型配置」中填写，或通过本地未入库环境配置注入
const ALIYUN_API_KEY = ''
const HOME_LANG_KEY = 'home_lang_switch'
const HOME_THEME_KEY = 'home_theme_switch'
const HOME_MODEL_CFG_KEY = 'home_model_cfg'
const HOME_UI_STATE_KEY = 'home_ui_state'
const DEFAULT_MODELS = [
  'qwen3-coder-flash',
  'qwen-turbo-2025-07-15',
  'tongyi-xiaomi-analysis-flash',
  'qwen3-coder-next',
  'qwen-turbo-2025-04-28',
  'qwen-flash',
  'qwen-turbo-2024-11-01',
  'qwen3-30b-a3b-instruct-2507',
  'qwen-turbo-latest',
  'qwen3-coder-480b-a35b-instruct',
  'tongyi-xiaomi-analysis-pro',
  'qwen2.5-14b-instruct',
  'codeqwen1.5-7b-chat',
  'qwen3-coder-plus-2025-07-22',
  'qwen-turbo',
  'deepseek-v3.1',
  'qwen2.5-32b-instruct',
  'qwen-plus-2025-07-14',
  'qwen2.5-7b-instruct-1m',
  'qwen3-next-80b-a3b-instruct',
  'qwen-coder-turbo-0919',
  'qwen2.5-7b-instruct',
  'qwen-plus-2025-04-28',
  'qwen-coder-plus-1106',
  'qwen-coder-turbo-latest',
  'qwen-coder-plus-latest',
  'qwen-plus-2025-12-01',
  'qwen-coder-turbo',
  'qwen2.5-coder-14b-instruct',
  'qwen2.5-coder-32b-instruct',
]

const langSwitch = ref(true)
const themeSwitch = ref(false)
const activeView = ref('平面地图')
const viewItems = ['数据列表', '平面地图', '三维地图', '条形图', '热力图']
const vizType = ref('country')
const ALL_VIZ_TABS = ['country', 'org', 'city']
const DEFAULT_MAP_NODE_SIZE = 70
const DEFAULT_THREE_D_BAR_SIZE = 40
const DEFAULT_MAP_LABEL_VISIBLE = false
const DEFAULT_MAP_NODE_OPACITY = 20
const DEFAULT_MAP_EDGE_WIDTH = 5
const DEFAULT_MAP_EDGE_OPACITY_LIGHT = 93
const DEFAULT_MAP_EDGE_OPACITY_DARK = 88
const DEFAULT_MAP_SIZE_MODE = 'scaled'
const DEFAULT_MAP_NODE_COLOR = '#ef4444'
const DEFAULT_MAP_EDGE_COLOR_LIGHT = '#000000'
const DEFAULT_MAP_EDGE_COLOR_DARK = '#ffffff'
const DEFAULT_MAP_EDGE_VISIBLE = false
const DEFAULT_THREE_D_BAR_COLOR = '#429488'
const DEFAULT_THREE_D_RENDER_MODE = 'bar'
const THREE_D_LABEL_MAX_CHARS = 18
const mapNodeSize = ref(DEFAULT_MAP_NODE_SIZE)
const scaledMapNodeSize = ref(DEFAULT_MAP_NODE_SIZE)
const threeDBarSize = ref(DEFAULT_THREE_D_BAR_SIZE)
const mapLabelVisible = ref(DEFAULT_MAP_LABEL_VISIBLE)
const mapNodeOpacity = ref(DEFAULT_MAP_NODE_OPACITY)
const mapEdgeWidth = ref(DEFAULT_MAP_EDGE_WIDTH)
const mapEdgeOpacity = ref(getDefaultMapEdgeOpacity(false))
const mapSizeMode = ref(DEFAULT_MAP_SIZE_MODE)
const mapNodeColor = ref(DEFAULT_MAP_NODE_COLOR)
const mapEdgeColor = ref(getDefaultMapEdgeColor(false))
const mapEdgeVisible = ref(DEFAULT_MAP_EDGE_VISIBLE)
const threeDBarColor = ref(DEFAULT_THREE_D_BAR_COLOR)
const threeDRenderMode = ref(DEFAULT_THREE_D_RENDER_MODE)
const nativeColorInputRef = ref(null)
const colorPicker = ElColorPicker
const colorPickerNetWorkNode = ref(null)
const colorPickerNetWorkEdge = ref(null)

function getDefaultMapEdgeOpacity(isDark = themeSwitch.value) {
  return isDark ? DEFAULT_MAP_EDGE_OPACITY_DARK : DEFAULT_MAP_EDGE_OPACITY_LIGHT
}

function getDefaultMapEdgeColor(isDark = themeSwitch.value) {
  return isDark ? DEFAULT_MAP_EDGE_COLOR_DARK : DEFAULT_MAP_EDGE_COLOR_LIGHT
}

const vizOptions = computed(() => {
  const base = langSwitch.value
    ? [
      { label: '国家 / 地区', value: 'country' },
      { label: '机构', value: 'org' },
      { label: '城市', value: 'city' },
    ]
    : [
      { label: 'Country / Region', value: 'country' },
      { label: 'Organization', value: 'org' },
      { label: 'City', value: 'city' },
    ]
  // C3（机构列表）只有机构维度，国家/城市视图不可选
  return base.map((item) => ({
    ...item,
    disabled: parseField.value === 'C3' && item.value !== 'org',
  }))
})

const fileList = ref([])
const savedUploadNames = ref([])
const uploadRef = ref(null)
const uploadDisplayName = computed(() => {
  const emptyText = tLabel('未上传文件', 'No file uploaded')
  if (fileList.value.length === 0 && savedUploadNames.value.length === 0) return emptyText
  if (fileList.value.length === 0) return savedUploadNames.value[0]
  return fileList.value[0]?.name || emptyText
})
const displayedUploadFiles = computed(() => {
  if (fileList.value.length > 0) return fileList.value
  return savedUploadNames.value.map((name, i) => ({ uid: `saved-${i}`, name, __saved: true }))
})
const loading = ref(false)
const uploadProgress = ref(0)
const canStartUpload = computed(() => displayedUploadFiles.value.length > 0)
const rawDataDialogVisible = ref(false)
const parseResultDialogVisible = ref(false)
const parseProgressDialogVisible = ref(false)
const modelConfigDialogVisible = ref(false)
const demoMode = ref(false)
const customDemoActive = ref(false)
const demoLoading = ref(false)
const demoChoiceVisible = ref(false)
const demoRawTableLoading = ref(false)
const demoRawTableRows = ref([])
const demoAvailableTiers = ref({
  C1: { country: false, org: false, city: false },
  C3: { country: false, org: false, city: false },
})
const vizReloadKey = ref(0)
const vizAutoLoadEnabled = ref(false)  // 是否启用自动加载 viz 数据
const vizLoading = ref(false)
const vizLoadingProgress = ref(0)
const vizMeta = ref({ total: null, source: '', tier: '', displayCount: null })
const latestSessionId = ref('')
const latestRecordCount = ref(0)
const parsedFieldAvailability = ref({ C1: false, C3: false })

// Affiliation 模式状态
const affiliationMode = ref(false)
const affiliationSubtypes = ref([]) // ['affiliation_country', 'affiliation_org']

const effectiveSessionId = computed(() => latestSessionId.value || props.sessionId)
const effectiveRecordCount = computed(() => latestRecordCount.value || props.recordCount)

const parseField = ref('C1')
const c1TierChecks = ref({
  country: false,
  org: false,
  city: false,
})
const batchSize = ref(DEFAULT_MODELS.length)
const parseRunning = ref(false)
const parseProgress = ref(0)
const parseLogs = ref([])
const parseSummary = ref(null)
// 按字段分别缓存解析汇总（C1 / C3 各自独立），切换标签时显示各自结果，
// 避免出现「C1 标签下却显示 C3 的处理条数」这类串台问题。
const parseSummaryByField = ref({ C1: null, C3: null })
// 各层（国家/机构/城市）分别统计的解析汇总，按字段缓存；用于「选中几层就分别报告几层」
const parseTierSummaries = ref([])
const parseTierSummariesByField = ref({ C1: [], C3: [] })
// 各层「共处理条数」通常一致（同一份地址/机构），一致时提到顶部只显示一次
const parseTierSharedTotal = computed(() => {
  const list = parseTierSummaries.value
  if (!list.length) return null
  const first = list[0].total
  return list.every((t) => t.total === first) ? first : null
})
// 是否存在一次已完成的解析过程（有汇总或日志），用于显示「查看/隐藏解析过程」按钮
const hasParsedProcess = computed(() =>
  parseTierSummaries.value.length > 0
  || !!parseSummary.value
  || parseLogs.value.length > 0,
)
const logBoxRef = ref(null)

const geoRecords = ref([])
const geoTotal = ref(0)
const geoPage = ref(1)
const geoPageSize = ref(50)
const rankRecords = ref([])
const vizViewRef = ref(null)
const threeDMapEl = ref(null)
const threeDItems = ref([])
const threeDEdges = ref([])
const threeDEdgesSignature = ref('')
let vizLoadingTimer = null

function stopVizLoadingProgress(reset = true) {
  if (vizLoadingTimer) {
    clearInterval(vizLoadingTimer)
    vizLoadingTimer = null
  }
  if (reset) vizLoadingProgress.value = 0
}

function startVizLoadingProgress() {
  stopVizLoadingProgress(false)
  vizLoadingProgress.value = Math.max(3, Math.floor(Number(vizLoadingProgress.value) || 0))
  vizLoadingTimer = window.setInterval(() => {
    const current = Number(vizLoadingProgress.value) || 0
    if (current >= 95) return
    const step = current < 20 ? 2 : current < 45 ? 3 : current < 70 ? 2 : 1
    vizLoadingProgress.value = Math.min(95, current + step)
  }, 320)
}
const parseTableWrapRef = ref(null)
const parseTableWrapWidth = ref(0)
const parseResultTableRef = ref(null)
const FULL_TOP_N = 10000
const DEMO_DEFAULT_C1_TIER = 'country'
const DEMO_COUNT_API_MAP = {
  C1: { country: 'demoC1CountryCount', city: 'demoC1CityCount', org: 'demoC1OrgCount' },
  C3: { org: 'demoC3Count' },
}
const DEMO_MATRIX_API_MAP = {
  C1: { country: 'C1CountryMatrix', city: 'C1CityMatrix', org: 'C1OrgMatrix' },
  C3: { org: 'C3OrgMatrix' },
}
const DEMO_LIST_API_MAP = {
  C1: { country: 'demoC1CountryList', city: 'demoC1CityList', org: 'demoC1OrgList' },
  C3: { org: 'demoC3List' },
}

let threeDMapChart = null
let renderingThreeD = false
let parseTableResizeObserver = null
let threeDBaseMapTextureCanvas = null
let threeDCameraChangeHandler = null
const DEFAULT_THREE_D_VIEW_CONTROL = Object.freeze({
  autoRotate: false,
  autoRotateSpeed: 3.2,
  distance: 155,
  minDistance: 1,
  maxDistance: 500,
  targetCoord: [105, 30],
  rotateSensitivity: 1.8,
  zoomSensitivity: 2,
  panSensitivity: 1,
})
const threeDViewState = ref({
  distance: DEFAULT_THREE_D_VIEW_CONTROL.distance,
  alpha: null,
  beta: null,
  center: null,
})
const threeDLabelDetailLevel = ref(-1)

// ── 大模型多服务商配置（复现 LLM Chat 设置页：服务商列表 + 图标 + 模型发现/选择/清除）──
const PROVIDER_DEFS = [
  {
    key: 'deepseek', name: 'DeepSeek', icon: deepseekIcon,
    backendProvider: 'DeepSeek', defaultBaseUrl: 'https://api.deepseek.com/v1',
  },
  {
    key: 'siliconflow', name: 'SiliconFlow', icon: siliconflowIcon,
    backendProvider: 'SiliconFlow', defaultBaseUrl: 'https://api.siliconflow.cn/v1',
  },
  {
    key: 'qwen', name: 'Qwen', icon: qwenIcon,
    backendProvider: 'Aliyun', defaultBaseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    defaultApiKey: ALIYUN_API_KEY,
    defaultModels: DEFAULT_MODELS.map((m) => ({ model: m })),
  },
  {
    key: 'openai', name: 'OpenAI', icon: openaiIcon,
    backendProvider: 'OpenAI', defaultBaseUrl: 'https://api.openai.com/v1',
  },
  {
    key: 'anthropic', name: 'Anthropic', icon: anthropicIcon,
    backendProvider: 'Anthropic', defaultBaseUrl: 'https://api.anthropic.com',
  },
  {
    key: 'custom', name: 'Custom', icon: customIcon,
    backendProvider: 'Custom', defaultBaseUrl: '',
  },
]

function buildDefaultProviderConfigs() {
  const out = {}
  for (const p of PROVIDER_DEFS) {
    out[p.key] = {
      api_key: p.defaultApiKey || '',
      base_url: p.defaultBaseUrl || '',
      models: (p.defaultModels || []).map((m) => ({ ...m })),
      verified: Boolean(p.defaultModels?.length),
    }
  }
  return out
}

const providerConfigs = ref(buildDefaultProviderConfigs())
const activeProviderKey = ref('qwen')
const activeProviderDef = computed(() => PROVIDER_DEFS.find((p) => p.key === activeProviderKey.value) || PROVIDER_DEFS[0])
const activeProviderCfg = computed(() => providerConfigs.value[activeProviderKey.value])
const testingProvider = ref(false)
const testingProviderKey = ref('')
const testProgressText = ref('')
const showProviderTestProgress = computed(() => (
  testingProvider.value
  && Boolean(testProgressText.value)
  && testingProviderKey.value === activeProviderKey.value
))
const fetchedModels = ref([])
const modelSelectVisible = ref(false)
const modelSelectChecks = ref({})
const modelSearch = ref('')

const filteredFetchedModels = computed(() => {
  const q = modelSearch.value.trim().toLowerCase()
  if (!q) return fetchedModels.value
  return fetchedModels.value.filter((item) => item.model.toLowerCase().includes(q))
})

/** 全部服务商已配置模型的扁平列表（解析时逐一调用） */
const selectedModels = computed(() => {
  const out = []
  for (const p of PROVIDER_DEFS) {
    for (const m of providerConfigs.value[p.key]?.models || []) {
      out.push(m.model)
    }
  }
  return out
})

const statusText = computed(() => {
  if (parseRunning.value) return '解析中'
  if (loading.value) return '加载中'
  if (effectiveSessionId.value) return '已加载'
  return '就绪'
})
const showParseProgressIcon = computed(() => parseRunning.value)
const rankNameLabel = computed(() => {
  if (affiliationMode.value) {
    if (vizType.value === 'country') return tLabel('国家 / 地区', 'Country / Region')
    if (vizType.value === 'org') return tLabel('机构', 'Organization')
    if (vizType.value === 'city') return tLabel('城市', 'City')
    return tLabel('名称', 'Name')
  }
  if (vizType.value === 'country') return tLabel('国家 / 地区', 'Country / Region')
  if (vizType.value === 'org') return tLabel('机构', 'Organization')
  if (vizType.value === 'city') return tLabel('城市', 'City')
  return tLabel('名称', 'Name')
})
const affiliationNameLabel = computed(() => {
  if (vizType.value === 'country') return tLabel('国家 / 地区', 'Country / Region')
  if (vizType.value === 'org') return tLabel('机构', 'Organization')
  if (vizType.value === 'city') return tLabel('城市', 'City')
  return tLabel('名称', 'Name')
})
const parseResultDialogTitle = computed(() => {
  if (affiliationMode.value) {
    return langSwitch.value ? '解析结果表格' : 'Parsed Result Table'
  }
  return langSwitch.value
    ? `${parseField.value}解析结果表格`
    : `${parseField.value} Parsed Result Table`
})
const selectedC1Tiers = computed(() => ['country', 'org', 'city'].filter((tier) => c1TierChecks.value[tier]))
const c1AllChecked = computed(() => selectedC1Tiers.value.length === 3)
const c1AllIndeterminate = computed(() => {
  const n = selectedC1Tiers.value.length
  return n > 0 && n < 3
})
const activeTier = computed(() => {
  if (vizType.value === 'country' || vizType.value === 'org' || vizType.value === 'city') return vizType.value
  return 'country'
})
const parseResultRows = computed(() => geoRecords.value)
const panelVizType = computed(() => {
  if (activeView.value === '平面地图') return 'map'
  if (activeView.value === '热力图') return 'heatmap'
  if (activeView.value === '条形图') return parseField.value === 'C3' ? 'org' : vizType.value
  return vizType.value
})
const panelField = computed(() => {
  if (affiliationMode.value) {
    // Affiliation 模式：根据 vizType 映射到对应的 field
    if (vizType.value === 'country') return 'affiliation_country'
    if (vizType.value === 'org') return 'affiliation_org'
    if (vizType.value === 'city') return 'affiliation_city'
    return affiliationSubtypes.value[0] || 'affiliation_country'
  }
  return parseField.value
})
const hasThreeDData = computed(() => {
  const list = Array.isArray(threeDItems.value) ? threeDItems.value : []
  return list.some((item) => Number.isFinite(Number(item?.lng)) && Number.isFinite(Number(item?.lat)))
})
const vizMetaText = computed(() => {
  // 优先用图上实际展示条数，与表格总量对齐
  const shown = Number(vizMeta.value.displayCount)
  const total = Number(vizMeta.value.total)
  const count = shown > 0 ? shown : total
  if (!Number.isFinite(count) || count <= 0) return ''
  const tierMapZh = { country: '国家/地区', org: '机构', city: '城市' }
  const tierMapEn = { country: 'countries/regions', org: 'organizations', city: 'cities' }
  const zhTier = tierMapZh[vizMeta.value.tier] || '项目'
  const enTier = tierMapEn[vizMeta.value.tier] || 'items'
  return langSwitch.value
    ? `共提取和显示了 ${count} 个${zhTier}`
    : `Extracted and displayed ${count} ${enTier}`
})
const showMapParamsPanel = computed(() => (
  ((activeView.value === '平面地图' || activeView.value === '热力图') && Number(vizMeta.value.displayCount) > 0)
  || (activeView.value === '三维地图' && hasThreeDData.value)
))
const showNodeColorControl = computed(() => activeView.value === '平面地图' || activeView.value === '三维地图')
const showThreeDRenderModeControl = computed(() => activeView.value === '三维地图')
const threeDRenderTargetLabel = computed(() => {
  if (activeView.value === '三维地图' && threeDRenderMode.value === 'bar') {
    return { zh: '柱体', en: 'Bar' }
  }
  return { zh: '节点', en: 'Node' }
})
const mapColorControlLabel = computed(() => {
  if (activeView.value === '三维地图') {
    return tLabel(`${threeDRenderTargetLabel.value.zh}颜色`, `${threeDRenderTargetLabel.value.en} Color`)
  }
  return tLabel('节点颜色', 'Nodes Color')
})
const mapOpacityControlLabel = computed(() => {
  if (activeView.value === '三维地图') {
    return tLabel(`${threeDRenderTargetLabel.value.zh}透明度`, `${threeDRenderTargetLabel.value.en} Opacity`)
  }
  return tLabel('节点透明度', 'Node Opacity')
})
const mapLabelControlLabel = computed(() => {
  if (activeView.value === '三维地图') {
    return tLabel('节点名称', 'Node Names')
  }
  return tLabel('标签显示', 'Labels')
})
const mapEdgeWidthControlLabel = computed(() => tLabel('连线粗细', 'Edge Width'))
const mapEdgeOpacityControlLabel = computed(() => tLabel('连线透明度', 'Edge Opacity'))
const mapEdgeColorControlLabel = computed(() => tLabel('连线颜色', 'Edge Color'))
const showMapLabelControl = computed(() => (
  activeView.value === '平面地图'
  || activeView.value === '热力图'
  || activeView.value === '三维地图'
))
const showMapEdgesControl = computed(() => {
  if (activeView.value === '三维地图' && threeDRenderMode.value === 'point') return true
  return Boolean(
    activeView.value === '平面地图'
    && !affiliationMode.value
    && (
      (parseField.value === 'C1' && ['country', 'org', 'city'].includes(vizType.value))
      || (parseField.value === 'C3' && vizType.value === 'org')
    )
  )
})
const mapSizeControlLabel = computed(() => {
  if (activeView.value === '三维地图') {
    return tLabel(`${threeDRenderTargetLabel.value.zh}大小`, `${threeDRenderTargetLabel.value.en} Size`)
  }
  return tLabel('节点大小', 'Node Size')
})
const mapSizeModeControlAriaLabel = computed(() => {
  if (activeView.value === '三维地图') {
    return tLabel(`${threeDRenderTargetLabel.value.zh}大小模式`, `${threeDRenderTargetLabel.value.en} size mode`)
  }
  return tLabel('节点大小模式', 'Node size mode')
})
const showMapSizeModeControl = computed(() => activeView.value !== '三维地图' || threeDRenderMode.value === 'point')
const activeMapColor = computed({
  get() {
    return activeView.value === '三维地图' ? threeDBarColor.value : mapNodeColor.value
  },
  set(value) {
    if (activeView.value === '三维地图') {
      threeDBarColor.value = value
      return
    }
    mapNodeColor.value = value
  },
})
const activeMapEdgeColor = computed({
  get() {
    return mapEdgeColor.value
  },
  set(value) {
    mapEdgeColor.value = value
  },
})
const activeMapSize = computed({
  get() {
    if (activeView.value === '三维地图' && threeDRenderMode.value !== 'point') {
      return threeDBarSize.value
    }
    return mapNodeSize.value
  },
  set(value) {
    if (activeView.value === '三维地图' && threeDRenderMode.value !== 'point') {
      threeDBarSize.value = value
      return
    }
    mapNodeSize.value = value
  },
})
const showBoardMainTitle = computed(() => (
  (activeView.value === '平面地图' && Number(vizMeta.value.displayCount) > 0) ||
  (activeView.value === '热力图' && Number(vizMeta.value.displayCount) > 0) ||
  (activeView.value === '三维地图' && hasThreeDData.value)
))
const showExportGmlButton = computed(() => {
  if (affiliationMode.value) return false
  if (demoMode.value) return parseField.value === 'C3' ? vizType.value === 'org' : ['country', 'org', 'city'].includes(vizType.value)
  if (!effectiveSessionId.value || parseRunning.value) return false
  return Boolean(parsedFieldAvailability.value?.[parseField.value])
})

function getCurrentGmlFilename() {
  const field = parseField.value === 'C3' ? 'C3' : 'C1'
  const tier = field === 'C3'
    ? 'org'
    : (vizType.value === 'org' || vizType.value === 'city' ? vizType.value : 'country')
  return `entity_matrix_${field}_${tier}.gml`
}

function tLabel(zh, en) {
  return langSwitch.value ? zh : en
}

// 当前界面语言代码，用于把「解析进度日志」的语言随系统语言传给后端
function currentLang() {
  return langSwitch.value ? 'zh' : 'en'
}

function tierDisplayName(type) {
  if (type === 'country') return tLabel('国家 / 地区', 'Country / Region')
  if (type === 'org') return tLabel('机构', 'Organization')
  if (type === 'city') return tLabel('城市', 'City')
  return type
}

function buildEmptyTierAvailability() {
  return { country: false, org: false, city: false }
}

function resetDemoTierAvailability() {
  demoAvailableTiers.value = {
    C1: buildEmptyTierAvailability(),
    C3: buildEmptyTierAvailability(),
  }
}

function markDemoTierAvailable(field, tier) {
  if (!demoAvailableTiers.value[field] || !ALL_VIZ_TABS.includes(tier)) return
  demoAvailableTiers.value = {
    ...demoAvailableTiers.value,
    [field]: {
      ...demoAvailableTiers.value[field],
      [tier]: true,
    },
  }
}

function isAffiliationTierAvailable(type) {
  const field = type === 'country'
    ? 'affiliation_country'
    : type === 'org'
      ? 'affiliation_org'
      : 'affiliation_city'
  return affiliationSubtypes.value.includes(field)
}

function showTierUnavailableMessage(type) {
  ElMessage.warning(`${tierDisplayName(type)}${tLabel('未解析', ' is not parsed yet')}`)
}

async function ensureDemoTierAvailable(field, tier) {
  if (!ALL_VIZ_TABS.includes(tier)) return true
  if (demoAvailableTiers.value[field]?.[tier]) return true

  const countApiName = DEMO_COUNT_API_MAP[field]?.[tier]
  const listApiName = DEMO_LIST_API_MAP[field]?.[tier]
  if (!countApiName && !listApiName) return false

  try {
    if (countApiName) {
      const countRes = await getDemoData(countApiName)
      const countRows = normalizeDemoCountRows(countRes.data || {})
      if (countRows.length > 0) {
        markDemoTierAvailable(field, tier)
        return true
      }
    }

    if (listApiName) {
      const listRes = await getDemoData(listApiName)
      const srcRows = extractDemoList(listRes.data || {})
      if (srcRows.length > 0) {
        markDemoTierAvailable(field, tier)
        return true
      }
    }
  } catch (_) {}

  return false
}

async function canSwitchVizType(type) {
  if (!ALL_VIZ_TABS.includes(type)) return true

  if (demoMode.value) {
    return await ensureDemoTierAvailable(parseField.value, type)
  }

  if (affiliationMode.value) {
    return isAffiliationTierAvailable(type)
  }

  if (parseField.value !== 'C1') {
    return true
  }

  if (!effectiveSessionId.value) {
    return true
  }

  try {
    const res = await getTierProgress(effectiveSessionId.value)
    const c1Progress = res.data?.C1 || {}
    const target = c1Progress[type]
    return Boolean(
      target?.complete ||
      (Number(target?.parsed) > 0) ||
      (Number(target?.percent) > 0) ||
      (Number(target?.total) > 0)
    )
  } catch (_) {
    ElMessage.warning(tLabel('无法获取分层解析状态', 'Unable to get tier parsing status'))
    return false
  }
}

function viewText(item) {
  if (langSwitch.value) return item
  if (item === '数据列表') return 'Data Table'
  if (item === '平面地图') return 'Map'
  if (item === '三维地图') return '3D Map'
  if (item === '条形图') return 'Bar Chart'
  if (item === '热力图') return 'Density Map'
  return item
}

function changeNodeColor() {}
function changeEdgeColor() {}

function openSystemColorPicker() {
  const picker = colorPickerNetWorkNode.value
  if (picker?.openPanel) {
    picker.openPanel()
    return
  }
  if (picker?.handleOpen) {
    picker.handleOpen()
    return
  }
  if (picker?.handleTrigger) {
    picker.handleTrigger()
    return
  }
  nativeColorInputRef.value?.click?.()
}

function onNativeColorInput(event) {
  const color = event?.target?.value
  if (color) activeMapColor.value = color
}

function resetNodeColor() {
  mapNodeColor.value = DEFAULT_MAP_NODE_COLOR
  mapEdgeColor.value = getDefaultMapEdgeColor()
  threeDBarColor.value = DEFAULT_THREE_D_BAR_COLOR
}

function resetMapParamSettings() {
  mapLabelVisible.value = DEFAULT_MAP_LABEL_VISIBLE
  mapSizeMode.value = DEFAULT_MAP_SIZE_MODE
  scaledMapNodeSize.value = DEFAULT_MAP_NODE_SIZE
  mapNodeSize.value = DEFAULT_MAP_NODE_SIZE
  threeDBarSize.value = DEFAULT_THREE_D_BAR_SIZE
  mapNodeOpacity.value = DEFAULT_MAP_NODE_OPACITY
  mapEdgeWidth.value = DEFAULT_MAP_EDGE_WIDTH
  mapEdgeOpacity.value = getDefaultMapEdgeOpacity()
  mapNodeColor.value = DEFAULT_MAP_NODE_COLOR
  mapEdgeColor.value = getDefaultMapEdgeColor()
  mapEdgeVisible.value = DEFAULT_MAP_EDGE_VISIBLE
  threeDBarColor.value = DEFAULT_THREE_D_BAR_COLOR
  threeDRenderMode.value = DEFAULT_THREE_D_RENDER_MODE
  threeDEdges.value = []
  threeDEdgesSignature.value = ''
  vizReloadKey.value += 1
}


function toggleAllC1Tiers(checked) {
  const value = Boolean(checked)
  c1TierChecks.value = {
    country: value,
    org: value,
    city: value,
  }
}

function isLoggedInNow() {
  // 本地开发可通过 VITE_DISABLE_AUTH=true 跳过登录（.env.development.local）
  if (import.meta.env.VITE_DISABLE_AUTH === 'true') return true
  const loginFlag = localStorage.getItem('mssIsLogin')
  const mssLogin = localStorage.getItem('mssLogin')
  const userInfo = localStorage.getItem('userInfoAiGeovis')
    || localStorage.getItem('userInfoAigeovis')
    || localStorage.getItem('userInfoAI')
    || localStorage.getItem('userInfoCast')
  return Boolean(
    (loginFlag && loginFlag !== 'false')
    || (mssLogin && mssLogin !== 'false')
    || userInfo
  )
}

function ensureLoggedIn() {
  if (isLoggedInNow()) return true
  ElMessage.warning('请先登录')
  return false
}

function selectProvider(key) {
  if (testingProvider.value && key !== testingProviderKey.value) {
    ElMessage.warning(tLabel(
      '正在测试当前服务商，请等待完成后再切换。',
      'A provider test is running. Please wait until it finishes before switching.',
    ))
    return
  }
  activeProviderKey.value = key
}

/**
 * 测试当前服务商连通性：进度显示在模型列表标题旁（加载图标+文案），完成后弹出主题化结果提示。
 */
async function testProviderConnection() {
  const def = activeProviderDef.value
  const cfg = activeProviderCfg.value
  if (!cfg.api_key && def.key !== 'custom') {
    ElMessage.warning(tLabel('请先填写 API Key', 'Please enter API key first'))
    return
  }
  if (def.key === 'custom' && !cfg.base_url.trim()) {
    ElMessage.warning(tLabel('自定义服务商需填写 Base URL', 'Custom provider requires a Base URL'))
    return
  }
  testingProvider.value = true
  testingProviderKey.value = def.key
  testProgressText.value = tLabel('正在连接并拉取模型列表…', 'Connecting and fetching model list…')
  try {
    let modelCount = 0
    try {
      const listRes = await listModels({
        type: 'official',
        provider: def.backendProvider,
        api_key: cfg.api_key,
        base_url: cfg.base_url,
      })
      modelCount = Array.isArray(listRes.data?.models) ? listRes.data.models.length : 0
    } catch (_) {
      modelCount = 0
    }

    testProgressText.value = modelCount > 0
      ? tLabel(
        `共发现 ${modelCount} 个模型，正在测速中…`,
        `Found ${modelCount} models, benchmarking…`,
      )
      : tLabel('正在测速可用模型…', 'Benchmarking available models…')

    const res = await benchmarkModels({
      type: 'official',
      provider: def.backendProvider,
      api_key: cfg.api_key,
      base_url: cfg.base_url,
      timeout: 3.0,
      max_workers: 12,
    })
    const { passed, total_tested, failed } = res.data || {}
    const passedList = Array.isArray(passed) ? passed : []
    const failedList = Array.isArray(failed) ? failed : []
    const tested = total_tested || modelCount || (passedList.length + failedList.length)

    // 达标模型在前，未达标也列出但默认不勾选
    const passedNames = new Set(passedList.map((item) => item.model))
    fetchedModels.value = [
      ...passedList.map((item) => ({
        model: item.model,
        elapsed: item.elapsed,
        passed: true,
        error: null,
      })),
      ...failedList
        .filter((item) => item?.model && !passedNames.has(item.model))
        .map((item) => ({
          model: item.model,
          elapsed: item.elapsed,
          passed: false,
          error: item.error || null,
        })),
    ]

    if (fetchedModels.value.length === 0) {
      testProgressText.value = ''
      ElMessage.warning(tLabel(
        `共测试 ${tested} 个模型，未返回任何模型`,
        `Tested ${tested} models; no models returned`,
      ))
      return
    }

    const existing = new Set(cfg.models.map((m) => m.model))
    const checks = {}
    let autoSelectLeft = existing.size === 0 ? 30 : 0
    fetchedModels.value.forEach((item) => {
      if (existing.has(item.model)) {
        checks[item.model] = true
        return
      }
      // 仅自动勾选达标模型；未达标默认不勾选
      if (item.passed && autoSelectLeft > 0) {
        checks[item.model] = true
        autoSelectLeft -= 1
        return
      }
      checks[item.model] = false
    })
    modelSelectChecks.value = checks
    modelSearch.value = ''
    modelSelectVisible.value = true
    testProgressText.value = ''
    ElMessage.success(tLabel(
      `测试完成：共 ${tested} 个，达标 ${passedList.length}，未达标 ${failedList.length}`,
      `Test finished: ${tested} total, ${passedList.length} passed, ${failedList.length} below threshold`,
    ))
  } catch (e) {
    testProgressText.value = ''
    const msg = e.response?.data?.detail || e.message
    ElMessage.error(tLabel('测试失败：', 'Test failed: ') + String(msg))
  } finally {
    testingProvider.value = false
    testingProviderKey.value = ''
    testProgressText.value = ''
  }
}

function setAllModelChecks(checked) {
  const next = {}
  for (const item of filteredFetchedModels.value) next[item.model] = checked
  modelSelectChecks.value = { ...modelSelectChecks.value, ...next }
}

function confirmModelSelect() {
  const cfg = activeProviderCfg.value
  cfg.models = fetchedModels.value.filter((item) => modelSelectChecks.value[item.model])
  cfg.verified = cfg.models.length > 0
  modelSelectVisible.value = false
  ElMessage.success(tLabel(`已选择 ${cfg.models.length} 个模型`, `${cfg.models.length} models selected`))
}

function removeProviderModel(name) {
  const cfg = activeProviderCfg.value
  cfg.models = cfg.models.filter((m) => m.model !== name)
  if (cfg.models.length === 0) cfg.verified = false
}

/** 清除当前服务商配置（API Key、模型列表、验证状态） */
function clearProviderConfig() {
  const def = activeProviderDef.value
  providerConfigs.value[def.key] = {
    api_key: '',
    base_url: def.defaultBaseUrl || '',
    models: [],
    verified: false,
  }
  ElMessage.success(tLabel(`已清除 ${def.name} 配置`, `${def.name} configuration cleared`))
}

function resetDefaults() {
  providerConfigs.value = buildDefaultProviderConfigs()
  activeProviderKey.value = 'qwen'
  ElMessage.success(tLabel('已恢复默认模型配置', 'Default model configuration restored'))
}

function openModelConfigDialog() {
  if (!ensureLoggedIn()) return
  modelConfigDialogVisible.value = true
}

function resetHomeSettings() {
  langSwitch.value = true
  themeSwitch.value = false
  resetDefaults()
}


function isFiniteCoord(lat, lng) {
  return Number.isFinite(Number(lat)) && Number.isFinite(Number(lng))
}

function buildThreeDGlobeData(geocodeItems) {
  const list = Array.isArray(geocodeItems) ? geocodeItems : []
  const pointsData = []
  const pointMeta = []

  for (const item of list) {
    const lng = Number(item?.lng)
    const lat = Number(item?.lat)
    const count = Number(item?.count) || 0
    if (!Number.isFinite(lng) || !Number.isFinite(lat)) continue
    const org = item?.organization || item?.org || ''
    const city = item?.City1 || item?.city || ''
    const country = item?.country || ''
    const name = item?.name || org || city || country || 'Unknown'
    pointsData.push([lng, lat, count])
    pointMeta.push({
      name,
      country,
      city,
      organization: org,
      lng,
      lat,
      count,
    })
  }

  return { pointsData, pointMeta }
}

function getPointColor(type) {
  if (type === '总部') return '#ff5b4f'
  if (type === '办事处') return '#37a2ff'
  return '#36d399'
}

function truncateThreeDLabelName(name) {
  const text = typeof name === 'string' ? name.trim() : ''
  if (!text) return ''
  if (text.length <= THREE_D_LABEL_MAX_CHARS) return text
  return `${text.slice(0, THREE_D_LABEL_MAX_CHARS - 1)}…`
}

function getThreeDLabelDensityProfile(distanceValue) {
  const distance = Number.isFinite(Number(distanceValue)) ? Number(distanceValue) : DEFAULT_THREE_D_VIEW_CONTROL.distance
  if (distance >= 185) return { level: 0, maxLabels: Infinity, cellSize: 0, showAll: true }
  if (distance >= 155) return { level: 1, maxLabels: Infinity, cellSize: 0, showAll: true }
  if (distance >= 130) return { level: 2, maxLabels: Infinity, cellSize: 0, showAll: true }
  if (distance >= 110) return { level: 3, maxLabels: Infinity, cellSize: 0, showAll: true }
  if (distance >= 90) return { level: 4, maxLabels: Infinity, cellSize: 0, showAll: true }
  if (distance >= 72) return { level: 5, maxLabels: Infinity, cellSize: 0, showAll: true }
  return { level: 6, maxLabels: Infinity, cellSize: 0, showAll: true }
}

function buildThreeDVisibleLabelIndexSet(points, distanceValue) {
  const profile = getThreeDLabelDensityProfile(distanceValue)
  const safePoints = Array.isArray(points) ? points : []
  return { indexSet: new Set(safePoints.map((_, index) => index)), profile }
}

function syncThreeDViewState(partial = {}) {
  const nextDistance = Number(partial?.distance)
  threeDViewState.value = {
    distance: Number.isFinite(nextDistance) ? nextDistance : threeDViewState.value.distance,
    alpha: Number.isFinite(Number(partial?.alpha)) ? Number(partial.alpha) : threeDViewState.value.alpha,
    beta: Number.isFinite(Number(partial?.beta)) ? Number(partial.beta) : threeDViewState.value.beta,
    center: Array.isArray(partial?.center) ? [...partial.center] : threeDViewState.value.center,
  }
}

function buildThreeDViewControlOption() {
  const current = threeDViewState.value || {}
  return {
    autoRotate: DEFAULT_THREE_D_VIEW_CONTROL.autoRotate,
    autoRotateSpeed: DEFAULT_THREE_D_VIEW_CONTROL.autoRotateSpeed,
    minDistance: DEFAULT_THREE_D_VIEW_CONTROL.minDistance,
    maxDistance: DEFAULT_THREE_D_VIEW_CONTROL.maxDistance,
    rotateSensitivity: DEFAULT_THREE_D_VIEW_CONTROL.rotateSensitivity,
    zoomSensitivity: DEFAULT_THREE_D_VIEW_CONTROL.zoomSensitivity,
    panSensitivity: DEFAULT_THREE_D_VIEW_CONTROL.panSensitivity,
    distance: Number.isFinite(Number(current.distance)) ? Number(current.distance) : DEFAULT_THREE_D_VIEW_CONTROL.distance,
    ...(Number.isFinite(Number(current.alpha)) ? { alpha: Number(current.alpha) } : {}),
    ...(Number.isFinite(Number(current.beta)) ? { beta: Number(current.beta) } : {}),
    ...(Array.isArray(current.center) ? { center: [...current.center] } : { targetCoord: [...DEFAULT_THREE_D_VIEW_CONTROL.targetCoord] }),
  }
}

function bindThreeDChartEvents() {
  if (!threeDMapChart) return
  if (threeDCameraChangeHandler) {
    threeDMapChart.off('globeChangeCamera', threeDCameraChangeHandler)
  }
  threeDCameraChangeHandler = (params = {}) => {
    syncThreeDViewState(params)
    threeDLabelDetailLevel.value = getThreeDLabelDensityProfile(params?.distance).level
  }
  threeDMapChart.on('globeChangeCamera', threeDCameraChangeHandler)
}


function shouldLoadThreeDEdges() {
  return Boolean(
    activeView.value === '三维地图'
    && threeDRenderMode.value === 'point'
    && mapEdgeVisible.value
    && !affiliationMode.value
    && (demoMode.value || effectiveSessionId.value)
    && ((parseField.value === 'C1' && ['country', 'org', 'city'].includes(activeTier.value)) || (parseField.value === 'C3' && activeTier.value === 'org'))
  )
}

function getThreeDEdgesCacheKey() {
  return JSON.stringify({
    demoMode: demoMode.value,
    sessionId: effectiveSessionId.value || '',
    field: parseField.value,
    tier: activeTier.value,
    mode: threeDRenderMode.value,
  })
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value))
}

function lngLatToUnitVector(lng, lat) {
  const lngRad = (Number(lng) || 0) * Math.PI / 180
  const latRad = (Number(lat) || 0) * Math.PI / 180
  const cosLat = Math.cos(latRad)
  return [
    cosLat * Math.cos(lngRad),
    Math.sin(latRad),
    cosLat * Math.sin(lngRad),
  ]
}

function unitVectorToLngLat(vector) {
  const [x, y, z] = Array.isArray(vector) ? vector : [0, 0, 0]
  const lng = Math.atan2(z, x) * 180 / Math.PI
  const lat = Math.atan2(y, Math.sqrt(x * x + z * z)) * 180 / Math.PI
  return [lng, lat, 0]
}

function normalizeVector(vector) {
  const [x, y, z] = Array.isArray(vector) ? vector : [0, 0, 0]
  const len = Math.sqrt(x * x + y * y + z * z) || 1
  return [x / len, y / len, z / len]
}

function buildSurfaceCurveCoords(source, target) {
  const start = lngLatToUnitVector(source.lng, source.lat)
  const end = lngLatToUnitVector(target.lng, target.lat)
  const dot = clamp(start[0] * end[0] + start[1] * end[1] + start[2] * end[2], -1, 1)
  const omega = Math.acos(dot)
  const sinOmega = Math.sin(omega)
  const stepCount = Math.max(24, Math.min(96, Math.ceil((omega * 180 / Math.PI) / 3)))
  const coords = []

  for (let i = 0; i <= stepCount; i += 1) {
    const t = i / stepCount
    let point
    if (sinOmega < 1e-6) {
      point = normalizeVector([
        start[0] * (1 - t) + end[0] * t,
        start[1] * (1 - t) + end[1] * t,
        start[2] * (1 - t) + end[2] * t,
      ])
    } else {
      const startScale = Math.sin((1 - t) * omega) / sinOmega
      const endScale = Math.sin(t * omega) / sinOmega
      point = [
        start[0] * startScale + end[0] * endScale,
        start[1] * startScale + end[1] * endScale,
        start[2] * startScale + end[2] * endScale,
      ]
    }
    coords.push(unitVectorToLngLat(point))
  }

  return coords
}

async function ensureThreeDEdgesLoaded(force = false) {
  if (!shouldLoadThreeDEdges()) {
    threeDEdges.value = []
    threeDEdgesSignature.value = ''
    return
  }
  const cacheKey = getThreeDEdgesCacheKey()
  if (!force && threeDEdgesSignature.value === cacheKey) return
  try {
    const edgeField = parseField.value === 'C3' ? 'C3' : 'C1'
    const res = demoMode.value
      ? await getDemoMatrix(DEMO_MATRIX_API_MAP[edgeField]?.[activeTier.value])
      : await getEntityMatrix(effectiveSessionId.value, edgeField, activeTier.value, 220, 0)
    const nodes = Array.isArray(res.data?.nodes) ? res.data.nodes : []
    const nodeMap = new Map(
      nodes
        .filter((node) => Number.isFinite(Number(node?.lng)) && Number.isFinite(Number(node?.lat)))
        .map((node) => [node.name, { lng: Number(node.lng), lat: Number(node.lat) }])
    )
    const rawEdges = (Array.isArray(res.data?.edges) ? res.data.edges : [])
      .filter((edge) => Number(edge?.weight) > 0)
      .sort((a, b) => (Number(b?.weight) || 0) - (Number(a?.weight) || 0))
      .slice(0, 320)
    const { minW, maxW } = edgeWeightRange(rawEdges)

    threeDEdges.value = rawEdges.map((edge) => {
      const source = nodeMap.get(edge?.source)
      const target = nodeMap.get(edge?.target)
      if (!source || !target) return null
      const weight = Number(edge?.weight) || 0
      const baseWidth = edgeWeightToBaseWidth(weight, minW, maxW, {
        minPx: 0.5,
        maxPx: 2.6,
        power: 0.55,
      })
      return {
        fromName: edge?.source || '',
        toName: edge?.target || '',
        value: weight,
        baseWidth,
        coords: buildSurfaceCurveCoords(source, target),
      }
    }).filter(Boolean)
    threeDEdgesSignature.value = cacheKey
  } catch (_) {
    threeDEdges.value = []
    threeDEdgesSignature.value = cacheKey
  }
}

async function renderThreeDMap() {
  if (renderingThreeD) return
  if (activeView.value !== '三维地图' || !hasThreeDData.value || !threeDMapEl.value) {
    vizLoading.value = false
    return
  }
  renderingThreeD = true
  if (activeView.value !== '三维地图' || !threeDMapEl.value) {
    vizLoading.value = false
    renderingThreeD = false
    return
  }

  if (threeDMapChart && threeDMapChart.getDom() !== threeDMapEl.value) {
    disposeThreeDMap()
  }
  if (!threeDMapChart) {
    threeDMapChart = echarts.init(threeDMapEl.value)
    bindThreeDChartEvents()
  }

  const { pointsData, pointMeta } = buildThreeDGlobeData(threeDItems.value)
  const safePointsRaw = Array.isArray(pointsData) ? pointsData : []
  const safePointMetaRaw = Array.isArray(pointMeta) ? pointMeta : []
  const maxBars = 300
  const safePoints = safePointsRaw
    .map((point, index) => ({ point, meta: safePointMetaRaw[index] || null }))
    .sort((a, b) => (Number(b?.point?.[2]) || 0) - (Number(a?.point?.[2]) || 0))
    .slice(0, maxBars)
  const maxCount = safePoints.reduce((m, item) => Math.max(m, Number(item?.point?.[2]) || 0), 0)
  const safeMax = Math.max(1, maxCount)
  const baseHeight = 4
  const extraHeight = safeMax > 200 ? 86 : 70

  const getColumnHeight = (count) => {
    if (count <= 0) return baseHeight
    const ratio = count / safeMax
    return baseHeight + Math.pow(ratio, 0.68) * extraHeight
  }

  const currentLabelDistance = threeDViewState.value?.distance
  const { indexSet: visibleLabelIndexSet, profile: visibleLabelProfile } = buildThreeDVisibleLabelIndexSet(safePoints, currentLabelDistance)
  threeDLabelDetailLevel.value = visibleLabelProfile.level

  const buildLabelText = (labelName, index) => {
    if (!visibleLabelIndexSet.has(index)) return ''
    return truncateThreeDLabelName(labelName)
  }

  const columnBars = safePoints.map(({ point, meta }, i) => {
    const count = Number(point?.[2]) || 0
    const height = getColumnHeight(count)
    const labelName = meta?.name || meta?.organization || meta?.city || meta?.country || `No.${i + 1}`
    const labelText = buildLabelText(labelName, i)
    return {
      name: labelName,
      labelText,
      label: { show: Boolean(mapLabelVisible.value && labelText) },
      value: [point[0], point[1], height],
      count,
    }
  })
  try {
    const threeDDark = themeSwitch.value
    const baseMapTexture = ensureThreeDBaseMapTexture(threeDDark)
    const opacityValue = Math.min(100, Math.max(1, Number(mapNodeOpacity.value || DEFAULT_MAP_NODE_OPACITY)))
    const mainOpacity = Math.max(0, 1 - opacityValue / 100)
    const mainColor = typeof threeDBarColor.value === 'string' && threeDBarColor.value.trim()
      ? threeDBarColor.value
      : DEFAULT_THREE_D_BAR_COLOR
    const dotSizeValue = Math.min(100, Math.max(1, Number(mapNodeSize.value || DEFAULT_MAP_NODE_SIZE)))
    const dotScale = 0.45 + (dotSizeValue / 100) * 1.55
    const isFixed = mapSizeMode.value === 'fixed'
    const maxCount = safeMax
    const dotData = safePoints.map(({ point, meta }, i) => {
      const count = Number(point?.[2]) || 0
      const ratio = Math.pow(count / maxCount, 0.65)
      const size = isFixed
        ? Math.max(6, dotSizeValue * 0.25)
        : Math.max(6, (6 + ratio * 22) * dotScale)
      const labelName = meta?.name || meta?.organization || meta?.city || meta?.country || `No.${i + 1}`
      const labelText = buildLabelText(labelName, i)
      return {
        name: labelName,
        value: [point[0], point[1], 0],
        count,
        symbolSize: size,
        labelText,
        label: { show: Boolean(mapLabelVisible.value && labelText) },
      }
    })

    let series = []
    if (threeDRenderMode.value === 'point') {
      await ensureThreeDEdgesLoaded()
      const edgeWidthValue = Math.min(20, Math.max(1, Number(mapEdgeWidth.value || DEFAULT_MAP_EDGE_WIDTH)))
      const edgeWidthRatio = Math.pow(edgeWidthValue / 20, 1.08)
      const edgeWidthScale = 0.24 + edgeWidthRatio * 4.1
      const edgeOpacityValue = Math.min(100, Math.max(1, Number(mapEdgeOpacity.value || getDefaultMapEdgeOpacity())))
      const edgeOpacity = mapEdgeVisible.value ? Math.max(0, 1 - edgeOpacityValue / 100) : 0
      const renderedEdges = (Array.isArray(threeDEdges.value) ? threeDEdges.value : []).map((item) => {
        const width = Math.max(0.35, (Number(item?.baseWidth) || 0.5) * edgeWidthScale)
        return {
          ...item,
          lineStyle: { width },
        }
      })
      series = [
        {
          name: '节点',
          type: 'scatter3D',
          coordinateSystem: 'globe',
          data: dotData,
          symbol: 'circle',
          symbolSize: (data) => Number(data?.symbolSize) || 8,
          itemStyle: {
            color: mainColor,
            opacity: mainOpacity,
          },
          label: {
            show: Boolean(mapLabelVisible.value),
            position: 'top',
            distance: 8,
            formatter: (params) => params?.data?.labelText || '',
            fontSize: 12,
            color: threeDDark ? '#ffffff' : '#000000',
          },
          silent: true,
          zlevel: 3,
        },
      ]
      if (mapEdgeVisible.value && renderedEdges.length > 0) {
        series.unshift(
          {
            name: '连线',
            type: 'lines3D',
            coordinateSystem: 'globe',
            polyline: true,
            data: renderedEdges,
            blendMode: 'source-over',
            lineStyle: {
              color: mapEdgeColor.value || getDefaultMapEdgeColor(),
              opacity: edgeOpacity,
              curveness: 0,
            },
            effect: {
              show: false,
            },
            silent: true,
            zlevel: 1,
          },
        )
      }
    } else {
      series = [
        {
          name: '柱体',
          type: 'bar3D',
          coordinateSystem: 'globe',
          data: columnBars,
          bevelSize: 0,
          minHeight: 0.6,
          barSize: Math.max(0.35, Number(threeDBarSize.value || DEFAULT_THREE_D_BAR_SIZE) / 40),
          shading: 'color',
          itemStyle: {
            color: mainColor,
            opacity: Math.max(0.01, mainOpacity),
          },
          label: {
            show: Boolean(mapLabelVisible.value),
            position: 'top',
            distance: 2,
            opacity: 1,
            formatter: (params) => params?.data?.labelText || '',
            fontSize: 12,
            color: threeDDark ? '#ffffff' : '#000000',
          },
          silent: true,
        },
      ]
    }
    threeDMapChart.setOption({
      animation: false,
      backgroundColor: threeDDark ? '#161f31' : 'transparent',
      tooltip: { show: false },
      globe: {
        show: true,
        baseTexture: baseMapTexture,
        baseColor: threeDDark ? '#435066' : '#f7f7f8',
        shading: 'color',
        environment: threeDDark ? '#161f31' : '#ffffff',
        light: {
          main: { intensity: 0, shadow: false },
          ambient: { intensity: 0, shadow: false },
        },
        atmosphere: { show: false },
        viewControl: buildThreeDViewControlOption(),
      },
      series,
    }, true)
  } finally {
    threeDMapChart.resize()
    vizLoading.value = false
    renderingThreeD = false
  }
}

function ensureThreeDBaseMapTexture(isDark) {
  if (typeof document === 'undefined') return null
  const width = 4096
  const height = 2048
  if (!threeDBaseMapTextureCanvas) {
    threeDBaseMapTextureCanvas = document.createElement('canvas')
  }
  threeDBaseMapTextureCanvas.width = width
  threeDBaseMapTextureCanvas.height = height
  const ctx = threeDBaseMapTextureCanvas.getContext('2d')
  if (!ctx) return threeDBaseMapTextureCanvas

  const oceanColor = isDark ? '#435066' : '#f7f7f8'
  const landColor = isDark ? '#8d98ae' : '#d2d0d0'
  const borderColor = 'rgba(0,0,0,0)'
  const lineWidth = 0

  ctx.clearRect(0, 0, width, height)
  ctx.fillStyle = oceanColor
  ctx.fillRect(0, 0, width, height)
  ctx.fillStyle = landColor
  ctx.strokeStyle = borderColor
  ctx.lineWidth = lineWidth
  ctx.lineJoin = 'round'
  ctx.lineCap = 'round'

  const features = Array.isArray(world?.features) ? world.features : []
  for (const feature of features) {
    const geometry = feature?.geometry
    if (!geometry) continue
    drawWorldGeometryToCanvas(ctx, geometry, width, height)
  }
  return threeDBaseMapTextureCanvas.toDataURL('image/png')
}

function drawWorldGeometryToCanvas(ctx, geometry, width, height) {
  if (!geometry) return
  const { type, coordinates } = geometry
  if (type === 'Polygon') {
    drawWorldPolygonToCanvas(ctx, coordinates, width, height)
    return
  }
  if (type === 'MultiPolygon') {
    for (const polygon of coordinates || []) {
      drawWorldPolygonToCanvas(ctx, polygon, width, height)
    }
  }
}

function drawWorldPolygonToCanvas(ctx, polygon, width, height) {
  if (!Array.isArray(polygon) || polygon.length === 0) return
  ctx.beginPath()
  for (const ring of polygon) {
    drawWorldRingToCanvas(ctx, ring, width, height)
  }
  ctx.fill('evenodd')
  ctx.stroke()
}

function drawWorldRingToCanvas(ctx, ring, width, height) {
  if (!Array.isArray(ring) || ring.length === 0) return
  let started = false
  for (const point of ring) {
    const [x, y] = projectLonLatToTexture(point, width, height)
    if (!started) {
      ctx.moveTo(x, y)
      started = true
    } else {
      ctx.lineTo(x, y)
    }
  }
  if (started) ctx.closePath()
}

function projectLonLatToTexture(point, width, height) {
  const lon = Number(point?.[0]) || 0
  const lat = Number(point?.[1]) || 0
  const x = ((lon + 180) / 360) * width
  const y = ((90 - lat) / 180) * height
  return [x, y]
}

function disposeThreeDMap() {
  if (!threeDMapChart) return
  if (threeDCameraChangeHandler) {
    threeDMapChart.off('globeChangeCamera', threeDCameraChangeHandler)
    threeDCameraChangeHandler = null
  }
  threeDMapChart.dispose()
  threeDMapChart = null
  syncThreeDViewState({
    distance: DEFAULT_THREE_D_VIEW_CONTROL.distance,
    alpha: null,
    beta: null,
    center: null,
  })
  threeDLabelDetailLevel.value = -1
}

function disposeThreeDBaseMapTexture() {
  threeDBaseMapTextureCanvas = null
}

function handleThreeDResize() {
  if (activeView.value === '三维地图' && threeDMapChart) {
    threeDMapChart.resize()
  }
}

function buildConfigs() {
  const configs = []
  for (const p of PROVIDER_DEFS) {
    const cfg = providerConfigs.value[p.key]
    for (const m of cfg?.models || []) {
      configs.push({
        type: 'official',
        provider: p.backendProvider,
        api_key: cfg.api_key,
        base_url: cfg.base_url,
        model: m.model,
        name: PROVIDER_DEFS.filter((d) => providerConfigs.value[d.key]?.models?.length).length > 1
          ? `${p.name}:${m.model}`
          : m.model,
      })
    }
  }
  if (configs.length === 0) {
    return [{
      type: 'official',
      provider: 'Custom',
      api_key: '',
      base_url: '',
      model: 'rule',
      name: 'rule',
    }]
  }
  return configs
}

function extractDemoList(payload) {
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload?.items)) return payload.items
  if (Array.isArray(payload?.records)) return payload.records
  if (Array.isArray(payload?.data)) return payload.data
  return []
}

function normalizeDemoCountRows(payload) {
  const rows = extractDemoList(payload)
  return rows.map((item, index) => ({
    rank: index + 1,
    name: item?.name || item?.country || item?.city || item?.organization || item?.org || '-',
    count: Number(item?.count ?? item?.value ?? item?.num ?? 0) || 0,
    lat: item?.lat ?? item?.latitude ?? item?.Latitude ?? null,
    lng: item?.lng ?? item?.longitude ?? item?.Longitude ?? null,
    address: item?.address || item?.raw || '',
  }))
}

async function loadDemoRawTable() {
  demoRawTableLoading.value = true
  try {
    const res = await getDemoData('demoList')
    const rows = extractDemoList(res.data || {})
    demoRawTableRows.value = rows
  } finally {
    demoRawTableLoading.value = false
  }
}

async function loadDemoParseRows(page = 1) {
  const field = parseField.value
  const tier = activeTier.value
  const listApiName = DEMO_LIST_API_MAP[field]?.[tier]
  if (!listApiName) {
    geoRecords.value = []
    geoTotal.value = 0
    return
  }
  const res = await getDemoData(listApiName)
  markDemoTierAvailable(field, tier)
  const srcRows = extractDemoList(res.data || {})
  const rows = parseField.value === 'C3'
    ? srcRows.map((item, index) => ({
      rank: index + 1,
      Organization: item?.Organization || item?.organization || item?.org || '',
      C3_Latitude: item?.C3_Latitude ?? item?.Latitude ?? item?.latitude ?? null,
      C3_Longitude: item?.C3_Longitude ?? item?.Longitude ?? item?.longitude ?? null,
      address: item?.address || item?.C3 || item?.raw || '',
    }))
    : normalizeDemoCountRows(res.data || {})
  geoTotal.value = rows.length
  const start = (page - 1) * geoPageSize.value
  const end = start + geoPageSize.value
  geoRecords.value = rows.slice(start, end)
}

async function doUpload() {
  if (!ensureLoggedIn()) return
  if (!canStartUpload.value) {
    ElMessage.warning(tLabel('请上传数据文件或打开案例。', 'Please upload a data file or open a demo.'))
    return
  }
  const uploadables = fileList.value.filter((f) => Boolean(f?.raw))
  if (uploadables.length === 0) {
    ElMessage.warning(tLabel('请重新选择文件后再开始加载。', 'Please reselect the file and load again.'))
    triggerUploadPicker()
    return
  }

  loading.value = true
  uploadProgress.value = 10

  const fd = new FormData()
  for (const f of uploadables) {
    fd.append('files', f.raw)
  }

  try {
    uploadProgress.value = 45
    const res = await uploadWos(fd)
    uploadProgress.value = 100

    // 先清空上一会话的画布/表格状态，再写入新 session
    demoMode.value = false
    customDemoActive.value = false
    geoRecords.value = []
    rankRecords.value = []
    threeDItems.value = []
    threeDEdges.value = []
    threeDEdgesSignature.value = ''
    geoTotal.value = 0
    geoPage.value = 1
    vizMeta.value = { total: null, source: '', tier: '', displayCount: null }
    parseProgress.value = 0
    parseLogs.value = []
    parseSummary.value = null
    parseTierSummaries.value = []
    parseSummaryByField.value = { C1: null, C3: null }
    parseTierSummariesByField.value = { C1: [], C3: [] }
    parseRunning.value = false
    parseResultDialogVisible.value = false
    parseProgressDialogVisible.value = false
    parsedFieldAvailability.value = { C1: false, C3: false }
    vizAutoLoadEnabled.value = false

    latestRecordCount.value = res.data.record_count
    savedUploadNames.value = Array.isArray(res.data?.files) ? res.data.files : fileList.value.map((f) => f?.name).filter(Boolean)

    const fileType = res.data?.file_type
    const preParsed = Boolean(res.data?.pre_parsed)

    if (fileType === 'affiliation') {
      affiliationMode.value = true
      affiliationSubtypes.value = [...new Set(res.data?.affiliation_subtypes || ['affiliation_org'])]
      if (affiliationSubtypes.value.length > 0) {
        const firstType = affiliationSubtypes.value[0]
        if (firstType === 'affiliation_country') vizType.value = 'country'
        else if (firstType === 'affiliation_org') vizType.value = 'org'
        else if (firstType === 'affiliation_city') vizType.value = 'city'
      } else {
        vizType.value = 'org'
      }
      activeView.value = '平面地图'

      // 含经纬度的本地地址：与自定义案例一致，直接可视化；否则等待启动解析
      vizAutoLoadEnabled.value = preParsed
      latestSessionId.value = res.data.session_id
      emit('session-created', {
        sessionId: res.data.session_id,
        recordCount: res.data.record_count,
      })

      if (preParsed) {
        parseProgress.value = 100
        await refreshAffiliationResults(1)
        await loadThreeDItems()
        await nextTick()
        vizReloadKey.value += 1
        if (activeView.value === '三维地图') {
          await renderThreeDMap()
        }
        ElMessage.success(tLabel(
          `加载成功，共 ${res.data.record_count} 条记录（已含坐标，可直接查看地图）。`,
          `Loaded ${res.data.record_count} records with coordinates; maps are ready.`,
        ))
      } else {
        vizReloadKey.value += 1
        ElMessage.success(tLabel(
          `加载成功，共 ${res.data.record_count} 条记录。请点击「启动解析」开始处理。`,
          `Loaded ${res.data.record_count} records. Click Start Parse to continue.`,
        ))
      }

      // 原始数据表随新 session 刷新（不强制弹窗打扰；用户点「打开表格」即可）
      rawDataDialogVisible.value = false
      return
    }

    // WoS 模式
    affiliationMode.value = false
    affiliationSubtypes.value = []
    vizAutoLoadEnabled.value = false
    latestSessionId.value = res.data.session_id
    emit('session-created', {
      sessionId: res.data.session_id,
      recordCount: res.data.record_count,
    })
    vizReloadKey.value += 1
    rawDataDialogVisible.value = true
    ElMessage.success(tLabel(
      `加载成功，共 ${res.data.record_count} 条记录`,
      `Loaded ${res.data.record_count} records`,
    ))
  } catch (e) {
    const msg = e.response?.data?.detail || e.message
    ElMessage.error(tLabel('加载失败：', 'Load failed: ') + msg)
  } finally {
    loading.value = false
  }
}

async function openRawDataDialog() {
  if (!ensureLoggedIn()) return
  if (demoMode.value) {
    try {
      await loadDemoRawTable()
    } catch (e) {
      ElMessage.error(tLabel('加载案例表格失败：', 'Failed to load demo table: ') + (e.response?.data?.detail || e.message))
      return
    }
    rawDataDialogVisible.value = true
    return
  }
  if (!effectiveSessionId.value) {
    ElMessage.warning(tLabel('请上传数据文件或打开案例。', 'Please upload a data file or open a demo.'))
    return
  }
  rawDataDialogVisible.value = true
}

function openDemo() {
  if (!ensureLoggedIn()) return
  demoChoiceVisible.value = true
}

async function openCustomDemo() {
  demoChoiceVisible.value = false
  demoLoading.value = true
  try {
    const res = await createCustomDemoSession()
    fileList.value = []
    // 默认案例不占用上传文件框展示
    savedUploadNames.value = []
    demoMode.value = false
    customDemoActive.value = true
    parsedFieldAvailability.value = { C1: false, C3: false }
    affiliationMode.value = true
    affiliationSubtypes.value = [...new Set(res.data?.affiliation_subtypes || ['affiliation_org'])]
    vizType.value = 'org'
    activeView.value = '平面地图'
    geoPage.value = 1
    rankRecords.value = []
    threeDItems.value = []
    threeDEdges.value = []
    threeDEdgesSignature.value = ''
    parseProgress.value = 0
    parseLogs.value = []
    parseSummary.value = null
    parseTierSummaries.value = []
    parseSummaryByField.value = { C1: null, C3: null }
    parseTierSummariesByField.value = { C1: [], C3: [] }
    parseRunning.value = false
    rawDataDialogVisible.value = false
    parseResultDialogVisible.value = false
    parseProgressDialogVisible.value = false
    vizMeta.value = { total: null, source: '', tier: '', displayCount: null }

    const preParsed = Boolean(res.data?.pre_parsed)
    // 先打开自动加载，再写入 session，避免 VizView 竞态卡在 loading
    vizAutoLoadEnabled.value = Boolean(preParsed)
    latestRecordCount.value = res.data.record_count
    latestSessionId.value = res.data.session_id
    emit('session-created', {
      sessionId: res.data.session_id,
      recordCount: res.data.record_count,
    })

    if (preParsed) {
      parseProgress.value = 100
      await refreshAffiliationResults(1)
      await loadThreeDItems()
      await nextTick()
      vizReloadKey.value += 1
      if (activeView.value === '三维地图') {
        await renderThreeDMap()
      }
    }
    ElMessage.success(tLabel('案例数据加载完成', 'Demo data loaded'))
  } catch (e) {
    ElMessage.error(tLabel('加载自定义案例失败：', 'Failed to load custom demo: ') + (e.response?.data?.detail || e.message))
  } finally {
    demoLoading.value = false
  }
}

async function openWosDemo() {
  demoChoiceVisible.value = false
  demoLoading.value = true
  try {
    fileList.value = []
    savedUploadNames.value = []
    demoMode.value = true
    customDemoActive.value = false
    resetDemoTierAvailability()
    demoRawTableLoading.value = false
    demoRawTableRows.value = []
    vizAutoLoadEnabled.value = true
    latestSessionId.value = ''
    latestRecordCount.value = 0
    affiliationMode.value = false
    affiliationSubtypes.value = []
    parseField.value = 'C1'
    c1TierChecks.value = { country: false, org: false, city: false }
    vizType.value = DEMO_DEFAULT_C1_TIER
    activeView.value = '平面地图'
    geoPage.value = 1
    rankRecords.value = []
    threeDItems.value = []
  threeDEdges.value = []
    threeDEdgesSignature.value = ''
    parseProgress.value = 0
    parseLogs.value = []
    parseSummary.value = null
    parseTierSummaries.value = []
    parseSummaryByField.value = { C1: null, C3: null }
    parseTierSummariesByField.value = { C1: [], C3: [] }
    parseRunning.value = false
    vizMeta.value = { total: null, source: '', tier: '', displayCount: null }
    rawDataDialogVisible.value = false
    parseResultDialogVisible.value = false
    parseProgressDialogVisible.value = false
    emit('session-created', { sessionId: '', recordCount: 0 })
    const res = await getDemoData(DEMO_COUNT_API_MAP.C1[DEMO_DEFAULT_C1_TIER])
    const rows = normalizeDemoCountRows(res.data || {})
    markDemoTierAvailable('C1', DEMO_DEFAULT_C1_TIER)
    geoTotal.value = rows.length
    geoRecords.value = rows.slice(0, geoPageSize.value)
    vizReloadKey.value += 1
    ElMessage.success(tLabel('案例数据加载完成', 'Demo data loaded'))
  } catch (e) {
    demoMode.value = false
    ElMessage.error(tLabel('加载案例失败：', 'Failed to load demo: ') + (e.response?.data?.detail || e.message))
  } finally {
    demoLoading.value = false
  }
}

function triggerUploadPicker() {
  if (!ensureLoggedIn()) return
  const input = uploadRef.value?.$el?.querySelector?.('input[type="file"]')
  if (input) input.click()
}

async function onSelectView(view) {
  if (!ensureLoggedIn()) return
  if (view === '数据列表') {
    // Affiliation 模式下直接打开弹窗，WoS 模式检查数据
    if (affiliationMode.value) {
      geoPage.value = 1
      await refreshAffiliationResults(1)
      if (geoRecords.value.length === 0) {
        ElMessage.warning('暂无解析结果数据')
        return
      }
      parseResultDialogVisible.value = true
    } else {
      openParseResultDialog()
    }
    return
  }
  activeView.value = view
  if (view === '三维地图') {
    vizLoading.value = true
    if (!effectiveSessionId.value) return
    if (threeDItems.value.length === 0) await loadThreeDItems()
    await nextTick()
    await renderThreeDMap()
    vizLoading.value = false
    return
  }
  vizLoading.value = false
}

async function doParse() {
  if (!ensureLoggedIn()) return
  // WoS / 自定义案例：案例数据已就绪，无需再点解析（文案与主题一致）
  if (demoMode.value || customDemoActive.value) {
    ElMessage.warning(tLabel(
      '案例数据已加载完成，无需启动解析。',
      'Demo data is already loaded; parsing is not required.',
    ))
    return
  }
  if (!effectiveSessionId.value) {
    ElMessage.warning(tLabel(
      '请先上传数据文件或打开案例。',
      'Please upload a data file or open a demo first.',
    ))
    return
  }

  // 启用 viz 自动加载
  vizAutoLoadEnabled.value = true

  // Affiliation 模式：若已有匹配结果，先让用户选择沿用缓存还是大模型重算
  if (affiliationMode.value) {
    const reuseExisting = await askAffiliationParseMode()
    if (reuseExisting === null) return
    parseRunning.value = true
    parseProgress.value = 0
    parseLogs.value = []
    parseProgressDialogVisible.value = true
    await startAffiliationParse({ skipCache: reuseExisting === false })
    return
  }

  // WoS 模式：需要勾选解析项
  if (parseField.value === 'C1' && selectedC1Tiers.value.length === 0) {
    ElMessage.warning('请至少勾选一个解析项')
    return
  }

  // C1 分层 / C3：可先查固定参考库（机构→坐标），让用户选择增量匹配（沿用库内坐标）还是全量重算
  let tierSkipCache = false
  if ((parseField.value === 'C1'
        && selectedC1Tiers.value.some((t) => t === 'country' || t === 'org'))
      || parseField.value === 'C3') {
    const reuseExisting = await askAffiliationParseMode()
    if (reuseExisting === null) return
    tierSkipCache = reuseExisting === false
  }

  parseRunning.value = true
  parseProgress.value = 0
  parseLogs.value = []
  parseProgressDialogVisible.value = true

  try {
    if (parseField.value === 'C3') {
      await startParseC1(effectiveSessionId.value, buildConfigs(), batchSize.value, 'C3', tierSkipCache, currentLang())
      const finished = await pollProgress()
      if (!finished) return
      parsedFieldAvailability.value = { ...parsedFieldAvailability.value, C3: true }
      vizType.value = 'org'
      await refreshParseResultData(1)
      await loadThreeDItems()
      vizReloadKey.value += 1
      parseResultDialogVisible.value = true
      return
    }

    await startParseBatchTiers(
      effectiveSessionId.value,
      buildConfigs(),
      batchSize.value,
      'C1',
      selectedC1Tiers.value,
      tierSkipCache,
      currentLang(),
    )
    const finished = await pollProgress()
    if (!finished) return
    parsedFieldAvailability.value = { ...parsedFieldAvailability.value, C1: true }
    if (selectedC1Tiers.value.length > 0) {
      vizType.value = selectedC1Tiers.value[0]
    }
    await refreshParseResultData(1)
    await loadThreeDItems()
    vizReloadKey.value += 1
    parseResultDialogVisible.value = true
  } catch (e) {
    ElMessage.error(tLabel('启动解析失败：', 'Failed to start parse: ') + (e.response?.data?.detail || e.message))
    parseRunning.value = false
    parseProgressDialogVisible.value = false
  }
}

async function doStop() {
  if (!ensureLoggedIn()) return
  if (!effectiveSessionId.value) return
  try {
    await stopParseC1(effectiveSessionId.value, currentLang())
    ElMessage.info(tLabel('停止信号已发送，等待当前请求完成...', 'Stop signal sent, waiting for the current request to finish...'))
  } catch (e) {
    ElMessage.error(tLabel('停止失败：', 'Failed to stop: ') + (e.response?.data?.detail || e.message))
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function normalizeTierLogs(tiers) {
  if (!tiers || typeof tiers !== 'object') return []
  const rows = []
  // 按固定顺序拼接各层完整日志，避免 Object.entries 顺序不确定或旧日志被截断后“被覆盖”
  const order = [
    'country', 'affiliation_country',
    'org', 'affiliation_org',
    'city', 'affiliation_city',
    'C1', 'C3',
  ]
  const seen = new Set()
  const appendTier = (tierName) => {
    if (seen.has(tierName)) return
    seen.add(tierName)
    const logs = Array.isArray(tiers?.[tierName]?.logs) ? tiers[tierName].logs : []
    for (const line of logs) {
      const text = String(line || '').trim()
      if (!text) continue
      rows.push(`[${tierName}] ${text}`)
    }
  }
  for (const tierName of order) appendTier(tierName)
  for (const tierName of Object.keys(tiers)) appendTier(tierName)
  return rows
}

function normalizeSummarySource(summarySource) {
  if (!summarySource || typeof summarySource !== 'object') return null
  const hasKnownMetric = ['total', 'success', 'failed', 'success_rate'].some((key) => summarySource[key] !== undefined && summarySource[key] !== null)
  if (!hasKnownMetric) return null
  return {
    total: Number(summarySource.total) || 0,
    success: Number(summarySource.success) || 0,
    failed: Number(summarySource.failed) || 0,
    successRate: Number(summarySource.success_rate) || 0,
  }
}

function extractParsedFieldAvailability(raw) {
  const data = raw && typeof raw === 'object' ? raw : {}
  const tiers = data.tiers && typeof data.tiers === 'object' ? data.tiers : {}
  const c1Summary = normalizeSummarySource(tiers?.country?.report) || normalizeSummarySource(tiers?.C1?.report)
  const c3Summary = normalizeSummarySource(tiers?.org?.report) || normalizeSummarySource(tiers?.C3?.report)
  return {
    C1: Number(c1Summary?.total) > 0,
    C3: Number(c3Summary?.total) > 0,
  }
}

const TIER_LABELS = {
  country: ['国家 / 地区', 'Country / Region'],
  org: ['机构', 'Organization'],
  city: ['城市', 'City'],
  affiliation_country: ['国家 / 地区', 'Country / Region'],
  affiliation_org: ['机构', 'Organization'],
  affiliation_city: ['城市', 'City'],
}

function tierLabel(tier) {
  const pair = TIER_LABELS[tier]
  return pair ? tLabel(pair[0], pair[1]) : String(tier || '')
}

// 计算占比（相对总数），最多保留 2 位小数
function tierPct(count, total) {
  if (!total || total <= 0) return 0
  return Math.round((Number(count) / Number(total)) * 10000) / 100
}

// 从批量分层进度里按层构建各自的解析汇总（国家 / 机构 / 城市 分别统计）。
// 与解析模式无关：C1 用 country/org/city，affiliation 用 affiliation_*，按存在的键构建，
// 避免因 affiliationMode 标志与实际键名不一致而匹配不到、退回旧的单行格式。
function buildTierSummaries(tiers) {
  if (!tiers || typeof tiers !== 'object') return []
  const order = [
    'country', 'affiliation_country',
    'org', 'affiliation_org',
    'city', 'affiliation_city',
  ]
  const out = []
  for (const tier of order) {
    const s = normalizeSummarySource(tiers?.[tier]?.report)
    if (s && s.total > 0) out.push({ tier, ...s })
  }
  return out
}

function pickSummaryFromTiers(tiers) {
  if (!tiers || typeof tiers !== 'object') return null
  const preferredTiers = affiliationMode.value
    ? ['affiliation', 'affiliation_country', 'affiliation_org', 'affiliation_city']
    : parseField.value === 'C3'
      ? ['org', 'C3']
      : ['country', 'C1']

  for (const tierName of preferredTiers) {
    const summary = normalizeSummarySource(tiers?.[tierName]?.report)
    if (summary && summary.total > 0) return summary
  }

  return null
}

function normalizeProgressPayload(raw) {
  const data = raw && typeof raw === 'object' ? raw : {}
  const isBatch = data.overall_progress !== undefined || data.overall_status !== undefined || data.tiers !== undefined
  if (isBatch) {
    const overall = Number(data.overall_progress)
    const progress = Number.isFinite(overall) ? Math.max(0, Math.min(100, overall)) : 0
    const status = String(data.overall_status || '')
    const topLogs = Array.isArray(data.logs) ? data.logs.map((v) => String(v)).filter((s) => s.trim()) : []
    const tierLogs = normalizeTierLogs(data.tiers)
    // 顶层摘要日志 + 各层完整过程日志（C1 / 本地 affiliation 共用）
    const logs = topLogs.length ? [...topLogs, ...tierLogs] : tierLogs
    const report = data.report && typeof data.report === 'object' ? data.report : null
    const summary = normalizeSummarySource(report?.by_tier?.affiliation)
      || normalizeSummarySource(report)
      || pickSummaryFromTiers(data.tiers)
    // 各层分别统计（国家/机构/城市），供前端按层展示
    const tierSummaries = buildTierSummaries(data.tiers)
    // 分层/批量进度属于 C1（地址列表）任务
    return { progress, status, logs, summary, tierSummaries, field: 'C1' }
  }

  const legacyProgress = Number(data.progress)
  const progress = Number.isFinite(legacyProgress) ? Math.max(0, Math.min(100, legacyProgress)) : 0
  const status = String(data.status || '')
  const logs = Array.isArray(data.logs) ? data.logs.map((v) => String(v)) : []
  // 统一解析 / C3（旧模式）：后端把总数/成功/失败放在顶层 report，需在此读取，
  // 否则解析完不会显示「共处理 N 条，成功 X，失败 Y，成功率 Z%」汇总。
  const summary = normalizeSummarySource(data.report)
  // 统一解析（C3）只有机构一层，包装成单条 tier 汇总便于统一展示
  const tierSummaries = summary ? [{ tier: 'org', ...summary }] : []
  // 统一解析（旧模式）属于 C3（机构列表）任务
  return { progress, status, logs, summary, tierSummaries, field: 'C3' }
}

async function pollProgress() {
  while (effectiveSessionId.value) {
    try {
      const res = await getParseProgress(effectiveSessionId.value)
      const { status, progress, logs, summary, tierSummaries, field: taskField } = normalizeProgressPayload(res.data)
      if (!affiliationMode.value) {
        parsedFieldAvailability.value = extractParsedFieldAvailability(res.data)
      }
      parseProgress.value = progress
      parseLogs.value = logs
      if (summary && status === 'done') {
        parseSummary.value = summary
        parseTierSummaries.value = tierSummaries || []
        // 按任务所属字段归档（affiliation 模式不按 C1/C3 归档）
        if (!affiliationMode.value && (taskField === 'C1' || taskField === 'C3')) {
          parseSummaryByField.value[taskField] = summary
          parseTierSummariesByField.value[taskField] = tierSummaries || []
        }
      }

      await nextTick()
      if (logBoxRef.value) logBoxRef.value.scrollTop = logBoxRef.value.scrollHeight

      if (status === 'done') {
        parseRunning.value = false
        parseProgressDialogVisible.value = false
        ElMessage.success(tLabel('解析完成：当前解析任务已完成', 'Parse finished: current task completed'))
        return true
      }
      if (status === 'stopped' || status === 'stopping') {
        parseRunning.value = false
        parseProgressDialogVisible.value = false
        ElMessage.warning(tLabel('解析已停止，已处理部分数据可查看结果', 'Parse stopped; partial results are available'))
        return false
      }
      if (status === 'error') {
        parseRunning.value = false
        parseProgressDialogVisible.value = false
        ElMessage.error('解析出错，查看日志了解详情')
        return false
      }
    } catch (_) {}
    await sleep(1500)
  }
  return false
}

async function loadGeoResults(page = 1) {
  if (demoMode.value) {
    geoPage.value = page
    try {
      await loadDemoParseRows(page)
    } catch (e) {
      ElMessage.error('加载案例列表失败：' + (e.response?.data?.detail || e.message))
    }
    return
  }
  if (!effectiveSessionId.value) return
  geoPage.value = page

  // Affiliation 模式
  if (affiliationMode.value) {
    try {
      const field = affiliationSubtypes.value[0] || 'affiliation_country'
      const tier = getAffiliationTier(field)
      const res = await getTierResults(effectiveSessionId.value, field, tier, page, geoPageSize.value)
      geoRecords.value = res.data.records || []
      geoTotal.value = Number(res.data.total) || 0
    } catch (e) {
      ElMessage.error('加载解析结果失败')
    }
    return
  }

  try {
    if (parseField.value === 'C3') {
      const res = await getGeoResults(effectiveSessionId.value, page, geoPageSize.value, 'C3')
      geoRecords.value = Array.isArray(res.data.records) ? res.data.records : []
      geoTotal.value = Number(res.data.total) || 0
      return
    }
    const res = await getTierResults(effectiveSessionId.value, 'C1', activeTier.value, page, geoPageSize.value)
    geoRecords.value = res.data.records
    geoTotal.value = Number(res.data.total) || 0
  } catch (e) {
    ElMessage.error('加载解析结果失败')
  }
}

function buildRankRecords(items, tier) {
  const list = Array.isArray(items) ? items : []
  return list.map((item, index) => ({
    rank: index + 1,
    name: item?.name || item?.organization || item?.org || item?.city || item?.City1 || item?.country || '-',
    count: Number(item?.count ?? item?.value) || 0,
    lat: item?.lat,
    lng: item?.lng,
    address: item?.address || '',
    tier,
  }))
}

async function loadRankResults() {
  if (demoMode.value) return
  if (!effectiveSessionId.value) return

  // Affiliation 模式
  if (affiliationMode.value) {
    try {
      const field = getAffiliationFieldByVizType()
      const res = await getVizData(effectiveSessionId.value, field, FULL_TOP_N)
      const data = res.data || {}
      rankRecords.value = buildRankRecords(data.geocode_items || [], vizType.value)
      geoRecords.value = rankRecords.value
      geoTotal.value = rankRecords.value.length
    } catch (_) {
      rankRecords.value = []
      geoRecords.value = []
      geoTotal.value = 0
      ElMessage.error('加载排名结果失败')
    }
    return
  }

  try {
    if (parseField.value === 'C3') {
      const res = await getVizData(effectiveSessionId.value, 'C3', 30)
      const data = res.data || {}
      if (vizType.value === 'country') rankRecords.value = buildRankRecords(data.country_counts, 'country')
      else if (vizType.value === 'org') rankRecords.value = buildRankRecords(data.org_counts, 'org')
      else if (vizType.value === 'city') rankRecords.value = buildRankRecords(data.city_counts, 'city')
      else rankRecords.value = []
      geoRecords.value = rankRecords.value
      geoTotal.value = rankRecords.value.length
      return
    }
    const tier = activeTier.value
    const res = await getTierStats(effectiveSessionId.value, 'C1', tier, 30)
    rankRecords.value = buildRankRecords(res.data?.items || [], tier)
    geoRecords.value = rankRecords.value
    geoTotal.value = rankRecords.value.length
  } catch (_) {
    rankRecords.value = []
    geoRecords.value = []
    geoTotal.value = 0
    ElMessage.error('加载排名结果失败')
  }
}

async function refreshParseResultData(page = geoPage.value || 1) {
  if (affiliationMode.value) {
    await refreshAffiliationResults(page)
    return
  }
  if (parseField.value === 'C3') {
    await loadGeoResults(page)
    return
  }
  await loadGeoResults(page)
}

function onGeoPageSizeChange() {
  geoPage.value = 1
  if (affiliationMode.value) {
    refreshAffiliationResults(1)
  } else {
    refreshParseResultData(1)
  }
}

function parseResultIndex(index) {
  return (geoPage.value - 1) * geoPageSize.value + index + 1
}

function bindParseTableResizeObserver() {
  if (!parseTableWrapRef.value || typeof ResizeObserver === 'undefined') return
  if (parseTableResizeObserver) {
    parseTableResizeObserver.disconnect()
    parseTableResizeObserver = null
  }
  parseTableResizeObserver = new ResizeObserver((entries) => {
    const entry = entries?.[0]
    if (!entry) return
    parseTableWrapWidth.value = Math.floor(entry.contentRect.width)
  })
  parseTableResizeObserver.observe(parseTableWrapRef.value)
}

function unbindParseTableResizeObserver() {
  if (!parseTableResizeObserver) return
  parseTableResizeObserver.disconnect()
  parseTableResizeObserver = null
}

function parseResultColWidth(kind) {
  const widthBase = parseTableWrapWidth.value || 980
  if (parseField.value === 'C3') {
    const fixed = 270
    const available = Math.max(widthBase - fixed - 12, 320)
    const weightMap = { org: 2.1, raw: 2.8 }
    const totalWeight = 4.9
    const unit = Math.max(22, Math.floor(available / totalWeight))
    return Math.max(60, Math.floor(unit * (weightMap[kind] || 1)))
  }
  if (affiliationMode.value) {
    const fixed = 70
    const available = Math.max(widthBase - fixed - 16, 760)
    const w = {
      rankName: Math.floor(available * 0.36),
      lat: Math.floor(available * 0.14),
      lng: Math.floor(available * 0.14),
      raw: Math.floor(available * 0.24),
    }
    if (kind === 'rankName') return Math.max(300, w.rankName)
    if (kind === 'lat') return Math.max(130, w.lat)
    if (kind === 'lng') return Math.max(130, w.lng)
    if (kind === 'raw') return Math.max(220, w.raw)
    return 80
  }
  const fixed = 70
  const available = Math.max(widthBase - fixed - 16, 560)
  const w = {
    rankName: Math.floor(available * 0.20),
    lat: Math.floor(available * 0.12),
    lng: Math.floor(available * 0.12),
    rankValue: Math.floor(available * 0.10),
    raw: Math.floor(available * 0.46),
  }
  if (kind === 'rankName') return Math.max(120, w.rankName)
  if (kind === 'lat') return Math.max(90, w.lat)
  if (kind === 'lng') return Math.max(90, w.lng)
  if (kind === 'rankValue') return Math.max(80, w.rankValue)
  if (kind === 'raw') return Math.max(220, w.raw)
  return 60
}

async function loadThreeDItems() {
  threeDEdgesSignature.value = ''
  if (demoMode.value) {
    try {
      const demoName = parseField.value === 'C3'
        ? DEMO_COUNT_API_MAP.C3.org
        : DEMO_COUNT_API_MAP.C1[activeTier.value] || DEMO_COUNT_API_MAP.C1.country
      const res = await getDemoData(demoName)
      const rows = normalizeDemoCountRows(res.data || {})
      threeDItems.value = rows.map((item) => ({
        country: activeTier.value === 'country' ? item?.name : '',
        city: activeTier.value === 'city' ? item?.name : '',
        organization: activeTier.value === 'org' ? item?.name : '',
        lat: item?.lat,
        lng: item?.lng,
        count: item?.count,
      }))
    } catch (_) {
      threeDItems.value = []
    }
    return
  }
  if (!effectiveSessionId.value) return

  // Affiliation 模式：与表格全量一致
  if (affiliationMode.value) {
    try {
      const field = getAffiliationFieldByVizType()
      const res = await getVizData(effectiveSessionId.value, field, FULL_TOP_N)
      threeDItems.value = (Array.isArray(res.data?.geocode_items) ? res.data.geocode_items : []).map((item) => ({
        ...item,
        organization: item?.organization || item?.org || '',
        org: item?.org || item?.organization || '',
        city: item?.City1 || item?.city || '',
        City1: item?.City1 || item?.city || '',
        country: item?.country || '',
        name: item?.name || item?.organization || item?.org || item?.city || item?.country || '',
        count: Number(item?.count ?? item?.value) || 0,
      }))
    } catch (_) {
      threeDItems.value = []
    }
    return
  }

  try {
    if (parseField.value === 'C3') {
      const res = await getVizData(effectiveSessionId.value, 'C3', FULL_TOP_N)
      threeDItems.value = Array.isArray(res.data?.geocode_items) ? res.data.geocode_items : []
      return
    }
    const res = await getTierStats(effectiveSessionId.value, 'C1', activeTier.value, FULL_TOP_N)
    const items = Array.isArray(res.data?.items) ? res.data.items : []
    threeDItems.value = items.map((item) => ({
      country: activeTier.value === 'country' ? item?.name : item?.country,
      city: activeTier.value === 'city' ? item?.name : '',
      organization: activeTier.value === 'org' ? item?.name : '',
      lat: item?.lat,
      lng: item?.lng,
      count: item?.count,
    }))
  } catch (_) {
    threeDItems.value = []
  }
}

async function restoreResults() {
  if (demoMode.value) {
    await refreshParseResultData(1)
    return
  }
  if (!effectiveSessionId.value) return
  try {
    try {
      const progressRes = await getParseProgress(effectiveSessionId.value)
      if (!affiliationMode.value) {
        parsedFieldAvailability.value = extractParsedFieldAvailability(progressRes.data)
      }
      const { summary, tierSummaries, field: taskField } = normalizeProgressPayload(progressRes.data)
      if (summary) {
        // 服务端只保留最近一次任务，据其所属字段归档，避免刷新后
        // 在 C1 标签下误显示 C3 的汇总（反之亦然）
        if (!affiliationMode.value && (taskField === 'C1' || taskField === 'C3')) {
          parseSummaryByField.value[taskField] = summary
          parseTierSummariesByField.value[taskField] = tierSummaries || []
          parseSummary.value = parseSummaryByField.value[parseField.value] || null
          parseTierSummaries.value = parseTierSummariesByField.value[parseField.value] || []
        } else {
          parseSummary.value = summary
          parseTierSummaries.value = tierSummaries || []
        }
      }
    } catch (_) {}

    const res = affiliationMode.value
      ? await getGeoResults(effectiveSessionId.value, 1, geoPageSize.value, affiliationSubtypes.value[0] || 'affiliation_country')
      : parseField.value === 'C3'
        ? await getGeoResults(effectiveSessionId.value, 1, geoPageSize.value, 'C3')
        : await getTierResults(effectiveSessionId.value, 'C1', activeTier.value, 1, geoPageSize.value)
    if (res.data.total > 0) {
      geoRecords.value = res.data.records
      geoTotal.value = res.data.total
      parseProgress.value = 100
      if (parseLogs.value.length === 0) {
        const resultLabel = affiliationMode.value ? 'Affiliation' : parseField.value
        parseLogs.value = [tLabel(
          `已有 ${resultLabel} 解析结果，共 ${res.data.total} 条记录`,
          `Existing ${resultLabel} parse results: ${res.data.total} records`,
        )]
      }
    }
  } catch (_) {}
}

async function openParseResultDialog() {
  if (!ensureLoggedIn()) return
  if (demoMode.value) {
    geoPage.value = 1
    await refreshParseResultData(1)
    if (parseResultRows.value.length === 0) {
      ElMessage.warning('案例暂无可展示结果')
      return
    }
    parseResultDialogVisible.value = true
    return
  }
  if (!effectiveSessionId.value) {
    ElMessage.warning('请先上传并解析数据')
    return
  }

  // Affiliation 模式：直接刷新数据列表
  if (affiliationMode.value) {
    geoPage.value = 1
    await refreshAffiliationResults(1)
    parseResultDialogVisible.value = true
    return
  }

  await refreshParseResultData(geoPage.value || 1)
  if (parseResultRows.value.length === 0) {
    const tip = `${parseField.value} 尚无解析结果`
    ElMessage.warning(tip)
    return
  }
  parseResultDialogVisible.value = true
}

function handleUploadBoxClick(event) {
  if (event?.target?.closest?.('.upload-file-remove')) {
    return
  }
  if (!ensureLoggedIn()) {
    event?.preventDefault()
    event?.stopPropagation()
    return
  }
  if (displayedUploadFiles.value.length > 0) triggerUploadPicker()
}

function handleUploadChange() {
  if (!ensureLoggedIn()) {
    fileList.value = []
  }
}

function clearUploads() {
  if (!ensureLoggedIn()) return
  resetAllContent()
}

function resetAllContent() {
  demoMode.value = false
  customDemoActive.value = false
  demoLoading.value = false
  demoRawTableLoading.value = false
  demoRawTableRows.value = []
  fileList.value = []
  savedUploadNames.value = []
  latestSessionId.value = ''
  latestRecordCount.value = 0
  parsedFieldAvailability.value = { C1: false, C3: false }
  affiliationMode.value = false
  affiliationSubtypes.value = []
  parseField.value = 'C1'
  c1TierChecks.value = { country: false, org: false, city: false }
  batchSize.value = DEFAULT_MODELS.length
  vizType.value = 'country'
  activeView.value = '平面地图'
  geoRecords.value = []
  rankRecords.value = []
  threeDItems.value = []
  geoTotal.value = 0
  geoPage.value = 1
  parseProgress.value = 0
  parseLogs.value = []
  parseSummary.value = null
  parseTierSummaries.value = []
  parseSummaryByField.value = { C1: null, C3: null }
  parseTierSummariesByField.value = { C1: [], C3: [] }
  vizMeta.value = { total: null, source: '', tier: '', displayCount: null }
  parseRunning.value = false
  rawDataDialogVisible.value = false
  parseResultDialogVisible.value = false
  parseProgressDialogVisible.value = false
  localStorage.removeItem(HOME_UI_STATE_KEY)
  emit('session-created', { sessionId: '', recordCount: 0 })
}

function removeUpload(file) {
  if (!ensureLoggedIn()) return
  if (file?.__saved) {
    savedUploadNames.value = savedUploadNames.value.filter((name) => name !== file.name)
    return
  }
  const uid = file?.uid
  const idx = fileList.value.findIndex((f) => {
    if (!f) return false
    if (uid != null && f.uid === uid) return true
    if (f === file) return true
    return f.name === file?.name && f.size === file?.size
  })
  if (idx >= 0) fileList.value.splice(idx, 1)
}

function selectParseField(field) {
  if (!ensureLoggedIn()) return
  if (parseRunning.value) return
  if (parseField.value === field) return
  parseField.value = field
  vizType.value = field === 'C3' ? 'org' : 'country'
  // 切换字段时显示该字段各自的解析汇总，避免串台
  parseSummary.value = parseSummaryByField.value[field] || null
  parseTierSummaries.value = parseTierSummariesByField.value[field] || []
  // 无论演示模式与否，都刷新为该字段对应的结果表与可视化
  geoPage.value = 1
  refreshParseResultData(1)
  vizReloadKey.value += 1
}

/**
 * 启动解析前询问：沿用已有匹配（本地缓存/已解析坐标）还是强制大模型重算。
 * @returns {Promise<boolean|null>} true=沿用缓存, false=跳过缓存重算, null=取消
 */
async function askAffiliationParseMode() {
  // 无结果时仍提示一次，因为服务端可能有历史 affiliation_cache
  // 左：使用已有匹配（cancel）  右：大模型重新加载（confirm）
  try {
    await ElMessageBox.confirm(
      tLabel('检测到固定参考库中可能已有匹配坐标。', 'Existing matched coordinates may already be available in the reference database.'),
      tLabel('选择解析方式', 'Choose parse mode'),
      {
        confirmButtonText: tLabel('大模型重新加载', 'Reload with LLM'),
        cancelButtonText: tLabel('使用已有匹配', 'Use existing matches'),
        distinguishCancelAndClose: true,
        type: 'info',
        customClass: 'parse-mode-confirm',
        confirmButtonClass: 'parse-mode-confirm-btn',
      },
    )
    return false // 确认 = 大模型重算
  } catch (action) {
    if (action === 'cancel') return true // 取消侧按钮 = 使用已有匹配
    return null
  }
}

async function startAffiliationParse({ skipCache = false } = {}) {
  if (!effectiveSessionId.value) return

  parseRunning.value = true
  parseProgress.value = 0
  parseLogs.value = []
  parseProgressDialogVisible.value = true

  try {
    await startParseAffiliation(effectiveSessionId.value, buildConfigs(), batchSize.value, skipCache, currentLang())
    const finished = await pollProgress()
    if (!finished) return

    // 解析完成后自动切换到结果视图
    activeView.value = '数据列表'
    await refreshAffiliationResults(1)
    parseResultDialogVisible.value = true
    vizReloadKey.value += 1
  } catch (e) {
    ElMessage.error(tLabel('启动解析失败：', 'Failed to start parse: ') + (e.response?.data?.detail || e.message))
    parseRunning.value = false
    parseProgressDialogVisible.value = false
  }
}

async function refreshAffiliationResults(page = 1) {
  if (!effectiveSessionId.value) return
  geoPage.value = page
  try {
    const field = getAffiliationFieldByVizType()
    const res = await getGeoResults(effectiveSessionId.value, page, geoPageSize.value, field)
    geoRecords.value = res.data.records || []
    geoTotal.value = Number(res.data.total) || 0
  } catch (e) {
    ElMessage.error('加载解析结果失败')
  }
}

function getAffiliationTier(field) {
  if (field === 'affiliation_country') return 'country'
  if (field === 'affiliation_org') return 'org'
  if (field === 'affiliation_city') return 'city'
  return 'country'
}

// ── 确定性地理编码兜底：对仍缺坐标的条目调用 Nominatim 补齐并回填 ──
const geocodeFallbackRunning = ref(false)

async function doGeocodeFallback() {
  if (!effectiveSessionId.value || geocodeFallbackRunning.value) return
  geocodeFallbackRunning.value = true
  try {
    let res
    if (affiliationMode.value) {
      res = await runGeocode(effectiveSessionId.value, '', true)
    } else if (parseField.value === 'C3') {
      res = await runGeocode(effectiveSessionId.value, '', true, 'C3')
    } else {
      // C1 分层解析：对当前查看的层级做兜底
      res = await runGeocode(effectiveSessionId.value, '', true, 'C1', vizType.value)
    }
    const d = res.data || {}
    if ((d.checked || 0) === 0) {
      ElMessage.info(tLabel('所有条目均已有坐标，无需兜底。', 'All entries already have coordinates.'))
    } else {
      ElMessage.success(tLabel(
        `兜底完成：检查 ${d.checked} 条，补齐 ${d.filled} 条。`,
        `Fallback done: ${d.filled} of ${d.checked} entries filled.`,
      ))
    }
    // 刷新结果表与可视化
    if (affiliationMode.value) {
      await refreshAffiliationResults(geoPage.value || 1)
    } else {
      await refreshParseResultData(geoPage.value || 1)
    }
    vizReloadKey.value += 1
    if (activeView.value === '三维地图') {
      await loadThreeDItems()
      await nextTick()
      await renderThreeDMap()
    }
  } catch (e) {
    ElMessage.error(tLabel('兜底编码失败：', 'Geocode fallback failed: ') + (e.response?.data?.detail || e.message))
  } finally {
    geocodeFallbackRunning.value = false
  }
}

function getAffiliationFieldByVizType(type = vizType.value) {
  if (type === 'org') return 'affiliation_org'
  if (type === 'city') return 'affiliation_city'
  return 'affiliation_country'
}

async function selectVizType(type) {
  if (!ensureLoggedIn()) return
  if (parseRunning.value) return
  // C3（机构列表）仅支持机构视图，国家/城市不可选
  if (parseField.value === 'C3' && type !== 'org') return
  if (vizLoading.value && vizType.value !== type) return
  const canSwitch = await canSwitchVizType(type)
  if (!canSwitch) {
    showTierUnavailableMessage(type)
    return
  }
  if (demoMode.value) {
    vizType.value = parseField.value === 'C3' ? 'org' : type
    if (parseResultDialogVisible.value) {
      geoPage.value = 1
      await refreshParseResultData(1)
    }
    if (activeView.value === '三维地图') {
      await loadThreeDItems()
      await nextTick()
      await renderThreeDMap()
    }
    return
  }

  // Affiliation 模式
  if (affiliationMode.value) {
    vizType.value = type
    geoPage.value = 1
    await refreshAffiliationResults(1)
    vizReloadKey.value += 1
    if (activeView.value === '三维地图') {
      await loadThreeDItems()
      await nextTick()
      await renderThreeDMap()
    }
    return
  }

  vizType.value = type
  if (activeView.value === '三维地图') {
    await loadThreeDItems()
    await nextTick()
    await renderThreeDMap()
  }
}

async function doExportParseResults() {
  if (geoTotal.value === 0) {
    ElMessage.warning(tLabel('暂无可导出的解析结果', 'No parse results to export'))
    return
  }
  try {
    let rows = []
    if (demoMode.value) {
      // 案例模式：拉取当前层级完整列表
      const field = parseField.value
      const tier = activeTier.value
      const listApiName = DEMO_LIST_API_MAP[field]?.[tier]
      if (listApiName) {
        const res = await getDemoData(listApiName)
        rows = extractDemoList(res.data || {})
      } else {
        rows = [...parseResultRows.value]
      }
    } else if (affiliationMode.value) {
      const field = getAffiliationFieldByVizType()
      const res = await getGeoResults(effectiveSessionId.value, 1, Math.max(geoTotal.value, 1), field)
      rows = res.data.records || []
    } else if (parseField.value === 'C3') {
      const res = await getGeoResults(effectiveSessionId.value, 1, Math.max(geoTotal.value, 1), 'C3')
      rows = res.data.records || []
    } else {
      const res = await getTierResults(effectiveSessionId.value, 'C1', activeTier.value, 1, Math.max(geoTotal.value, 1))
      rows = res.data.records || []
    }
    if (!rows.length) {
      ElMessage.warning(tLabel('暂无可导出的解析结果', 'No parse results to export'))
      return
    }
    const keys = Object.keys(rows[0])
    const escape = (v) => {
      const s = v == null ? '' : String(v)
      return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
    }
    const lines = [keys.join(',')]
    for (const row of rows) {
      lines.push(keys.map((k) => escape(row[k])).join(','))
    }
    const blob = new Blob(['\ufeff' + lines.join('\n')], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const tag = affiliationMode.value
      ? (vizType.value || 'org')
      : (parseField.value === 'C3' ? 'C3' : `C1_${activeTier.value}`)
    a.download = `parse_results_${tag}.csv`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success(tLabel(`已导出 ${rows.length} 条`, `Exported ${rows.length} rows`))
  } catch (e) {
    ElMessage.error(tLabel('导出失败：', 'Export failed: ') + (e.response?.data?.detail || e.message))
  }
}

async function doExportGml() {
  if (!ensureLoggedIn()) return
  if (demoMode.value) {
    const filename = getCurrentGmlFilename()
    const url = `https://smartdata.las.ac.cn/AiGeovis/AiGeovis/AiGeovis_api/api/demo/gml/download?filename=${encodeURIComponent(filename)}`
    window.open(url, '_blank', 'noopener')
    return
  }
  if (!effectiveSessionId.value) {
    ElMessage.warning(tLabel('请先上传并解析数据', 'Please upload and parse data first'))
    return
  }

  const field = parseField.value === 'C3' ? 'C3' : 'C1'
  const tier = field === 'C3'
    ? 'org'
    : (vizType.value === 'org' || vizType.value === 'city' ? vizType.value : 'country')

  try {
    const res = await exportEntityMatrixGml(
      effectiveSessionId.value,
      field,
      tier,
      10000,
      0,
      'normalized',
      false,
    )
    const url = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = url
    a.download = `entity_matrix_${field}_${tier}.gml`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success(tLabel('GML 导出成功', 'GML export completed'))
  } catch (e) {
    const msg = e.response?.data?.detail || e.message || tLabel('导出失败', 'Export failed')
    ElMessage.error(`${tLabel('导出失败', 'Export failed')}: ${msg}`)
  }
}

function resetCurrentVisualization() {
  if (!ensureLoggedIn()) return
  if (!(effectiveSessionId.value || demoMode.value)) return
  if (parseRunning.value) return

  resetMapParamSettings()

  if (activeView.value === '三维地图') {
    syncThreeDViewState({
      distance: DEFAULT_THREE_D_VIEW_CONTROL.distance,
      alpha: null,
      beta: null,
      center: null,
    })
    threeDLabelDetailLevel.value = getThreeDLabelDensityProfile(DEFAULT_THREE_D_VIEW_CONTROL.distance).level
    if (threeDMapChart) {
      threeDMapChart.setOption({
        globe: {
          viewControl: { ...DEFAULT_THREE_D_VIEW_CONTROL },
        },
      })
    }
    return
  }

  vizViewRef.value?.resetViewport?.()
}

function openParseProgressDialog() {
  if (!ensureLoggedIn()) return
  parseProgressDialogVisible.value = true
}

// 解析完成后仍可回看/隐藏解析过程（进度 + 日志），C1 / C3 / 本地数据通用
function toggleParseProgressDialog() {
  if (!ensureLoggedIn()) return
  parseProgressDialogVisible.value = !parseProgressDialogVisible.value
}

function onVizStatsMeta(payload) {
  if (!payload || typeof payload !== 'object') return
  vizMeta.value = {
    total: Number(payload.total) || 0,
    source: payload.source || '',
    tier: payload.tier || '',
    displayCount: Number(payload.display_count) || 0,
  }
}

function onVizLoading(value) {
  if (value) {
    vizLoading.value = true
    return
  }
  vizLoadingProgress.value = 100
  window.setTimeout(() => {
    vizLoading.value = false
    stopVizLoadingProgress()
  }, 160)
}

watch(() => props.sessionId, () => {
  vizLoading.value = false
  parseLogs.value = []
  parseProgress.value = 0
  parseSummary.value = null
  parseTierSummaries.value = []
  parseSummaryByField.value = { C1: null, C3: null }
  parseTierSummariesByField.value = { C1: [], C3: [] }
  geoRecords.value = []
  rankRecords.value = []
  threeDItems.value = []
  geoTotal.value = 0
  vizMeta.value = { total: null, source: '', tier: '', displayCount: null }
  restoreResults()
})

watch(parseField, () => {
  // C3 只有机构维度，强制视图为 org（国家/城市不可用）
  if (parseField.value === 'C3' && vizType.value !== 'org') {
    vizType.value = 'org'
  }
  geoRecords.value = []
  rankRecords.value = []
  threeDItems.value = []
  geoTotal.value = 0
  vizMeta.value = { total: null, source: '', tier: '', displayCount: null }
  parseProgress.value = 0
  parseLogs.value = []
  // 切换字段时立即显示该字段各自的解析汇总（演示模式下 restoreResults 会提前返回、
  // 不恢复汇总，故这里直接从按字段缓存取，避免切回后状态消失）
  parseSummary.value = (parseField.value === 'C1' || parseField.value === 'C3')
    ? (parseSummaryByField.value[parseField.value] || null)
    : null
  parseTierSummaries.value = (parseField.value === 'C1' || parseField.value === 'C3')
    ? (parseTierSummariesByField.value[parseField.value] || [])
    : []
  if (parseResultDialogVisible.value) {
    refreshParseResultData(1)
  }
  if (demoMode.value) {
    vizReloadKey.value += 1
  }
  restoreResults()
})

watch(vizType, () => {
  if (parseResultDialogVisible.value) {
    if (affiliationMode.value) {
      refreshAffiliationResults(1)
    } else {
      refreshParseResultData(1)
    }
  }
})

watch(vizLoading, (value) => {
  if (value) {
    startVizLoadingProgress()
    return
  }
  if (!vizLoadingTimer) {
    vizLoadingProgress.value = 0
  }
})

watch(() => selectedModels.value.length, (n) => {
  if (n > 0) batchSize.value = n
})

watch(langSwitch, (v) => {
  localStorage.setItem(HOME_LANG_KEY, v ? 'zh' : 'en')
})

watch(themeSwitch, (v, prev) => {
  const prevEdgeColorDefault = getDefaultMapEdgeColor(prev)
  const nextEdgeColorDefault = getDefaultMapEdgeColor(v)
  const prevEdgeOpacityDefault = getDefaultMapEdgeOpacity(prev)
  const nextEdgeOpacityDefault = getDefaultMapEdgeOpacity(v)

  if (mapEdgeColor.value === prevEdgeColorDefault) {
    mapEdgeColor.value = nextEdgeColorDefault
  }
  if (Number(mapEdgeOpacity.value) === prevEdgeOpacityDefault) {
    mapEdgeOpacity.value = nextEdgeOpacityDefault
  }

  localStorage.setItem(HOME_THEME_KEY, v ? 'dark' : 'light')
  window.dispatchEvent(new Event('app-theme-change'))
})

watch(themeSwitch, async () => {
  if (activeView.value !== '三维地图') return
  await nextTick()
  await renderThreeDMap()
})

watch(mapNodeSize, (value) => {
  if (mapSizeMode.value === 'scaled') {
    scaledMapNodeSize.value = value
  }
})

watch(mapSizeMode, (mode, prevMode) => {
  if (mode === 'fixed' && prevMode !== 'fixed') {
    scaledMapNodeSize.value = mapNodeSize.value
    mapNodeSize.value = 20
    return
  }
  if (mode === 'scaled' && prevMode === 'fixed') {
    mapNodeSize.value = scaledMapNodeSize.value
  }
})

watch([activeView, parseField, affiliationMode, affiliationSubtypes, c1TierChecks, batchSize, vizType, vizAutoLoadEnabled, savedUploadNames, mapNodeSize, threeDBarSize, mapLabelVisible, mapNodeOpacity, mapEdgeWidth, mapEdgeOpacity, mapSizeMode, mapNodeColor, mapEdgeColor, mapEdgeVisible, threeDBarColor, threeDRenderMode], () => {
  const payload = {
    activeView: activeView.value,
    parseField: parseField.value,
    affiliationMode: affiliationMode.value,
    affiliationSubtypes: affiliationSubtypes.value,
    c1TierChecks: c1TierChecks.value,
    batchSize: batchSize.value,
    vizType: vizType.value,
    vizAutoLoadEnabled: vizAutoLoadEnabled.value,
    parseSummary: parseSummary.value,
    mapNodeSize: mapNodeSize.value,
    threeDBarSize: threeDBarSize.value,
    mapLabelVisible: mapLabelVisible.value,
    mapNodeOpacity: mapNodeOpacity.value,
    mapEdgeWidth: mapEdgeWidth.value,
    mapEdgeOpacity: mapEdgeOpacity.value,
    mapSizeMode: mapSizeMode.value,
    mapNodeColor: mapNodeColor.value,
    mapEdgeColor: mapEdgeColor.value,
    mapEdgeVisible: mapEdgeVisible.value,
    threeDBarColor: threeDBarColor.value,
    threeDRenderMode: threeDRenderMode.value,
    savedUploadNames: savedUploadNames.value,
  }
  localStorage.setItem(HOME_UI_STATE_KEY, JSON.stringify(payload))
}, { deep: true })

watch([threeDBarSize, mapLabelVisible, mapNodeOpacity, threeDBarColor, threeDRenderMode, mapEdgeVisible, mapEdgeWidth, mapEdgeOpacity, mapNodeSize, mapSizeMode, mapEdgeColor], async () => {
  if (activeView.value !== '三维地图') return
  await nextTick()
  await renderThreeDMap()
}, { deep: true })

watch([providerConfigs, activeProviderKey], () => {
  const payload = {
    version: 2,
    providerConfigs: providerConfigs.value,
    activeProviderKey: activeProviderKey.value,
  }
  localStorage.setItem(HOME_MODEL_CFG_KEY, JSON.stringify(payload))
}, { deep: true })

watch(parseResultDialogVisible, async (visible) => {
  if (!visible) {
    if (activeView.value === '数据列表') activeView.value = '平面地图'
    unbindParseTableResizeObserver()
    return
  }
  await nextTick()
  if (parseTableWrapRef.value) {
    parseTableWrapWidth.value = parseTableWrapRef.value.clientWidth || parseTableWrapWidth.value
    bindParseTableResizeObserver()
  }
  parseResultTableRef.value?.doLayout?.()
})

watch(parseTableWrapWidth, async () => {
  if (!parseResultDialogVisible.value) return
  await nextTick()
  parseResultTableRef.value?.doLayout?.()
})

watch(threeDItems, async () => {
  if (activeView.value !== '三维地图') return
  await nextTick()
  await renderThreeDMap()
}, { deep: true })

watch(activeView, async (view) => {
  if (view !== '三维地图') {
    disposeThreeDMap()
    return
  }
  await loadThreeDItems()
  await nextTick()
  await renderThreeDMap()
})

onMounted(() => {
  const savedLang = localStorage.getItem(HOME_LANG_KEY)
  if (savedLang === 'zh') langSwitch.value = true
  if (savedLang === 'en') langSwitch.value = false

  const savedTheme = localStorage.getItem(HOME_THEME_KEY)
  if (savedTheme === 'dark') themeSwitch.value = true
  if (savedTheme === 'light') themeSwitch.value = false

  const savedModelCfg = localStorage.getItem(HOME_MODEL_CFG_KEY)
  if (savedModelCfg) {
    try {
      const parsed = JSON.parse(savedModelCfg)
      // 仅识别 v2（多服务商）结构；旧结构直接丢弃，使用默认配置
      if (parsed?.version === 2 && parsed?.providerConfigs && typeof parsed.providerConfigs === 'object') {
        const restored = buildDefaultProviderConfigs()
        for (const p of PROVIDER_DEFS) {
          const saved = parsed.providerConfigs[p.key]
          if (!saved || typeof saved !== 'object') continue
          restored[p.key] = {
            api_key: typeof saved.api_key === 'string' ? saved.api_key : '',
            base_url: typeof saved.base_url === 'string' ? saved.base_url : (p.defaultBaseUrl || ''),
            models: Array.isArray(saved.models)
              ? saved.models.filter((m) => m && typeof m.model === 'string').map((m) => ({ ...m }))
              : [],
            verified: Boolean(saved.verified),
          }
        }
        providerConfigs.value = restored
        if (PROVIDER_DEFS.some((p) => p.key === parsed.activeProviderKey)) {
          activeProviderKey.value = parsed.activeProviderKey
        }
      }
    } catch (_) {}
  }

  const savedUiState = localStorage.getItem(HOME_UI_STATE_KEY)
  if (savedUiState) {
    try {
      const parsed = JSON.parse(savedUiState)
      if (viewItems.includes(parsed?.activeView)) {
        activeView.value = parsed.activeView === '数据列表' ? '平面地图' : parsed.activeView
      }
      if (parsed?.parseField === 'C1' || parsed?.parseField === 'C3') parseField.value = parsed.parseField
      if (typeof parsed?.affiliationMode === 'boolean') affiliationMode.value = parsed.affiliationMode
      if (Array.isArray(parsed?.affiliationSubtypes)) {
        affiliationSubtypes.value = parsed.affiliationSubtypes.filter((v) => typeof v === 'string' && v.trim())
      }
      if (parsed?.c1TierChecks && typeof parsed.c1TierChecks === 'object') {
        c1TierChecks.value = {
          country: Boolean(parsed.c1TierChecks.country),
          org: Boolean(parsed.c1TierChecks.org),
          city: Boolean(parsed.c1TierChecks.city),
        }
      }
      if (Number.isFinite(Number(parsed?.batchSize)) && Number(parsed.batchSize) > 0) batchSize.value = Number(parsed.batchSize)
      if (['country', 'org', 'city'].includes(parsed?.vizType)) vizType.value = parsed.vizType
      if (typeof parsed?.vizAutoLoadEnabled === 'boolean') vizAutoLoadEnabled.value = parsed.vizAutoLoadEnabled
      if (parsed?.parseSummary && typeof parsed.parseSummary === 'object') {
        const restoredSummary = {
          total: Number(parsed.parseSummary.total) || 0,
          success: Number(parsed.parseSummary.success) || 0,
          failed: Number(parsed.parseSummary.failed) || 0,
          successRate: Number(parsed.parseSummary.successRate) || 0,
        }
        parseSummary.value = restoredSummary
        if (parseField.value === 'C1' || parseField.value === 'C3') {
          parseSummaryByField.value[parseField.value] = restoredSummary
        }
      }
      if (Array.isArray(parsed?.savedUploadNames)) {
        savedUploadNames.value = parsed.savedUploadNames.filter((v) => typeof v === 'string' && v.trim())
      }
      if (Number.isFinite(Number(parsed?.mapNodeSize))) {
        mapNodeSize.value = Number(parsed.mapNodeSize)
        scaledMapNodeSize.value = Number(parsed.mapNodeSize)
      }
      if (Number.isFinite(Number(parsed?.threeDBarSize))) threeDBarSize.value = Number(parsed.threeDBarSize)
      if (typeof parsed?.mapLabelVisible === 'boolean') mapLabelVisible.value = parsed.mapLabelVisible
      if (Number.isFinite(Number(parsed?.mapNodeOpacity))) mapNodeOpacity.value = Number(parsed.mapNodeOpacity)
      if (Number.isFinite(Number(parsed?.mapEdgeWidth))) mapEdgeWidth.value = Number(parsed.mapEdgeWidth)
      if (Number.isFinite(Number(parsed?.mapEdgeOpacity))) mapEdgeOpacity.value = Number(parsed.mapEdgeOpacity)
      if (parsed?.mapSizeMode === 'fixed' || parsed?.mapSizeMode === 'scaled') mapSizeMode.value = parsed.mapSizeMode
      if (typeof parsed?.mapNodeColor === 'string' && parsed.mapNodeColor.trim()) {
        mapNodeColor.value = parsed.mapNodeColor
      } else if (typeof parsed?.labelColor === 'string' && parsed.labelColor.trim()) {
        mapNodeColor.value = parsed.labelColor
      }
      if (typeof parsed?.mapEdgeColor === 'string' && parsed.mapEdgeColor.trim()) {
        mapEdgeColor.value = parsed.mapEdgeColor
      }
      if (typeof parsed?.mapEdgeVisible === 'boolean') mapEdgeVisible.value = parsed.mapEdgeVisible
      if (typeof parsed?.threeDBarColor === 'string' && parsed.threeDBarColor.trim()) {
        threeDBarColor.value = parsed.threeDBarColor
      }
      if (parsed?.threeDRenderMode === 'bar' || parsed?.threeDRenderMode === 'point') {
        threeDRenderMode.value = parsed.threeDRenderMode
      }
    } catch (_) {}
  }

  restoreResults()
  window.addEventListener('resize', handleThreeDResize)
  window.addEventListener('app-logout', resetHomeSettings)
})

onBeforeUnmount(() => {
  unbindParseTableResizeObserver()
  window.removeEventListener('resize', handleThreeDResize)
  window.removeEventListener('app-logout', resetHomeSettings)
  disposeThreeDMap()
  disposeThreeDBaseMapTexture()
})
</script>

<style scoped>
@import url('./CSS/homeview.css');
</style>
