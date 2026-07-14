<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import { extractError } from '@/api/client'

const router = useRouter()
const auth = useAuthStore()
const toast = useToastStore()

const countryCodes = ['+40', '+373', '+380', '+1', '+44', '+49', '+33', '+34', '+39', '+7']

const form = reactive({
  first_name: '',
  last_name: '',
  username: '',
  email: '',
  phone_country_code: '+40',
  phone_number: '',
  password1: '',
  password2: '',
})
const loading = ref(false)
const errors = ref({})

async function submit() {
  loading.value = true
  errors.value = {}
  try {
    await auth.register({ ...form })
    toast.success('Account created! Check your email to activate your account.')
    router.push({ name: 'login' })
  } catch (e) {
    errors.value = e.response?.data || {}
    toast.error(extractError(e))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="container py-5">
    <div class="row justify-content-center">
      <div class="col-md-7">
        <div class="card shadow-sm">
          <div class="card-body p-4">
            <h3 class="text-center mb-4">{{ $t('auth.registerTitle') }}</h3>
            <form @submit.prevent="submit">
              <div class="row">
                <div class="col-md-6 mb-3">
                  <label class="form-label">{{ $t('auth.firstName') }}</label>
                  <input type="text" class="form-control" v-model="form.first_name" required />
                </div>
                <div class="col-md-6 mb-3">
                  <label class="form-label">{{ $t('auth.lastName') }}</label>
                  <input type="text" class="form-control" v-model="form.last_name" required />
                </div>
              </div>
              <div class="mb-3">
                <label class="form-label">{{ $t('auth.username') }}</label>
                <input type="text" class="form-control" :class="{ 'is-invalid': errors.username }" v-model="form.username" required />
                <div class="invalid-feedback">{{ errors.username?.[0] }}</div>
              </div>
              <div class="mb-3">
                <label class="form-label">{{ $t('auth.email') }}</label>
                <input type="email" class="form-control" :class="{ 'is-invalid': errors.email }" v-model="form.email" required />
                <div class="invalid-feedback">{{ errors.email?.[0] }}</div>
              </div>
              <div class="mb-3">
                <label class="form-label">{{ $t('auth.phone') }}</label>
                <div class="input-group">
                  <select class="form-select" style="max-width: 120px" v-model="form.phone_country_code">
                    <option v-for="c in countryCodes" :key="c" :value="c">{{ c }}</option>
                  </select>
                  <input type="text" class="form-control" v-model="form.phone_number" placeholder="712 345 678" />
                </div>
              </div>
              <div class="row">
                <div class="col-md-6 mb-3">
                  <label class="form-label">{{ $t('auth.password') }}</label>
                  <input type="password" class="form-control" :class="{ 'is-invalid': errors.password1 }" v-model="form.password1" required />
                  <div class="invalid-feedback">{{ errors.password1?.[0] }}</div>
                </div>
                <div class="col-md-6 mb-3">
                  <label class="form-label">{{ $t('auth.confirmPassword') }}</label>
                  <input type="password" class="form-control" :class="{ 'is-invalid': errors.password2 }" v-model="form.password2" required />
                  <div class="invalid-feedback">{{ errors.password2?.[0] }}</div>
                </div>
              </div>
              <button type="submit" class="btn btn-primary w-100" :disabled="loading">
                <span v-if="loading" class="spinner-border spinner-border-sm me-1"></span>
                {{ $t('auth.registerButton') }}
              </button>
            </form>
            <hr />
            <p class="text-center mb-0">
              {{ $t('auth.haveAccount') }}
              <RouterLink :to="{ name: 'login' }">{{ $t('auth.signIn') }}</RouterLink>
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
