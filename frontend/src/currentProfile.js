import { ref } from 'vue'
import { apiBaseUrl, apiFetch } from './api.js'

export const currentProfile = ref(null)
export const profileLoading = ref(false)
export const profileError = ref('')
let pendingRequest

export function loadCurrentProfile() {
  if (pendingRequest) return pendingRequest
  profileLoading.value = true
  profileError.value = ''
  pendingRequest = (async () => {
    try {
      const response = await apiFetch(`${apiBaseUrl}/api/auth/profile/`)
      if (!response.ok) throw new Error('Unable to load your profile')
      currentProfile.value = await response.json()
    } catch (error) {
      currentProfile.value = null
      profileError.value = error.message
    } finally {
      profileLoading.value = false
      pendingRequest = null
    }
  })()
  return pendingRequest
}
