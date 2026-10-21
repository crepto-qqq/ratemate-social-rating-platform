<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import AppLayout from '../components/AppLayout.vue'
import AppIcon from '../components/AppIcon.vue'
import ListPagination from '../components/ListPagination.vue'
import { apiBaseUrl, apiFetch } from '../api.js'

const sections = [
  { key: 'users', label: 'Users', description: 'Search member accounts. Account changes are not part of content moderation.' },
  { key: 'templates', label: 'Templates', description: 'Hide a template from the community or restore it later.' },
  { key: 'ratings', label: 'Public ratings', description: 'Review and remove public rating posts.' },
  { key: 'comments', label: 'Comments', description: 'Review comments on templates and public ratings.' },
  { key: 'actions', label: 'Action history', description: 'A record of content decisions made by administrators.' },
]

const activeSection = ref('templates')
const section = computed(() => sections.find((entry) => entry.key === activeSection.value))
const searchInput = ref('')
const searchQuery = ref('')
const commentKind = ref('all')
const page = ref(1)
const items = ref([])
const hasMore = ref(false)
const checkingAccess = ref(true)
const isAdmin = ref(false)
const accessError = ref('')
const loading = ref(false)
const listError = ref('')
const status = ref('')
const pendingAction = ref(null)
const reason = ref('')
const actionError = ref('')
const saving = ref(false)
const reasonInput = ref(null)
const inspectorClose = ref(null)
const inspection = ref(null)
const inspectionItemsPage = ref(1)
const inspectionCriteriaPage = ref(1)
const inspectionRankingPage = ref(1)
const inspectionItemsPageCount = computed(() => Math.ceil((inspection.value?.data?.items?.length || 0) / 10))
const inspectionCriteriaPageCount = computed(() => Math.ceil((inspection.value?.data?.criteria?.length || 0) / 10))
const inspectionRankingPageCount = computed(() => Math.ceil((inspection.value?.data?.ranking?.length || 0) / 10))
const inspectionItems = computed(() => inspection.value?.data?.items?.slice((inspectionItemsPage.value - 1) * 10, inspectionItemsPage.value * 10) || [])
const inspectionCriteria = computed(() => inspection.value?.data?.criteria?.slice((inspectionCriteriaPage.value - 1) * 10, inspectionCriteriaPage.value * 10) || [])
const inspectionRanking = computed(() => inspection.value?.data?.ranking?.slice((inspectionRankingPage.value - 1) * 10, inspectionRankingPage.value * 10) || [])
const inspectionScoreItems = computed(() => {
  const items = new Map((inspection.value?.data?.template?.items || []).map((item) => [item.id, item]))
  return inspectionRanking.value.map((rank) => items.get(rank.itemId)).filter(Boolean)
})
const scoreLookup = computed(() => new Map(((inspection.value?.kind === 'rating' ? inspection.value?.data?.scores : []) || [])
  .map((score) => [`${score.itemId}:${score.criterionId}`, score.score])))
let loadVersion = 0
let inspectionVersion = 0

function formatDate(value) {
  if (!value) return 'Date unavailable'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Date unavailable' : date.toLocaleString()
}

function detailMessage(data, fallback) {
  if (typeof data?.detail === 'string') return data.detail
  if (typeof data?.error === 'string') return data.error
  if (typeof data?.reason?.[0] === 'string') return data.reason[0]
  return fallback
}

async function checkAccess() {
  checkingAccess.value = true
  accessError.value = ''
  try {
    const response = await apiFetch(`${apiBaseUrl}/api/moderation/me/`)
    const data = await response.json().catch(() => ({}))
    if (!response.ok) {
      accessError.value = response.status === 401
        ? 'Sign in to access this page.'
        : detailMessage(data, 'Unable to check administrator access.')
      return
    }
    isAdmin.value = Boolean(data.isAdmin)
    if (isAdmin.value) await loadItems()
  } catch (error) {
    accessError.value = error.message || 'Unable to connect to the server.'
  } finally {
    checkingAccess.value = false
  }
}

