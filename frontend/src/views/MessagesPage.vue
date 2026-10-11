<script setup>
import AppIcon from '../components/AppIcon.vue'
import AppLayout from '../components/AppLayout.vue'
</script>

<template>
  <AppLayout>
    <div class="messages-heading">
      <div><div class="eyebrow">RECENT ACTIVITY</div><h1>Messages</h1></div>
    </div>
    <section class="empty-results" aria-label="Messages">
      <AppIcon name="bell" />
      <h2>Messages are not available yet.</h2>
      <RouterLink class="action-button" to="/home_page">Back to Discover</RouterLink>
    </section>
  </AppLayout>
</template>
