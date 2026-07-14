<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api/client'

const route = useRoute()
const state = ref('loading') // loading | success | error

onMounted(async () => {
  try {
    await api.post('/auth/activate/', { uid: route.params.uid, token: route.params.token })
    state.value = 'success'
  } catch (e) {
    state.value = 'error'
  }
})
</script>

<template>
  <div class="container py-5">
    <div class="row justify-content-center">
      <div class="col-md-6 text-center">
        <div class="card shadow-sm">
          <div class="card-body p-5">
            <div v-if="state === 'loading'">
              <div class="spinner-border text-primary mb-3"></div>
              <p>{{ $t('auth.activating') }}</p>
            </div>
            <div v-else-if="state === 'success'">
              <i class="bi bi-check-circle-fill text-success" style="font-size: 3rem"></i>
              <h4 class="mt-3">{{ $t('auth.activationSuccess') }}</h4>
              <RouterLink :to="{ name: 'login' }" class="btn btn-primary mt-3">{{ $t('auth.signIn') }}</RouterLink>
            </div>
            <div v-else>
              <i class="bi bi-x-circle-fill text-danger" style="font-size: 3rem"></i>
              <h4 class="mt-3">{{ $t('auth.activationFailed') }}</h4>
              <RouterLink :to="{ name: 'register' }" class="btn btn-outline-primary mt-3">{{ $t('nav.register') }}</RouterLink>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