async function loadItems() {
  if (!isAdmin.value) return
  const current = ++loadVersion
  loading.value = true
  listError.value = ''
  const params = new URLSearchParams({ page: String(page.value) })
  if (searchQuery.value) params.set('q', searchQuery.value)
  if (activeSection.value === 'comments' && commentKind.value !== 'all') {
    params.set('kind', commentKind.value)
  }
  try {
    const response = await apiFetch(`${apiBaseUrl}/api/moderation/${activeSection.value}/?${params}`)
    const data = await response.json().catch(() => ({}))
    if (!response.ok) {
      if (response.status === 401) {
        accessError.value = 'Sign in to access this page.'
        isAdmin.value = false
        return
      }
      if (response.status === 403) {
        isAdmin.value = false
        throw new Error('Your account does not have administrator access.')
      }
      throw new Error(detailMessage(data, 'Unable to load this list.'))
    }
    if (current !== loadVersion) return
    items.value = Array.isArray(data[activeSection.value]) ? data[activeSection.value] : []
    hasMore.value = Boolean(data.hasMore)
  } catch (error) {
    if (current === loadVersion) listError.value = error.message || 'Unable to connect to the server.'
  } finally {
    if (current === loadVersion) loading.value = false
  }
}

function selectSection(key) {
  if (activeSection.value === key) return
  activeSection.value = key
  page.value = 1
  searchInput.value = ''
  searchQuery.value = ''
  status.value = ''
  loadItems()
}

function search() {
  searchQuery.value = searchInput.value.trim()
  page.value = 1
  loadItems()
}

function clearSearch() {
  searchInput.value = ''
  searchQuery.value = ''
  page.value = 1
  loadItems()
}

function setPage(nextPage) {
  if (nextPage < 1 || (nextPage > page.value && !hasMore.value)) return
  page.value = nextPage
  loadItems()
}

watch(commentKind, () => {
  if (activeSection.value === 'comments') {
    page.value = 1
    loadItems()
  }
})

function openAction(kind, item) {
  const config = {
    hide: {
      title: 'Hide template',
      target: item.title,
      explanation: 'The template and its public ratings will no longer be visible to the community. Their data is kept so the template can be restored.',
      button: 'Hide template',
      endpoint: `templates/${item.id}/hide/`,
      success: 'Template hidden.',
    },
    restore: {
      title: 'Restore template',
      target: item.title,
      explanation: 'The template and its retained public ratings will become visible again.',
      button: 'Restore template',
      endpoint: `templates/${item.id}/restore/`,
      success: 'Template restored.',
    },
    removeRating: {
      title: 'Permanently remove public rating',
      target: `${item.owner.name}’s rating of ${item.templateTitle}`,
      explanation: 'This rating post and its comments and likes will be permanently deleted. This cannot be undone.',
      button: 'Remove rating permanently',
      endpoint: `ratings/${item.id}/remove/`,
      success: 'Public rating removed.',
      destructive: true,
    },
    removeComment: {
      title: 'Permanently remove comment',
      target: `${item.author.name}’s comment on ${item.postTitle}`,
      explanation: 'The comment will be permanently deleted. Its author will receive a moderation notice. This cannot be undone.',
      button: 'Remove comment permanently',
      endpoint: `comments/${item.kind}/${item.id}/remove/`,
      success: 'Comment removed.',
      destructive: true,
    },
  }[kind]
  pendingAction.value = config
  reason.value = ''
  actionError.value = ''
  nextTick(() => reasonInput.value?.focus())
}

function closeAction() {
  if (saving.value) return
  pendingAction.value = null
  reason.value = ''
  actionError.value = ''
}

