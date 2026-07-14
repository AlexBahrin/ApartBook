<script setup>
import { onMounted } from 'vue'
import { useConfigStore } from '@/stores/config'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import NavBar from '@/components/NavBar.vue'
import AppFooter from '@/components/AppFooter.vue'
import ToastHost from '@/components/ToastHost.vue'

const config = useConfigStore()
const auth = useAuthStore()
const router = useRouter()

onMounted(async () => {
  config.fetchConfig()
  if (!auth.initialized) {
    await auth.fetchMe()
  }
  if (auth.isAuthenticated) {
    config.fetchUnread()
  }
  window.addEventListener('auth:logout', () => {
    auth.logout()
    router.push({ name: 'login' })
  })
})
</script>

<template>
  <div class="d-flex flex-column min-vh-100">
    <NavBar />
    <main class="flex-grow-1">
      <RouterView />
    </main>
    <AppFooter />
    <ToastHost />
  </div>
</template>
