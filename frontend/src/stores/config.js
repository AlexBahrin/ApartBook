import { defineStore } from 'pinia'
import api from '@/api/client'

export const useConfigStore = defineStore('config', {
  state: () => ({
    currencies: {},
    defaultCurrency: 'RON',
    currency: localStorage.getItem('currency') || 'RON',
    languages: [],
    unreadMessages: 0,
  }),
  getters: {
    currencySymbol: (state) => state.currencies[state.currency]?.symbol || '',
  },
  actions: {
    async fetchConfig() {
      const { data } = await api.get('/config/')
      this.currencies = data.currencies
      this.defaultCurrency = data.default_currency
      this.languages = data.languages
      if (!this.currencies[this.currency]) {
        this.currency = data.default_currency
      }
    },
    setCurrency(code) {
      this.currency = code
      localStorage.setItem('currency', code)
    },
    async fetchUnread() {
      try {
        const { data } = await api.get('/unread-counts/')
        this.unreadMessages = data.unread_messages
      } catch (e) {
        this.unreadMessages = 0
      }
    },
  },
})
