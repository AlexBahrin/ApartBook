<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import api, { extractError } from '@/api/client'
import { useConfigStore } from '@/stores/config'
import { useToastStore } from '@/stores/toast'

const route = useRoute()
const router = useRouter()
const config = useConfigStore()
const toast = useToastStore()
const { t } = useI18n()

const booking = ref(null)
const loading = ref(true)
const acting = ref(false)

const CANCELLABLE_STATUSES = ['PENDING', 'CONFIRMED']

function canCancel(status) {
  return CANCELLABLE_STATUSES.includes(status)
}

async function load() {
  loading.value = true
  try {
    const { data } = await api.get(`/my/bookings/${route.params.id}/`)
    booking.value = data
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    loading.value = false
  }
}

async function cancel() {
  if (!confirm(t('dashboard.cancelConfirm'))) return
  acting.value = true
  try {
    const { data } = await api.post(`/my/bookings/${route.params.id}/cancel/`)
    booking.value = data
    toast.success(t('dashboard.cancelled'))
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    acting.value = false
  }
}

async function contactOwner() {
  try {
    const { data } = await api.post(`/my/conversations/start/${booking.value.id}/`)
    router.push({ name: 'my-conversation', params: { id: data.id } })
  } catch (e) {
    toast.error(extractError(e))
  }
}

onMounted(load)
</script>

<template>
  <div class="container py-4">
    <RouterLink :to="{ name: 'my-bookings' }" class="btn btn-link ps-0 mb-2"><i class="bi bi-arrow-left"></i> {{ $t('common.back') }}</RouterLink>

    <div v-if="loading" class="text-center py-5"><div class="spinner-border text-primary"></div></div>

    <div v-else-if="booking" class="row g-4">
      <div class="col-lg-8">
        <div class="card shadow-sm">
          <div class="card-body">
            <h3>{{ booking.apartment.title }}</h3>
            <span class="badge bg-secondary mb-3">{{ $t('status.' + booking.status) }}</span>
            <table class="table">
              <tbody>
                <tr><th>{{ $t('dashboard.checkIn') }}</th><td>{{ booking.check_in }}</td></tr>
                <tr><th>{{ $t('dashboard.checkOut') }}</th><td>{{ booking.check_out }}</td></tr>
                <tr><th>{{ $t('dashboard.nights') }}</th><td>{{ booking.nights }}</td></tr>
                <tr><th>{{ $t('dashboard.guests') }}</th><td>{{ booking.guests_count }}</td></tr>
                <tr><th>{{ $t('dashboard.total') }}</th><td class="fw-bold text-primary">{{ booking.total_price }} {{ config.currencySymbol }}</td></tr>
                <tr v-if="booking.notes"><th>{{ $t('booking.notes') }}</th><td>{{ booking.notes }}</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
      <div class="col-lg-4">
        <div class="card shadow-sm">
          <div class="card-body d-grid gap-2">
            <button class="btn btn-outline-primary" @click="contactOwner">
              <i class="bi bi-chat-dots"></i> {{ $t('dashboard.contactOwner') }}
            </button>
            <button v-if="canCancel(booking.status)" class="btn btn-outline-danger" :disabled="acting" @click="cancel">
              <i class="bi bi-x-circle"></i> {{ $t('dashboard.cancelBooking') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
