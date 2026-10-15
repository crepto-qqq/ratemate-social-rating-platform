<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from './AppIcon.vue'
import { apiBaseUrl, apiFetch } from '../api.js'
import { currentProfile, loadCurrentProfile, profileLoading, profileError } from '../currentProfile.js'
import { apiBaseUrl, apiFetch } from '../api.js'

const route = useRoute()
const router = useRouter()
const query = ref('')
const profileName = computed(() => currentProfile.value?.userName || (profileLoading.value ? 'Loading…' : 'Profile unavailable'))
const profileInitial = computed(() => currentProfile.value?.userName?.trim().charAt(0).toUpperCase() || '?')
const unreadCount = ref(0)
let unreadTimer

async function refreshUnreadCount() {
  try {
    const response = await apiFetch(`${apiBaseUrl}/api/notifications/unread-count/`)
    if (!response.ok) {
      unreadCount.value = 0
      return
    }
    const data = await response.json()
    unreadCount.value = Number(data.unreadCount) || 0
  } catch {
    unreadCount.value = 0
  }
}

onMounted(() => {
  loadCurrentProfile()
  refreshUnreadCount()
  window.addEventListener('notifications:updated', refreshUnreadCount)
  unreadTimer = window.setInterval(refreshUnreadCount, 30000)
})
onUnmounted(() => {
  window.removeEventListener('notifications:updated', refreshUnreadCount)
  window.clearInterval(unreadTimer)
})

const section = computed(() => route.meta.section || 'Discover')
const navItems = computed(() => {
  const items = [
    { to: '/home_page', icon: 'compass', label: 'Discover', section: 'Discover' },
    { to: '/create', icon: 'plus', label: 'Create a template', section: 'Create' },
    { to: '/rate', icon: 'star', label: 'Rate a template', section: 'Rate' },
    { to: '/messages', icon: 'bell', label: 'Messages', section: 'Messages' },
  ]
  if (currentProfile.value?.isAdmin) items.push({ to: '/admin', icon: 'shield', label: 'Admin', section: 'Admin' })
  items.push({ to: '/profile', icon: 'user', label: 'Personal space', section: 'Profile' })
  return items
})

function search() {
  const value = query.value.trim()
  if (value) router.push({ path: '/home_page', query: { q: value } })
}

async function signOut() {
  try {
    const response = await apiFetch(`${apiBaseUrl}/api/auth/logout/`, { method: 'POST' })
    if (!response.ok) throw new Error('Could not sign out.')
    currentProfile.value = null
    await router.push('/login')
  } catch (error) {
    profileError.value = error.message || 'Could not sign out.'
  }
}
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <RouterLink class="brand" to="/home_page" aria-label="Ratemate home">
        <span class="brand-icon">r<span>·</span></span>ratemate<span class="brand-dot">.</span>
      </RouterLink>
      <nav aria-label="Main navigation">
        <RouterLink v-for="item in navItems" :key="item.to" :to="item.to" :aria-label="item.section === 'Messages' && unreadCount ? `${item.label}, ${unreadCount} unread` : item.label" :title="item.label" class="nav-item" :class="{ active: section === item.section }">
          <AppIcon :name="item.icon" />
          <span>{{ item.label }}</span>
          <b v-if="item.section === 'Messages' && unreadCount" class="nav-unread">{{ unreadCount > 99 ? '99+' : unreadCount }}</b>
        </RouterLink>
      </nav>
      <div class="sidebar-bottom">
        <button class="sign-out" type="button" @click="signOut">Sign out</button>
        <RouterLink class="profile" to="/profile">
          <span class="avatar"><img v-if="currentProfile?.avatarUrl" :src="currentProfile.avatarUrl" alt="Your avatar"><template v-else>{{ profileInitial }}</template></span>
          <div><strong>{{ profileName }}</strong><small>{{ profileError || 'Your personal space' }}</small></div>
          <AppIcon name="chevron" />
        </RouterLink>
      </div>
    </aside>
    <div class="workspace">
      <header class="topbar">
        <span class="breadcrumb">Community <span>/</span> <strong>{{ route.meta.title || section }}</strong></span>
        <form class="search" role="search" @submit.prevent="search">
          <AppIcon name="search" />
          <input v-model="query" aria-label="Search templates" placeholder="Search templates and authors" maxlength="200">
          <button type="submit" aria-label="Search"><AppIcon name="search" /></button>
        </form>
        <RouterLink class="avatar top-avatar" to="/profile" aria-label="Open personal space"><img v-if="currentProfile?.avatarUrl" :src="currentProfile.avatarUrl" alt="Your avatar"><template v-else>{{ profileInitial }}</template></RouterLink>
      </header>
      <main><slot /></main>
    </div>
  </div>
</template>

<style scoped>
.sign-out { border: 0; background: transparent; color: #697265; cursor: pointer; padding: 12px; text-align: left; width: 100%; }
.avatar { overflow: hidden; }
.avatar img { width: 100%; height: 100%; object-fit: cover; }
.nav-item { position: relative; }
.nav-unread { display: inline-flex; align-items: center; justify-content: center; min-width: 22px; height: 22px; margin-left: auto; padding: 0 5px; border-radius: 11px; background: #be493e; color: white; font-size: 11px; line-height: 1; }
@media (max-width: 620px) { .nav-unread { position: absolute; top: 3px; right: 3px; min-width: 17px; height: 17px; padding: 0 3px; font-size: 9px; } }
</style>
