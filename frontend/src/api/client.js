import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api',
  headers: { 'Content-Type': 'application/json' },
})

let accessToken = localStorage.getItem('access') || null
let refreshToken = localStorage.getItem('refresh') || null

export function setTokens(access, refresh) {
  accessToken = access || null
  refreshToken = refresh || null
  if (access) localStorage.setItem('access', access)
  else localStorage.removeItem('access')
  if (refresh) localStorage.setItem('refresh', refresh)
  else localStorage.removeItem('refresh')
}

export function getAccessToken() {
  return accessToken
}

api.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }
  return config
})

// Refresh-on-401 handling with a single-flight refresh promise.
let refreshing = null

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    const status = error.response?.status

    if (status === 401 && !original._retry && refreshToken && !original.url.includes('/auth/')) {
      original._retry = true
      try {
        if (!refreshing) {
          refreshing = axios
            .post(`${api.defaults.baseURL}/auth/refresh/`, { refresh: refreshToken })
            .finally(() => {
              // reset after settle
            })
        }
        const { data } = await refreshing
        refreshing = null
        setTokens(data.access, data.refresh || refreshToken)
        original.headers.Authorization = `Bearer ${data.access}`
        return api(original)
      } catch (e) {
        refreshing = null
        setTokens(null, null)
        window.dispatchEvent(new CustomEvent('auth:logout'))
        return Promise.reject(e)
      }
    }
    return Promise.reject(error)
  }
)

/** Extract a human-readable message from a DRF error response. */
export function extractError(error, fallback = 'Something went wrong.') {
  const data = error?.response?.data
  if (!data) return error?.message || fallback
  if (typeof data === 'string') return data
  if (data.detail) return data.detail
  const parts = []
  for (const [key, val] of Object.entries(data)) {
    if (Array.isArray(val)) parts.push(`${val.join(' ')}`)
    else if (typeof val === 'string') parts.push(val)
  }
  return parts.length ? parts.join(' ') : fallback
}

export default api
