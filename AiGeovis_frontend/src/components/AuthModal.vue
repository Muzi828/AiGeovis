<template>
  <div>
    <transition name="modal">
      <div v-if="visible" class="auth-modal-overlay" @click="closeModal">
        <div class="auth-modal" @click.stop>
          <div v-show="isLoading" class="loading-overlay">
            <div class="loading-spinner">
              <div class="spinner-ring"></div>
              <p class="loading-text">{{ loadingText }}</p>
            </div>
          </div>

          <button @click="closeModal" class="modal-close">x</button>

          <div class="auth-content">
            <h2 class="form-title">{{ getFormTitle }}</h2>

            <form class="auth-form" @submit.prevent="handleSubmit" autocomplete="off">
              <template v-if="currentMode === 'login'">
                <div class="form-group">
                  <label class="form-label">Username</label>
                  <input
                    type="text"
                    v-model="username"
                    class="form-input"
                    placeholder="Enter your username"
                    required
                  />
                </div>

                <div class="form-group">
                  <label class="form-label">Password</label>
                  <input
                    :type="showPassword ? 'text' : 'password'"
                    v-model="password"
                    class="form-input"
                    placeholder="Enter your password"
                    required
                  />
                </div>

                <div v-if="errorMessage" class="error-message">
                  {{ errorMessage }}
                </div>

                <div class="button-group">
                  <button type="button" @click="setMode('register')" class="secondary-button">
                    Register
                  </button>
                  <button type="submit" :disabled="isLoading" class="primary-button">
                    <div v-if="isLoading" class="loading-icon"></div>
                    {{ isLoading ? 'Logging in...' : 'Login' }}
                  </button>
                </div>
              </template>

              <template v-else-if="currentMode === 'register'">
                <div class="form-group">
                  <label class="form-label">Username (at least 2 characters)</label>
                  <input
                    type="text"
                    v-model="name"
                    class="form-input"
                    placeholder="Enter username (at least 2 characters)"
                    @blur="validateName"
                    required
                    autocomplete="new-username"
                  />
                  <div v-if="nameError" class="field-error">{{ nameError }}</div>
                </div>

                <div class="form-group">
                  <label class="form-label">Password (at least 6 characters)</label>
                  <input
                    :type="showPassword ? 'text' : 'password'"
                    v-model="password"
                    class="form-input"
                    placeholder="Enter password (at least 6 characters)"
                    @blur="validatePassword"
                    required
                    autocomplete="new-password"
                  />
                  <div v-if="passwordError" class="field-error">{{ passwordError }}</div>
                </div>

                <div class="form-group">
                  <label class="form-label">Email</label>
                  <input
                    type="email"
                    v-model="email"
                    class="form-input"
                    placeholder="Enter email address"
                    @blur="validateEmail"
                    required
                    autocomplete="new-email"
                  />
                  <div v-if="emailError" class="field-error">{{ emailError }}</div>
                </div>

                <div class="form-group">
                  <label class="form-label">Institution</label>
                  <input
                    type="text"
                    v-model="unit"
                    class="form-input"
                    placeholder="Enter institution name"
                    required
                    autocomplete="new-organization"
                  />
                </div>

                <div class="form-group">
                  <label class="form-label">Phone Number</label>
                  <input
                    type="tel"
                    v-model="phone"
                    class="form-input"
                    placeholder="Enter phone number"
                    required
                    autocomplete="new-number"
                  />
                </div>

                <div v-if="registerSuccess" class="success-message">
                  {{ registerSuccess }}
                </div>

                <div v-if="registerError" class="error-message">
                  {{ registerError }}
                </div>

                <div class="button-group">
                  <button type="button" @click="setMode('login')" class="secondary-button">
                    Cancel
                  </button>
                  <button type="submit" :disabled="isLoading" class="primary-button">
                    <div v-if="isLoading" class="loading-icon"></div>
                    {{ isLoading ? 'Registering...' : 'Register' }}
                  </button>
                </div>
              </template>
            </form>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script>
import axios from 'axios'