async function openInspection(kind, id) {
  const current = ++inspectionVersion
  inspectionItemsPage.value = 1
  inspectionCriteriaPage.value = 1
  inspectionRankingPage.value = 1
  inspection.value = { kind, id, loading: true, error: '', data: null }
  nextTick(() => inspectorClose.value?.focus())
  try {
    const response = await apiFetch(`${apiBaseUrl}/api/moderation/${kind}s/${id}/`)
    const data = await response.json().catch(() => ({}))
    if (current !== inspectionVersion) return
    if (!response.ok) {
      if (response.status === 401) {
        accessError.value = 'Sign in to access this page.'
        isAdmin.value = false
        closeInspection()
        return
      }
      if (response.status === 403) {
        isAdmin.value = false
        closeInspection()
        return
      }
      throw new Error(detailMessage(data, 'Unable to load content details.'))
    }
    inspection.value.data = data[kind]
  } catch (error) {
    if (current === inspectionVersion) inspection.value.error = error.message || 'Unable to connect to the server.'
  } finally {
    if (current === inspectionVersion) inspection.value.loading = false
  }
}

function closeInspection() {
  inspectionVersion += 1
  inspection.value = null
}

async function confirmAction() {
  if (!pendingAction.value || saving.value) return
  const explanation = reason.value.trim()
  if (!explanation) {
    actionError.value = 'Enter a reason before continuing.'
    return
  }
  saving.value = true
  actionError.value = ''
  try {
    const response = await apiFetch(`${apiBaseUrl}/api/moderation/${pendingAction.value.endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason: explanation }),
    })
    const data = await response.json().catch(() => ({}))
    if (response.status === 401 || response.status === 403) {
      if (response.status === 401) accessError.value = 'Sign in to access this page.'
      isAdmin.value = false
      pendingAction.value = null
      return
    }
    if (!response.ok) throw new Error(detailMessage(data, 'Unable to complete this action.'))
    status.value = data.message || pendingAction.value.success
    pendingAction.value = null
    reason.value = ''
    await loadItems()
    if (!listError.value && items.value.length === 0 && page.value > 1) {
      page.value -= 1
      await loadItems()
    }
  } catch (error) {
    actionError.value = error.message || 'Unable to connect to the server.'
  } finally {
    saving.value = false
  }
}

onMounted(checkAccess)
</script>

<template>
  <AppLayout>
    <header class="admin-heading">
      <div>
        <div class="eyebrow">COMMUNITY CARE</div>
        <h1>Admin</h1>
        <p>Review community content and keep a record of decisions.</p>
      </div>
      <span class="admin-label">Content moderation</span>
    </header>

    <section v-if="checkingAccess" class="admin-state" role="status">
      <span class="admin-spinner" />
      <p>Checking administrator access…</p>
    </section>

    <section v-else-if="accessError" class="admin-state" role="alert">
      <h2>Unable to open Admin</h2>
      <p>{{ accessError }}</p>
      <button class="action-button" type="button" @click="checkAccess">Try again</button>
    </section>

    <section v-else-if="!isAdmin" class="admin-state" role="alert">
      <h2>Administrator access required</h2>
      <p>This page is available only to designated administrators.</p>
      <RouterLink class="action-button" to="/home_page">Back to Discover</RouterLink>
    </section>

    <div v-else class="admin-workspace">
      <nav class="admin-tabs" aria-label="Admin sections">
        <button v-for="tab in sections" :key="tab.key" type="button" :aria-current="activeSection === tab.key ? 'page' : undefined" @click="selectSection(tab.key)">
          {{ tab.label }}
        </button>
      </nav>

      <div class="admin-section-head">
        <div>
          <h2>{{ section.label }}</h2>
          <p>{{ section.description }}</p>
        </div>
        <span v-if="activeSection === 'users'" class="read-only-label">Read only</span>
      </div>

      <div v-if="status" class="admin-success" role="status">{{ status }}</div>

      <div class="admin-toolbar">
        <form class="admin-search" role="search" @submit.prevent="search">
          <AppIcon name="search" />
          <div class="search-field"><input v-length-feedback v-model="searchInput" :aria-label="`Search ${section.label.toLowerCase()}`" :placeholder="`Search ${section.label.toLowerCase()}`" maxlength="200"></div>
          <button class="action-button primary" type="submit">Search</button>
          <button v-if="searchQuery" class="action-button" type="button" @click="clearSearch">Clear</button>
        </form>
        <label v-if="activeSection === 'comments'" class="admin-filter">
          Comment type
          <select v-model="commentKind">
            <option value="all">All comments</option>
            <option value="template">Template comments</option>
            <option value="rating">Rating comments</option>
          </select>
        </label>
      </div>

      <div v-if="listError" class="admin-list-state" role="alert">
        <p>{{ listError }}</p>
        <button class="action-button" type="button" @click="loadItems">Try again</button>
      </div>
      <div v-else-if="loading" class="admin-list-state" role="status">Loading {{ section.label.toLowerCase() }}…</div>
      <div v-else-if="!items.length" class="admin-list-state">No {{ section.label.toLowerCase() }} found.</div>

      <div v-else class="admin-list">
        <article v-for="item in items" :key="activeSection === 'comments' ? `${item.kind}:${item.id}` : item.id" class="admin-card">
          <template v-if="activeSection === 'users'">
            <div class="admin-card-main">
              <div class="admin-card-top"><h3>{{ item.name }}</h3><span class="admin-id">#{{ item.id }}</span><span v-if="item.isStaff" class="admin-pill">Administrator</span></div>
              <p>{{ item.email }}</p>
              <small>Joined {{ formatDate(item.joinedAt) }}</small>
            </div>
          </template>

          <template v-else-if="activeSection === 'templates'">
            <div class="admin-card-main">
              <div class="admin-card-top"><h3>{{ item.title }}</h3><span class="admin-id">#{{ item.id }}</span><span class="admin-pill" :class="{ hidden: item.isHidden }">{{ item.isHidden ? 'Hidden' : 'Visible' }}</span></div>
              <p v-if="item.description" class="admin-excerpt">{{ item.description }}</p>
              <div class="admin-meta"><span>By {{ item.owner.name }}</span><span>{{ formatDate(item.createdAt) }}</span><span>{{ item.ratingCount }} ratings</span><span>{{ item.commentCount }} comments</span><span>{{ item.favoriteCount }} saves</span></div>
            </div>
            <div class="admin-card-actions">
              <button class="action-button" type="button" @click="openInspection('template', item.id)">Inspect</button>
              <RouterLink v-if="!item.isHidden" class="action-button" :to="`/templates/${item.id}`">View post</RouterLink>
              <button class="action-button" :class="{ 'admin-danger': !item.isHidden }" type="button" @click="openAction(item.isHidden ? 'restore' : 'hide', item)">{{ item.isHidden ? 'Restore' : 'Hide' }}</button>
            </div>
          </template>

          <template v-else-if="activeSection === 'ratings'">
            <div class="admin-card-main">
              <div class="admin-card-top"><h3>{{ item.owner.name }}’s rating</h3><span class="admin-id">#{{ item.id }}</span></div>
              <p>Based on <strong>{{ item.templateTitle }}</strong></p>
              <div class="admin-meta"><span>{{ formatDate(item.createdAt) }}</span><span>{{ item.commentCount }} comments</span><span>{{ item.likeCount }} likes</span></div>
            </div>
            <div class="admin-card-actions">
              <button class="action-button" type="button" @click="openInspection('rating', item.id)">Inspect</button>
              <RouterLink v-if="!item.templateHidden" class="action-button" :to="`/ratings/${item.id}`">View post</RouterLink>
              <button class="action-button admin-danger" type="button" @click="openAction('removeRating', item)">Remove</button>
            </div>
          </template>

          <template v-else-if="activeSection === 'comments'">
            <div class="admin-card-main">
              <div class="admin-card-top"><h3>{{ item.author.name }}</h3><span class="admin-id">#{{ item.id }}</span><span class="admin-pill">{{ item.kind === 'template' ? 'Template' : 'Rating' }} comment</span></div>
              <p class="admin-comment-content">{{ item.content }}</p>
              <div class="admin-meta"><span>On {{ item.postTitle }}</span><span>{{ formatDate(item.createdAt) }}</span></div>
            </div>
            <div class="admin-card-actions">
              <button class="action-button" type="button" @click="openInspection(item.kind, item.postId)">Inspect context</button>
              <RouterLink v-if="!item.templateHidden" class="action-button" :to="item.kind === 'template' ? `/templates/${item.postId}` : `/ratings/${item.postId}#comments`">View context</RouterLink>
              <button class="action-button admin-danger" type="button" @click="openAction('removeComment', item)">Remove</button>
            </div>
          </template>

          <template v-else>
            <div class="admin-card-main">
              <div class="admin-card-top"><h3>{{ item.targetLabel }}</h3><span class="admin-id">#{{ item.id }}</span><span class="admin-pill">{{ item.action }}</span></div>
              <p class="admin-excerpt">{{ item.reason }}</p>
              <div class="admin-meta"><span>{{ item.targetType }} #{{ item.targetId }}</span><span>By {{ item.actor.name }}</span><span>{{ formatDate(item.createdAt) }}</span></div>
            </div>
          </template>
        </article>
      </div>

      <div v-if="!loading && !listError && (page > 1 || hasMore)" class="admin-pagination">
        <button class="action-button" type="button" :disabled="page === 1" @click="setPage(page - 1)">Previous</button>
        <span>Page {{ page }}</span>
        <button class="action-button" type="button" :disabled="!hasMore" @click="setPage(page + 1)">Next</button>
      </div>
    </div>

    <div v-if="inspection" class="admin-modal-backdrop" @click.self="closeInspection">
      <section class="admin-modal admin-inspector" role="dialog" aria-modal="true" aria-labelledby="admin-inspector-title" @keydown.esc="closeInspection">
        <div class="admin-modal-header"><span class="eyebrow">CONTENT INSPECTION</span><button ref="inspectorClose" class="admin-close" type="button" aria-label="Close" @click="closeInspection">×</button></div>
        <div v-if="inspection.loading" class="admin-inspection-state" role="status"><h2 id="admin-inspector-title">Content details</h2>Loading content…</div>
        <div v-else-if="inspection.error" class="admin-inspection-state" role="alert"><h2 id="admin-inspector-title">Unable to load content</h2>{{ inspection.error }}</div>
        <template v-else-if="inspection.data">
          <div class="admin-inspection-heading">
            <h2 id="admin-inspector-title">{{ inspection.kind === 'template' ? inspection.data.title : `${inspection.data.owner.name}’s rating` }}</h2>
            <span v-if="inspection.kind === 'template' ? inspection.data.isHidden : inspection.data.templateHidden" class="admin-pill hidden">Template hidden</span>
          </div>
          <p class="admin-inspection-byline">{{ inspection.kind === 'template' ? `By ${inspection.data.owner.name}` : `Based on ${inspection.data.template.title}` }} · {{ formatDate(inspection.data.createdAt) }}</p>
          <p v-if="(inspection.kind === 'template' ? inspection.data.description : inspection.data.template.description)" class="admin-inspection-description">{{ inspection.kind === 'template' ? inspection.data.description : inspection.data.template.description }}</p>

          <template v-if="inspection.kind === 'template'">
            <div class="admin-inspection-stats"><span>{{ inspection.data.ratingCount }} ratings</span><span>{{ inspection.data.commentCount }} comments</span><span>{{ inspection.data.favoriteCount }} saves</span></div>
            <h3>Criteria</h3>
            <ul class="admin-criteria"><li v-for="criterion in inspectionCriteria" :key="criterion.id"><strong>{{ criterion.name }}</strong><span>Weight {{ criterion.weight }}</span></li></ul>
            <ListPagination :page="inspectionCriteriaPage" :total-pages="inspectionCriteriaPageCount" label="Inspection criteria" @change="inspectionCriteriaPage = $event" />
            <h3>Items</h3>
            <ul class="admin-items"><li v-for="item in inspectionItems" :key="item.id"><img v-if="item.imageUrl" :src="item.imageUrl" :alt="item.name"><span>{{ item.name }}</span></li></ul>
            <ListPagination :page="inspectionItemsPage" :total-pages="inspectionItemsPageCount" label="Inspection items" @change="inspectionItemsPage = $event" />
          </template>

          <template v-else>
            <div class="admin-inspection-stats"><span>{{ inspection.data.likeCount }} likes</span><span>{{ inspection.data.commentCount }} comments</span></div>
            <h3>Final ranking</h3>
            <ol class="admin-ranking"><li v-for="(rank, index) in inspectionRanking" :key="rank.itemId"><span class="admin-rank">{{ (inspectionRankingPage - 1) * 10 + index + 1 }}</span><img v-if="rank.imageUrl" :src="rank.imageUrl" :alt="rank.name"><strong>{{ rank.name }}</strong><b>{{ Number(rank.score).toFixed(1) }}/100</b></li></ol>
            <ListPagination :page="inspectionRankingPage" :total-pages="inspectionRankingPageCount" label="Inspection ranking" @change="inspectionRankingPage = $event" />
            <h3>Scores by criterion</h3>
            <div class="admin-score-scroll"><table><thead><tr><th>Item</th><th v-for="criterion in inspection.data.template.criteria" :key="criterion.id">{{ criterion.name }}</th></tr></thead><tbody><tr v-for="item in inspectionScoreItems" :key="item.id"><th>{{ item.name }}</th><td v-for="criterion in inspection.data.template.criteria" :key="criterion.id">{{ scoreLookup.get(`${item.id}:${criterion.id}`) ?? '—' }}</td></tr></tbody></table></div>
          </template>
        </template>
      </section>
    </div>

    <div v-if="pendingAction" class="admin-modal-backdrop" @click.self="closeAction">
      <section class="admin-modal" role="dialog" aria-modal="true" aria-labelledby="admin-action-title" aria-describedby="admin-action-description" @keydown.esc="closeAction">
        <div class="admin-modal-header"><span class="eyebrow">ADMIN ACTION</span><button class="admin-close" type="button" :disabled="saving" aria-label="Close" @click="closeAction">×</button></div>
        <h2 id="admin-action-title">{{ pendingAction.title }}</h2>
        <p class="admin-target">{{ pendingAction.target }}</p>
        <p id="admin-action-description">{{ pendingAction.explanation }}</p>
        <form @submit.prevent="confirmAction">
          <label class="editor-field" for="admin-reason">Reason <span class="optional">Required; recorded with this action and sent to the affected author.</span></label>
          <textarea v-length-feedback id="admin-reason" ref="reasonInput" v-model="reason" rows="4" maxlength="1000" required placeholder="Explain why this content is being handled" />
          <p v-if="actionError" class="admin-action-error" role="alert">{{ actionError }}</p>
          <div class="admin-modal-actions"><button class="action-button" type="button" :disabled="saving" @click="closeAction">Cancel</button><button class="action-button" :class="pendingAction.destructive ? 'admin-danger-solid' : 'primary'" type="submit" :disabled="saving || !reason.trim()">{{ saving ? 'Saving…' : pendingAction.button }}</button></div>
        </form>
      </section>
    </div>
  </AppLayout>
</template>

<style scoped>
.admin-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; margin-bottom: 34px; }
.admin-heading h1 { margin: 0; }
.admin-heading p, .admin-section-head p { color: var(--text-secondary); font-size: 14px; line-height: 1.6; }
.admin-label, .read-only-label { background: #edf3e7; border-radius: 7px; color: #517041; font-size: 12px; padding: 8px 11px; white-space: nowrap; }
.read-only-label { background: #f0f2ed; color: var(--text-secondary); }
.admin-state, .admin-list-state { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 250px; padding: 32px; border: 1px solid #e5ebdf; border-radius: 12px; background: #fbfcf9; color: var(--text-secondary); text-align: center; }
.admin-state h2 { color: #273326; margin: 0; }
.admin-state p { margin: 12px 0 20px; }
.admin-spinner { width: 34px; height: 34px; border: 3px solid #dce5d6; border-top-color: var(--green); border-radius: 50%; animation: spin .8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.admin-workspace { min-width: 0; }
.admin-tabs { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 28px; border-bottom: 1px solid var(--line); padding-bottom: 14px; }
.admin-tabs button { border: 0; border-radius: 8px; background: transparent; color: var(--text-secondary); font-size: 14px; padding: 10px 14px; cursor: pointer; }
.admin-tabs button:hover { background: #f2f5ef; }
.admin-tabs button[aria-current] { background: #e5eee1; color: var(--green); font-weight: 700; }
.admin-section-head { display: flex; justify-content: space-between; gap: 20px; align-items: flex-start; }
.admin-section-head h2 { margin: 0; font-size: 21px; }
.admin-section-head p { margin: 7px 0 0; }
.admin-success { margin-top: 20px; padding: 12px 15px; border: 1px solid #cfe2c5; border-radius: 9px; background: #f0f7eb; color: #315b38; font-size: 14px; }
.admin-toolbar { display: flex; flex-wrap: wrap; align-items: end; justify-content: space-between; gap: 14px; margin: 24px 0 18px; }
.admin-search { display: flex; flex: 1; min-width: 220px; max-width: 620px; gap: 8px; align-items: center; }
.admin-search > svg { width: 18px; height: 18px; color: var(--text-secondary); flex-shrink: 0; }
.admin-search input { flex: 1; width: 100%; min-width: 0; min-height: 44px; border: 1px solid #dce4d4; border-radius: 9px; padding: 10px 12px; background: #fff; color: #34492d; font-size: 14px; }
.admin-filter { display: flex; flex-direction: column; gap: 5px; color: var(--text-secondary); font-size: 12px; }
.admin-filter select { min-height: 44px; border: 1px solid #dce4d4; border-radius: 9px; padding: 0 11px; background: white; color: #34492d; font-size: 14px; }
.admin-list-state { min-height: 190px; }
.admin-list { display: grid; gap: 12px; }
.admin-card { display: flex; justify-content: space-between; align-items: center; gap: 24px; min-width: 0; padding: 20px 22px; border: 1px solid #e5ebdf; border-radius: 11px; background: #fbfcf9; }
.admin-card-main { min-width: 0; }
.admin-card-top, .admin-meta, .admin-card-actions { display: flex; align-items: center; flex-wrap: wrap; gap: 8px 13px; }
.admin-card-top h3 { margin: 0; font-size: 16px; overflow-wrap: anywhere; }
.admin-card-main > p { margin: 8px 0; color: var(--text-secondary); font-size: 13px; line-height: 1.55; overflow-wrap: anywhere; }
.admin-card-main > small, .admin-meta { color: var(--text-secondary); font-size: 12px; }
.admin-excerpt { display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 3; overflow: hidden; white-space: pre-wrap; }
.admin-comment-content { white-space: pre-wrap; overflow-wrap: anywhere; }
.admin-id { color: var(--text-secondary); font-size: 12px; }
.admin-pill { border-radius: 6px; background: #edf3e7; color: #517041; font-size: 11px; padding: 5px 8px; white-space: nowrap; }
.admin-pill.hidden { background: #f4ebe1; color: #986b40; }
.admin-card-actions { flex-shrink: 0; justify-content: flex-end; }
.admin-danger { border-color: #e7ccc8; color: #a4463f; }
.admin-danger:hover { background: #fbefed; }
.admin-pagination { display: flex; align-items: center; justify-content: center; gap: 18px; padding: 27px 0; color: var(--text-secondary); font-size: 13px; }
.admin-modal-backdrop { position: fixed; z-index: 30; inset: 0; display: grid; place-items: center; overflow-y: auto; padding: 20px; background: #15211780; }
.admin-modal { width: min(100%, 520px); max-height: calc(100vh - 40px); overflow-y: auto; padding: 27px; border: 1px solid #dde6d8; border-radius: 15px; background: #fff; box-shadow: 0 18px 55px #14261b33; }
.admin-modal-header { display: flex; align-items: center; justify-content: space-between; }
.admin-close { border: 0; background: transparent; color: var(--text-secondary); font-size: 25px; cursor: pointer; }
.admin-modal h2 { margin: 5px 0 8px; font-size: 22px; }
.admin-modal p { color: var(--text-secondary); font-size: 14px; line-height: 1.6; }
.admin-modal .admin-target { margin: 0; color: #334b39; font-weight: 700; overflow-wrap: anywhere; }
.admin-modal form { margin-top: 23px; }
.admin-modal .editor-field { display: block; margin-bottom: 8px; }
.admin-modal textarea { width: 100%; min-height: 110px; resize: vertical; border: 1px solid #dce4d4; border-radius: 9px; padding: 12px; color: #34492d; font: inherit; }
.admin-action-error { margin: 8px 0 0; color: #a4463f !important; }
.admin-modal-actions { display: flex; justify-content: flex-end; flex-wrap: wrap; gap: 10px; margin-top: 22px; }
.admin-danger-solid { border-color: #a4463f; background: #a4463f; color: #fff; }
.admin-danger-solid:hover { background: #913a34; }
.admin-inspector { width: min(100%, 760px); }
.admin-inspection-state { padding: 45px 12px; color: var(--text-secondary); text-align: center; }
.admin-inspection-heading { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }
.admin-inspection-heading h2 { margin: 8px 0 0; }
.admin-inspection-byline { margin: 8px 0 0; font-size: 12px !important; color: var(--text-secondary) !important; }
.admin-inspection-description { white-space: pre-wrap; overflow-wrap: anywhere; }
.admin-inspection-stats { display: flex; flex-wrap: wrap; gap: 8px; margin: 18px 0; }
.admin-inspection-stats span { border-radius: 7px; background: #edf3e7; color: #517041; padding: 7px 9px; font-size: 12px; }
.admin-inspector h3 { margin: 24px 0 12px; font-size: 15px; }
.admin-criteria, .admin-items, .admin-ranking { list-style: none; padding: 0; margin: 0; }
.admin-criteria { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.admin-criteria li { display: flex; justify-content: space-between; gap: 10px; border: 1px solid #e5ebdf; border-radius: 8px; background: #fbfcf9; padding: 12px; font-size: 13px; }
.admin-criteria span { color: var(--text-secondary); white-space: nowrap; }
.admin-items { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.admin-items li { display: flex; align-items: center; gap: 11px; min-width: 0; border: 1px solid #e5ebdf; border-radius: 8px; background: #fbfcf9; padding: 9px; font-size: 13px; overflow-wrap: anywhere; }
.admin-items img, .admin-ranking img { width: 45px; height: 45px; border-radius: 7px; object-fit: cover; flex-shrink: 0; }
.admin-ranking li { display: flex; align-items: center; gap: 12px; border-bottom: 1px solid var(--line); padding: 10px 0; font-size: 13px; }
.admin-ranking strong { overflow-wrap: anywhere; }
.admin-ranking b { margin-left: auto; color: #325c48; white-space: nowrap; }
.admin-rank { display: grid; place-items: center; width: 25px; height: 25px; border-radius: 7px; background: #e9f0e1; color: #325c48; flex-shrink: 0; }
.admin-score-scroll { max-width: 100%; overflow: auto; border: 1px solid var(--line); border-radius: 8px; }
.admin-score-scroll table { width: 100%; border-collapse: collapse; white-space: nowrap; font-size: 12px; }
.admin-score-scroll th, .admin-score-scroll td { padding: 10px; border-bottom: 1px solid var(--line); text-align: left; }
.admin-score-scroll thead { background: #f7f9f4; }
@media (max-width: 750px) { .admin-heading, .admin-section-head { flex-direction: column; } .admin-card { align-items: flex-start; flex-direction: column; } .admin-card-actions { justify-content: flex-start; } .admin-search { max-width: none; } }
@media (max-width: 620px) { .admin-heading { margin-bottom: 24px; } .admin-tabs button { padding: 9px 11px; } .admin-toolbar, .admin-search { align-items: stretch; } .admin-search { flex-wrap: wrap; } .admin-search > svg { display: none; } .admin-search input { flex-basis: 100%; } .admin-card { padding: 16px; } .admin-modal { padding: 20px; } .admin-criteria, .admin-items { grid-template-columns: 1fr; } }
</style>
