<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import AppLayout from '../components/AppLayout.vue'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'
const emptyProfile = { username: '', email: '', bio: '', avatarUrl: '' }
const profile = reactive({ ...emptyProfile, password: '', passwordConfirm: '' })
const savedProfile = reactive({ ...emptyProfile })
const avatarInput = ref(null)
const pendingAvatarFile = ref(null)
const loading = ref(true)
const saving = ref(false)
const loadError = ref('')
const status = ref('')
const error = ref('')
const avatarInitial = computed(() => profile.username.trim().charAt(0).toUpperCase() || '?')

function applyProfile(data) {
  const latest = {
    username: data.userName ?? '',
    email: data.email ?? '',
    bio: data.bio ?? '',
    avatarUrl: data.avatarUrl ?? '',
  }
  Object.assign(profile, latest, { password: '', passwordConfirm: '' })
  Object.assign(savedProfile, latest)
  pendingAvatarFile.value = null
}

async function loadProfile() {
  loading.value = true
  loadError.value = ''
  try {
    const response = await fetch(`${apiBaseUrl}/api/auth/profile/`)
    const data = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(data.detail || 'Unable to load your profile.')
    applyProfile(data)
    status.value = 'Profile is up to date'
  } catch (requestError) {
    loadError.value = requestError.message || 'Unable to connect to the server.'
  } finally {
    loading.value = false
  }
}

function changed() {
  status.value = 'Unsaved changes'
  error.value = ''
}

function selectAvatar() {
  avatarInput.value?.click()
}

function updateAvatar(event) {
  const file = event.target.files?.[0]
  if (!file) return
  error.value = ''
  if (file.size > 5 * 1024 * 1024) {
    error.value = 'The avatar cannot be larger than 5 MB.'
    event.target.value = ''
    return
  }

  pendingAvatarFile.value = file
  profile.avatarUrl = URL.createObjectURL(file)
  changed()
}

async function save() {
  error.value = ''
  if (profile.password !== profile.passwordConfirm) {
    error.value = 'The two passwords do not match.'
    return
  }

  const hasChanges = profile.username !== savedProfile.username
    || profile.bio !== savedProfile.bio
    || Boolean(profile.password)
    || Boolean(pendingAvatarFile.value)
  if (!hasChanges) {
    status.value = 'Profile is up to date'
    return
  }

  const formData = new FormData()
  formData.append('userName', profile.username)
  formData.append('bio', profile.bio)
  if (profile.password) formData.append('password', profile.password)
  if (pendingAvatarFile.value) formData.append('avatar', pendingAvatarFile.value)

  saving.value = true
  status.value = 'Saving changes…'
  try {
    const response = await fetch(`${apiBaseUrl}/api/auth/profile/`, {
      method: 'POST',
      body: formData,
    })
    const data = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(data.detail || 'Unable to save your profile.')
    applyProfile(data)
    if (avatarInput.value) avatarInput.value.value = ''
    status.value = data.message || 'Profile saved'
  } catch (requestError) {
    error.value = requestError.message || 'Unable to connect to the server.'
    status.value = 'Changes not saved'
  } finally {
    saving.value = false
  }
}

function cancel() {
  Object.assign(profile, savedProfile, { password: '', passwordConfirm: '' })
  pendingAvatarFile.value = null
  if (avatarInput.value) avatarInput.value.value = ''
  error.value = ''
  status.value = 'Changes cancelled'
}

onMounted(loadProfile)
</script>