function md5(input) {
  function cmn(q, a, b, x, s, t) {
    a = (a + q + x + t) | 0
    return (((a << s) | (a >>> (32 - s))) + b) | 0
  }
  function ff(a, b, c, d, x, s, t) { return cmn((b & c) | (~b & d), a, b, x, s, t) }
  function gg(a, b, c, d, x, s, t) { return cmn((b & d) | (c & ~d), a, b, x, s, t) }
  function hh(a, b, c, d, x, s, t) { return cmn(b ^ c ^ d, a, b, x, s, t) }
  function ii(a, b, c, d, x, s, t) { return cmn(c ^ (b | ~d), a, b, x, s, t) }
  function md5cycle(state, k) {
    let [a, b, c, d] = state
    a = ff(a, b, c, d, k[0], 7, -680876936); d = ff(d, a, b, c, k[1], 12, -389564586)
    c = ff(c, d, a, b, k[2], 17, 606105819); b = ff(b, c, d, a, k[3], 22, -1044525330)
    a = ff(a, b, c, d, k[4], 7, -176418897); d = ff(d, a, b, c, k[5], 12, 1200080426)
    c = ff(c, d, a, b, k[6], 17, -1473231341); b = ff(b, c, d, a, k[7], 22, -45705983)
    a = ff(a, b, c, d, k[8], 7, 1770035416); d = ff(d, a, b, c, k[9], 12, -1958414417)
    c = ff(c, d, a, b, k[10], 17, -42063); b = ff(b, c, d, a, k[11], 22, -1990404162)
    a = ff(a, b, c, d, k[12], 7, 1804603682); d = ff(d, a, b, c, k[13], 12, -40341101)
    c = ff(c, d, a, b, k[14], 17, -1502002290); b = ff(b, c, d, a, k[15], 22, 1236535329)
    a = gg(a, b, c, d, k[1], 5, -165796510); d = gg(d, a, b, c, k[6], 9, -1069501632)
    c = gg(c, d, a, b, k[11], 14, 643717713); b = gg(b, c, d, a, k[0], 20, -373897302)
    a = gg(a, b, c, d, k[5], 5, -701558691); d = gg(d, a, b, c, k[10], 9, 38016083)
    c = gg(c, d, a, b, k[15], 14, -660478335); b = gg(b, c, d, a, k[4], 20, -405537848)
    a = gg(a, b, c, d, k[9], 5, 568446438); d = gg(d, a, b, c, k[14], 9, -1019803690)
    c = gg(c, d, a, b, k[3], 14, -187363961); b = gg(b, c, d, a, k[8], 20, 1163531501)
    a = gg(a, b, c, d, k[13], 5, -1444681467); d = gg(d, a, b, c, k[2], 9, -51403784)
    c = gg(c, d, a, b, k[7], 14, 1735328473); b = gg(b, c, d, a, k[12], 20, -1926607734)
    a = hh(a, b, c, d, k[5], 4, -378558); d = hh(d, a, b, c, k[8], 11, -2022574463)
    c = hh(c, d, a, b, k[11], 16, 1839030562); b = hh(b, c, d, a, k[14], 23, -35309556)
    a = hh(a, b, c, d, k[1], 4, -1530992060); d = hh(d, a, b, c, k[4], 11, 1272893353)
    c = hh(c, d, a, b, k[7], 16, -155497632); b = hh(b, c, d, a, k[10], 23, -1094730640)
    a = hh(a, b, c, d, k[13], 4, 681279174); d = hh(d, a, b, c, k[0], 11, -358537222)
    c = hh(c, d, a, b, k[3], 16, -722521979); b = hh(b, c, d, a, k[6], 23, 76029189)
    a = hh(a, b, c, d, k[9], 4, -640364487); d = hh(d, a, b, c, k[12], 11, -421815835)
    c = hh(c, d, a, b, k[15], 16, 530742520); b = hh(b, c, d, a, k[2], 23, -995338651)
    a = ii(a, b, c, d, k[0], 6, -198630844); d = ii(d, a, b, c, k[7], 10, 1126891415)
    c = ii(c, d, a, b, k[14], 15, -1416354905); b = ii(b, c, d, a, k[5], 21, -57434055)
    a = ii(a, b, c, d, k[12], 6, 1700485571); d = ii(d, a, b, c, k[3], 10, -1894986606)
    c = ii(c, d, a, b, k[10], 15, -1051523); b = ii(b, c, d, a, k[1], 21, -2054922799)
    a = ii(a, b, c, d, k[8], 6, 1873313359); d = ii(d, a, b, c, k[15], 10, -30611744)
    c = ii(c, d, a, b, k[6], 15, -1560198380); b = ii(b, c, d, a, k[13], 21, 1309151649)
    a = ii(a, b, c, d, k[4], 6, -145523070); d = ii(d, a, b, c, k[11], 10, -1120210379)
    c = ii(c, d, a, b, k[2], 15, 718787259); b = ii(b, c, d, a, k[9], 21, -343485551)
    state[0] = (state[0] + a) | 0
    state[1] = (state[1] + b) | 0
    state[2] = (state[2] + c) | 0
    state[3] = (state[3] + d) | 0
  }
  function md5blk(s) {
    const md5blks = []
    for (let i = 0; i < 64; i += 4) {
      md5blks[i >> 2] = s.charCodeAt(i) + (s.charCodeAt(i + 1) << 8) +
        (s.charCodeAt(i + 2) << 16) + (s.charCodeAt(i + 3) << 24)
    }
    return md5blks
  }
  function md51(s) {
    let n = s.length
    const state = [1732584193, -271733879, -1732584194, 271733878]
    let i
    for (i = 64; i <= n; i += 64) md5cycle(state, md5blk(s.substring(i - 64, i)))
    s = s.substring(i - 64)
    const tail = new Array(16).fill(0)
    for (i = 0; i < s.length; i++) tail[i >> 2] |= s.charCodeAt(i) << ((i % 4) << 3)
    tail[i >> 2] |= 0x80 << ((i % 4) << 3)
    if (i > 55) { md5cycle(state, tail); tail.fill(0) }
    tail[14] = n * 8
    md5cycle(state, tail)
    return state
  }
  const hexChr = '0123456789abcdef'.split('')
  function rhex(n) {
    let s = ''
    for (let j = 0; j < 4; j++) s += hexChr[(n >> (j * 8 + 4)) & 0x0f] + hexChr[(n >> (j * 8)) & 0x0f]
    return s
  }
  return md51(input).map(rhex).join('')
}

