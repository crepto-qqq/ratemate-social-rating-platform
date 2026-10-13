<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import AppLayout from '../components/AppLayout.vue'
import { apiBaseUrl, apiFetch } from '../api.js'

const router = useRouter()
const notifications = ref([])
const filter = ref('all')
const loading = ref(true)
const error = ref('')
const actionError = ref('')
const markingAll = ref(false)
const unreadCount = ref(0)
const page = ref(1)
const hasMore = ref(false)
const loadingMore = ref(false)
let requestId = 0

function setFilter(value) {
  if (filter.value === value) return
  filter.value = value
  loadNotifications()
}

async function loadNotifications({ more = false } = {}) {
  const currentRequest = ++requestId
  if (more) loadingMore.value = true
  else loading.value = true
  try {
    const nextPage = more ? page.value + 1 : 1
    const unread = filter.value === 'unread' ? '&unread=1' : ''
    const response = await apiFetch(`${apiBaseUrl}/api/notifications/?page=${nextPage}${unread}`)
    const data = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(data.detail || 'Unable to load notifications.')
    if (currentRequest !== requestId) return
    const incoming = Array.isArray(data.notifications) ? data.notifications : []
    notifications.value = more ? [...notifications.value, ...incoming] : incoming
    page.value = nextPage
    hasMore.value = Boolean(data.hasMore)
    unreadCount.value = Number(data.unreadCount) || 0
    error.value = ''
    window.dispatchEvent(new Event('notifications:updated'))
  } catch (requestError) {
    if (currentRequest !== requestId) return
    if (more) actionError.value = requestError.message || 'Unable to load more messages.'
    else error.value = requestError.message || 'Unable to load notifications.'
  } finally {
    if (currentRequest === requestId) {
      loading.value = false
      loadingMore.value = false
    }
  }
}