<template>
  <AppLayout>
    <div class="personal-heading">
      <div class="eyebrow">YOUR CORNER OF RATEMATE</div>
      <h1>User profile</h1>
      <p>View and update your basic account information.</p>
    </div>

    <div v-if="loading" class="profile-state" role="status">
      <span class="loading-spinner" />
      <p>Loading your profile…</p>
    </div>

    <div v-else-if="loadError" class="profile-state profile-load-error" role="alert">
      <h2>Unable to load your profile</h2>
      <p>{{ loadError }}</p>
      <button class="action-button" type="button" @click="loadProfile">Try again</button>
    </div>

    <form v-else class="profile-editor" @submit.prevent="save">
      <div class="profile-editor-heading">
        <div>
          <h2>Profile details</h2>
          <p>The values below show your current profile and can be edited directly.</p>
        </div>
        <span class="save-status">{{ status }}</span>
      </div>

      <section class="avatar-field" aria-labelledby="avatar-label">
        <div v-if="profile.avatarUrl" class="profile-photo-preview">
          <img :src="profile.avatarUrl" alt="Current profile avatar">
        </div>
        <div v-else class="profile-photo-preview">{{ avatarInitial }}</div>
        <div>
          <strong id="avatar-label">Avatar</strong>
          <p>JPG, PNG or WebP, up to 5 MB.</p>
          <input ref="avatarInput" class="visually-hidden" type="file" accept="image/jpeg,image/png,image/webp" @change="updateAvatar">
          <button type="button" class="action-button" @click="selectAvatar">Choose image</button>
        </div>
      </section>

      <div class="profile-form-grid">
        <label class="editor-field">
          Username
          <input v-model.trim="profile.username" autocomplete="username" minlength="3" maxlength="30" required @input="changed">
        </label>

        <label class="editor-field">
          Email address <span class="optional">Cannot be changed</span>
          <input v-model="profile.email" class="readonly-field" autocomplete="email" type="email" readonly>
        </label>

        <label class="editor-field profile-wide">
          Bio <span class="optional">Optional</span>
          <textarea v-model="profile.bio" rows="4" maxlength="300" placeholder="What do you enjoy rating?" @input="changed" />
          <small>{{ profile.bio.length }} / 300</small>
        </label>

        <label class="editor-field">
          New password <span class="optional">Leave blank to keep your current password</span>
          <input v-model="profile.password" autocomplete="new-password" type="password" minlength="6" placeholder="Enter a new password" @input="changed">
        </label>

        <label class="editor-field">
          Confirm new password
          <input v-model="profile.passwordConfirm" autocomplete="new-password" type="password" minlength="6" placeholder="Enter the new password again" @input="changed">
        </label>
      </div>

      <p v-if="error" class="profile-error" role="alert">{{ error }}</p>

      <div class="profile-form-footer">
        <p>Your changes will be saved to your account.</p>
        <div>
          <button type="button" class="action-button" :disabled="saving" @click="cancel">Cancel</button>
          <button class="action-button primary" :disabled="saving">{{ saving ? 'Saving…' : 'Save changes' }}</button>
        </div>
      </div>
    </form>
  </AppLayout>
</template>

<style scoped>
.profile-state {
  display: grid;
  place-items: center;
  max-width: 920px;
  min-height: 320px;
  padding: 40px;
  border: 1px solid #e5ebdf;
  border-radius: 12px;
  background: #fbfcf9;
  color: #7e8878;
  text-align: center;
}

.profile-state h2 { margin: 0; color: #273326; font-size: 20px; }
.profile-state p { margin: 8px 0 18px; }
.profile-load-error { display: flex; flex-direction: column; justify-content: center; }

.loading-spinner {
  width: 34px;
  height: 34px;
  border: 3px solid #dce5d6;
  border-top-color: var(--green);
  border-radius: 50%;
  animation: profile-spin .8s linear infinite;
}

@keyframes profile-spin { to { transform: rotate(360deg); } }

.profile-editor {
  max-width: 920px;
  padding: 28px;
  border: 1px solid #e5ebdf;
  border-radius: 12px;
  background: #fbfcf9;
}

.profile-editor-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  padding-bottom: 24px;
  border-bottom: 1px solid var(--line);
}

.profile-editor-heading h2 { margin: 0; font-size: 20px; }
.profile-editor-heading p { margin: 8px 0 0; color: #7e8878; font-size: 14px; }

.avatar-field {
  display: flex;
  align-items: center;
  gap: 22px;
  padding: 28px 0;
  border-bottom: 1px solid var(--line);
}

.avatar-field p { margin: 6px 0 12px; color: #8b9584; font-size: 12px; }

.profile-photo-preview {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 88px;
  height: 88px;
  overflow: hidden;
  border-radius: 50%;
  background: #e5ebdd;
  color: #5c714f;
  font-size: 30px;
  font-weight: 700;
}

.profile-photo-preview img { width: 100%; height: 100%; object-fit: cover; }

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.profile-form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 22px 24px;
  padding-top: 28px;
}

.profile-wide { grid-column: 1 / -1; }
.profile-form-grid small { align-self: flex-end; color: #929c8c; font-size: 12px; }
.readonly-field { background: #f1f3ef !important; color: #727b70 !important; cursor: not-allowed; }
.profile-error { margin: 22px 0 0; color: #a74842; font-size: 13px; }

.profile-form-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-top: 28px;
  padding-top: 20px;
  border-top: 1px solid var(--line);
}

.profile-form-footer > p { margin: 0; color: #849079; font-size: 12px; }
.profile-form-footer > div { display: flex; gap: 10px; }

@media (max-width: 900px) {
  .profile-form-grid { grid-template-columns: 1fr; }
  .profile-wide { grid-column: auto; }
}

@media (max-width: 620px) {
  .profile-editor { padding: 20px; }
  .profile-editor-heading,
  .profile-form-footer { align-items: flex-start; flex-direction: column; }
  .avatar-field { align-items: flex-start; }
}
</style>
