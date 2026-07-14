<script setup>
import { ref } from 'vue'
import api, { extractError } from '@/api/client'
import { useToastStore } from '@/stores/toast'

const toast = useToastStore()
const email = ref('')
const loading = ref(false)
const sent = ref(false)

async function submit() {
  loading.value = true
  try {
    await api.post('/auth/password-reset/', { email: email.value })
    sent.value = true
  } catch (e) {
    toast.error(extractError(e))
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
            <h3 class="text-center mb-3">{{ $t('auth.resetTitle') }}</h3>
            <div v-if="sent" class="alert alert-success">{{ $t('auth.resetSent') }}</div>
            <template v-else>
              <p class="text-muted">{{ $t('auth.resetIntro') }}</p>
              <form @submit.prevent="submit">
                <div class="mb-3">
                  <label class="form-label">{{ $t('auth.email') }}</label>
                  <input type="email" class="form-control" v-model="email" required />
                </div>
                <button type="submit" class="btn btn-primary w-100" :disabled="loading">
                  <span v-if="loading" class="spinner-border spinner-border-sm me-1"></span>
                  {{ $t('auth.resetButton') }}
                </button>
              </form>
            </template>
            <div class="text-center mt-3">
              <RouterLink :to="{ name: 'login' }" class="small">{{ $t('auth.signIn') }}</RouterLink>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