function formatDate(value) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return new Intl.DateTimeFormat('en-AU', { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}

function iconFor(type) {
  if (type?.includes('favorite')) return 'bookmark'
  if (type?.includes('like')) return 'heart'
  if (type?.includes('moderation') || type?.includes('removed') || type?.includes('hidden')) return 'shield'
  return 'bell'
}

function messageTitle(notification) {
  const title = notification.summary || 'content'
  if (notification.type === 'moderation') {
    const action = notification.action === 'restored' ? 'restored'
      : notification.action === 'hidden' ? 'hidden' : 'removed'
    if (notification.targetType === 'template') return `Template “${title}” was ${action} by an administrator.`
    return `Your ${notification.targetType || 'content'} “${title}” was ${action} by an administrator.`
  }
  const name = notification.actorName || 'Someone'
  if (notification.type === 'template_favorite') return `${name} saved your template “${title}”.`
  if (notification.type === 'template_comment') return `${name} commented on your template “${title}”.`
  if (notification.type === 'rating_like') return `${name} liked your rating of “${title}”.`
  if (notification.type === 'rating_comment') return `${name} commented on your rating of “${title}”.`
  return title
}

async function openNotification(notification) {
  actionError.value = ''
  if (!notification.isRead) {
    try {
      const response = await apiFetch(`${apiBaseUrl}/api/notifications/${notification.id}/read/`, { method: 'POST' })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(data.detail || 'Unable to mark this notification as read.')
      notification.isRead = true
      if (filter.value === 'unread') {
        notifications.value = notifications.value.filter((item) => item.id !== notification.id)
        loadNotifications()
      }
      unreadCount.value = Number(data.unreadCount) || 0
      window.dispatchEvent(new Event('notifications:updated'))
    } catch (requestError) {
      actionError.value = requestError.message || 'Unable to mark this notification as read.'
      return
    }
  }
  if (notification.targetUrl?.startsWith('/')) router.push(notification.targetUrl)
}

async function markAllRead() {
  if (!unreadCount.value || markingAll.value) return
  markingAll.value = true
  actionError.value = ''
  try {
    const response = await apiFetch(`${apiBaseUrl}/api/notifications/read-all/`, { method: 'POST' })
    const data = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(data.detail || 'Unable to mark notifications as read.')
    notifications.value.forEach((item) => { item.isRead = true })
    if (filter.value === 'unread') {
      notifications.value = []
      page.value = 1
      hasMore.value = false
    }
    unreadCount.value = 0
    window.dispatchEvent(new Event('notifications:updated'))
  } catch (requestError) {
    actionError.value = requestError.message || 'Unable to mark notifications as read.'
  } finally {
    markingAll.value = false
  }
}

onMounted(() => loadNotifications())
</script>

<template>
  <AppLayout>
    <div class="messages-heading">
      <div>
        <div class="eyebrow">RECENT ACTIVITY</div>
        <h1>Messages</h1>
        <p>Updates about your templates, ratings and content decisions.</p>
      </div>
      <button class="action-button" type="button" :disabled="!unreadCount || markingAll" @click="markAllRead">
        {{ markingAll ? 'Updating…' : 'Mark all as read' }}
      </button>
    </div>

    <div class="message-toolbar">
      <div class="filter-tabs" role="group" aria-label="Filter messages">
        <button type="button" :class="{ active: filter === 'all' }" :aria-pressed="filter === 'all'" @click="setFilter('all')">All</button>
        <button type="button" :class="{ active: filter === 'unread' }" :aria-pressed="filter === 'unread'" @click="setFilter('unread')">Unread <span v-if="unreadCount">{{ unreadCount }}</span></button>
      </div>
      <button class="text-button" type="button" @click="loadNotifications()">Refresh</button>
    </div>

    <p v-if="actionError" class="message-error" role="alert">{{ actionError }}</p>
    <div v-if="loading" class="empty-results" role="status">Loading messages…</div>
    <section v-else-if="error" class="empty-results" role="alert">
      <h2>Unable to load messages</h2>
      <p>{{ error }}</p>
      <button class="action-button" type="button" @click="loadNotifications()">Try again</button>
    </section>
    <section v-else-if="!notifications.length" class="empty-results" aria-label="Messages">
      <AppIcon name="bell" />
      <h2>{{ filter === 'unread' ? 'All caught up' : 'No messages yet' }}</h2>
      <p>{{ filter === 'unread' ? 'You have no unread messages.' : 'New activity and content decisions will appear here.' }}</p>
    </section>
    <section v-else class="message-list" aria-label="Messages">
      <button
        v-for="notification in notifications"
        :key="notification.id"
        class="message-item"
        :class="{ unread: !notification.isRead }"
        type="button"
        @click="openNotification(notification)"
      >
        <span class="message-icon"><AppIcon :name="iconFor(notification.type)" /></span>
        <span class="message-copy">
          <span class="message-title">{{ messageTitle(notification) }}</span>
          <span v-if="notification.preview" class="message-preview">{{ notification.preview }}</span>
          <span v-if="notification.reason" class="message-reason">Reason: {{ notification.reason }}</span>
          <small>{{ formatDate(notification.createdAt) }}</small>
        </span>
        <span v-if="!notification.isRead" class="unread-dot" aria-label="Unread" />
        <AppIcon v-if="notification.targetUrl" name="chevron" class="message-chevron" />
      </button>
    </section>
    <div v-if="!loading && !error && hasMore" class="message-more">
      <button class="action-button" type="button" :disabled="loadingMore" @click="loadNotifications({ more: true })">
        {{ loadingMore ? 'Loading…' : 'Load more' }}
      </button>
    </div>
  </AppLayout>
</template>

<style scoped>
.message-list { width: 100%; }
.message-item { width: 100%; border: 0; border-bottom: 1px solid var(--line); background: transparent; color: inherit; font: inherit; text-align: left; cursor: pointer; }
.message-item:hover, .message-item:focus-visible { background: #f2f6ef; }
.message-item.unread { background: #f8faf6; }
.message-icon { flex: 0 0 40px; }
.message-icon svg { width: 20px; height: 20px; }
.message-copy { display: grid; gap: 5px; min-width: 0; }
.message-title { color: #2d3d2f; font-weight: 650; }
.message-preview, .message-reason { color: #667060; font-size: 13px; overflow-wrap: anywhere; }
.message-copy small { display: block; margin-top: 3px; }
.unread-dot { flex: 0 0 8px; width: 8px; height: 8px; margin-top: 11px; border-radius: 50%; background: var(--green); }
.message-chevron { flex: 0 0 18px; width: 18px; height: 18px; margin-top: 10px; color: #91a188; }
.message-error { color: #a74842; font-size: 13px; }
.message-more { max-width: 1000px; padding: 22px 0 38px; text-align: center; }
.filter-tabs span { margin-left: 3px; }
@media (max-width: 620px) { .message-copy { gap: 7px; } .message-chevron { display: none; } }
</style>
