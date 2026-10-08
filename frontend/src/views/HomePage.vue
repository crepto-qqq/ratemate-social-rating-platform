<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import AppLayout from '../components/AppLayout.vue'
import { photoUrl, templates } from '../data/demo.js'

const route = useRoute()
const router = useRouter()
const failedImages = ref(new Set())
const query = computed(() => String(route.query.q || '').trim())
const results = computed(() => query.value
  ? templates.map((template, id) => ({ template, id })).filter(({ template }) => template.slice(0, 4).join(' ').toLowerCase().includes(query.value.toLowerCase()))
  : templates.map((template, id) => ({ template, id })))

function imageFailed(id) {
  failedImages.value = new Set([...failedImages.value, id])
}
</script>

<template>
  <AppLayout>
    <div v-if="!query" class="heading">
      <div><div class="eyebrow">A LITTLE CURIOSITY GOES A LONG WAY</div><h1>Find your next great rating.</h1><p>Explore perspectives. Find a template. Make it your own.</p></div>
      <span class="community-mark"><AppIcon name="sparkle" /> Made by the community</span>
    </div>
    <div v-if="!query" class="feed-heading"><h2>For you <span>Handpicked perspectives</span></h2><span class="feed-count">12 templates to explore</span></div>
    <div v-else class="search-summary">
      <p>Search results for “{{ query }}” · {{ results.length }} results</p>
      <button class="text-button" @click="router.push('/home_page')">Clear search</button>
    </div>
    <section v-if="results.length" class="masonry" aria-label="Recommended rating templates">
      <article v-for="({ template, id }) in results" :key="id" class="card">
        <RouterLink class="cover" :class="{ fallback: failedImages.has(id) }" :style="{ aspectRatio: `1/${template[6]}` }" :to="`/templates/${id}`">
          <img v-if="!failedImages.has(id)" :src="photoUrl(template[1], 700)" :alt="`${template[2]} inspiration for ${template[0]}`" @error="imageFailed(id)">
          <span v-else>{{ template[0] }}</span>
          <span class="category">{{ template[2] }}</span>
          <span class="item-count"><AppIcon name="layers" />{{ template[5] }} items to rate</span>
        </RouterLink>
        <RouterLink class="card-title" :to="`/templates/${id}`">{{ template[0] }}</RouterLink>
        <div class="card-meta"><span class="mini-avatar">{{ template[3].split(' ').map(word => word[0]).join('') }}</span><span>{{ template[3] }}</span><span class="likes"><AppIcon name="heart" />{{ template[4] }}</span></div>
      </article>
    </section>
    <div v-else class="empty-results"><AppIcon name="search" /><h2>No relevant results found</h2><p>There are no matching templates to show.</p><button class="action-button" @click="router.push('/home_page')">Back to Discover</button></div>
    <footer v-if="!query">You've seen this week's picks.<span>Something worth rating is always around the corner.</span></footer>
  </AppLayout>
</template>
