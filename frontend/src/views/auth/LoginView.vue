<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useConfigStore } from '@/stores/config'
import { useToastStore } from '@/stores/toast'
import { extractError } from '@/api/client'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const config = useConfigStore()
const toast = useToastStore()

const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

async function submit() {
  loading.value = true
  error.value = ''
  try {
    const user = await auth.login(username.value, password.value)
    config.fetchUnread()
    const next = route.query.next
    if (next) router.push(next)
    else router.push({ name: user.is_staff ? 'staff-bookings' : 'landing' })
  } catch (e) {
    error.value = extractError(e, 'Invalid username or password.')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="container py-5">
    <div class="row justify-content-center">
      <div class="col-md-5">
        <div class="card shadow-sm">
          <div class="card-body p-4">
            <h3 class="text-center mb-4">{{ $t('auth.loginTitle') }}</h3>
            <div v-if="error" class="alert alert-danger">{{ error }}</div>
            <form @submit.prevent="submit">
              <div class="mb-3">
                <label class="form-label">{{ $t('auth.username') }}</label>
                <input type="text" class="form-control" v-model="username" required autofocus />
              </div>
              <div class="mb-3">
                <label class="form-label">{{ $t('auth.password') }}</label>
                <input type="password" class="form-control" v-model="password" required />
              </div>
              <button type="submit" class="btn btn-primary w-100" :disabled="loading">
                <span v-if="loading" class="spinner-border spinner-border-sm me-1"></span>
                {{ $t('auth.loginButton') }}
              </button>
            </form>
            <div class="text-center mt-3">
              <RouterLink :to="{ name: 'password-reset' }" class="small">{{ $t('auth.forgotPassword') }}</RouterLink>
            </div>
            <hr />
            <p class="text-center mb-0">
              {{ $t('auth.noAccount') }}
              <RouterLink :to="{ name: 'register' }">{{ $t('auth.signUp') }}</RouterLink>
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
