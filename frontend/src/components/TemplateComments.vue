<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { apiBaseUrl, apiFetch } from '../api.js'
import { currentProfile, profileLoading } from '../currentProfile.js'

const props = defineProps({ templateId: Number, resultId: Number })
const comments = ref([])
const loading = ref(false)
const loadError = ref('')
const retryReset = ref(true)
const actionError = ref('')
const draft = ref('')
const editId = ref(null)
const deleteId = ref(null)
const editContent = ref('')
const busy = ref(false)
const hasMore = ref(false)
const page = ref(0)
const validDraft = computed(() => draft.value.trim().length > 0 && draft.value.trim().length <= 2000)
const validEdit = computed(() => editContent.value.trim().length > 0 && editContent.value.trim().length <= 2000)
const endpoint = props.resultId
  ? `${apiBaseUrl}/api/ratings/public/${props.resultId}/comments/`
  : `${apiBaseUrl}/api/templates/${props.templateId}/comments/`
let active = true
let requestVersion = 0

async function readResponse(response) {
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.detail || 'Unable to update comments. Please try again.')
  return data
}

async function loadComments(reset = false) {
  const version = ++requestVersion
  const nextPage = reset ? 1 : page.value + 1
  loading.value = true
  loadError.value = ''
  retryReset.value = reset
  try {
    const data = await readResponse(await apiFetch(`${endpoint}?page=${nextPage}`))
    if (!active || version !== requestVersion) return
    comments.value = reset ? data.comments : [...comments.value, ...data.comments.filter(c => !comments.value.some(existing => existing.id === c.id))]
    page.value = nextPage
    hasMore.value = data.hasMore
  } catch (error) {
    if (active && version === requestVersion) loadError.value = error.message
  } finally {
    if (active && version === requestVersion) loading.value = false
  }
}

async function postComment() {
  if (busy.value || !validDraft.value) return
  busy.value = true
  actionError.value = ''
  try {
    await readResponse(await apiFetch(endpoint, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: draft.value }),
    }))
    if (!active) return
    draft.value = ''
    await loadComments(true)
  } catch (error) { if (active) actionError.value = error.message }
  finally { if (active) busy.value = false }
}

function startEdit(comment) {
  deleteId.value = null
  editId.value = comment.id
  editContent.value = comment.content
  actionError.value = ''
}

async function saveEdit() {
  if (busy.value || !validEdit.value) return
  busy.value = true
  actionError.value = ''
  const id = editId.value
  try {
    const updated = await readResponse(await apiFetch(`${endpoint}${id}/`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: editContent.value }),
    }))
    if (!active) return
    comments.value = comments.value.map(comment => comment.id === id ? updated : comment)
    editId.value = null
  } catch (error) { if (active) actionError.value = error.message }
  finally { if (active) busy.value = false }
}

async function deleteComment(comment) {
  if (busy.value) return
  busy.value = true
  actionError.value = ''
  try {
    const response = await apiFetch(`${endpoint}${comment.id}/`, { method: 'DELETE' })
    if (!response.ok) await readResponse(response)
    if (!active) return
    comments.value = comments.value.filter(c => c.id !== comment.id)
    deleteId.value = null
    if (editId.value === comment.id) editId.value = null
    await loadComments(true)
  } catch (error) { if (active) actionError.value = error.message }
  finally { if (active) busy.value = false }
}

function formattedTime(value) { return new Date(value).toLocaleString() }
onMounted(() => loadComments(true))
onBeforeUnmount(() => { active = false; requestVersion++ })
</script>

