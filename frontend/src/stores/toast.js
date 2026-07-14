import { defineStore } from 'pinia'

let counter = 0

export const useToastStore = defineStore('toast', {
  state: () => ({
    toasts: [],
  }),
  actions: {
    push(message, type = 'success', timeout = 4000) {
      const id = ++counter
      this.toasts.push({ id, message, type })
      if (timeout) {
        setTimeout(() => this.remove(id), timeout)
      }
    },
    success(message) {
      this.push(message, 'success')
    },
    error(message) {
      this.push(message, 'danger', 6000)
    },
    info(message) {
      this.push(message, 'info')
    },
    remove(id) {
      this.toasts = this.toasts.filter((t) => t.id !== id)
    },
  },
})
