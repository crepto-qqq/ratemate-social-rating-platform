<script setup>
import { computed, ref } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import AppLayout from '../components/AppLayout.vue'
import { notifications } from '../data/demo.js'

const filter = ref('all')
const unreadOnly = ref(false)
const readIds = ref(new Set([5]))
const visible = computed(() => notifications.filter(item => (filter.value === 'all' || item.type === filter.value) && (!unreadOnly.value || !readIds.value.has(item.id))))
function markRead(id) { readIds.value = new Set([...readIds.value, id]) }
function markAllRead() { readIds.value = new Set(notifications.map(item => item.id)) }
</script>

<template>
  <AppLayout>
    <div class="messages-heading"><div><div class="eyebrow">RECENT ACTIVITY</div><h1>Messages</h1><p>See how the community is responding to your public templates.</p></div><button class="text-button" @click="markAllRead">Mark all as read</button></div>
    <div class="message-toolbar"><div class="filter-tabs"><button v-for="item in [['all','All'],['like','Likes'],['comment','Comments']]" :key="item[0]" :class="{ active: filter === item[0] }" @click="filter = item[0]">{{ item[1] }}</button></div><label class="toggle-label"><input v-model="unreadOnly" type="checkbox">Unread only</label></div>
    <section class="message-list">
      <article v-for="message in visible" :key="message.id" class="message-item" :class="{ unread: !readIds.has(message.id) }">
        <span class="message-icon"><AppIcon :name="message.type === 'like' ? 'heart' : 'bell'" /></span>
        <div class="message-copy"><div><strong>{{ message.actor }}</strong> {{ message.type === 'like' ? 'liked' : 'commented on' }} <b>{{ message.template }}</b></div><p v-if="message.text">“{{ message.text }}”</p><small>{{ message.date }}</small></div>
        <button v-if="!readIds.has(message.id)" class="text-button" @click="markRead(message.id)">Mark read</button>
      </article>
      <div v-if="!visible.length" class="inline-empty">No messages match this filter.</div>
    </section>
  </AppLayout>
</template>
