<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import AppLayout from '../components/AppLayout.vue'
import { photoUrl, templateDetail } from '../data/demo.js'

const route = useRoute()
const router = useRouter()
const liked = ref(false)
const saved = ref(false)
const comment = ref('')
const comments = ref([
  { author: 'Sam Taylor', initials: 'ST', text: 'I like how clear the criteria are. This gives me a useful starting point for my own ratings.' },
  { author: 'Riley Chen', initials: 'RC', text: 'The weighted scores make the final ranking much easier to understand.' },
])
const data = computed(() => templateDetail(Number(route.params.id)))
const ranked = computed(() => [...(data.value?.items || [])].sort((a, b) => b.score - a.score))
const totalWeight = computed(() => data.value?.criteria.reduce((sum, item) => sum + Math.abs(item.weight), 0) || 1)

function postComment() {
  const text = comment.value.trim()
  if (!text) return
  comments.value.unshift({ author: 'jamie_parker', initials: 'J', text })
  comment.value = ''
}
</script>

<template>
  <AppLayout>
    <div v-if="data">
      <button class="text-button back-button" @click="router.back()"><AppIcon name="back" />Back to Discover</button>
      <div class="detail-hero">
        <div class="detail-cover"><img :src="photoUrl(data.template[1], 1000)" :alt="data.template[0]"></div>
        <div class="detail-intro">
          <span class="detail-category">{{ data.template[2] }}</span><h1>{{ data.template[0] }}</h1>
          <div class="detail-author"><span class="avatar">{{ data.template[3].split(' ').map(word => word[0]).join('') }}</span><div><strong>{{ data.template[3] }}</strong><small>Public template · {{ data.items.length }} items</small></div></div>
          <p>{{ data.description }}</p>
          <div class="detail-actions">
            <button class="action-button" :aria-pressed="liked" @click="liked = !liked"><AppIcon name="heart" />{{ liked ? 'Liked' : 'Like' }} · {{ data.template[4] + Number(liked) }}</button>
            <button class="action-button primary" :aria-pressed="saved" @click="saved = !saved"><AppIcon name="bookmark" />{{ saved ? 'Saved to favorites' : 'Save to favorites' }}</button>
          </div>
        </div>
      </div>
      <div class="detail-body">
        <div class="detail-main">
          <section class="detail-section"><div class="section-heading"><h2>Rating criteria</h2><span>{{ data.criteria.length }} criteria · 1–5 stars each</span></div><div class="criteria-list">
            <div v-for="criterion in data.criteria" :key="criterion.name" class="criterion"><strong>{{ criterion.name }}</strong><span>Weight {{ criterion.weight }}</span><div class="weight-track"><div :style="{ width: `${Math.abs(criterion.weight) / totalWeight * 100}%` }" /></div><small>{{ Math.round(Math.abs(criterion.weight) / totalWeight * 100) }}% of total weight</small></div>
          </div></section>
          <section class="detail-section"><div class="section-heading"><h2>Items & author’s ratings</h2><span>{{ data.items.length }} items</span></div><p class="section-description">Overall scores use the weighted 1–5 star ratings, scaled to 100.</p><div class="table-scroll"><table><thead><tr><th>Item</th><th v-for="criterion in data.criteria" :key="criterion.name">{{ criterion.name }}</th><th>Score</th></tr></thead><tbody><tr v-for="item in data.items" :key="item.name"><th>{{ item.name }}</th><td v-for="(rating, index) in item.ratings" :key="index"><span class="rating-star">★</span> {{ rating }}</td><td><strong>{{ item.score.toFixed(1) }}</strong></td></tr></tbody></table></div></section>
          <section class="detail-section comments-section"><h2>Comments ({{ comments.length }})</h2><form @submit.prevent="postComment"><label for="comment-text">Join the conversation</label><textarea id="comment-text" v-model="comment" maxlength="1000" rows="3" placeholder="What do you think of this template?" /><div class="comment-form-bottom"><span>{{ comment.length }} / 1000</span><button class="action-button primary" :disabled="!comment.trim()">Post comment</button></div></form><article v-for="item in comments" :key="item.text" class="comment"><span class="avatar">{{ item.initials }}</span><div><strong>{{ item.author }}</strong><small>Community member</small><p>{{ item.text }}</p></div></article></section>
        </div>
        <aside class="ranking-panel"><div class="section-heading"><h2>Author’s ranking</h2></div><p>Highest score first</p><ol><li v-for="(item, index) in ranked" :key="item.name"><span class="rank-number">{{ index + 1 }}</span><span>{{ item.name }}</span><strong>{{ item.score.toFixed(1) }}</strong></li></ol><div class="reuse-note">Save this template to your favorites to use it later. Your own version will keep its criteria and items, with all ratings cleared.</div></aside>
      </div>
    </div>
    <div v-else class="empty-results"><h2>Template not found</h2><RouterLink class="action-button" to="/home_page">Back to Discover</RouterLink></div>
  </AppLayout>
</template>
