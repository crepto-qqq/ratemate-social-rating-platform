<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from './AppIcon.vue'
import { apiBaseUrl, apiFetch } from '../api.js'
import { currentProfile, loadCurrentProfile, profileLoading, profileError } from '../currentProfile.js'

const route = useRoute()
const router = useRouter()
const query = ref('')
const profileName = computed(() => currentProfile.value?.userName || (profileLoading.value ? 'Loading…' : 'Profile unavailable'))
const profileInitial = computed(() => currentProfile.value?.userName?.trim().charAt(0).toUpperCase() || '?')
onMounted(loadCurrentProfile)

const section = computed(() => route.meta.section || 'Discover')
const navItems = [
  { to: '/home_page', icon: 'compass', label: 'Discover', section: 'Discover' },
  { to: '/create', icon: 'plus', label: 'Create a template', section: 'Create' },
  { to: '/rate', icon: 'star', label: 'Rate a template', section: 'Rate' },
  { to: '/messages', icon: 'bell', label: 'Messages', section: 'Messages' },
  { to: '/profile', icon: 'user', label: 'Personal space', section: 'Profile' },
]

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
        <RouterLink v-for="item in navItems" :key="item.to" :to="item.to" :aria-label="item.label" :title="item.label" class="nav-item" :class="{ active: section === item.section }">
          <AppIcon :name="item.icon" />
          <span>{{ item.label }}</span>
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
</style>
