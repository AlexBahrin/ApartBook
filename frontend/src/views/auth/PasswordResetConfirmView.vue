<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api, { extractError } from '@/api/client'
import { useToastStore } from '@/stores/toast'

const route = useRoute()
const router = useRouter()
const toast = useToastStore()

const password1 = ref('')
const password2 = ref('')
const loading = ref(false)

async function submit() {
  loading.value = true
  try {
    await api.post('/auth/password-reset/confirm/', {
      uid: route.params.uid,
      token: route.params.token,
      new_password1: password1.value,
      new_password2: password2.value,
    })
    toast.success('Your password has been reset. You can now log in.')
    router.push({ name: 'login' })
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
            <h3 class="text-center mb-3">{{ $t('auth.setNewPassword') }}</h3>
            <form @submit.prevent="submit">
              <div class="mb-3">
                <label class="form-label">{{ $t('auth.newPassword') }}</label>
                <input type="password" class="form-control" v-model="password1" required />
              </div>
              <div class="mb-3">
                <label class="form-label">{{ $t('auth.confirmPassword') }}</label>
                <input type="password" class="form-control" v-model="password2" required />
              </div>
              <button type="submit" class="btn btn-primary w-100" :disabled="loading">
                <span v-if="loading" class="spinner-border spinner-border-sm me-1"></span>
                {{ $t('common.save') }}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
