<template>
  <div class="user-management-container" :class="{ 'dark-theme': isDarkTheme }">
    <div class="header-container">
      <div class="header-content">
        <div class="header-left">
          <button @click="handleReturn" class="return-button">
            <div class="icon-wrapper">
              <svg class="back-icon" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M15 18l-6-6 6-6" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </div>
            <span>{{ this.Lang === 'CN' ? '返回' : 'Back' }}</span>
          </button>
          <div class="platform-title">{{ this.Lang === 'CN' ? 'AiGeovis 用户管理平台' : 'User Management Platform of AiGeovis' }}</div>
        </div>

        <div class="header-right">
          <div class="total-users-badge">
            <svg style="width: 16px; height: 16px; color: #2563eb;" fill="currentColor" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg">
              <path d="M727.04 931.84c-20.48 0-40.96-15.36-40.96-40.96v-87.04c0-35.84-15.36-66.56-40.96-92.16s-56.32-40.96-92.16-40.96H215.04c-35.84 0-66.56 15.36-92.16 40.96s-40.96 56.32-40.96 92.16v87.04c0 20.48-15.36 40.96-40.96 40.96s-40.96-15.36-40.96-40.96v-87.04c0-56.32 20.48-107.52 61.44-148.48 40.96-40.96 92.16-61.44 148.48-61.44h343.04c56.32 0 107.52 20.48 148.48 61.44 40.96 40.96 61.44 92.16 61.44 148.48v87.04c0 25.6-15.36 40.96-35.84 40.96zM384 506.88c-117.76 0-209.92-92.16-209.92-209.92s92.16-209.92 209.92-209.92 209.92 92.16 209.92 209.92-92.16 209.92-209.92 209.92z m0-343.04c-71.68 0-133.12 61.44-133.12 133.12s61.44 133.12 133.12 133.12 133.12-61.44 133.12-133.12-61.44-133.12-133.12-133.12zM983.04 931.84c-20.48 0-40.96-15.36-40.96-40.96v-87.04c0-30.72-10.24-56.32-25.6-81.92s-40.96-40.96-71.68-46.08c-20.48-5.12-30.72-25.6-25.6-46.08s25.6-30.72 46.08-25.6c46.08 10.24 87.04 35.84 112.64 76.8 30.72 35.84 46.08 81.92 46.08 128v87.04c-5.12 20.48-20.48 35.84-40.96 35.84zM680.96 501.76c-15.36 0-30.72-10.24-35.84-30.72-5.12-20.48 5.12-40.96 25.6-46.08 30.72-5.12 56.32-25.6 71.68-46.08 20.48-25.6 25.6-51.2 25.6-81.92s-10.24-56.32-25.6-81.92-40.96-40.96-71.68-46.08c-20.48-5.12-30.72-25.6-25.6-46.08s25.6-30.72 46.08-25.6c46.08 10.24 87.04 35.84 112.64 76.8 30.72 35.84 46.08 81.92 46.08 128s-15.36 92.16-46.08 128-66.56 61.44-112.64 76.8c0-5.12-5.12-5.12-10.24-5.12z" />
            </svg>
            <span class="total-users-text">{{ this.Lang === 'CN' ? '用户数量' : 'Number of Users' }}</span>
            <span class="total-users-count">{{totalUsers}}</span>
          </div>
          <div class="total-users-badge">
            <svg style="width: 16px; height: 16px; color: #2563eb;" fill="currentColor" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg">
              <path d="M727.04 931.84c-20.48 0-40.96-15.36-40.96-40.96v-87.04c0-35.84-15.36-66.56-40.96-92.16s-56.32-40.96-92.16-40.96H215.04c-35.84 0-66.56 15.36-92.16 40.96s-40.96 56.32-40.96 92.16v87.04c0 20.48-15.36 40.96-40.96 40.96s-40.96-15.36-40.96-40.96v-87.04c0-56.32 20.48-107.52 61.44-148.48 40.96-40.96 92.16-61.44 148.48-61.44h343.04c56.32 0 107.52 20.48 148.48 61.44 40.96 40.96 61.44 92.16 61.44 148.48v87.04c0 25.6-15.36 40.96-35.84 40.96zM384 506.88c-117.76 0-209.92-92.16-209.92-209.92s92.16-209.92 209.92-209.92 209.92 92.16 209.92 209.92-92.16 209.92-209.92 209.92z m0-343.04c-71.68 0-133.12 61.44-133.12 133.12s61.44 133.12 133.12 133.12 133.12-61.44 133.12-133.12-61.44-133.12-133.12-133.12zM983.04 931.84c-20.48 0-40.96-15.36-40.96-40.96v-87.04c0-30.72-10.24-56.32-25.6-81.92s-40.96-40.96-71.68-46.08c-20.48-5.12-30.72-25.6-25.6-46.08s25.6-30.72 46.08-25.6c46.08 10.24 87.04 35.84 112.64 76.8 30.72 35.84 46.08 81.92 46.08 128v87.04c-5.12 20.48-20.48 35.84-40.96 35.84zM680.96 501.76c-15.36 0-30.72-10.24-35.84-30.72-5.12-20.48 5.12-40.96 25.6-46.08 30.72-5.12 56.32-25.6 71.68-46.08 20.48-25.6 25.6-51.2 25.6-81.92s-10.24-56.32-25.6-81.92-40.96-40.96-71.68-46.08c-20.48-5.12-30.72-25.6-25.6-46.08s25.6-30.72 46.08-25.6c46.08 10.24 87.04 35.84 112.64 76.8 30.72 35.84 46.08 81.92 46.08 128s-15.36 92.16-46.08 128-66.56 61.44-112.64 76.8c0-5.12-5.12-5.12-10.24-5.12z" />
            </svg>
            <span class="total-users-text">{{ this.Lang === 'CN' ? '今日新增用户' : 'New Users Today' }}</span>
            <span class="total-users-count">{{newUsersToday}}</span>
          </div>
          <!--          <div class="total-users-badge">-->
          <!--            <svg style="width: 16px; height: 16px; color: #2563eb;" fill="currentColor" viewBox="0 0 24 24">-->
          <!--              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>-->
          <!--            </svg>-->
          <!--            <span class="total-users-text">{{ this.Lang === 'CN' ? '机构数量' : 'Number of Institutions' }}</span>-->
          <!--            <span class="total-users-count">{{institutionNum}}</span>-->
          <!--          </div>-->
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="main-content">
      <div class="table-card">
        <!-- Tabs -->
        <div class="tabs-container">
          <div class="tabs-toolbar">
            <div class="tabs-wrapper">
              <button
                  @click="activeName = 'first'"
                  :class="['tab-button', { 'active': activeName === 'first' }]"
              >
                <svg style="width: 16px; height: 16px;" fill="currentColor" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg">
                  <path d="M727.04 931.84c-20.48 0-40.96-15.36-40.96-40.96v-87.04c0-35.84-15.36-66.56-40.96-92.16s-56.32-40.96-92.16-40.96H215.04c-35.84 0-66.56 15.36-92.16 40.96s-40.96 56.32-40.96 92.16v87.04c0 20.48-15.36 40.96-40.96 40.96s-40.96-15.36-40.96-40.96v-87.04c0-56.32 20.48-107.52 61.44-148.48 40.96-40.96 92.16-61.44 148.48-61.44h343.04c56.32 0 107.52 20.48 148.48 61.44 40.96 40.96 61.44 92.16 61.44 148.48v87.04c0 25.6-15.36 40.96-35.84 40.96zM384 506.88c-117.76 0-209.92-92.16-209.92-209.92s92.16-209.92 209.92-209.92 209.92 92.16 209.92 209.92-92.16 209.92-209.92 209.92z m0-343.04c-71.68 0-133.12 61.44-133.12 133.12s61.44 133.12 133.12 133.12 133.12-61.44 133.12-133.12-61.44-133.12-133.12-133.12zM983.04 931.84c-20.48 0-40.96-15.36-40.96-40.96v-87.04c0-30.72-10.24-56.32-25.6-81.92s-40.96-40.96-71.68-46.08c-20.48-5.12-30.72-25.6-25.6-46.08s25.6-30.72 46.08-25.6c46.08 10.24 87.04 35.84 112.64 76.8 30.72 35.84 46.08 81.92 46.08 128v87.04c-5.12 20.48-20.48 35.84-40.96 35.84zM680.96 501.76c-15.36 0-30.72-10.24-35.84-30.72-5.12-20.48 5.12-40.96 25.6-46.08 30.72-5.12 56.32-25.6 71.68-46.08 20.48-25.6 25.6-51.2 25.6-81.92s-10.24-56.32-25.6-81.92-40.96-40.96-71.68-46.08c-20.48-5.12-30.72-25.6-25.6-46.08s25.6-30.72 46.08-25.6c46.08 10.24 87.04 35.84 112.64 76.8 30.72 35.84 46.08 81.92 46.08 128s-15.36 92.16-46.08 128-66.56 61.44-112.64 76.8c0-5.12-5.12-5.12-10.24-5.12z" />
                </svg>
                <span class="tab-text">{{ this.Lang === 'CN' ? '用户' : 'Users' }}</span>
                <span class="tab-count users">{{ ordinaryTotal }}</span>
              </button>
              <button
                  @click="activeName = 'second'"
                  :class="['tab-button', { 'active': activeName === 'second' }]"
              >
                <svg style="width: 16px; height: 16px;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
                <span class="tab-text">{{ this.Lang === 'CN' ? '管理员' : 'Administrators' }}</span>
                <span class="tab-count admin">{{ manageTotal }}</span>
              </button>
            </div>

            <div class="search-filter-group panel-search-group">
              <div class="search-input-wrapper">
                <el-input
                    size="medium"
                    v-model="searchValue"
                    @keyup.enter.native="queryUserInfoData"
                    @clear="queryUserInfoData"
                    :placeholder=" this.Lang === 'CN' ? '检索用户、邮箱或机构...' : 'Search users, emails or organizations...' "
                    clearable
                    class="search-input"
                ></el-input>
              </div>
              <button @click="exportList" class="export-csv-button">
                <svg xmlns="http://www.w3.org/2000/svg" style="width: 16px; height: 16px;" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                <span style="margin-left: 8px;">{{ this.Lang === 'CN' ? '导出用户' : 'Export CSV' }}</span>
              </button>
            </div>
          </div>

            <!--            <button-->
            <!--                @click="activeName = 'third'"-->
            <!--                :class="['tab-button', { 'active': activeName === 'third' }]"-->
            <!--            >-->
            <!--              <svg style="width: 16px; height: 16px;" fill="none" stroke="currentColor" viewBox="0 0 24 24">-->
            <!--                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />-->
            <!--              </svg>-->
            <!--              <span class="tab-text">{{ this.Lang === 'CN' ? '机构' : 'Institutions' }}</span>-->
            <!--              <span class="tab-count users">{{ institutionNum }}</span>-->
            <!--            </button>-->
            <!--            <button-->
            <!--                @click="activeName = 'fourth'"-->
            <!--                :class="['tab-button', { 'active': activeName === 'fourth' }]"-->
            <!--            >-->
            <!--              <svg style="width: 16px; height: 16px;" fill="none" stroke="currentColor" viewBox="0 0 24 24">-->
            <!--                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />-->
            <!--              </svg>-->
            <!--              <span class="tab-text">{{ this.Lang === 'CN' ? '中国科学院系统' : 'CAS Systems' }}</span>-->
            <!--              <span class="tab-count users">{{ CASData.length }}</span>-->
            <!--            </button>-->
          </div>
        </div>

        <!-- Table Container -->
        <div class="table-container">
          <div class="table-wrapper">
            <!-- Users List Table -->
            <div v-show="activeName === 'first'">
              <table>
                <thead>
                <tr>
                  <th style="width: 50px;text-align: center;max-width: 50px;">#</th>
                  <th style="width: 300px;">{{ this.Lang === 'CN' ? '用户名' : 'Username' }}</th>
                  <th style="width: 300px;">{{ this.Lang === 'CN' ? '用户 ID' : 'User ID' }}</th>
                  <th style="width: 200px;">{{ this.Lang === 'CN' ? '电话' : 'Phone' }}</th>
                  <th>{{ this.Lang === 'CN' ? '机构' : 'Organization' }}</th>
                  <th style="width: 120px;">{{ this.Lang === 'CN' ? '属性' : 'Role' }}</th>
                  <th class="created-column">{{ this.Lang === 'CN' ? '注册时间' : 'Created' }}</th>
                  <th style="width: 200px;">{{ this.Lang === 'CN' ? '管理' : 'Actions' }}</th>
                </tr>
                </thead>
                <tbody>
                <tr v-for="(user, index) in userOrdinaryInfoData" :key="user.userId" :class="{ 'highlight-row': user.userIdentity === 2 }">
                  <td style="text-align: center;">
                    <div class="cell-content font-medium">{{ tableRowIndexRender(index) }}</div>
                  </td>
                  <td>
                    <div class="user-info-cell">
                      <div class="avatar" :style="{ background: getAvatarColor(user.userIdentity) }">
                        {{ user.userName ? user.userName.substring(0, 2).toUpperCase() : 'UN' }}
                      </div>
                      <div>
                        <div class="cell-content font-medium">{{ user.userName }}</div>
                        <div class="cell-content-secondary">{{ user.userEmail }}</div>
                      </div>
                    </div>
                  </td>
                  <td>
                    <div class="cell-content" style="overflow: hidden;text-overflow: ellipsis;white-space: nowrap;">{{ user.userId.substring(0,25) }}...</div>
                  </td>
                  <td>
                    <div class="cell-content">{{ user.userMobile }}</div>
                  </td>
                  <td>
                    <div v-if="user.isEditing" class="edit-institution-cell">
                      <input
                          type="text"
                          v-model="user.userInstitution"
                          class="edit-input"
                          @blur="handleSave(user)"
                          @keyup.enter="handleSave(user)"
                          v-focus
                      />
                      <button @click="handleSave(user)" class="icon-button save-button">
                        <i class="el-icon-check"></i>
                      </button>
                      <button @click="handleCancel(user)" class="icon-button cancel-button">
                        <i class="el-icon-close"></i>
                      </button>
                    </div>
                    <div v-else class="institution-cell" @click="handleEdit(user)">
                      <span style="margin-right: 8px;overflow: hidden;text-overflow: ellipsis;white-space: nowrap;">
                        {{ user.userInstitution && user.userInstitution.length > 16 ?
                          user.userInstitution.substring(0, 16) + '...' :
                          user.userInstitution
                        }}
                      </span>
                      <div class="edit-icon-wrapper">
                        <i class="el-icon-edit"></i>
                      </div>
                    </div>
                  </td>
                  <td>
                     <span class="identity-badge" :style="getIdentityBadge(user.userIdentity)">
                      {{ getIdentityText(user.userIdentity) }}
                    </span>
                  </td>
                  <td class="created-column cell-content-secondary">{{ user.insertTime }}</td>
                  <td>
                    <div v-if="isCurrentUserAdmin()" class="control-buttons">
                      <i v-if="isUserSending(user.userId)" class="el-icon-loading"></i>
                      <svg v-else @click="sendEmail(user)" :fill="isDarkTheme ? '#9ec5ff' : '#515151'" t="1755569702315" class="icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="31582" style="margin-right: 10px;cursor: pointer;" width="20" height="20">
                        <path d="M883.438 883.386V697.334h37.211v186.052c0 41.118-33.303 74.421-74.421 74.421H176.439c-41.118 0-74.421-33.303-74.421-74.421V474.071c0-41.118 33.303-74.421 74.421-74.421h186.052v37.211H176.439c-1.303 0-2.419 0.632-3.684 0.745l338.578 237.031 338.578-237.031c-1.265-0.112-2.381-0.745-3.684-0.745H660.175V399.65h186.053c41.117 0 74.421 33.303 74.421 74.421h-37.211c0-4.503-1.116-8.707-2.567-12.689l-369.537 258.65-369.537-258.65c-1.451 3.982-2.567 8.186-2.567 12.689v409.315c0 20.503 16.707 37.211 37.211 37.211h669.788c20.501 0 37.209-16.708 37.209-37.211z m0-260.473v-74.421h37.211v74.421h-37.211zM585.754 846.176v-37.211h223.263v37.211H585.754z m74.421-111.631v-37.211h148.842v37.211H660.175zM514.44 64.745l220.174 260.473H585.736v186.09H436.931v-186.90H288.089L514.44 64.745z m-0.409 57.193l-144.34 166.07h104.413v186.09h74.421v-186.09h105.901l-140.395-166.07z" p-id="31583"></path>
                      </svg>
                      <button @click="setIdentity(user.userId, 1, user.userIdentity, user)"
                              :class="['role-button admin', { 'active': user.userIdentity === 1 }]"
                              :disabled="isDisabled || isUserIdentityLoading(user.userId)">
                        <i v-if="isIdentityLoading(user.userId, 1)" class="el-icon-loading"></i>
                        <span v-else>Admin</span>
                      </button>
                      <button @click="setIdentity(user.userId, 2, user.userIdentity, user)"
                              :class="['role-button user', { 'active': user.userIdentity === 2 }]"
                              :disabled="isDisabled || isUserIdentityLoading(user.userId)">
                        <i v-if="isIdentityLoading(user.userId, 2)" class="el-icon-loading"></i>
                        <span v-else>User</span>
                      </button>
                      <button @click="delectById(user.userId)" class="icon-button delete-button">
                        <i class="el-icon-delete"></i>
                      </button>
                    </div>
                  </td>
                </tr>
                <tr v-if="userOrdinaryInfoData.length === 0">
                  <td colspan="7" class="loading-cell"> {{ this.Lang === 'CN' ? '暂无数据' : 'No data found' }}</td>
                </tr>
                </tbody>
              </table>
            </div>

            <!-- Admin Table -->
            <div v-show="activeName === 'second'">
              <table>
                <thead>
                <tr>
                  <th style="width: 50px;text-align: center;max-width: 50px;">#</th>
                  <th style="width: 300px;">{{ this.Lang === 'CN' ? '用户名' : 'Username' }}</th>
                  <th style="width: 300px;">{{ this.Lang === 'CN' ? '用户 ID' : 'User ID' }}</th>
                  <th style="width: 200px;">{{ this.Lang === 'CN' ? '电话' : 'Phone' }}</th>
                  <th style="">{{ this.Lang === 'CN' ? '机构' : 'Organization' }}</th>
                  <th style="width: 120px;">{{ this.Lang === 'CN' ? '属性' : 'Role' }}</th>
                  <th class="created-column">{{ this.Lang === 'CN' ? '注册时间' : 'Created' }}</th>
                  <th style="width: 200px;">{{ this.Lang === 'CN' ? '管理' : 'Actions' }}</th>
                </tr>
                </thead>
                <tbody>
                <tr v-for="(user, index) in userManageInfoData" :key="user.userId">
                  <td style="text-align: center;">
                    <div class="cell-content font-medium">{{ index + 1 }}</div>
                  </td>
                  <td>
                    <div class="user-info-cell">
                      <div class="avatar" :style="{ background: getAvatarColor(user.userIdentity) }">
                        {{ user.userName ? user.userName.substring(0, 2).toUpperCase() : 'UN' }}
                      </div>
                      <div>
                        <div class="cell-content font-medium">{{ user.userName }}</div>
                        <div class="cell-content-secondary">{{ user.userEmail }}</div>
                      </div>
                    </div>
                  </td>
                  <td>
                    <div class="cell-content">{{ user.userId.substring(0,25) }}...</div>
                  </td>
                  <td>
                    <div class="cell-content">{{ user.userMobile }}</div>
                  </td>
                  <td>
                    <div v-if="user.isEditing" class="edit-institution-cell">
                      <input
                          type="text"
                          v-model="user.userInstitution"
                          class="edit-input"
                          @blur="handleSave(user)"
                          @keyup.enter="handleSave(user)"
                          v-focus
                      />
                      <button @click="handleSave(user)" class="icon-button save-button">
                        <i class="el-icon-check"></i>
                      </button>
                      <button @click="handleCancel(user)" class="icon-button cancel-button">
                        <i class="el-icon-close"></i>
                      </button>
                    </div>
                    <div v-else class="institution-cell" @click="handleEdit(user)">
                      <span class="institution-text">
                        {{ user.userInstitution && user.userInstitution.length > 16 ?
                          user.userInstitution.substring(0, 16) + '...' :
                          user.userInstitution
                        }}
                      </span>
                      <div class="edit-icon-wrapper">
                        <i class="el-icon-edit"></i>
                      </div>
                    </div>
                  </td>
                  <td>
                      <span class="identity-badge" :style="getIdentityBadge(user.userIdentity)">
                        {{ user.userIdentity === 1 ? "Admin" : "User" }}
                      </span>
                  </td>
                  <td class="created-column cell-content-secondary">{{ user.insertTime }}</td>
                  <td>
                    <div v-if="isCurrentUserAdmin()" class="control-buttons">
                      <i v-show="isUserSending(user.userId)" class="el-icon-loading" style="margin-right: 10px; font-size: 16px; color: #409eff;"></i>
                      <svg v-show="!isUserSending(user.userId)" @click="sendEmail(user)" :fill="isDarkTheme ? '#9ec5ff' : '#515151'" t="1755569702315" class="icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="31582" style="margin-right: 10px;cursor: pointer;" width="20" height="20">
                        <path d="M883.438 883.386V697.334h37.211v186.052c0 41.118-33.303 74.421-74.421 74.421H176.439c-41.118 0-74.421-33.303-74.421-74.421V474.071c0-41.118 33.303-74.421 74.421-74.421h186.052v37.211H176.439c-1.303 0-2.419 0.632-3.684 0.745l338.578 237.031 338.578-237.031c-1.265-0.112-2.381-0.745-3.684-0.745H660.175V399.65h186.053c41.117 0 74.421 33.303 74.421 74.421h-37.211c0-4.503-1.116-8.707-2.567-12.689l-369.537 258.65-369.537-258.65c-1.451 3.982-2.567 8.186-2.567 12.689v409.315c0 20.503 16.707 37.211 37.211 37.211h669.788c20.501 0 37.209-16.708 37.209-37.211z m0-260.473v-74.421h37.211v74.421h-37.211zM585.754 846.176v-37.211h223.263v37.211H585.754z m74.421-111.631v-37.211h148.842v37.211H660.175zM514.44 64.745l220.174 260.473H585.736v186.09H436.931v-186.90H288.089L514.44 64.745z m-0.409 57.193l-144.34 166.07h104.413v186.09h74.421v-186.09h105.901l-140.395-166.07z" p-id="31583"></path>
                      </svg>
                      <button @click="setIdentity(user.userId, 1, user.userIdentity, user)"
                              :class="['role-button admin', { 'active': user.userIdentity === 1 }]"
                              :disabled="isDisabled || isUserIdentityLoading(user.userId)">
                        <i v-if="isIdentityLoading(user.userId, 1)" class="el-icon-loading"></i>
                        <span v-else>Admin</span>
                      </button>
                      <button @click="setIdentity(user.userId, 2, user.userIdentity, user)"
                              :class="['role-button user', { 'active': user.userIdentity === 2 }]"
                              :disabled="isDisabled || isUserIdentityLoading(user.userId)">
                        <i v-if="isIdentityLoading(user.userId, 2)" class="el-icon-loading"></i>
                        <span v-else>User</span>
                      </button>
                      <button @click="delectById(user.userId)" class="icon-button delete-button">
                        <i class="el-icon-delete"></i>
                      </button>
                    </div>
                  </td>
                </tr>
                <tr v-if="userManageInfoData.length === 0">
                  <td colspan="7" class="loading-cell">{{ this.Lang === 'CN' ? '暂无数据' : 'No data found' }}</td>
                </tr>
                </tbody>
              </table>
            </div>

            <!-- 在 Institutions 标签页内容中修改 -->
            <div v-show="activeName === 'third'" class="chart-container">
              <div class="chart-layout">
                <div class="chart-left">
                  <div ref="chart" style="width: 100%; height: 100%;"></div>
                </div>
                <div class="chart-right">
                  <div class="institution-table-container">
                    <div class="table-header">
                      <span class="table-title">#</span>
                      <span class="table-title">{{ this.Lang === 'CN' ? '机构' : 'Institutions' }}</span>
                      <span class="table-title">{{ this.Lang === 'CN' ? '数量' : 'Count' }}</span>
                    </div>
                    <div class="table-body">
                      <div
                          v-for="(item, index) in sortedInstitutionList"
                          :key="index"
                          class="table-row"
                      >
                        <span class="table-cell index">{{ index + 1 }}</span>
                        <span class="table-cell name">{{ item.institutionName }}</span>
                        <span class="table-cell count">{{ item.count }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 在 CAS Institutions 标签页内容中修改 -->
            <div v-show="activeName === 'fourth'" class="chart-container">
              <div class="chart-layout">
                <div class="chart-left">
                  <div ref="CASChart" style="width: 100%; height: 100%;"></div>
                </div>
                <div class="chart-right">
                  <div class="institution-table-container">
                    <div class="table-header">
                      <span class="table-title">#</span>
                      <span class="table-title">{{ this.Lang === 'CN' ? '机构' : 'Institutions' }}</span>
                      <span class="table-title">{{ this.Lang === 'CN' ? '数量' : 'Count' }}</span>
                    </div>
                    <div class="table-body">
                      <div
                          v-for="(item, index) in sortedCASList"
                          :key="index"
                          class="table-row"
                      >
                        <span class="table-cell index">{{ index + 1 }}</span>
                        <span class="table-cell name">{{ item.institutionName }}</span>
                        <span class="table-cell count">{{ item.count }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

          </div>
        </div>

        <!-- Pagination -->
        <!-- 将文件2中的分页容器部分替换为以下代码 -->
        <!-- Pagination -->
        <div class="pagination-container" v-show="activeName === 'first'">
          <div class="pagination-info">
            {{ Lang === 'CN'
              ? `共 ${total} 条记录，第 ${pageInfo.pageNum} / ${Math.ceil(total / pageInfo.pageSize)} 页`
              : `Total ${total} records, Page ${pageInfo.pageNum} / ${Math.ceil(total / pageInfo.pageSize)}`
            }}
          </div>
          <div class="pagination-controls">
            <button
                class="pagination-btn"
                @click="handleCurrentChange(1)"
                :disabled="pageInfo.pageNum === 1"
            >
              {{ Lang === 'CN' ? '首页' : 'First' }}
            </button>
            <button
                class="pagination-btn"
                @click="handleCurrentChange(pageInfo.pageNum - 1)"
                :disabled="pageInfo.pageNum === 1"
            >
              {{ Lang === 'CN' ? '上一页' : 'Prev' }}
            </button>

            <div class="page-numbers">
              <button
                  v-for="page in paginationPages"
                  :key="page"
                  class="pagination-btn page-number"
                  :class="{ active: pageInfo.pageNum === page }"
                  @click="handleCurrentChange(page)"
              >
                {{ page }}
              </button>
            </div>

            <button
                class="pagination-btn"
                @click="handleCurrentChange(pageInfo.pageNum + 1)"
                :disabled="pageInfo.pageNum >= Math.ceil(total / pageInfo.pageSize)"
            >
              {{ Lang === 'CN' ? '下一页' : 'Next' }}
            </button>
            <button
                class="pagination-btn"
                @click="handleCurrentChange(Math.ceil(total / pageInfo.pageSize))"
                :disabled="pageInfo.pageNum >= Math.ceil(total / pageInfo.pageSize)"
            >
              {{ Lang === 'CN' ? '末页' : 'Last' }}
            </button>
          </div>
          <div class="page-size-selector">
            <select v-model="pageInfo.pageSize" @change="handleSizeChange(pageInfo.pageSize)" class="page-size-select">
              <option value="50">50/{{ Lang === 'CN' ? '页' : 'page' }}</option>
              <option value="100">100/{{ Lang === 'CN' ? '页' : 'page' }}</option>
              <option value="150">150/{{ Lang === 'CN' ? '页' : 'page' }}</option>
              <option value="200">200/{{ Lang === 'CN' ? '页' : 'page' }}</option>
            </select>
          </div>
        </div>

      </div>
    </div>
</template>

<script>
import { getRandomInt } from "../utils/commonUtils";
// import { mapState } from "vuex";

function debounce(fn, wait = 100) {
  let timer = null;
  return function debounced(...args) {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => {
      fn.apply(this, args);
    }, wait);
  };
}

export default {
  name: "UserManage",
  data() {
    return {
      userOrdinaryInfoData: [],
      userManageInfoData: [],
      totalUsers: 0,
      newUsersToday: 0,
      total: 0,
      ordinaryTotal: 0,
      manageTotal: 0,
      isDisabled: false,
      userInfoFidex: (() => {
        try {
          const raw = window.localStorage.getItem("userInfoAI") || window.localStorage.getItem("userInfoCast") || "{}";
          return JSON.parse(raw);
        } catch (error) {
          return {};
        }
      })(),
      activeName: 'first',
      institutionNum: 0,
      isDownload: false,
      pageInfo: {
        pageNum: 1,
        pageSize: 50
      },
      InstitutionContent: [],
      loginCount: 0,
      searchValue: '',
      InstitutionList: [],
      CASData: [],
      CASChart: null,
      isSaving: false,
      chartResizeHandler: null,
      sending: false,
      sendingUsers: {}, // 用对象替代 Set，键为 userId，值为 true
      identityLoading: {}
      ,
      isDarkTheme: false
    };
  },
  directives: {
    focus: {
      inserted(el) {
        el.querySelector('input').focus()
      }
    }
  },
  computed: {
    theme() {
      // console.log(newVal,'theme1');
      return this.$store?.state?.theme || false;
    },
    Lang() {
      // console.log(newVal, 'lang1');
      return this.$store?.state?.isEnglish ? 'EN' : 'CN';
    },
    sortedInstitutionList() {
      return [...this.InstitutionContent].sort((a, b) => b.count - a.count);
    },

    sortedCASList() {
      return [...this.CASData].sort((a, b) => b.count - a.count);
    },
    paginationPages() {
      const pages = [];
      const total = Math.ceil(this.total / this.pageInfo.pageSize);
      if (total <= 5) {
        for (let i = 1; i <= total; i++) {
          pages.push(i);
        }
      } else {
        let start = Math.max(1, this.pageInfo.pageNum - 2);
        let end = Math.min(total, this.pageInfo.pageNum + 2);

        if (this.pageInfo.pageNum < 3) {
          end = 5;
        }
        if (this.pageInfo.pageNum > total - 2) {
          start = total - 4;
        }

        for (let i = start; i <= end; i++) {
          pages.push(i);
        }
      }
      return pages;
    }
  },
  mounted() {
    this.syncThemeState();
    this.queryUserInfoData();
    // this.getInstitutionData();
    this.getNewUserToday()
    this.chartResizeHandler = debounce(() => {
      if (this.chart) {
        this.chart.resize()
      }
      if (this.CASChart) {
        this.CASChart.resize()
      }
    }, 100)
    window.addEventListener('resize', this.chartResizeHandler)
    window.addEventListener('app-theme-change', this.syncThemeState)
  },
  beforeDestroy() {
    window.removeEventListener('resize', this.chartResizeHandler)
    window.removeEventListener('app-theme-change', this.syncThemeState)
  },
  watch: {
    activeName(val){
      switch (val) {
        case "third":
          this.getChart()
          break
        case "fourth":
          this.getCASChart()
          break
      }
    },
    theme(newVal) {
      // console.log(newVal,'theme2');
      return false;
    },
    Lang(newVal) {
      // console.log(newVal, 'lang2');
      return this.$store?.state?.isEnglish ? 'EN' : 'CN';
    },
    '$route.query.theme'() {
      this.syncThemeState();
    },
  },
  methods: {
    syncThemeState() {
      const savedTheme = localStorage.getItem('home_theme_switch');
      if (savedTheme === 'dark') {
        this.isDarkTheme = true;
        return;
      }
      if (savedTheme === 'light') {
        this.isDarkTheme = false;
        return;
      }

      const routeTheme = this.$route?.query?.theme;
      if (routeTheme === 'dark') {
        this.isDarkTheme = true;
        return;
      }
      if (routeTheme === 'light') {
        this.isDarkTheme = false;
        return;
      }
      this.isDarkTheme = localStorage.getItem('home_theme_switch') === 'dark';
    },
    isCurrentUserAdmin() {
      const candidates = [
        'userInfoAiGeovis',
        'userInfoAigeovis',
        'userInfoAI',
        'userInfoCast',
      ];
      for (const key of candidates) {
        const raw = localStorage.getItem(key);
        if (!raw) continue;
        try {
          const user = JSON.parse(raw);
          if (Number(user?.userIdentity) === 1) return true;
        } catch (e) {
          // ignore parse error and try next key
        }
      }
      return false;
    },
    async handleReturn(){
      window.location.hash = '#/home'
    },
    refreshInstitutions() {
      this.getChart()
    },
    refreshCAS() {
      this.getCASChart()
    },
    // Handle edit click
    handleEdit(row) {
      // Set editing state
      this.$set(row, 'isEditing', true)
      // Save original value for cancel
      row.originalInstitution = row.userInstitution
    },
    // Handle cancel edit
    handleCancel(row) {
      row.userInstitution = row.originalInstitution
      this.$set(row, 'isEditing', false)
    },
    // Handle save
    async handleSave(row) {
      // If saving, don't process
      if (this.isSaving) return;

      // Set saving flag
      this.isSaving = true;

      // Hide input immediately
      this.$set(row, 'isEditing', false);

      // If no change, exit editing
      if (row.originalInstitution === row.userInstitution) {
        this.isSaving = false;
        return;
      }

      try {
        // Call save API
        const formData = new FormData();
        formData.set('userId', row.userId);
        formData.set('InstitutionInfo', row.userInstitution);
        await this.request.post('/knowledgexUser/updateUserInstitution', formData).then((res) => {
          // Save success
          this.$notify({
            title: 'Notice',
            message: "Updated successfully",
            type: 'success',
            offset: 100
          });
          this.$set(row, 'isEditing', false);
          this.queryUserInfoData();
        });

      } catch (error) {
        // Save failed, restore original value
        this.$notify({
          title: 'Notice',
          message: "Update failed",
          type: 'error',
          offset: 100
        });
        row.userInstitution = row.originalInstitution;
        this.$set(row, 'isEditing', false);
      } finally {
        // Reset saving flag
        this.isSaving = false;
      }
    },

    // 发送邮件
    sendEmail(val) {
      // console.log('发送邮件开始，用户ID:', val.userId);

      // 设置发送状态
      this.$set(this.sendingUsers, val.userId, true);

      this.request.post(`/knowledgexUser/sendUserEmail?userId=${val.userId}&systemType=18`)
          .then(res => {
            if (res.data.code === 200 && res.data.flag) {
              this.$notify({
                title: 'Tip',
                message: 'Password has been sent to email！',
                type: 'success',
                offset: 100
              });
            } else {
              this.$notify({
                title: 'Tip',
                message: res.data.obj,
                type: 'error',
                offset: 100
              });
            }
          })
          .catch((err) => {
            this.$notify({
              title: 'Tip',
              message: err,
              type: 'error',
              offset: 100
            });
          })
          .finally(() => {
            // console.log('发送完成，移除用户ID:', val.userId);
            // 清除发送状态
            this.$delete(this.sendingUsers, val.userId);
          });
    },

    // 检查用户是否正在发送邮件
    isUserSending(userId) {
      return !!this.sendingUsers[userId];
    },

    isIdentityLoading(userId, identity) {
      return this.identityLoading[userId] === identity;
    },

    isUserIdentityLoading(userId) {
      return !!this.identityLoading[userId];
    },

    getNewUserToday() {
      this.request.get('/knowledgexUser/todayUsers?systemType=18').then((res) => {
        if (res.data.code === 200 && res.data.flag) {
          this.newUsersToday = res.data.obj
        }
      })
    },

    //Delete account
    delectById(id){
      this.$confirm('Are you sure to delete this user?', 'Confirm', {
        confirmButtonText: 'Confirm',
        cancelButtonText: 'Cancel',
        type: 'warning'
      }).then(() => {
        const formData = new FormData();
        formData.set('userId', id);
        const url = `/knowledgexUser/deleteUserInfoData`;
        this.request.post(url, formData).then(res=>{
          if(res.data){
            this.$notify({
              title: 'Notice',
              message: "Delete successfully！",
              type: 'success',
              offset: 100
            });
          }else{
            this.$notify({
              title: 'Notice',
              message: "Deletion failed！",
              type: 'error',
              offset: 100
            });
          }
          this.queryUserInfoData();
        })

      }).catch(() => {
        this.$notify({
          title: 'Notice',
          message: "Deletion cancelled",
          type: 'info',
          offset: 100
        });
      });
    },

    tableRowClassName({row}) {
      // Check condition
      if (row.userIdentity === 3) {
        return 'highlight-row';  // Return custom class
      }
      return '';  // No class if no condition met
    },

    // Set identity
    setIdentity(userId, identity, currentIdentity, row) {
      if (this.isDisabled || this.isUserIdentityLoading(userId)) return;
      this.isDisabled = true;
      this.$set(this.identityLoading, userId, identity);

      const formData = new FormData();
      formData.set('userId', userId);
      const isSameIdentity = identity === currentIdentity;

      if (!isSameIdentity) {
        formData.set('userIdentity', identity);
        if (identity === 2) {
          formData.set('systemType', '18');
        }
      }

      this.request.post('/knowledgexUser/updateUserInfoData', formData).then((res) => {
        if (res.status === 200) {
          this.$notify({
            title: 'Notice',
            message: 'Identity set successfully！',
            type: 'success',
            offset: 100
          });
          if (!isSameIdentity) {
            row.userIdentity = identity;
          }
          this.queryUserInfoData();
        }
      }).finally(() => {
        this.isDisabled = false;
        this.$delete(this.identityLoading, userId);
      });
    },

    // Custom row index
    tableRowIndexRender(index) {
      return (this.pageInfo.pageNum - 1) * this.pageInfo.pageSize + index + 1;
    },

    handleSizeChange(val) {
      this.pageInfo.pageSize = val;
      this.queryUserInfoData();
    },

    handleCurrentChange(val) {
      this.pageInfo.pageNum = val;
      this.queryUserInfoData();
    },

    // Query user info
    async queryUserInfoData() {
      try {
        // Use Promise.all to ensure both requests complete before calculating total
        // const userInfo = JSON.parse(localStorage.getItem('userInfoAI'));
        const [
          ordinaryRes,
          manageRes
        ] = await Promise.all([
          this.request.get(`/knowledgexUser/queryOrdinaryUserInfoData?Keyword=${this.searchValue}`, {
            params: {
              pageNum: this.pageInfo.pageNum,
              pageSize: this.pageInfo.pageSize,
              systemType: '18'
            }
          }),
          this.request.get("/knowledgexUser/queryManageUserInfoData", {
            params: {
              pageNum: this.pageInfo.pageNum,
              pageSize: this.pageInfo.pageSize,
              systemType: '18'
            }
          })
        ]);

        // Handle regular user data
        if (ordinaryRes.status === 200) {
          const ordinaryObj = ordinaryRes.data && ordinaryRes.data.obj;
          // your actual response: { obj: { total, content: [...] } }
          if (ordinaryObj && Array.isArray(ordinaryObj.content)) {
            this.userOrdinaryInfoData = ordinaryObj.content;
            this.ordinaryTotal = Number(ordinaryObj.total || ordinaryObj.content.length || 0);
          } else if (Array.isArray(ordinaryObj)) {
            this.userOrdinaryInfoData = ordinaryObj;
            this.ordinaryTotal = ordinaryObj.length;
          } else {
            this.userOrdinaryInfoData = [];
            this.ordinaryTotal = 0;
          }
        }

        // Handle admin data
        if (manageRes.status === 200) {
          const manageObj = manageRes.data && manageRes.data.obj;
          // your actual response: { obj: [...] }
          if (Array.isArray(manageObj)) {
            this.userManageInfoData = manageObj;
            this.manageTotal = manageObj.length;
          } else if (manageObj && Array.isArray(manageObj.content)) {
            this.userManageInfoData = manageObj.content;
            this.manageTotal = Number(manageObj.total || manageObj.content.length || 0);
          } else {
            this.userManageInfoData = [];
            this.manageTotal = 0;
          }
        }

        // Calculate total after both requests complete
        this.total = this.ordinaryTotal;
        this.totalUsers = this.manageTotal + this.ordinaryTotal

      } catch (error) {
        console.error('Failed to get user data:', error);
      }
    },

    // 获取机构数据
    async getInstitutionData() {
      try {
        const response = await this.request.get('https://smartdata.las.ac.cn/citeinsight-pro/citeinsight-pro/citeinsightpro_api/user/queryInstitutionSize');
        if (response.status === 200) {
          this.InstitutionContent = response.data.obj.institutionSizeMap || [];
          this.institutionNum = this.InstitutionContent.length;

          // 过滤出包含"中国科学院"的机构
          this.CASData = this.InstitutionContent.filter(item =>
              item.institutionName && (item.institutionName.includes('中国科学院') || item.institutionName.includes('中国科学技术大学') || item.institutionName.includes('上海科技大学'))
          );
        }
      } catch (error) {
        console.error('获取机构数据失败:', error);
        // 设置默认值避免报错
        this.InstitutionContent = [];
        this.CASData = [];
        this.institutionNum = 0;
      }
    },

    downloadExportBlob(res) {
      const blob = new Blob([res.data], { type: "application/octet-stream" });
      const contentDisposition = res.headers?.["content-disposition"] || "";
      const fileNameMatch = contentDisposition.match(/filename\\*?=(?:UTF-8''|\"?)([^\";]+)/i);
      const decodedName = fileNameMatch ? decodeURIComponent(fileNameMatch[1].replace(/\"/g, "")) : "";
      const fileName = decodedName || `users_${Date.now()}.csv`;

      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    },

    exportList(formData) {
      this.request
          .post('/knowledgexUser/exportUsers', formData, { responseType: "blob" })
          .then((res) => {
            if (res.status === 200) {
              try {
                this.downloadExportBlob(res);
                this.isDownload = false
              } catch (e) {
                this.$notify({
                  title: 'Notice',
                  message: "File download error, please contact the administrator! Error content:" + e,
                  type: 'warning',
                  offset: 100
                });
              }
            } else {
              this.$notify({
                title: 'Notice',
                message: "File download error, please contact the administrator!",
                type: 'warning',
                offset: 100
              });
            }
          })
          .catch((err) => {
            this.$notify({
              title: 'Notice',
              message: "File download error, please contact the administrator! Error content:" +
                  err,
              type: 'error',
              offset: 100
            });
          });
    },

    getChart() {
      if (this.InstitutionContent.length === 0) return; // 添加这行检查

      let options = this.getInstitutionsChart('all');
      this.$nextTick(() => {
        if (this.$refs.chart && !this.chart) {
          this.chart = this.$echarts.init(this.$refs.chart);
        }
        if (this.chart) {
          this.chart.setOption(options);
        }
      });
    },

    getCASChart() {
      if (this.CASData.length === 0) return; // 添加这行检查

      let options = this.getInstitutionsChart('CAS');
      this.$nextTick(() => {
        if (this.$refs.CASChart && !this.CASChart) {
          this.CASChart = this.$echarts.init(this.$refs.CASChart);
        }
        if (this.CASChart) {
          this.CASChart.setOption(options);
        }
      });
    },

    getInstitutionsChart(val) {
      let filteredData = val === 'all' ? this.InstitutionContent : this.CASData;

      return {
        toolbox: {
          show: true,
          feature: {
            saveAsImage: { show: false }
          },
          right: "3%",
          top: "2%"
        },
        tooltip: {
          show: true,
          trigger: "item",
          formatter: function (params) {
            return `
          <div style="text-align: left;">
            <p><strong>${params.name}</strong></p>
            <p>Count: ${params.value}</p>
          </div>
        `;
          }
        },
        series: [{
          type: 'wordCloud',
          shape: 'circle',
          keepAspect: false,
          top: '3%',
          left: 'center',
          width: '100%',
          height: '90%',
          right: null,
          bottom: null,
          sizeRange: [12, 50],
          rotationRange: val === 'all' ? [0,0] : [0,0],
          rotationStep: 45,
          gridSize: 8,
          drawOutOfBound: false,
          layoutAnimation: true,
          textStyle: {
            fontFamily: 'PingFang SC, PingFang TC, Microsoft YaHei, Helvetica Neue, Helvetica, Arial, sans-serif',
            fontWeight: 'bold'
            // 完全不设置 color，让 ECharts 使用默认的多彩配色
          },
          emphasis: {
            textStyle: {
              textShadowBlur: 3,
              textShadowColor: '#333'
            }
          },
          data: filteredData.map(v => ({ value: v.count, name: v.institutionName }))
        }]
      }
    },

    getIdentityText(identity) {
      const textMap = {
        1: 'Admin',
        2: 'User',
        3: '未审核'
      };
      return textMap[identity] || '未知';
    },

    getIdentityBadge(identity) {
      if (identity === 3) {
        // 身份为3时：红字，无背景
        return {
          color: '#ef4444',
          background: 'transparent'
        };
      }

      const colors = {
        1: 'linear-gradient(to right, #8b5cf6, #ec4899)', // Admin - 紫粉渐变
        2: 'linear-gradient(to right, #3b82f6, #06b6d4)', // User - 蓝青渐变
      };

      return {
        background: colors[identity] || '#6b7280',
        color: 'white'
      };
    },

    // Get avatar color
    getAvatarColor(identity) {
      const colors = {
        1: 'linear-gradient(135deg, #a855f7, #f472b6)',
        2: 'linear-gradient(135deg, #60a5fa, #34d399)',
        3: 'linear-gradient(135deg, #60a5fa, #34d399)',
      };
      return colors[identity] || '#6b7280';
    },
  },
};
</script>
<style scoped>
/* 基本样式和布局 */
.user-management-container {
  width: 100%;
  height: 100%;
  min-height: 100%;
  /*border: 1px solid red;*/
  position: relative;
  overflow-y: auto;
  overflow-x: hidden;
  background: #fff;
  /*padding-top: 80px;*/
  padding-bottom: 12px;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  font-family: 'PingFang SC', 'PingFang TC', 'Microsoft YaHei', 'Helvetica Neue', Helvetica, Arial, sans-serif;
}

.header-container {
  width: calc(100% - 48px);
  margin: 0 24px;
  background-color: rgba(255, 255, 255, 0.9);
  /*border-bottom: 1px solid rgba(229, 231, 235, 0.5);*/
  /*box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);*/
}

.header-content {
  width: 100%;
  /*margin: 0 auto;*/
  padding: 24px 24px 0 24px;
  display: flex;
  box-sizing: border-box;
  align-items: center;
  justify-content: space-between;
  /*border: 1px solid blue;*/
}
.created-column {
  width: 200px;
  /*min-width: 150px;*/
  /*max-width: 150px;*/
  white-space: nowrap; /* 防止内容换行 */
  overflow: hidden;
  text-overflow: ellipsis; /* 超长显示省略号 */
}
.header-left, .header-right, .search-filter-group, .total-users-badge, .pagination-left, .pagination-right, .pagination-content {
  display: flex;
  align-items: center;
  gap: 16px;
}
.search-filter-group { gap: 12px; }
.total-users-badge { gap: 8px; }

.main-content {
  width: calc(100% - 48px);
  /*border: 1px solid red;*/
  margin: 0 24px;
  padding: 20px 24px 32px 24px;
  box-sizing: border-box;
  /*height: calc(100vh - 270px);*/
  /*overflow-y: auto;*/
}

/* 按钮样式 */
button {
  cursor: pointer;
  border: none;
  background-color: transparent;
  transition: all 0.2s;
}

.return-button {
  display: flex;
  align-items: center;
  color: #4b5563;
  font-size: 14px;
  font-weight: 500;
  margin-right: 30px;
}
.return-button .icon-wrapper {
  padding: 8px;
  border-radius: 50%;
  transition: background-color 0.2s;
}
.return-button .icon-wrapper i {
  font-size: 20px;
}

.back-icon {
  width: 18px;
  height: 18px;
  display: block;
}
.return-button:hover { color: #111827; }
.return-button:hover .icon-wrapper { background-color: #f3f4f6; }

.platform-title {
  font-size: 22px;
  font-weight: 700;
  color: #111827;
  line-height: 1.2;
}

.filter-button {
  padding:  8px 12px;
  background-color: #f3f4f6;
  border-radius: 12px;
  color: #4b5563;
}
.filter-button:hover { background-color: #e5e7eb; }
.export-csv-button {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background: linear-gradient(to right, #10b981, #059669);
  color: white;
  border-radius: 12px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  font-size: 14px;
  font-weight: 500;
}
.export-csv-button:hover {
  background: linear-gradient(to right, #059669, #047857);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
}

/* Element UI 搜索框样式重写 */
.search-input {
  width: 330px;
}

::v-deep .el-input__inner {
  padding: 12px;
  border: 1px solid #d1d5db;
  border-radius: 12px;
  background-color: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(4px);
  color: #374151;
  font-size: 14px;
  height: 40px;
  transition: all 0.2s;
}

::v-deep .el-input__inner:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.search-button {
  border-radius: 0 12px 12px 0 !important;
  height: 40px;
  background-color: #1890ff;
  border-color: #1890ff;
}

/* 徽章 */
.total-users-badge {
  padding: 2px 16px;
  min-height: 52px;
  box-sizing: border-box;
  background: linear-gradient(to right, #dbeafe, #e0e7ff);
  border-radius: 12px;
  border: 1px solid #bfdbfe;
}
.total-users-text { font-size: 14px; font-weight: 500; color: #4b5563; }
.total-users-count { font-size: 25px; line-height: 1; font-weight: bold; color: #2563eb; padding: 2px 0; }

/* 卡片和表格 */
.table-card {
  background-color: white;
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid #f3f4f6;
  margin-bottom: 15px;
}
.tabs-container {
  padding: 8px 24px 8px;
  display: flex;
  align-items: center;
}

.tabs-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  width: 100%;
  min-height: 54px;
  /*border: 1px solid red;*/
}

.panel-search-group {
  margin-left: auto;
}

.tabs-wrapper {
  display: flex;
  gap: 4px;
  padding: 5px;
  background-color: #f3f4f6;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
}
.tab-button {
  display: flex;
  align-items: center;
  padding: 10px 22px;
  font-size: 14px;
  font-weight: 500;
  border-radius: 8px;
  color: #6b7280;
}
.tab-button.active {
  background-color: #ffffff;
  color: #2563eb;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}
.tab-text { margin-left: 8px; }
.tab-count {
  margin-left: 8px;
  padding: 2px 8px;
  font-size: 12px;
  border-radius: 50px;
}
.tab-count.users { background-color: #dbeafe; color: #2563eb; }
.tab-count.admin { background-color: #f3e8ff; color: #7c3aed; }

.table-container { padding: 18px 24px 24px; flex: 1;width: 100%;box-sizing: border-box; }
.table-wrapper {
  overflow: hidden;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}
table {
  width: 100%;
  border-collapse: collapse;
}
th, td {
  padding: 16px 24px;
  text-align: left;
  font-size: 14px;
}
th {
  background: linear-gradient(to right, #f9fafb, #f3f4f6);
  border-bottom: 1px solid #e5e7eb;
  font-size: 12px;
  font-weight: 600;
  color: #4b5563;
  letter-spacing: 0.05em;
}
tbody tr {
  border-bottom: 1px solid #f3f4f6;
  transition: all 0.2s;
}
tbody tr:last-child {
  border-bottom: none;
}
tbody tr:hover {
  background-color: rgba(249, 250, 251, 0.5);
}
.cell-content { color: #111827; }
.cell-content.font-medium { font-weight: 500; }
.cell-content-secondary { color: #6b7280; font-size: 12px; }

.loading-cell {
  text-align: center;
  color: #6b7280;
  padding: 40px;
  font-size: 16px;
}

.user-info-cell { display: flex; align-items: center; gap: 12px; }
.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 14px;
  font-weight: 500;
  /*border: 2px solid white;*/
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}
.institution-cell {
  display: flex;
  align-items: center;
  cursor: pointer;
  padding: 8px 12px;
  border-radius: 8px;
  transition: all 0.2s;
  color: #000 !important;
}
.institution-text {
  display: inline-block;
  margin-right: 8px;
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.institution-cell .edit-icon-wrapper {
  color: #9ca3af;
  opacity: 0;
  transition: opacity 0.2s;
}
.institution-cell:hover {
  color: #2563eb;
  background-color: #dbeafe;
}
.institution-cell:hover .edit-icon-wrapper { opacity: 1; }

.edit-institution-cell { display: flex; align-items: center; gap: 8px; }
.edit-input {
  font-size: 14px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 8px 12px;
  width: 160px;
  outline: none;
}
.edit-input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.identity-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 12px 6px 12px;
  border-radius: 50px;
  font-size: 12px;
  font-weight: 500;
}

.control-buttons {
  display: flex;
  align-items: center;
  gap: 8px;
}
.role-button {
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 500;
  border-radius: 8px;
}
.role-button.admin { background-color: #e9d5ff; color: #8b5cf6; }
.role-button.admin.active { background: linear-gradient(to right, #8b5cf6, #ec4899); color: white; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
.role-button.admin:hover:not(.active) { background: linear-gradient(to right, #8b5cf6, #ec4899); color: #fff; }

.role-button.user { background-color: #d1fae5; color: #059669; }
.role-button.user.active { background: linear-gradient(135deg, #60a5fa, #34d399); color: white; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
.role-button.user:hover:not(.active) { background: linear-gradient(135deg, #60a5fa, #34d399); color: #fff }

.icon-button {
  padding: 8px;
  border-radius: 8px;
}
.icon-button.save-button { color: #059669; }
.icon-button.save-button:hover { background-color: #f0fdf4; }
.icon-button.cancel-button { color: #4b5563; }
.icon-button.cancel-button:hover { background-color: #f9fafb; }
.icon-button.delete-button { color: #ef4444; }
.icon-button.delete-button:hover { background-color: #fef2f2; }

/* 特殊行样式 */
.highlight-row {
  color: #ef6d6e;
}

/* 删除原有的分页相关CSS，替换为以下样式 */

/* 分页容器样式 */
.pagination-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 20px;
  border-top: 1px solid #e5e7eb;
  margin-top: 20px;
  background-color: #fff;
}


.pagination-info {
  font-size: 14px;
  color: #6b7280;
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pagination-btn {
  padding: 6px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  background: #ffffff;
  color: #374151;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.pagination-btn:hover:not(:disabled) {
  background: #f9fafb;
  border-color: #d1d5db;
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination-btn.active {
  background: #374151;
  color: white;
  border-color: #374151;
}


.page-numbers {
  display: flex;
  align-items: center;
  gap: 4px;
}

.page-number {
  min-width: 32px;
  text-align: center;
}

.page-size-selector {
  display: flex;
  align-items: center;
  gap: 8px;
}

.page-size-select {
  padding: 6px 8px;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  background: #ffffff;
  color: #374151;
  font-size: 12px;
  cursor: pointer;
}

.chart-container{
  height: calc(100vh - 395px);
  /*border: 1px solid red;*/
}

/* 响应式分页样式 */
@media (max-width: 768px) {
  .pagination-container {
    flex-direction: column;
    gap: 16px;
    text-align: center;
  }

  .pagination-controls {
    flex-wrap: wrap;
    justify-content: center;
  }

  .page-numbers {
    order: -1;
    margin-bottom: 8px;
  }
}

/* ====================== DARK THEME - 分层设计 ====================== */


.chart-layout {
  display: flex;
  gap: 24px;
  height: 100%;
}

.chart-left {
  flex: 2;
  min-width: 0;
}

.chart-right {
  flex: 1;
  min-width: 300px;
}

.institution-table-container {
  height: 100%;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
  background-color: white;
}

.table-header {
  display: grid;
  grid-template-columns: 60px 1fr 80px;
  background: linear-gradient(to right, #f9fafb, #f3f4f6);
  border-bottom: 1px solid #e5e7eb;
  padding: 12px 16px;
  font-weight: 600;
  font-size: 12px;
  color: #4b5563;
  letter-spacing: 0.05em;
}

.table-body {
  height: calc(100% - 48px);
  overflow-y: auto;
}

.table-row {
  display: grid;
  grid-template-columns: 60px 1fr 80px;
  padding: 12px 16px;
  border-bottom: 1px solid #f3f4f6;
  transition: background-color 0.2s;
}

.table-row:hover {
  background-color: rgba(249, 250, 251, 0.5);
}

.table-row:last-child {
  border-bottom: none;
}

.table-cell {
  font-size: 14px;
  display: flex;
  align-items: center;
}

.table-cell.index {
  font-weight: 500;
  color: #6b7280;
  justify-content: center;
}

.table-cell.name {
  color: #111827;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.table-cell.count {
  font-weight: 600;
  color: #2563eb;
  justify-content: center;
}

/* 来源标签 */
.source-tag-container {
  display: flex;
  justify-content: center;
}

.source-tag {
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  border-radius: 50px;
  font-size: 12px;
  font-weight: 500;
  text-align: center;
}

.source-tag.primary {
  background-color: #dbeafe;
  color: #1d4ed8;
}

.source-tag.success {
  background-color: #d1fae5;
  color: #059669;
}

.source-tag.warning {
  background-color: #fef3c7;
  color: #d97706;
}

.source-tag.danger {
  background-color: #fee2e2;
  color: #dc2626;
}

.source-tag.purple {
  background-color: #f3e8ff;
  color: #7c3aed;
}

.source-tag.dark-primary {   color:#93c5fd; } /* blue-300，8.15:1 */
.source-tag.dark-success {   color:#34d399; } /* emerald-400，7.88:1 */
.source-tag.dark-warning {  color:#fbbf24; } /* amber-400，8.97:1 */
.source-tag.dark-danger  {   color:#f87171; } /* red-400，5.84:1 */
.source-tag.dark-purple  {   color:#c4b5fd; } /* violet-300，8.25:1 */
</style>

<style>
body.app-dark .user-management-container {
  background: #101729;
  color: #dbe3f6;
}

body.app-dark .header-container {
  background-color: rgba(21, 26, 36, 0.92);
}

body.app-dark .return-button {
  color: #ffffff;
}

body.app-dark .return-button:hover {
  color: #e4ebfa;
}

body.app-dark .platform-title {
  color: #e5ecfb;
}

body.app-dark .return-button:hover .icon-wrapper {
  background-color: #2f3748;
}

body.app-dark .filter-button {
  background-color: #2a3242;
  color: #c2ccdf;
}

body.app-dark .filter-button:hover {
  background-color: #354058;
}

body.app-dark .total-users-badge {
  background: #242e43;
  border: 1px solid #3f5d95;
}

body.app-dark .total-users-text {
  color: #b7c2d8;
}

body.app-dark .total-users-count {
  color: #56a2ff;
}

body.app-dark .search-input .el-input__inner {
  border-color: #394458;
  background-color: #252d3d;
  color: #dbe3f6;
}

body.app-dark .search-input .el-input__wrapper {
  background-color: #252d3d !important;
  box-shadow: 0 0 0 1px #394458 inset !important;
}

body.app-dark .search-input .el-input__wrapper.is-focus {
  box-shadow: 0 0 0 1px #56a2ff inset !important;
}

body.app-dark .search-input .el-input__inner::placeholder {
  color: #8e9ab2;
}

body.app-dark .table-card,
body.app-dark .table-container,
body.app-dark .institution-table-container,
body.app-dark .pagination-container {
  background: #1f2633;
  border-color: #323c4e;
}

body.app-dark .table-wrapper {
  border-color: #323c4e;
}

body.app-dark th,
body.app-dark .table-header {
  background: linear-gradient(to right, #2a3242, #252d3d);
  border-bottom-color: #323c4e;
  color: #b7c2d8;
}

body.app-dark td,
body.app-dark tbody tr,
body.app-dark .table-row {
  border-bottom-color: #2f394b;
}

body.app-dark tbody tr:hover,
body.app-dark .table-row:hover {
  background-color: #262f3f;
}

body.app-dark .cell-content,
body.app-dark .table-cell.name {
  color: #e5ecfb;
}

body.app-dark .cell-content-secondary,
body.app-dark .loading-cell,
body.app-dark .table-cell.index,
body.app-dark .pagination-info {
  color: #97a3bc;
}

body.app-dark .institution-cell {
  color: #d5deee !important;
}

body.app-dark .institution-cell:hover {
  color: #8eb8ff;
  background-color: #2b3952;
}

body.app-dark .edit-input,
body.app-dark .page-size-select {
  background: #252d3d;
  border-color: #394458;
  color: #dbe3f6;
}

body.app-dark .edit-input:focus {
  border-color: #5b8cff;
  box-shadow: 0 0 0 3px rgba(91, 140, 255, 0.2);
}

body.app-dark .pagination-btn {
  background: #252d3d;
  border-color: #394458;
  color: #c5d0e6;
}

body.app-dark .pagination-btn:hover:not(:disabled) {
  background: #313b4f;
  border-color: #4a5873;
}

body.app-dark .pagination-btn.active {
  background: #4f7fff;
  border-color: #4f7fff;
  color: #fff;
}

body.app-dark .tab-button {
  color: #b8c3d9;
}

body.app-dark .tabs-wrapper {
  width: fit-content;
  max-width: 100%;
  background-color: #3a4458;
  border: 1px solid rgba(128, 145, 175, 0.35);
}

body.app-dark .tab-button.active {
  background: #4d5a71;
  color: #56a2ff;
  box-shadow: inset 0 0 0 1px rgba(126, 146, 180, 0.45);
}

body.app-dark .icon-button.save-button:hover {
  background-color: #1d3a32;
}

body.app-dark .icon-button.cancel-button:hover {
  background-color: #30384a;
}

body.app-dark .icon-button.delete-button:hover {
  background-color: #4a2c33;
}
</style>
