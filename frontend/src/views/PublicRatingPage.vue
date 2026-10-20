<script setup>
import { usePageTitle } from '../composables/usePageTitle.js'
import { computed, nextTick, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppLayout from '../components/AppLayout.vue'
import AppIcon from '../components/AppIcon.vue'
import RatingLikeButton from '../components/RatingLikeButton.vue'
import TemplateComments from '../components/TemplateComments.vue'
import { apiBaseUrl, apiFetch } from '../api.js'
const route = useRoute()
const data = ref(null)

usePageTitle(() => data.value?.template.title)
const loading = ref(true)
const error = ref('')
const scores = computed(() => new Map((data.value?.scores || []).map(s => [s.itemId + ':' + s.criterionId, s.score])))
let version = 0
async function loadRating() {
  const current = ++version
  loading.value = true
  error.value = ''
  data.value = null
  try {
    const response = await apiFetch(apiBaseUrl + '/api/ratings/public/' + route.params.id + '/')
    const result = await response.json()
    if (!response.ok) throw new Error(response.status === 404 ? 'This rating is unavailable or private.' : 'Unable to load this rating.')
    if (current === version) data.value = result
  } catch (e) { if (current === version) error.value = e.message }
  finally {
    if (current === version) {
      loading.value = false
      await nextTick()
      if (current === version && route.hash === '#comments') document.getElementById('comments')?.scrollIntoView()
    }
  }
}
watch(() => route.params.id, loadRating, { immediate: true })
</script>
<template>
  <AppLayout>
    <RouterLink class="text-button back-button" to="/home_page"><AppIcon name="back" />Back to community ratings</RouterLink>
    <div v-if="loading" class="empty-results" role="status">Loading rating…</div>
    <div v-else-if="error" class="empty-results" role="alert"><h2>{{ error }}</h2><button class="action-button" @click="loadRating">Try again</button></div>
    <div v-else-if="data" class="public-detail">
      <header class="rating-intro"><div class="eyebrow">A COMMUNITY PERSPECTIVE</div><h1>{{ data.template.title }}</h1><p>{{ data.template.description }}</p><div class="detail-author"><span class="avatar"><img v-if="data.author.avatarUrl" :src="data.author.avatarUrl" alt=""><template v-else>{{ data.author.name.charAt(0).toUpperCase() }}</template></span><div><strong>{{ data.author.name }}</strong><small>Public rating · {{ new Date(data.createdAt).toLocaleDateString() }}</small></div></div><div class="detail-actions"><RatingLikeButton :result="data" @change="Object.assign(data, $event)" /><RouterLink class="action-button" :to="'/templates/' + data.template.id"><AppIcon name="layers" />View original template</RouterLink></div></header>
      <div class="rating-detail-layout">
        <div class="rating-main">
          <section class="detail-section"><div class="section-heading"><h2>The final ranking</h2><span>{{ data.ranking.length }} items · score out of 100</span></div><ol class="full-ranking"><li v-for="(item, index) in data.ranking" :key="item.itemId"><span class="position">{{ index + 1 }}</span><img v-if="item.imageUrl" :src="item.imageUrl" :alt="item.name"><strong class="rank-name">{{ item.name }}</strong><b>{{ item.score.toFixed(1) }}<small>/100</small></b></li></ol></section>
          <section class="detail-section"><h2>Behind the scores</h2><p class="section-description">Each criterion uses 1–5 stars. The weighted average is scaled to 100.</p><div class="table-scroll"><table><thead><tr><th>Item</th><th v-for="criterion in data.template.criteria" :key="criterion.id">{{ criterion.name }} · weight {{ criterion.weight }}</th></tr></thead><tbody><tr v-for="item in data.template.items" :key="item.id"><th>{{ item.name }}</th><td v-for="criterion in data.template.criteria" :key="criterion.id">{{ scores.get(item.id + ':' + criterion.id) }} ★</td></tr></tbody></table></div></section>
          <div id="comments"><TemplateComments :key="data.id" :result-id="data.id" /></div>
        </div>
        <aside class="ranking-panel"><h2>A different take?</h2><p>Use the same template to create your own ranking.</p><RouterLink class="action-button primary" :to="'/templates/' + data.template.id">Explore the template</RouterLink></aside>
      </div>
    </div>
  </AppLayout>
</template>
<style scoped>
.public-detail, .rating-main { min-width: 0; }
.rating-intro { max-width: 900px; margin-bottom: 30px; }
.rating-intro > p { color: var(--text-secondary); line-height: 1.7; overflow-wrap: anywhere; }
.detail-actions { margin-top: 20px; align-items: center; }
.avatar { overflow: hidden; }
.avatar img { width: 100%; height: 100%; object-fit: cover; }
.rating-detail-layout { display: grid; grid-template-columns: minmax(0, 1fr) 280px; gap: 30px; align-items: start; }
.full-ranking { list-style: none; padding: 0; margin: 20px 0 0; }
.full-ranking li { display: flex; gap: 14px; align-items: center; padding: 16px 0; border-bottom: 1px solid var(--line); }
.position { width: 28px; height: 28px; display: grid; place-items: center; background: #e9f0e1; color: #325c48; border-radius: 8px; flex-shrink: 0; }
.full-ranking img { width: 64px; height: 64px; object-fit: contain; background: #f1f4ec; border-radius: 9px; flex-shrink: 0; }
.rank-name { min-width: 0; overflow-wrap: anywhere; font-size: 14px; }
.full-ranking b { margin-left: auto; color: #325c48; font-size: 23px; white-space: nowrap; }
.full-ranking small { font-size: 10px; color: var(--text-secondary); font-weight: 400; }
#comments { scroll-margin-top: 24px; }
@media (max-width: 1000px) { .rating-detail-layout { grid-template-columns: minmax(0, 1fr); } }
@media (max-width: 620px) { .full-ranking li { gap: 8px; flex-wrap: wrap; } .full-ranking img { width: 44px; height: 44px; } .full-ranking b { font-size: 19px; } .detail-actions { align-items: stretch; } }
</style>
