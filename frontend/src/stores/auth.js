import { defineStore } from 'pinia'
import api, { setTokens, getAccessToken } from '@/api/client'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    initialized: false,
  }),
  getters: {
    isAuthenticated: (state) => !!state.user,
    isStaff: (state) => !!state.user?.is_staff,
  },
  actions: {
    async login(username, password) {
      const { data } = await api.post('/auth/login/', { username, password })
      setTokens(data.access, data.refresh)
      this.user = data.user
      return data.user
    },

    async register(payload) {
      const { data } = await api.post('/auth/register/', payload)
      return data
    },

    async fetchMe() {
      if (!getAccessToken()) {
        this.initialized = true
        return null
      }
      try {
        const { data } = await api.get('/auth/me/')
        this.user = data
      } catch (e) {
        this.user = null
        setTokens(null, null)
      } finally {
        this.initialized = true
      }
      return this.user
    },

    async updateProfile(payload) {
      const { data } = await api.patch('/auth/me/', payload)
      this.user = data
      return data
    },

    logout() {
      this.user = null
      setTokens(null, null)
    },
  },
})
