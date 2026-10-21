<script setup>
import { apiBaseUrl, apiFetch } from '../api.js'
import { computed, onMounted, reactive, ref } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import AppLayout from '../components/AppLayout.vue'
import ListPagination from '../components/ListPagination.vue'


const mode = ref('new')
const step = ref(1)
const activeTemplate = ref(null)
const ratingPage = ref(1)
const favoritesPage = ref(1)
const historyPage = ref(1)
const rankingPage = ref(1)
const favoritesHasMore = ref(false)
const historyHasMore = ref(false)
const ratingSection = ref(null)
const editingResultId = ref(null)
const ratings = reactive({})
const error = ref('')
const saveStatus = ref('idle')
const saveError = ref('')
const savedResultId = ref(null)
const isPublic = ref(false)
const results = ref([])
const resultsLoading = ref(false)
const resultsError = ref('')
const favoriteTemplates = ref([])
const favoritesLoading = ref(false)
const favoritesError = ref('')
const failedImages = ref(new Set())
const steps = ['Choose template', 'Rate every item', 'Ranking']
const itemsPerPage = 10

const totalRatings = computed(() => activeTemplate.value ? activeTemplate.value.items.length * activeTemplate.value.criteria.length : 0)
const completedRatings = computed(() => Object.values(ratings).filter(score => score > 0).length)
const allRated = computed(() => totalRatings.value > 0 && completedRatings.value === totalRatings.value)
const ranking = computed(() => calculateRanking(activeTemplate.value, ratings))
const ratingPageCount = computed(() => Math.ceil((activeTemplate.value?.items.length || 0) / itemsPerPage))
const ratingPageStart = computed(() => (ratingPage.value - 1) * itemsPerPage)
const visibleRatingItems = computed(() => activeTemplate.value?.items.slice(ratingPageStart.value, ratingPageStart.value + itemsPerPage) || [])
const rankingPageCount = computed(() => Math.ceil(ranking.value.length / itemsPerPage))
const visibleRanking = computed(() => ranking.value.slice((rankingPage.value - 1) * itemsPerPage, rankingPage.value * itemsPerPage))

