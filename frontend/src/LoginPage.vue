<script setup>
import { apiBaseUrl, apiFetch } from './api.js'
import { currentProfile } from './currentProfile.js'
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const mode = ref('login')
const stage = ref('credentials')
const loading = ref(false)
const error = ref('')
const notice = ref('')
const challengeId = ref('')
const maskedEmail = ref('')
const retryAt = ref(0)
const form = reactive({ username: '', email: '', password: '', passwordConfirm: '', code: '' })

function reset(nextMode = mode.value) {
  mode.value = nextMode
  stage.value = 'credentials'
  challengeId.value = ''
  form.code = ''
  error.value = ''
  notice.value = ''
}

async function post(path, body) {
  const response = await apiFetch(`${apiBaseUrl}/api/auth/${path}/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.detail || 'The request failed. Please try again.')
  return data
}

function nextStep(data) {
  if (data.step === 'email_required') {
    stage.value = 'enroll'
    notice.value = data.detail
  } else if (data.step === 'activation' || data.step === 'login') {
    stage.value = data.step
    challengeId.value = data.challengeId
    maskedEmail.value = data.maskedEmail
    retryAt.value = Date.now() + (data.retryAfter || 60) * 1000
    notice.value = data.detail
    form.code = ''
  } else if (data.step === 'login_required') {
    reset('login')
    form.password = ''
    form.passwordConfirm = ''
    notice.value = data.detail
  } else if (data.step === 'authenticated') {
    currentProfile.value = null
    router.push('/home_page')
  }
}

async function submit() {
  error.value = ''
  notice.value = ''
  if (stage.value === 'credentials' && mode.value === 'register' && form.password !== form.passwordConfirm) {
    error.value = 'The passwords do not match.'
    return
  }
  loading.value = true
  try {
    let data
    if (stage.value === 'credentials') {
      data = await post(mode.value, {
        username: form.username,
        password: form.password,
        ...(mode.value === 'register' ? { email: form.email } : {}),
      })
    } else if (stage.value === 'enroll') {
      data = await post('enroll-email', { email: form.email })
    } else {
      data = await post('verify', { challengeId: challengeId.value, code: form.code })
    }
    nextStep(data)
  } catch (requestError) {
    error.value = requestError.message || 'Unable to connect to the server.'
  } finally {
    loading.value = false
  }
}

async function resend() {
  error.value = ''
  notice.value = ''
  if (Date.now() < retryAt.value) {
    error.value = 'Please wait one minute before requesting another code.'
    return
  }
  loading.value = true
  try {
    nextStep(await post('resend', { challengeId: challengeId.value }))
  } catch (requestError) {
    error.value = requestError.message || 'Unable to send a new code.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="login-page">
    <section class="login-card">
      <p class="game-name">⚔ RateMate</p>
      <h1>{{ stage === 'credentials' ? (mode === 'login' ? 'Welcome back' : 'Create an account') : stage === 'enroll' ? 'Add your email' : 'Check your email' }}</h1>
      <p class="hint">
        {{ stage === 'credentials' ? (mode === 'login' ? 'Sign in with your username and password.' : 'Register with an email address you can verify.') : stage === 'enroll' ? 'Your existing account needs a verified email address before you can sign in.' : `Enter the six-digit code sent to ${maskedEmail}. It expires in five minutes.` }}
      </p>
      <div v-if="stage === 'credentials'" class="tabs">
        <button :class="{ active: mode === 'login' }" type="button" @click="reset('login')">Sign in</button>
        <button :class="{ active: mode === 'register' }" type="button" @click="reset('register')">Register</button>
      </div>
      <form @submit.prevent="submit">
        <template v-if="stage === 'credentials'">
          <label for="username">Username</label>
          <input id="username" v-model.trim="form.username" autocomplete="username" minlength="3" maxlength="30" placeholder="Enter your username" required>
          <template v-if="mode === 'register'">
            <label for="email">Email address</label>
            <input id="email" v-model.trim="form.email" autocomplete="email" type="email" placeholder="you@example.com" required>
          </template>
          <label for="password">Password</label>
          <input id="password" v-model="form.password" :autocomplete="mode === 'login' ? 'current-password' : 'new-password'" :minlength="mode === 'register' ? 8 : undefined" type="password" :placeholder="mode === 'register' ? 'At least 8 characters' : 'Enter your password'" required>
          <template v-if="mode === 'register'">
            <small class="password-hint">Use at least 8 characters with uppercase and lowercase letters and a number.</small>
            <label for="password-confirm">Confirm password</label>
            <input id="password-confirm" v-model="form.passwordConfirm" autocomplete="new-password" minlength="8" type="password" placeholder="Enter your password again" required>
          </template>
        </template>
        <template v-else-if="stage === 'enroll'">
          <label for="email">Email address</label>
          <input id="email" v-model.trim="form.email" autocomplete="email" type="email" placeholder="you@example.com" required>
        </template>
        <template v-else>
          <label for="code">Six-digit code</label>
          <input id="code" v-model.trim="form.code" autocomplete="one-time-code" inputmode="numeric" pattern="[0-9]{6}" maxlength="6" placeholder="000000" required>
        </template>
        <p v-if="notice" class="message success" role="status">{{ notice }}</p>
        <p v-if="error" class="message error" role="alert">{{ error }}</p>
        <button class="submit-button" :disabled="loading" type="submit">
          {{ loading ? 'Please wait…' : stage === 'credentials' ? (mode === 'login' ? 'Sign in' : 'Register') : stage === 'enroll' ? 'Send verification code' : 'Verify code' }}
        </button>
        <template v-if="stage === 'activation' || stage === 'login'">
          <button class="text-button" type="button" :disabled="loading" @click="resend">Resend code</button>
          <button class="text-button" type="button" @click="reset('login')">Back to sign in</button>
        </template>
        <button v-else-if="stage === 'enroll'" class="text-button" type="button" @click="reset('login')">Back to sign in</button>
      </form>
    </section>
  </main>
</template>

<style scoped>
.login-page { align-items: center; background: linear-gradient(135deg, #26183d, #6a2f52); display: flex; justify-content: center; min-height: 100vh; padding: 24px; }
.login-card { background: #fffaf3; border-radius: 18px; box-shadow: 0 18px 45px #160d264d; max-width: 420px; padding: 38px; width: 100%; }
.game-name { color: #8c4653; font-weight: 700; margin: 0 0 28px; }
.hint { color: #70646a; margin: 0 0 24px; }
.login-card h1 { margin: 0 0 8px; }
.tabs { background: #efe5dc; border-radius: 10px; display: grid; grid-template-columns: 1fr 1fr; margin-bottom: 24px; padding: 4px; }
.tabs button { background: transparent; border: 0; border-radius: 7px; color: #75666d; cursor: pointer; padding: 9px; }
.tabs .active { background: white; color: #6d3451; font-weight: 700; }
form { display: flex; flex-direction: column; }
label { font-size: 14px; font-weight: 700; margin: 0 0 7px; }
input { border: 1px solid #d9cdd0; border-radius: 8px; font-size: 16px; margin: 0 0 18px; padding: 11px 12px; }
input:focus { border-color: #9a4a59; outline: 2px solid #e7b4a566; }
.password-hint { color: #70646a; margin: -12px 0 16px; }
.message { font-size: 14px; margin: 0 0 16px; }
.error { color: #b43342; }
.success { color: #307347; }
.submit-button { background: #783950; border: 0; border-radius: 8px; color: white; cursor: pointer; font-weight: 700; padding: 12px; }
.submit-button:disabled { cursor: wait; opacity: .65; }
.text-button { background: transparent; border: 0; color: #783950; cursor: pointer; margin-top: 12px; padding: 6px; }
</style>
