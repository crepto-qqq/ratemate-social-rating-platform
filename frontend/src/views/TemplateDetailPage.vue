<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import AppLayout from '../components/AppLayout.vue'
import { apiBaseUrl, apiFetch } from '../api.js'
import { currentProfile } from '../currentProfile.js'
const route = useRoute()
const data = ref(null)
const loading = ref(true)
const error = ref('')
const saving = ref(false)
const saveError = ref('')
const liked = ref(false)
const comment = ref('')
// Comments remain local demo content for now.
const comments = ref([
  { author: 'Sam Taylor', initials: 'ST', text: 'I like how clear the criteria are. This gives me a useful starting point for my own ratings.' },
  { author: 'Riley Chen', initials: 'RC', text: 'The weighted scores make the final ranking much easier to understand.' },
])
const totalWeight = computed(() => data.value?.criteria.reduce((sum, c) => sum + c.weight, 0) || 1)
let loadVersion = 0
async function loadTemplate() {
  const version = ++loadVersion
  loading.value = true
  data.value = null
  error.value = ''
  saveError.value = ''
  liked.value = false
  try {
    const response = await apiFetch(apiBaseUrl + '/api/templates/' + route.params.id + '/')
    if (!response.ok) throw new Error(response.status === 404 ? 'Template not found.' : 'Unable to load template.')
    const result = await response.json()
    if (version === loadVersion) data.value = result
  } catch (e) { if (version === loadVersion) error.value = e.message }
  finally { if (version === loadVersion) loading.value = false }
}
async function toggleFavorite() {
  if (!data.value || saving.value) return
  const template = data.value
  saving.value = true
  saveError.value = ''
  try {
    const response = await apiFetch(apiBaseUrl + '/api/templates/' + template.id + '/favorite/', { method: template.isFavorite ? 'DELETE' : 'POST' })
    const result = await response.json()
    if (!response.ok) throw new Error(result.detail || 'Unable to update favorites.')
    Object.assign(template, result)
  } catch (e) { saveError.value = e.message }
  finally { saving.value = false }
}
function postComment() {
  const text = comment.value.trim()
  if (!text || !currentProfile.value) return
  const author = currentProfile.value.userName
  comments.value.unshift({ author, initials: author.charAt(0).toUpperCase(), text })
  comment.value = ''
}
watch(() => route.params.id, loadTemplate, { immediate: true })
</script>
<template>
  <AppLayout>
    <div v-if="loading" class="empty-results" role="status">Loading template…</div>
    <div v-else-if="error" class="empty-results" role="alert"><h2>{{ error }}</h2><button class="action-button" @click="loadTemplate">Try again</button><RouterLink class="action-button" to="/home_page">Back to Discover</RouterLink></div>
    <div v-else-if="data">
      <RouterLink class="text-button back-button" to="/home_page"><AppIcon name="back" />Back to Discover</RouterLink>
      <div class="detail-hero">
        <div class="detail-cover"><img v-if="data.items[0]?.imageUrl" :src="data.items[0].imageUrl" :alt="data.title"><span v-else>{{ data.title }}</span></div>
        <div class="detail-intro">
          <h1>{{ data.title }}</h1>
          <div class="detail-author"><span class="avatar"><img v-if="data.author.avatarUrl" :src="data.author.avatarUrl" alt="Author avatar"><template v-else>{{ data.author.name.charAt(0).toUpperCase() || '?' }}</template></span><div><strong>{{ data.author.name }}</strong><small>Community template · {{ data.items.length }} items</small></div></div>
          <p>{{ data.description }}</p>
          <div class="detail-actions"><button class="action-button" :aria-pressed="liked" @click="liked = !liked"><AppIcon name="heart" />{{ liked ? 'Liked' : 'Like' }}</button><button class="action-button primary" :disabled="saving" :aria-pressed="data.isFavorite" @click="toggleFavorite"><AppIcon name="bookmark" />{{ saving ? 'Saving…' : data.isFavorite ? 'Saved to favorites' : 'Save to favorites' }} · {{ data.popularity }}</button></div>
          <p v-if="saveError" role="alert">{{ saveError }}</p>
        </div>
      </div>
      <div class="detail-body">
        <div class="detail-main">
          <section class="detail-section"><div class="section-heading"><h2>Rating criteria</h2><span>{{ data.criteria.length }} criteria · 1–5 stars each</span></div><div class="criteria-list"><div v-for="c in data.criteria" :key="c.id" class="criterion"><strong>{{ c.name }}</strong><span>Weight {{ c.weight }}</span><div class="weight-track"><div :style="{ width: c.weight / totalWeight * 100 + '%' }" /></div><small>{{ Math.round(c.weight / totalWeight * 100) }}% of total weight</small></div></div></section>
          <section class="detail-section"><div class="section-heading"><h2>Items to rate</h2><span>{{ data.items.length }} items</span></div><div class="template-items"><article v-for="item in data.items" :key="item.id"><img v-if="item.imageUrl" :src="item.imageUrl" :alt="item.name"><strong>{{ item.name }}</strong></article></div></section>
          <section class="detail-section comments-section"><h2>Comments ({{ comments.length }})</h2><form @submit.prevent="postComment"><label for="comment-text">Join the conversation</label><textarea id="comment-text" v-model="comment" maxlength="1000" rows="3" placeholder="What do you think of this template?" /><div class="comment-form-bottom"><span>{{ comment.length }} / 1000</span><button class="action-button primary" :disabled="!comment.trim() || !currentProfile">Post comment</button></div></form><article v-for="item in comments" :key="item.text" class="comment"><span class="avatar">{{ item.initials }}</span><div><strong>{{ item.author }}</strong><small>Community member</small><p>{{ item.text }}</p></div></article></section>
        </div>
        <aside class="ranking-panel"><h2>Make your own rating</h2><div class="reuse-note">Save this template to your favorites, then rate its items using the criteria above.</div><RouterLink class="action-button primary" to="/rate">Rate a template</RouterLink></aside>
      </div>
    </div>
  </AppLayout>
</template>
<style scoped>
.avatar { overflow: hidden; }
.avatar img { width: 100%; height: 100%; object-fit: cover; }
.template-items { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; }
.template-items article { display: grid; gap: 10px; }
.template-items img { width: 100%; aspect-ratio: 1; object-fit: cover; border-radius: 10px; }
.ranking-panel .action-button { margin-top: 20px; }
</style>