function goToRatingPage(page) {
  if (!Number.isInteger(page) || page < 1 || page > ratingPageCount.value || page === ratingPage.value) return
  ratingPage.value = page
  error.value = ''
  ratingSection.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function ratingKey(itemId, criterionId) {
  return `${itemId}:${criterionId}`
}

function calculateRanking(template, scoreSource) {
  if (!template) return []
  const totalWeight = template.criteria.reduce((sum, criterion) => sum + criterion.weight, 0)
  return template.items.map(item => {
    const weightedScore = template.criteria.reduce((sum, criterion) => {
      return sum + (scoreSource[ratingKey(item.id, criterion.id)] || 0) * criterion.weight
    }, 0)
    return { id: item.id, name: item.name, score: totalWeight ? weightedScore / totalWeight * 20 : 0 }
  }).sort((a, b) => b.score - a.score)
}

function resetRating() {
  activeTemplate.value = null
  ratingPage.value = 1
  rankingPage.value = 1
  editingResultId.value = null
  Object.keys(ratings).forEach(key => delete ratings[key])
  error.value = ''
  saveStatus.value = 'idle'
  saveError.value = ''
  savedResultId.value = null
  isPublic.value = false
  step.value = 1
}

function switchMode(nextMode) {
  mode.value = nextMode
  if (nextMode === 'new') {
    resetRating()
    loadFavorites()
  }
  if (nextMode === 'history') loadResults()
}

async function loadFavorites(nextPage = 1) {
  favoritesPage.value = nextPage
  favoritesLoading.value = true
  favoritesError.value = ''
  try {
    const response = await apiFetch(`${apiBaseUrl}/api/templates/favorites/?page=${nextPage}`)
    const data = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(data.detail || 'Unable to load your favorites.')
    if (nextPage > 1 && !data.templates?.length) return loadFavorites(nextPage - 1)
    favoriteTemplates.value = data.templates || []
    favoritesPage.value = nextPage
    favoritesHasMore.value = Boolean(data.hasMore)
  } catch (requestError) {
    favoritesError.value = requestError.message || 'Unable to connect to the server.'
  } finally {
    favoritesLoading.value = false
  }
}

function chooseTemplate(template) {
  resetRating()
  activeTemplate.value = template
  step.value = 2
}

function setRating(itemId, criterionId, score) {
  ratings[ratingKey(itemId, criterionId)] = score
  error.value = ''
}

function resultPayload() {
  const scores = []
  activeTemplate.value.items.forEach(item => {
    activeTemplate.value.criteria.forEach(criterion => {
      scores.push({
        itemId: item.id,
        criterionId: criterion.id,
        score: ratings[ratingKey(item.id, criterion.id)],
      })
    })
  })
  return { templateId: activeTemplate.value.id, isPublic: isPublic.value, scores }
}

async function saveResult() {
  if (!activeTemplate.value || !allRated.value || saveStatus.value === 'saving') return
  saveStatus.value = 'saving'
  saveError.value = ''
  const endpoint = editingResultId.value ? `/api/ratings/${editingResultId.value}/` : '/api/ratings/'
  try {
    const response = await apiFetch(`${apiBaseUrl}${endpoint}`, {
      method: editingResultId.value ? 'PATCH' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(resultPayload()),
    })
    const data = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(data.detail || 'Unable to save this rating result.')
    savedResultId.value = data.id
    editingResultId.value = data.id
    isPublic.value = Boolean(data.isPublic)
    saveStatus.value = 'saved'
  } catch (requestError) {
    saveError.value = requestError.message || 'Unable to connect to the server.'
    saveStatus.value = 'error'
  }
}

async function showRanking() {
  if (!allRated.value) {
    error.value = 'Complete every rating before viewing the ranking.'
    return
  }
  step.value = 3
  rankingPage.value = 1
  await saveResult()
}

async function loadResults(nextPage = 1) {
  historyPage.value = nextPage
  resultsLoading.value = true
  resultsError.value = ''
  try {
    const response = await apiFetch(`${apiBaseUrl}/api/ratings/?page=${nextPage}`)
    const data = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(data.detail || 'Unable to load your rating results.')
    const incoming = Array.isArray(data) ? data : data.results || []
    if (nextPage > 1 && !incoming.length) return loadResults(nextPage - 1)
    results.value = incoming
    historyPage.value = nextPage
    historyHasMore.value = Boolean(data.hasMore)
  } catch (requestError) {
    resultsError.value = requestError.message || 'Unable to connect to the server.'
  } finally {
    resultsLoading.value = false
  }
}

function editResult(result) {
  if (result.templateHidden) return
  activeTemplate.value = result.template
  ratingPage.value = 1
  editingResultId.value = result.id
  savedResultId.value = result.id
  isPublic.value = result.isPublic
  Object.keys(ratings).forEach(key => delete ratings[key])
  result.scores.forEach(entry => {
    ratings[ratingKey(entry.itemId, entry.criterionId)] = entry.score
  })
  saveStatus.value = 'saved'
  error.value = ''
  mode.value = 'new'
  step.value = 2
}

async function updateVisibility(result, value) {
  const response = await apiFetch(`${apiBaseUrl}/api/ratings/${result.id}/`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ isPublic: value }),
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.detail || 'Unable to update visibility.')
  result.isPublic = data.isPublic
  return data
}

async function toggleResultVisibility(result) {
  if (result.templateHidden) return
  result.actionError = ''
  try {
    await updateVisibility(result, !result.isPublic)
  } catch (requestError) {
    result.actionError = requestError.message
  }
}

async function toggleCurrentVisibility() {
  if (!savedResultId.value) return
  const record = { id: savedResultId.value, isPublic: isPublic.value }
  try {
    const data = await updateVisibility(record, !isPublic.value)
    isPublic.value = data.isPublic
  } catch (requestError) {
    saveError.value = requestError.message
    saveStatus.value = 'error'
  }
}

