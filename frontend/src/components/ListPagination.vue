<script setup>
defineProps({
  page: { type: Number, required: true },
  totalPages: { type: Number, default: 0 },
  hasMore: { type: Boolean, default: false },
  label: { type: String, default: 'List' },
})
const emit = defineEmits(['change'])
</script>

<template>
  <nav v-if="totalPages > 1 || page > 1 || hasMore" class="list-pagination" :aria-label="`${label} pages`">
    <button class="action-button" type="button" :disabled="page <= 1" @click="emit('change', page - 1)">Previous</button>
    <label v-if="totalPages">Page <select :value="page" :aria-label="`${label} page`" @change="emit('change', Number($event.target.value))"><option v-for="number in totalPages" :key="number" :value="number">{{ number }}</option></select> of {{ totalPages }}</label>
    <span v-else>Page {{ page }}</span>
    <button class="action-button" type="button" :disabled="totalPages ? page >= totalPages : !hasMore" @click="emit('change', page + 1)">Next</button>
  </nav>
</template>

<style scoped>
.list-pagination { display: flex; align-items: center; justify-content: center; flex-wrap: wrap; gap: 16px; padding: 24px 0; color: #697662; font-size: 13px; }
.list-pagination label { display: flex; align-items: center; gap: 6px; }
.list-pagination select { padding: 6px 8px; border: 1px solid #d8e2cf; border-radius: 6px; background: white; color: #273326; }
.list-pagination button:disabled { opacity: .45; cursor: default; }
@media (max-width: 620px) { .list-pagination { gap: 9px; } }
</style>
