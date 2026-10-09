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
    if (!tokenResponse.ok) throw new Error('无法获取 CSRF token，请刷新页面后重试。')
    const { csrfToken } = await tokenResponse.json()
    if (!csrfToken) throw new Error('服务器没有返回 CSRF token。')
    headers.set('X-CSRFToken', csrfToken)
  }
  return fetch(url, { ...options, headers, credentials: 'include' })
}