async function deleteResult(result) {
  if (!window.confirm(`Delete the rating for “${result.template.title}”?`)) return
  result.actionError = ''
  try {
    const response = await apiFetch(`${apiBaseUrl}/api/ratings/${result.id}/`, { method: 'DELETE' })
    const data = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(data.detail || 'Unable to delete this result.')
    results.value = results.value.filter(entry => entry.id !== result.id)
    await loadResults(results.value.length || historyPage.value === 1 ? historyPage.value : historyPage.value - 1)
  } catch (requestError) {
    result.actionError = requestError.message
  }
}

function formatDate(value) {
  return new Intl.DateTimeFormat('en', { dateStyle: 'medium' }).format(new Date(value))
}

onMounted(loadFavorites)
</script>

<template>
  <AppLayout>
    <div class="editor-heading rating-page-heading">
      <div><div class="eyebrow">YOUR RATING WORKSPACE</div><h1>Rate a template</h1><p>Create a new rating or manage results you have already saved.</p></div>
      <div class="rating-mode-tabs">
        <button :class="{ active: mode === 'new' }" type="button" @click="switchMode('new')">Start new rating</button>
        <button :class="{ active: mode === 'history' }" type="button" @click="switchMode('history')">My rating results</button>
      </div>
    </div>

    <section v-if="mode === 'history'" class="rate-content">
      <div class="history-heading"><div><h1>My rating results</h1><p>Review, edit, delete, or control who can see each result.</p></div><button class="action-button" type="button" @click="loadResults(historyPage)">Refresh</button></div>
      <div v-if="resultsLoading" class="history-state">Loading your results…</div>
      <div v-else-if="resultsError" class="history-state error-state"><p>{{ resultsError }}</p><button class="text-button" type="button" @click="loadResults(historyPage)">Try again</button></div>
      <div v-else-if="!results.length" class="history-state"><h2>No rating results yet</h2><p>Complete your first rating to see it here.</p><button class="action-button primary" type="button" @click="switchMode('new')">Start a rating</button></div>
      <div v-else class="history-list">
        <article v-for="result in results" :key="result.id" class="history-card">
          <div class="history-card-heading"><div><span class="state-badge">{{ result.templateHidden ? 'Template hidden' : result.isPublic ? 'Public' : 'Private' }}</span><h2>{{ result.template.title }}</h2><small>{{ formatDate(result.createdAt) }} · Result #{{ result.id }}</small></div><strong>{{ result.ranking[0]?.score.toFixed(1) }}</strong></div>
          <p v-if="result.templateHidden" class="history-hidden-note">This template is hidden by an administrator. You can view or delete this saved rating, but cannot edit or publish it until the template is restored. See your profile for the reason.</p>
          <ol><li v-for="(item, index) in result.ranking.slice(0, 3)" :key="item.itemId"><span>{{ index + 1 }}</span>{{ item.name }}<b>{{ item.score.toFixed(1) }}</b></li></ol>
          <p v-if="result.actionError" class="rate-error">{{ result.actionError }}</p>
          <div class="history-actions"><button v-if="!result.templateHidden" class="action-button" type="button" @click="editResult(result)">Edit ratings</button><button v-if="!result.templateHidden" class="action-button" type="button" @click="toggleResultVisibility(result)">{{ result.isPublic ? 'Make private' : 'Make public' }}</button><button class="text-button danger" type="button" @click="deleteResult(result)">Delete</button></div>
        </article>
        <ListPagination :page="historyPage" :has-more="historyHasMore" label="My rating results" @change="loadResults" />
      </div>
    </section>

    <template v-else>
      <div class="editor-steps rate-steps" aria-label="Rating steps"><button v-for="(label, index) in steps" :key="label" type="button" :aria-current="step === index + 1 ? 'step' : undefined" disabled><span>{{ index + 1 }}</span>{{ label }}</button></div>

      <section v-if="step === 1" class="rate-content">
        <h1>Choose from your favorites</h1><p class="editor-description">Only templates in your favorites can be used for a new rating.</p>
        <div v-if="favoritesLoading" class="history-state">Loading your favorite templates…</div>
        <div v-else-if="favoritesError" class="history-state error-state"><p>{{ favoritesError }}</p><button class="text-button" type="button" @click="loadFavorites(favoritesPage)">Try again</button></div>
        <div v-else-if="!favoriteTemplates.length" class="history-state"><h2>Your favorites are empty</h2><p>Create a template or add one to your favorites before starting a rating.</p><RouterLink class="action-button primary" to="/create">Create a template</RouterLink></div>
        <div v-else class="template-picker"><button v-for="entry in favoriteTemplates" :key="entry.id" type="button" class="template-option" @click="chooseTemplate(entry)"><img v-if="entry.items[0]?.imageUrl && !failedImages.has(entry.id)" :src="entry.items[0].imageUrl" :alt="entry.title" @error="failedImages = new Set([...failedImages, entry.id])"><div v-else class="template-image-fallback"><AppIcon name="star" /></div><span class="detail-category">Favorite · {{ entry.popularity }} saves</span><strong>{{ entry.title }}</strong><small>{{ entry.criteria.length }} criteria · {{ entry.items.length }} items</small><span class="choose-label">Use this template <AppIcon name="chevron" /></span></button></div>
        <ListPagination v-if="!favoritesLoading && !favoritesError && favoriteTemplates.length" :page="favoritesPage" :has-more="favoritesHasMore" label="Favorite templates" @change="loadFavorites" />
      </section>

      <section v-else-if="step === 2 && activeTemplate" ref="ratingSection" class="rate-content">
        <div class="rate-heading-row"><div><button v-if="!editingResultId" class="text-button" type="button" @click="resetRating"><AppIcon name="back" />Choose another template</button><h1>{{ activeTemplate.title }}</h1><p class="editor-description">{{ completedRatings }} of {{ totalRatings }} ratings completed.</p></div><div class="progress-ring">{{ Math.round(completedRatings / totalRatings * 100) }}%</div></div>
        <div class="rate-item-list"><article v-for="(item, itemIndex) in visibleRatingItems" :key="item.id" class="rate-item-card"><div class="rate-item-title"><span>{{ ratingPageStart + itemIndex + 1 }}</span><h2>{{ item.name }}</h2></div><div v-for="criterion in activeTemplate.criteria" :key="criterion.id" class="rate-criterion-row"><div><strong>{{ criterion.name }}</strong><small>Weight {{ criterion.weight }}</small></div><div class="stars"><button v-for="score in 5" :key="score" type="button" :class="{ selected: score <= (ratings[ratingKey(item.id, criterion.id)] || 0) }" :aria-label="`${item.name}: ${criterion.name}, ${score} stars`" @click="setRating(item.id, criterion.id, score)">★</button></div></div></article></div>
        <nav v-if="ratingPageCount > 1" class="rating-pagination" aria-label="Rating item pages">
          <button class="action-button" type="button" :disabled="ratingPage === 1" @click="goToRatingPage(ratingPage - 1)">Previous</button>
          <label>Page <select :value="ratingPage" aria-label="Rating page" @change="goToRatingPage(Number($event.target.value))"><option v-for="pageNumber in ratingPageCount" :key="pageNumber" :value="pageNumber">{{ pageNumber }}</option></select> of {{ ratingPageCount }} <span>· Items {{ ratingPageStart + 1 }}–{{ Math.min(ratingPageStart + itemsPerPage, activeTemplate.items.length) }} of {{ activeTemplate.items.length }}</span></label>
          <button class="action-button" type="button" :disabled="ratingPage === ratingPageCount" @click="goToRatingPage(ratingPage + 1)">Next</button>
        </nav>
        <p v-if="error" class="rate-error" role="alert">{{ error }}</p>
        <div class="rate-footer"><span>All fields are required; the result saves automatically after completion.</span><button class="action-button primary" type="button" :disabled="!allRated" @click="showRanking">{{ editingResultId ? 'Update and view ranking' : 'View ranking' }}</button></div>
      </section>

      <section v-else-if="activeTemplate" class="rate-content ranking-result">
        <div class="ranking-header"><div><div class="eyebrow">RATING COMPLETE</div><h1>Your ranking</h1><p>{{ activeTemplate.title }}</p></div><button class="action-button" type="button" @click="switchMode('history')">View my results</button></div>
        <div class="result-save-status" :class="saveStatus" role="status"><template v-if="saveStatus === 'saving'"><span class="save-dot" />Saving your rating result…</template><template v-else-if="saveStatus === 'saved'"><span>✓ Rating result saved<span v-if="savedResultId"> · ID {{ savedResultId }}</span></span><button class="text-button" type="button" @click="toggleCurrentVisibility">{{ isPublic ? 'Make private' : 'Make public' }}</button></template><template v-else-if="saveStatus === 'error'"><span>{{ saveError }}</span><button class="text-button" type="button" @click="saveResult">Try again</button></template></div>
        <div class="results-list"><article v-for="(item, index) in visibleRanking" :key="item.id" class="result-row"><span class="result-rank">{{ (rankingPage - 1) * itemsPerPage + index + 1 }}</span><div><strong>{{ item.name }}</strong><small>{{ activeTemplate.criteria.length }} weighted criteria</small></div><b>{{ item.score.toFixed(1) }}</b></article></div>
        <ListPagination :page="rankingPage" :total-pages="rankingPageCount" label="Your ranking" @change="rankingPage = $event" />
      </section>
    </template>
  </AppLayout>