<template>
  <section class="detail-section comments-section" aria-label="Comments">
    <h2>Comments</h2>
    <form v-if="currentProfile" class="comment-form" @submit.prevent="postComment">
      <label :for="`comment-${resultId || templateId}`">Add a comment</label>
      <textarea :id="`comment-${resultId || templateId}`" v-model="draft" maxlength="2000" rows="3" :placeholder="resultId ? 'Share your thoughts about this ranking…' : 'Share your thoughts about this template…'" :disabled="busy" required />
      <div class="form-actions"><small>{{ draft.length }}/2000</small><button class="action-button primary" type="submit" :disabled="busy || loading || !validDraft">{{ busy ? 'Saving…' : 'Post comment' }}</button></div>
    </form>
    <p v-else-if="profileLoading" role="status">Checking your account…</p>
    <p v-else class="guest-note"><RouterLink to="/login">Log in</RouterLink> to join the conversation.</p>
    <p v-if="actionError" class="comment-error" role="alert">{{ actionError }}</p>
    <p v-if="loading" role="status">Loading comments…</p>
    <div v-if="loadError" class="comment-error" role="alert"><p>{{ loadError }}</p><button class="text-button" :disabled="loading || busy" @click="loadComments(retryReset)">Try again</button></div>
    <p v-if="!loading && !loadError && !comments.length" class="inline-empty">No comments yet. Start the conversation.</p>
    <div class="comment-list">
      <article v-for="comment in comments" :key="comment.id" class="comment">
        <div class="comment-heading">
          <span class="comment-avatar"><img v-if="comment.author.avatarUrl" :src="comment.author.avatarUrl" alt=""><span v-else>{{ comment.author.name.charAt(0).toUpperCase() || '?' }}</span></span>
          <div><strong>{{ comment.author.name }}</strong><div class="comment-time"><time :datetime="comment.createdAt">{{ formattedTime(comment.createdAt) }}</time><span v-if="comment.isEdited" :title="formattedTime(comment.updatedAt)"> · Edited</span></div></div>
        </div>
        <form v-if="editId === comment.id" class="comment-form" @submit.prevent="saveEdit">
          <label :for="`edit-comment-${comment.id}`">Edit comment</label>
          <textarea :id="`edit-comment-${comment.id}`" v-model="editContent" maxlength="2000" rows="3" :disabled="busy" required />
          <div class="form-actions"><small>{{ editContent.length }}/2000</small><button class="text-button" type="button" :disabled="busy" @click="editId = null">Cancel</button><button class="action-button primary" type="submit" :disabled="busy || loading || !validEdit">Save changes</button></div>
        </form>
        <p v-else class="comment-content">{{ comment.content }}</p>
        <div v-if="comment.canManage && editId !== comment.id" class="comment-actions">
          <template v-if="deleteId === comment.id"><span>Delete this comment?</span><button class="text-button" :disabled="busy" @click="deleteId = null">Cancel</button><button class="text-button delete-button" :disabled="busy || loading" @click="deleteComment(comment)">Confirm delete</button></template>
          <template v-else><button class="text-button" :disabled="busy || loading" @click="startEdit(comment)">Edit</button><button class="text-button delete-button" :disabled="busy || loading" @click="deleteId = comment.id">Delete</button></template>
        </div>
      </article>
    </div>
    <button v-if="hasMore && !loadError" class="action-button" :disabled="loading || busy" @click="loadComments()">{{ loading ? 'Loading…' : 'Load more comments' }}</button>
  </section>
</template>

<style scoped>
.comments-section { min-width: 0; }
.comment-form { display: grid; gap: 10px; margin: 18px 0; }
.comment-form label { font-size: 13px; font-weight: 600; }
textarea { width: 100%; box-sizing: border-box; resize: vertical; padding: 12px; border: 1px solid #d8e2cf; border-radius: 9px; background: #fbfcf9; color: #273326; font: inherit; line-height: 1.5; }
textarea:focus { outline: 2px solid #668258; outline-offset: 2px; }
.form-actions { display: flex; align-items: center; justify-content: flex-end; flex-wrap: wrap; gap: 12px; }
.form-actions small { margin-right: auto; color: #778171; }
.comment-list { margin: 22px 0; }
.comment { display: block; padding: 20px 0; border-top: 1px solid var(--line); border-bottom: 0; }
.comment-heading { display: flex; align-items: center; gap: 10px; }
.comment-avatar { flex-shrink: 0; display: flex; align-items: center; justify-content: center; width: 36px; height: 36px; overflow: hidden; border-radius: 50%; background: #e5ebdd; color: #537048; }
.comment-avatar img { width: 100%; height: 100%; object-fit: cover; }
.comment-heading strong { overflow-wrap: anywhere; }
.comment-time { margin-top: 4px; color: #778171; font-size: 12px; }
.comment-content { white-space: pre-wrap; overflow-wrap: anywhere; line-height: 1.65; margin: 14px 0; }
.comment-actions { display: flex; flex-wrap: wrap; gap: 16px; }
.delete-button, .comment-error { color: #a74842; }
.guest-note { color: #778171; }
button:disabled { opacity: .6; cursor: default; }
</style>
