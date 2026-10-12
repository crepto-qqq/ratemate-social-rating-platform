<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import AppLayout from '../components/AppLayout.vue'
import RatingLikeButton from '../components/RatingLikeButton.vue'
import { apiBaseUrl, apiFetch } from '../api.js'
const route = useRoute()
const router = useRouter()
const tab = computed(() => route.query.tab === 'templates' ? 'templates' : 'ratings')
const query = computed(() => String(route.query.q || '').trim())
const templates = ref([])
const ratings = ref([])
const loading = ref(true)
const loadingMore = ref(false)
const error = ref('')
const hasMore = ref(false)
const page = ref(1)
const failedImages = ref(new Set())
const templateResults = computed(() => templates.value.filter(t => [t.title, t.description, t.author.name].join(' ').toLowerCase().includes(query.value.toLowerCase())))
const count = computed(() => tab.value === 'ratings' ? ratings.value.length : templateResults.value.length)
let version = 0
function setTab(value) { router.replace({ query: { ...route.query, tab: value } }) }
function imageFailed(key) { failedImages.value = new Set([...failedImages.value, key]) }
async function loadFeed(more = false) {
  const requestVersion = ++version
  if (more) loadingMore.value = true
  else { loading.value = true; loadingMore.value = false }
  error.value = ''
  const nextPage = more ? page.value + 1 : 1
  try {
    const endpoint = tab.value === 'ratings'
      ? '/api/ratings/public/?page=' + nextPage + '&q=' + encodeURIComponent(query.value)
      : '/api/templates/'
    const response = await apiFetch(apiBaseUrl + endpoint)
    const data = await response.json()
    if (!response.ok) throw new Error(data.detail || 'Unable to load Discover.')
    if (requestVersion !== version) return
    if (tab.value === 'ratings') {
      ratings.value = more ? [...ratings.value, ...data.results] : data.results
      hasMore.value = data.hasMore
      page.value = nextPage
    } else templates.value = data.templates
  } catch (e) { if (requestVersion === version) error.value = e.message }
  finally { if (requestVersion === version) { loading.value = false; loadingMore.value = false } }
}
watch([tab, query], () => loadFeed(), { immediate: true })
function formattedDate(value) { return new Date(value).toLocaleDateString('en', { month: 'short', day: 'numeric' }) }
</script>
<template>
  <AppLayout>
    <div class="heading"><div><div class="eyebrow">MADE BY THE COMMUNITY</div><h1>Discover a different perspective.</h1><p>See what comes out on top. Find a template. Share your own take.</p></div></div>
    <div class="discover-tabs" role="tablist" aria-label="Discover content">
      <button id="ratings-tab" role="tab" :aria-selected="tab === 'ratings'" aria-controls="ratings-panel" :class="{ active: tab === 'ratings' }" @click="setTab('ratings')"><AppIcon name="star" />Community ratings</button>
      <button id="templates-tab" role="tab" :aria-selected="tab === 'templates'" aria-controls="templates-panel" :class="{ active: tab === 'templates' }" @click="setTab('templates')"><AppIcon name="layers" />Templates</button>
    </div>
    <section :id="tab + '-panel'" role="tabpanel" :aria-labelledby="tab + '-tab'">
      <div class="feed-heading"><div><h2>{{ query ? 'Search results for “' + query + '”' : tab === 'ratings' ? 'Real ratings. Personal perspectives.' : 'A starting point for your next rating.' }}</h2><p class="feed-description">{{ tab === 'ratings' ? 'Completed rankings shared by the community.' : 'Save a template and make the ratings your own.' }}</p></div><span v-if="!loading && !error" class="feed-count">{{ count }} {{ tab === 'ratings' ? 'ratings' : 'templates' }}{{ tab === 'ratings' && hasMore ? ' loaded' : '' }}</span><RouterLink v-if="query" class="text-button" :to="{ path: '/home_page', query: { tab } }">Clear search</RouterLink></div>
      <div v-if="loading" class="empty-results" role="status">Loading {{ tab }}…</div>
      <div v-else-if="error && !loadingMore" class="empty-results" role="alert"><p>{{ error }}</p><button class="action-button" @click="loadFeed()">Try again</button></div>
      <template v-else-if="tab === 'ratings'">
        <div v-if="ratings.length" class="rating-grid">
          <article v-for="result in ratings" :key="result.id" class="public-rating-card">
            <RouterLink class="ranking-cover" :to="'/ratings/' + result.id">
              <img v-if="result.ranking[0]?.imageUrl && !failedImages.has('rating-' + result.id)" :src="result.ranking[0].imageUrl" :alt="result.ranking[0].name" @error="imageFailed('rating-' + result.id)">
              <AppIcon v-else name="star" />
              <span class="ranking-badge">COMMUNITY RANKING</span><span class="winner-badge">#1 · {{ result.ranking[0]?.name }}</span>
            </RouterLink>
            <div class="rating-card-body">
              <RouterLink class="card-title" :to="'/ratings/' + result.id">{{ result.template.title }}</RouterLink>
              <div class="card-meta"><span class="mini-avatar"><img v-if="result.author.avatarUrl" :src="result.author.avatarUrl" alt=""><template v-else>{{ result.author.name.charAt(0).toUpperCase() || '?' }}</template></span><span>{{ result.author.name }}</span><time :datetime="result.createdAt">{{ formattedDate(result.createdAt) }}</time></div>
              <ol class="ranking-preview"><li v-for="(item, index) in result.ranking.slice(0, 3)" :key="item.itemId"><span class="position" :class="{ first: index === 0 }">{{ index + 1 }}</span><span class="item-name">{{ item.name }}</span><strong>{{ item.score.toFixed(1) }}<small>/100</small></strong></li></ol>
              <div class="rating-card-footer"><RatingLikeButton :result="result" @change="Object.assign(result, $event)" /><RouterLink class="discussion-link" :to="'/ratings/' + result.id + '#comments'">Comments · {{ result.commentCount }}</RouterLink></div>
            </div>
          </article>
        </div>
        <div v-else class="empty-results"><h2>{{ query ? 'No matching public ratings' : 'Be the first to share a ranking.' }}</h2><p>{{ query ? 'Try another search.' : 'Complete a rating and make it public to share it here.' }}</p><RouterLink class="action-button primary" to="/rate">Rate a template</RouterLink></div>
        <div v-if="hasMore && ratings.length" class="load-more"><button class="action-button" :disabled="loadingMore" @click="loadFeed(true)">{{ loadingMore ? 'Loading…' : 'Load more ratings' }}</button></div>
      </template>
      <template v-else>
        <div v-if="templateResults.length" class="template-grid">
          <article v-for="t in templateResults" :key="t.id" class="card">
            <RouterLink class="cover" :class="{ fallback: !t.items[0]?.imageUrl || failedImages.has('template-' + t.id) }" :to="'/templates/' + t.id"><img v-if="t.items[0]?.imageUrl && !failedImages.has('template-' + t.id)" :src="t.items[0].imageUrl" :alt="t.title" @error="imageFailed('template-' + t.id)"><span v-else>{{ t.title }}</span><span class="item-count"><AppIcon name="layers" />{{ t.items.length }} items to rate</span></RouterLink>
            <RouterLink class="card-title" :to="'/templates/' + t.id">{{ t.title }}</RouterLink>
            <div class="card-meta"><span class="mini-avatar"><img v-if="t.author.avatarUrl" :src="t.author.avatarUrl" alt=""><template v-else>{{ t.author.name.charAt(0).toUpperCase() || '?' }}</template></span><span>{{ t.author.name }}</span><span class="likes" title="Favorites"><AppIcon name="bookmark" />{{ t.popularity }}</span></div>
          </article>
        </div>
        <div v-else class="empty-results"><h2>{{ query ? 'No matching templates' : 'No templates yet' }}</h2><p>{{ query ? 'Try another search.' : 'Create the first template to start exploring.' }}</p><RouterLink class="action-button" to="/create">Create a template</RouterLink></div>
      </template>
    </section>
  </AppLayout>
