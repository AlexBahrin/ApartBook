<script setup>
import { reactive, ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import { extractError } from '@/api/client'

const auth = useAuthStore()
const toast = useToastStore()
const saving = ref(false)

const form = reactive({
  first_name: '',
  last_name: '',
  email: '',
  phone_country_code: '+40',
  phone_number: '',
})

onMounted(() => {
  const u = auth.user
  if (u) {
    form.first_name = u.first_name
    form.last_name = u.last_name
    form.email = u.email
    form.phone_country_code = u.profile?.phone_country_code || '+40'
    form.phone_number = u.profile?.phone_number || ''
  }
})

async function save() {
  saving.value = true
  try {
    await auth.updateProfile({ ...form })
    toast.success('Saved successfully!')
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="container py-4">
    <div class="row justify-content-center">
      <div class="col-md-7">
        <h1 class="mb-4">{{ $t('nav.profile') }}</h1>
        <div class="card shadow-sm">
          <div class="card-body p-4">
            <form @submit.prevent="save">
              <div class="row">
                <div class="col-md-6 mb-3">
                  <label class="form-label">{{ $t('auth.firstName') }}</label>
                  <input type="text" class="form-control" v-model="form.first_name" />
                </div>
                <div class="col-md-6 mb-3">
                  <label class="form-label">{{ $t('auth.lastName') }}</label>
                  <input type="text" class="form-control" v-model="form.last_name" />
                </div>
              </div>
              <div class="mb-3">
                <label class="form-label">{{ $t('auth.email') }}</label>
                <input type="email" class="form-control" v-model="form.email" />
              </div>
              <div class="mb-3">
                <label class="form-label">{{ $t('auth.phone') }}</label>
                <div class="input-group">
                  <input type="text" class="form-control" style="max-width: 120px" v-model="form.phone_country_code" />
                  <input type="text" class="form-control" v-model="form.phone_number" />
                </div>
              </div>
              <button type="submit" class="btn btn-primary" :disabled="saving">
                <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>
                {{ $t('common.save') }}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
