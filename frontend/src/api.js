// Use the Vite same-origin proxy by default, in Docker and local development.
export const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? ''

export async function apiFetch(url, options = {}) {
  const headers = new Headers(options.headers)
  const method = (options.method ?? 'GET').toUpperCase()
  if (!['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(method)) {
    // Fetch a fresh token so login token rotation and expired cookies are handled.
    const tokenResponse = await fetch(`${apiBaseUrl}/api/auth/csrf/`, {
      credentials: 'include',
      cache: 'no-store',
    })
    if (!tokenResponse.ok) throw new Error('Unable to get a security token. Refresh the page and try again.')
    const { csrfToken } = await tokenResponse.json()
    if (!csrfToken) throw new Error('The server did not return a security token.')
    headers.set('X-CSRFToken', csrfToken)
  }
  return fetch(url, { ...options, headers, credentials: 'include' })
}