export default {
  name: 'AuthModal',
  props: {
    visible: { type: Boolean, default: false },
    Lang: { type: String, default: 'EN' },
    defaultMode: { type: String, default: 'login' },
    customRegisterTitle: { type: String, default: '' },
  },
  emits: ['close', 'login-success'],
  data() {
    return {
      currentMode: this.defaultMode || 'login',
      username: '',
      password: '',
      loadingText: 'Under verification...',
      name: '',
      unit: '',
      phone: '',
      email: '',
      isLoading: false,
      showPassword: false,
      nameError: '',
      emailError: '',
      passwordError: '',
      errorMessage: '',
      registerError: '',
      registerSuccess: '',
    }
  },
  computed: {
    getFormTitle() {
      if (this.currentMode === 'register') return this.customRegisterTitle || 'AiGeovis Register'
      return 'AiGeovis Login'
    },
    isFormValid() {
      if (this.currentMode === 'login') return this.username.trim() && this.password.trim()
      if (this.currentMode === 'register') {
        return this.name.trim() && this.unit.trim() && this.phone.trim() && this.email.trim() && this.password.trim() &&
          !this.nameError && !this.emailError && !this.passwordError
      }
      return false
    },
  },
  watch: {
    visible(v) { if (v) this.resetForm() },
  },
  methods: {
    closeModal() {
      this.$emit('close')
      this.resetForm()
    },
    setMode(mode) {
      this.currentMode = mode || 'login'
      this.clearErrors()
      this.resetFields()
    },
    clearErrors() {
      this.nameError = ''
      this.emailError = ''
      this.passwordError = ''
      this.errorMessage = ''
      this.registerError = ''
      this.registerSuccess = ''
    },
    resetFields() {
      this.username = ''
      this.password = ''
      this.name = ''
      this.unit = ''
      this.phone = ''
      this.email = ''
    },
    resetForm() {
      this.currentMode = this.defaultMode || 'login'
      this.isLoading = false
      this.showPassword = false
      this.resetFields()
      this.clearErrors()
    },
    validateName() {
      if (!this.name.trim()) this.nameError = 'Please enter username'
      else if (this.name.length < 2) this.nameError = 'Username must be at least 2 characters'
      else this.nameError = ''
    },
    validateEmail() {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
      if (!this.email.trim()) this.emailError = 'Please enter email'
      else if (!emailRegex.test(this.email)) this.emailError = 'Please enter a valid email format'
      else this.emailError = ''
    },
    validatePassword() {
      if (!this.password.trim()) this.passwordError = 'Please enter password'
      else if (this.password.length < 6) this.passwordError = 'Password must be at least 6 characters'
      else this.passwordError = ''
    },
    handleSubmit() {
      if (this.currentMode === 'login') this.handleLogin()
      else if (this.currentMode === 'register') this.handleRegister()
    },
    handleLogin() {
      if (!this.username.trim()) { this.errorMessage = 'Please enter username'; return }
      if (!this.password.trim()) { this.errorMessage = 'Please enter password'; return }
      this.isLoading = true

      setTimeout(() => {
        axios.post('https://smartdata.las.ac.cn/citeinsight-pro/citeinsight-pro/citeinsightpro_api/HisCiteUser/login', {
          username: this.username,
          password: md5(this.password),
        }).then((res) => {
          if (res.data.code === 200) {
            window.localStorage.setItem('userInfoAiGeovis', JSON.stringify(res.data.obj))
            window.localStorage.setItem('app_user_name', this.username)
            window.localStorage.setItem('mssIsLogin', 'true')
            this.$emit('login-success', res.data.obj)
            this.closeModal()
          } else {
            this.errorMessage = res.data.obj || 'Login failed, please check username and password'
          }
        }).catch(() => {
          this.errorMessage = 'Network connection failed, please try again later'
        }).finally(() => {
          this.isLoading = false
        })
      }, 800)
    },
    handleRegister() {
      this.validateName()
      this.validateEmail()
      this.validatePassword()

      if (!this.unit.trim()) { this.registerError = 'Please enter institution'; return }
      if (!this.phone.trim()) { this.registerError = 'Please enter phone number'; return }
      if (!this.isFormValid) { this.registerError = 'Please complete the registration information and check the format'; return }

      this.isLoading = true
      this.registerError = ''
      axios.post('https://smartdata.las.ac.cn/citeinsight-pro/citeinsight-pro/citeinsightpro_api/HisCiteUser/register', {
        email: this.email,
        password: this.password,
        username: this.name,
        phone: this.phone,
        unit: this.unit,
        systemType: '1',
      }).then((res) => {
        if (res.data.code === 200) {
          this.registerSuccess = 'Registration successful! Please login with your new account.'
          setTimeout(() => this.setMode('login'), 1200)
        } else {
          this.registerError = res.data.obj || 'Registration failed, please try again later'
        }
      }).catch(() => {
        this.registerError = 'Registration failed, please try again later'
      }).finally(() => {
        this.isLoading = false
      })
    },
  },
}
</script>