</template>
<style scoped>
.discover-tabs { display: flex; gap: 8px; flex-wrap: wrap; padding-bottom: 20px; border-bottom: 1px solid var(--line); margin-bottom: 28px; }
.discover-tabs button { display: inline-flex; align-items: center; gap: 9px; border: 1px solid transparent; padding: 12px 18px; border-radius: 10px; background: #f5f7f3; color: #7b8873; font-weight: 600; }
.discover-tabs button.active { background: #e6eee1; border-color: #d9e5d1; color: #325c48; }
.discover-tabs svg { width: 18px; height: 18px; }
.feed-description { color: #849079; font-size: 13px; margin: 8px 0 0; }
.template-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 260px), 1fr)); gap: 28px 24px; align-items: start; }
.rating-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 320px), 1fr)); gap: 24px; align-items: start; }
.card { display: block; min-width: 0; margin: 0; }
.cover { height: clamp(220px, 22vw, 340px); }
.cover img { object-fit: contain; }
.card-title { overflow-wrap: anywhere; }
.card-meta > span:nth-child(2) { min-width: 0; overflow-wrap: anywhere; }
.mini-avatar, .likes { flex-shrink: 0; }
.mini-avatar { overflow: hidden; }
.mini-avatar img { width: 100%; height: 100%; object-fit: cover; }
.public-rating-card { min-width: 0; border: 1px solid #e0e8da; border-radius: 14px; overflow: hidden; background: #fbfcf9; }
.ranking-cover { height: 190px; display: flex; align-items: center; justify-content: center; position: relative; background: #eff3e9; }
.ranking-cover img { width: 100%; height: 100%; object-fit: contain; }
.ranking-cover > svg { width: 48px; height: 48px; color: #839c6a; }
.ranking-badge { position: absolute; top: 14px; left: 14px; font-size: 9px; letter-spacing: 1.2px; font-weight: 700; padding: 7px 9px; border-radius: 6px; background: #fffffff0; color: #426447; }
.winner-badge { position: absolute; bottom: 12px; left: 14px; right: 14px; width: fit-content; max-width: calc(100% - 28px); overflow-wrap: anywhere; background: #325c48; color: white; padding: 7px 10px; border-radius: 6px; font-size: 12px; }
.rating-card-body { padding: 18px; }
.rating-card-body .card-title { margin: 0 0 12px; font-size: 18px; }
.card-meta time { margin-left: auto; flex-shrink: 0; }
.ranking-preview { list-style: none; padding: 0; margin: 18px 0; }
.ranking-preview li { display: flex; align-items: center; gap: 10px; padding: 10px 0; border-bottom: 1px solid #e8edde; }
.position { display: grid; place-items: center; width: 26px; height: 26px; border-radius: 7px; background: #eef2e8; color: #7d8c70; font-size: 12px; flex-shrink: 0; }
.position.first { background: #ddebcf; color: #325c48; font-weight: 700; }
.item-name { min-width: 0; overflow-wrap: anywhere; font-size: 13px; }
.ranking-preview strong { margin-left: auto; color: #325c48; font-size: 17px; white-space: nowrap; }
.ranking-preview small { font-weight: 400; color: #929c87; font-size: 10px; margin-left: 3px; }
.rating-card-footer { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.discussion-link { color: #7a8871; font-size: 12px; }
.load-more { text-align: center; margin: 28px 0; }
@media (max-width: 620px) { .cover { height: auto; aspect-ratio: 4 / 3; } .ranking-cover { height: 170px; } .rating-card-body { padding: 14px; } .discover-tabs button { flex: 1; padding: 10px; font-size: 12px; } }
</style>