</template>

<style scoped>
.rating-pagination{display:flex;align-items:center;justify-content:center;gap:16px;flex-wrap:wrap;margin-top:24px;color:#697662;font-size:13px}.rating-pagination label{display:flex;align-items:center;gap:6px;flex-wrap:wrap}.rating-pagination select{padding:6px 8px;border:1px solid #d8e2cf;border-radius:6px;background:#fff;color:#273326}.rating-pagination button:disabled{opacity:.45;cursor:default}
@media(max-width:620px){.rating-pagination label{order:-1;width:100%;justify-content:center}}
.rating-page-heading { align-items: flex-end; }.rating-mode-tabs{display:flex;gap:5px;padding:4px;border-radius:10px;background:#f0f3ed}.rating-mode-tabs button{padding:9px 14px;border:0;border-radius:7px;background:transparent;color:#74806f}.rating-mode-tabs button.active{background:white;color:var(--green);font-weight:700}.rate-steps button:disabled{cursor:default;opacity:1}.rate-content{max-width:1100px;margin:0 auto;padding-bottom:42px}.rate-content>h1{font-size:30px}.template-picker{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px;margin-top:28px}.template-option{position:relative;display:flex;flex-direction:column;align-items:flex-start;overflow:hidden;padding:0 0 18px;border:1px solid #e4eadd;border-radius:12px;background:#fbfcf9;color:#273326;text-align:left}.template-option:hover{border-color:#a8b99c;transform:translateY(-2px)}.template-option img{width:100%;height:150px;object-fit:cover}.template-image-fallback{display:flex;align-items:center;justify-content:center;width:100%;height:150px;background:#e9eee2;color:#537048}.template-image-fallback svg{width:35px;height:35px}.template-option .detail-category{margin:15px 16px 8px}.template-option strong{padding:0 16px;font-size:15px;line-height:1.45}.template-option small{padding:8px 16px 0;color:#899382}.choose-label{display:flex;align-items:center;gap:5px;margin:15px 16px 0;color:var(--green);font-size:13px;font-weight:700}.choose-label svg{width:15px;height:15px}.rate-heading-row,.ranking-header,.history-heading{display:flex;align-items:center;justify-content:space-between;gap:24px;margin-bottom:28px}.history-heading h1,.history-heading p{margin:0 0 9px}.history-heading p{color:#7a8872}.progress-ring{display:flex;align-items:center;justify-content:center;width:68px;height:68px;border:6px solid #dfe8d9;border-top-color:var(--green);border-radius:50%;color:var(--green);font-size:13px;font-weight:700}.rate-item-list,.history-list{display:grid;gap:16px}.rate-item-card,.history-card{padding:20px 24px;border:1px solid #e4eadd;border-radius:12px;background:#fbfcf9}.rate-item-title{display:flex;align-items:center;gap:12px;padding-bottom:15px}.rate-item-title span{display:flex;align-items:center;justify-content:center;width:30px;height:30px;border-radius:8px;background:#e9f0e4;color:var(--green)}.rate-item-title h2{margin:0;font-size:18px}.rate-criterion-row{display:flex;align-items:center;justify-content:space-between;gap:20px;padding:13px 0;border-top:1px solid var(--line)}.rate-criterion-row strong,.rate-criterion-row small{display:block}.rate-criterion-row small{margin-top:4px;color:#8a9484;font-size:11px}.rate-error{color:#a74842;font-size:13px}.rate-footer{display:flex;align-items:center;justify-content:space-between;gap:20px;margin-top:26px;padding-top:22px;border-top:1px solid var(--line)}.rate-footer span{color:#849079;font-size:12px}.ranking-header p{margin:10px 0 0;color:#7a8872}.result-save-status{display:flex;align-items:center;justify-content:space-between;gap:8px;min-height:44px;margin-bottom:18px;padding:10px 14px;border-radius:9px;background:#f3f6f0;color:#697662;font-size:13px}.result-save-status.saved{background:#e8f2e5;color:#31573b}.result-save-status.error{background:#faefec;color:#9b443d}.save-dot{width:8px;height:8px;border-radius:50%;background:#668258;animation:save-pulse .8s ease-in-out infinite alternate}@keyframes save-pulse{to{opacity:.3}}.history-state{padding:65px 30px;border:1px dashed #d8e2cf;border-radius:12px;text-align:center;color:#7b8775}.error-state{color:#9b443d}.history-card-heading{display:flex;justify-content:space-between;gap:20px}.history-card-heading h2{margin:12px 0 6px;font-size:18px}.history-card-heading small{color:#8a9484}.history-card-heading>strong{color:var(--green);font-size:25px}.history-card ol{list-style:none;margin:20px 0;padding:0;border-top:1px solid var(--line)}.history-card li{display:flex;gap:10px;padding:10px 0;border-bottom:1px solid var(--line);font-size:13px}.history-card li span{color:#829176}.history-card li b{margin-left:auto}.history-actions{display:flex;align-items:center;gap:10px;margin-top:18px}.danger{margin-left:auto;color:#a44b43}
@media(max-width:1000px){.template-picker{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:620px){.rating-page-heading,.rate-heading-row,.ranking-header,.rate-footer,.rate-criterion-row,.history-heading{align-items:flex-start;flex-direction:column}.template-picker{grid-template-columns:1fr}.rating-mode-tabs{width:100%}.rating-mode-tabs button{flex:1}.history-actions{align-items:stretch;flex-direction:column}.danger{margin-left:0}}

/* Align all rating stages with the page heading and shared content gutter. */
.rate-content { width: 100%; max-width: none; min-width: 0; margin: 0; text-align: left; }
.template-picker {
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 260px), 1fr));
  gap: 28px 24px;
  align-items: start;
}
.template-option { width: 100%; min-width: 0; }
.template-option img, .template-image-fallback {
  display: block;
  width: 100%;
  height: clamp(220px, 22vw, 340px);
  object-fit: contain;
  background: #eef0ea;
}
.template-image-fallback { display: flex; }
.template-option strong, .template-option small { overflow-wrap: anywhere; }
.rate-item-card, .history-card, .rate-heading-row > div, .ranking-header > div,
.history-heading > div, .rate-criterion-row > div, .result-row > div { min-width: 0; }
.rate-item-title > span, .progress-ring, .stars { flex-shrink: 0; }
.rate-item-title h2, .rate-criterion-row strong, .result-row strong, .history-card h2 { overflow-wrap: anywhere; }
.result-save-status, .history-actions { flex-wrap: wrap; }
.history-hidden-note { margin: 16px 0 0; color: #7b655b; font-size: 13px; line-height: 1.6; }
@media (max-width: 620px) {
  .template-picker { grid-template-columns: repeat(auto-fit, minmax(min(100%, 260px), 1fr)); gap: 24px; }
  .template-option img, .template-image-fallback { height: auto; aspect-ratio: 4 / 3; }
  .rate-item-card, .history-card { padding: 16px; }
  .rate-footer .action-button { width: 100%; }
}

</style>
