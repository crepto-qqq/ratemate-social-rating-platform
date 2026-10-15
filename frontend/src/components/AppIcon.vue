<script setup>
defineProps({ name: { type: String, required: true } })
</script>

<template>
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <template v-if="name === 'compass'"><circle cx="12" cy="12" r="9"/><path d="m16 8-2.5 5.5L8 16l2.5-5.5Z"/></template>
    <template v-else-if="name === 'plus'"><rect x="3" y="3" width="18" height="18" rx="5"/><path d="M12 8v8M8 12h8"/></template>
    <template v-else-if="name === 'bell'"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/></template>
    <template v-else-if="name === 'user'"><circle cx="12" cy="8" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/></template>
    <template v-else-if="name === 'search'"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4 4"/></template>
    <template v-else-if="name === 'heart'"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z"/></template>
    <template v-else-if="name === 'layers'"><path d="m12 3 9 5-9 5-9-5Zm-9 9 9 5 9-5M3 16l9 5 9-5"/></template>
    <template v-else-if="name === 'bookmark'"><path d="M6 3h12v18l-6-4-6 4Z"/></template>
    <template v-else-if="name === 'back'"><path d="M19 12H5m5-5-5 5 5 5"/></template>
    <template v-else-if="name === 'sparkle'"><path d="m12 2 3 7 7 3-7 3-3 7-3-7-7-3 7-3Z"/></template>
    <template v-else-if="name === 'star'"><path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2-5.6-3-5.6 3 1.1-6.2L3 9.6l6.2-.9Z"/></template>
    <template v-else-if="name === 'shield'"><path d="M12 2 4 5v6c0 5.2 3.2 8.7 8 11 4.8-2.3 8-5.8 8-11V5l-8-3Z"/><path d="m9 12 2 2 4-4"/></template>
    <template v-else><path d="m9 7 5 5-5 5"/></template>
  </svg>
</template>
