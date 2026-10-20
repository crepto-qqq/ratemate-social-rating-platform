<script setup>
import { apiBaseUrl, apiFetch } from '../api.js'
import { computed, onMounted, reactive, ref } from 'vue'
import AppLayout from '../components/AppLayout.vue'
import { currentProfile } from '../currentProfile.js'


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
const hiddenTemplates = ref([])
const hiddenRatings = ref([])
const hiddenLoading = ref(true)
const hiddenError = ref('')
const avatarInitial = computed(() => profile.username.trim().charAt(0).toUpperCase() || '?')

function applyProfile(data) {
  currentProfile.value = data
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
    const response = await apiFetch(`${apiBaseUrl}/api/auth/profile/`)
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
    const response = await apiFetch(`${apiBaseUrl}/api/auth/profile/`, {
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

async function loadHiddenContent() {
  hiddenLoading.value = true
  hiddenError.value = ''
  try {
    const response = await apiFetch(`${apiBaseUrl}/api/templates/mine/hidden/`)
    const data = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(data.detail || 'Unable to load content status.')
    hiddenTemplates.value = Array.isArray(data.templates) ? data.templates : []
    hiddenRatings.value = Array.isArray(data.ratings) ? data.ratings : []
  } catch (requestError) {
    hiddenError.value = requestError.message || 'Unable to load content status.'
  } finally {
    hiddenLoading.value = false
  }
}

function statusDate(value) {
  if (!value) return ''
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '' : new Intl.DateTimeFormat('en-AU', { dateStyle: 'medium' }).format(date)
}

onMounted(() => {
  loadProfile()
  loadHiddenContent()
})
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
          <span class="profile-field-label">Username</span>
          <input v-length-feedback v-model.trim="profile.username" autocomplete="username" minlength="3" maxlength="30" required @input="changed">
        </label>

        <label class="editor-field">
          <span class="profile-field-label">Email address</span>
          <input v-model="profile.email" class="readonly-field" autocomplete="email" type="email" readonly>
          <span class="optional">Cannot be changed</span>
        </label>

        <label class="editor-field profile-wide">
          <span class="profile-field-label">Bio <span class="optional">Optional</span></span>
          <textarea v-length-feedback v-model="profile.bio" rows="4" maxlength="300" placeholder="What do you enjoy rating?" @input="changed" />
          <small>{{ profile.bio.length }} / 300</small>
        </label>

        <label class="editor-field">
          <span class="profile-field-label">New password</span>
          <input v-length-feedback v-model="profile.password" autocomplete="new-password" type="password" minlength="8" placeholder="8+ characters, uppercase, lowercase, number" @input="changed">
          <span class="optional">Leave blank to keep your current password</span>
        </label>

        <label class="editor-field">
          <span class="profile-field-label">Confirm new password</span>
          <input v-length-feedback v-model="profile.passwordConfirm" autocomplete="new-password" type="password" minlength="8" placeholder="Enter the new password again" @input="changed">
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
    <section v-if="!loading && !loadError" class="hidden-content" aria-labelledby="hidden-heading">
      <div class="hidden-content-heading">
        <div>
          <div class="eyebrow">CONTENT STATUS</div>
          <h2 id="hidden-heading">Hidden content</h2>
          <p>Only an administrator can restore a hidden template. Your ratings remain saved while its template is hidden.</p>
        </div>
        <button class="action-button" type="button" :disabled="hiddenLoading" @click="loadHiddenContent">Refresh</button>
      </div>
      <p v-if="hiddenLoading" role="status">Loading content status…</p>
      <p v-else-if="hiddenError" class="profile-error" role="alert">{{ hiddenError }}</p>
      <p v-else-if="!hiddenTemplates.length && !hiddenRatings.length" class="hidden-empty">No hidden templates or affected ratings.</p>
      <div v-else class="hidden-list">
        <article v-for="template in hiddenTemplates" :key="`template-${template.id}`" class="hidden-card">
          <div><span class="state-badge">Template hidden</span><h3>{{ template.title }}</h3><p>{{ template.ratingCount }} saved rating{{ template.ratingCount === 1 ? '' : 's' }}</p></div>
          <div><strong>Reason</strong><p>{{ template.reason || 'No reason available.' }}</p><small v-if="template.hiddenAt">Hidden {{ statusDate(template.hiddenAt) }}</small></div>
        </article>
        <article v-for="rating in hiddenRatings" :key="`rating-${rating.id}`" class="hidden-card">
          <div><span class="state-badge">Rating unavailable</span><h3>{{ rating.templateTitle }}</h3><p>Your rating remains saved and will reappear if the template is restored.</p></div>
          <div><strong>Reason</strong><p>{{ rating.reason || 'No reason available.' }}</p><small v-if="rating.hiddenAt">Hidden {{ statusDate(rating.hiddenAt) }}</small></div>
        </article>
      </div>
    </section>
  </AppLayout>
</template>

<style scoped>
.profile-state {
  display: grid;
  place-items: center;
  max-width: 920px;
  min-height: 320px;
  padding: 40px;
  border: 1px solid var(--surface-green-border);
  border-radius: 12px;
  background: #fff;
  color: var(--text-secondary);
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
  border: 1px solid var(--surface-green-border);
  border-radius: 12px;
  background: #fff;
}

.profile-editor-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  padding-bottom: 24px;
  border-bottom: 1px solid var(--surface-green-border);
}

.profile-editor-heading h2 { color: var(--text-green); font-weight: 700; margin: 0; font-size: 20px; }
.profile-editor-heading p { margin: 8px 0 0; color: var(--text-secondary); font-size: 14px; }

.avatar-field {
  display: flex;
  align-items: center;
  gap: 22px;
  padding: 28px 0;
  border-bottom: 1px solid var(--surface-green-border);
}

.avatar-field p { margin: 6px 0 12px; color: var(--text-secondary); font-size: 12px; }

.profile-photo-preview {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 88px;
  height: 88px;
  overflow: hidden;
  border-radius: 50%;
  background: var(--avatar-background);
  color: var(--avatar-color);
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

.profile-form-grid > .editor-field { align-self: start; }
.profile-field-label { display: flex; align-items: baseline; gap: 8px; }
.profile-wide { grid-column: 1 / -1; }
.profile-form-grid small { align-self: flex-end; color: var(--text-secondary); font-size: 12px; }
.readonly-field { background: #f1f3ef !important; color: var(--text-secondary) !important; cursor: not-allowed; }
.profile-error { margin: 22px 0 0; color: #a74842; font-size: 13px; }

.profile-form-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-top: 28px;
  padding-top: 20px;
  border-top: 1px solid var(--surface-green-border);
}

.profile-form-footer > p { margin: 0; color: var(--text-secondary); font-size: 12px; }
.profile-form-footer > div { display: flex; gap: 10px; }

.hidden-content { max-width: 920px; margin: 28px 0 50px; padding: 28px; border: 1px solid var(--surface-green-border); border-radius: 12px; background: #fff; }
.hidden-content-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; }
.hidden-content-heading h2 { margin: 0; font-size: 20px; }
.hidden-content-heading p, .hidden-empty { color: var(--text-secondary); font-size: 14px; line-height: 1.6; }
.hidden-list { display: grid; gap: 14px; margin-top: 22px; }
.hidden-card { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 24px; padding: 18px; border: 1px solid var(--surface-green-border); border-radius: 10px; background: white; }
.hidden-card h3 { margin: 10px 0 6px; font-size: 17px; overflow-wrap: anywhere; }
.hidden-card p { margin: 6px 0; color: var(--text-secondary); font-size: 13px; line-height: 1.6; overflow-wrap: anywhere; }
.hidden-card strong, .hidden-card small { color: var(--text-secondary); font-size: 12px; }

@media (max-width: 900px) {
  .profile-form-grid { grid-template-columns: 1fr; }
  .profile-wide { grid-column: auto; }
}

@media (max-width: 620px) {
  .profile-editor { padding: 20px; }
  .profile-editor-heading,
  .profile-form-footer { align-items: flex-start; flex-direction: column; }
  .avatar-field { align-items: flex-start; }
  .hidden-content { padding: 20px; }
  .hidden-content-heading { flex-direction: column; }
  .hidden-card { grid-template-columns: 1fr; }
}
</style>
