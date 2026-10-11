<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import AppLayout from '../components/AppLayout.vue'
import { apiBaseUrl, apiFetch } from '../api.js'
const route = useRoute()
const templates = ref([])
const loading = ref(true)
const error = ref('')
const failedImages = ref(new Set())
const query = computed(() => String(route.query.q || '').trim())
const results = computed(() => templates.value.filter(t => [t.title, t.description, t.author.name].join(' ').toLowerCase().includes(query.value.toLowerCase())))
async function loadTemplates() {
  loading.value = true
  error.value = ''
  try {
    const response = await apiFetch(apiBaseUrl + '/api/templates/')
    if (!response.ok) throw new Error('Unable to load templates.')
    templates.value = (await response.json()).templates
  } catch (e) { error.value = e.message }
  finally { loading.value = false }
}
function imageFailed(id) { failedImages.value = new Set([...failedImages.value, id]) }
onMounted(loadTemplates)
</script>
<template>
  <AppLayout>
    <div class="heading"><div><div class="eyebrow">MADE BY THE COMMUNITY</div><h1>Find your next great rating.</h1><p>Explore perspectives. Find a template. Make it your own.</p></div></div>
    <div class="feed-heading"><h2>{{ query ? 'Search results for “' + query + '”' : 'Discover' }}</h2><span v-if="!loading && !error" class="feed-count">{{ results.length }} templates</span><RouterLink v-if="query" class="text-button" to="/home_page">Clear search</RouterLink></div>
    <div v-if="loading" class="empty-results" role="status">Loading templates…</div>
    <div v-else-if="error" class="empty-results" role="alert"><p>{{ error }}</p><button class="action-button" @click="loadTemplates">Try again</button></div>
    <section v-else-if="results.length" class="masonry" aria-label="Community templates">
      <article v-for="t in results" :key="t.id" class="card">
        <RouterLink class="cover" :class="{ fallback: !t.items[0]?.imageUrl || failedImages.has(t.id) }" style="aspect-ratio: 1/1.1" :to="'/templates/' + t.id">
          <img v-if="t.items[0]?.imageUrl && !failedImages.has(t.id)" :src="t.items[0].imageUrl" :alt="t.title" @error="imageFailed(t.id)"><span v-else>{{ t.title }}</span>
          <span class="item-count"><AppIcon name="layers" />{{ t.items.length }} items to rate</span>
        </RouterLink>
        <RouterLink class="card-title" :to="'/templates/' + t.id">{{ t.title }}</RouterLink>
        <div class="card-meta"><span class="mini-avatar"><img v-if="t.author.avatarUrl" :src="t.author.avatarUrl" alt="Author avatar"><template v-else>{{ t.author.name.charAt(0).toUpperCase() || '?' }}</template></span><span>{{ t.author.name }}</span><span class="likes" title="Favorites"><AppIcon name="bookmark" />{{ t.popularity }}</span></div>
      </article>
    </section>
    <div v-else class="empty-results"><h2>{{ query ? 'No matching templates' : 'No templates yet' }}</h2><p>{{ query ? 'Try another search.' : 'Create the first template to start exploring.' }}</p><RouterLink class="action-button" :to="query ? '/home_page' : '/create'">{{ query ? 'Back to Discover' : 'Create a template' }}</RouterLink></div>
  </AppLayout>
</template>
<style scoped>
.mini-avatar { overflow: hidden; }
.mini-avatar img { width: 100%; height: 100%; object-fit: cover; }
</style>