<style scoped>
.auth-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(3px);
  z-index: 3500;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.auth-modal {
  background: white;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  width: 100%;
  max-width: 450px;
  max-height: 90vh;
  overflow-y: auto;
  position: relative;
  animation: modalFadeIn 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes modalFadeIn {
  from { transform: scale(0.9); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}

.modal-enter-active, .modal-leave-active { transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
.modal-enter, .modal-leave-to { opacity: 0; }
.modal-enter .auth-modal, .modal-leave-to .auth-modal { transform: scale(0.9); }

.modal-close {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 32px;
  height: 32px;
  cursor: pointer;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6b7280;
  transition: all 0.2s ease;
  z-index: 10;
  background: none;
  border: none;
  font-size: 20px;
}
.modal-close:hover { background: rgba(0, 0, 0, 0.1); color: #374151; }

.auth-content { padding: 24px; }
.form-title { margin: 0 0 24px 0; color: #333; text-align: center; font-size: 18px; font-weight: bold; }
.auth-form { margin: 0; }
.form-group { margin-bottom: 16px; }
.form-label { display: block; margin-bottom: 8px; color: #555; font-size: 14px; }
.form-input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 16px; box-sizing: border-box; }
.form-input:focus { outline: none; border-color: #1976d2; }
.form-input::placeholder { color: #999; }
.field-error { color: #f44336; font-size: 12px; margin-top: 4px; }
.error-message { color: #f44336; font-size: 14px; margin-bottom: 16px; text-align: center; }
.success-message { background-color: #d4edda; color: #155724; padding: 12px; border-radius: 4px; margin-bottom: 16px; border: 1px solid #c3e6cb; text-align: center; font-size: 14px; }

.button-group { display: flex; justify-content: space-between; gap: 16px; margin-top: 24px; }
.secondary-button { flex: 1; padding: 10px 24px; border: 1px solid #1f2937; border-radius: 4px; background-color: #fff; color: #1f2937; font-size: 14px; cursor: pointer; transition: all 0.2s; }
.secondary-button:hover { background-color: #f5f5f5; }
.primary-button { flex: 1; padding: 10px 24px; border: none; border-radius: 4px; background-color: #1f2937; color: #fff; font-size: 14px; cursor: pointer; transition: all 0.2s; display: flex; align-items: center; justify-content: center; gap: 8px; }
.primary-button:hover:not(:disabled) { background-color: rgb(31, 41, 55, 0.85); }
.primary-button:disabled { opacity: 0.8; cursor: not-allowed; }

.loading-icon {
  width: 16px;
  height: 16px;
  border: 2px solid #fff;
  border-top: 2px solid transparent;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.loading-overlay {
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  border-radius: 16px;
}

.loading-spinner { text-align: center; }
.spinner-ring {
  width: 40px;
  height: 40px;
  border: 3px solid #e2e8f0;
  border-top: 3px solid #374151;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 16px;
}
.loading-text { color: #64748b; font-size: 14px; font-weight: 500; }

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@media (max-width: 640px) {
  .auth-modal { width: 90%; margin: 0 5%; }
  .auth-content { padding: 20px; }
}
</style>
