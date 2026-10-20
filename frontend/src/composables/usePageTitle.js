import { toValue, watch } from 'vue'
import { useRoute } from 'vue-router'

// Route changes provide the fallback; loaded page data can supply a specific name.
export function usePageTitle(title) {
  const route = useRoute()
  watch(
    [() => toValue(title), () => route.fullPath],
    ([value]) => {
      document.title = value?.trim() || route.meta.title || 'Ratemate'
    },
    { immediate: true, flush: 'post' },
  )
}
