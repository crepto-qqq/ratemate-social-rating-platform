<script setup>
import { ref } from 'vue'
import AppIcon from './AppIcon.vue'
import { apiBaseUrl, apiFetch } from '../api.js'
import { currentProfile } from '../currentProfile.js'
const props = defineProps({ result: { type: Object, required: true } })
const emit = defineEmits(['change'])
const busy = ref(false)
const error = ref('')
async function toggleLike() {
  if (busy.value || props.result.isOwner) return
  busy.value = true
  error.value = ''
  try {
    const response = await apiFetch(`${apiBaseUrl}/api/ratings/public/${props.result.id}/like/`, {
      method: props.result.isLiked ? 'DELETE' : 'POST',
    })
    const data = await response.json()
    if (!response.ok) throw new Error(data.detail || 'Unable to update your like.')
    emit('change', data)
  } catch (e) { error.value = e.message }
  finally { busy.value = false }
}
</script>
<template>
  <div class="like-control">
    <button v-if="currentProfile || result.isOwner" class="like-button" :class="{ selected: result.isLiked }" :aria-pressed="result.isLiked" :disabled="busy || result.isOwner" :title="result.isOwner ? 'You cannot like your own rating' : undefined" @click="toggleLike"><AppIcon name="heart" />{{ busy ? 'Saving…' : result.isLiked ? 'Liked' : 'Like' }} <span>{{ result.likeCount }}</span></button>
    <RouterLink v-else class="like-button" to="/login"><AppIcon name="heart" />Log in to like <span>{{ result.likeCount }}</span></RouterLink>
    <small v-if="error" role="alert">{{ error }}</small>
  </div>
</template>
<style scoped>
.like-button { display: inline-flex; align-items: center; gap: 7px; min-height: 40px; padding: 8px 12px; border: 1px solid #dce5d6; border-radius: 9px; background: #fff; color: var(--text-secondary); font-size: 12px; }
.like-button svg { width: 16px; height: 16px; }
.like-button.selected { color: #325c48; background: #edf4e8; }
.like-button.selected svg { fill: currentColor; }
.like-button:disabled { cursor: default; opacity: .65; }
.like-control small { display: block; max-width: 260px; margin-top: 6px; color: #a74842; }
</style>
