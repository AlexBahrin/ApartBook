<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api, { extractError } from '@/api/client'
import { useConfigStore } from '@/stores/config'
import { useToastStore } from '@/stores/toast'

const route = useRoute()
const config = useConfigStore()
const toast = useToastStore()

const booking = ref(null)
const loading = ref(true)
const acting = ref(false)
const edit = reactive({ check_in: '', check_out: '', guests_count: 1 })

function guestName(user) {
  const name = `${user.last_name || ''} ${user.first_name || ''}`.trim()
  return name || user.username
}

function guestPhone(user) {
  const p = user.profile
  if (!p || !p.phone_number) return '—'
  return `${p.phone_country_code || ''} ${p.phone_number}`.trim()
}

async function load() {
  loading.value = true
  try {
    const { data } = await api.get(`/staff/bookings/${route.params.id}/`)
    booking.value = data
    edit.check_in = data.check_in
    edit.check_out = data.check_out
    edit.guests_count = data.guests_count
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    loading.value = false
  }
}

async function setStatus(status) {
  acting.value = true
  try {
    const { data } = await api.post(`/staff/bookings/${route.params.id}/status/`, { status })
    booking.value = data
    toast.success('Status updated!')
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    acting.value = false
  }
}

async function saveEdit() {
  acting.value = true
  try {
    const { data } = await api.patch(`/staff/bookings/${route.params.id}/edit/`, { ...edit, guests_count: Number(edit.guests_count) })
    booking.value = data
    toast.success('Booking updated!')
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    acting.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="container py-4">
    <RouterLink :to="{ name: 'staff-bookings' }" class="btn btn-link ps-0 mb-2"><i class="bi bi-arrow-left"></i> {{ $t('common.back') }}</RouterLink>

    <div v-if="loading" class="text-center py-5"><div class="spinner-border text-primary"></div></div>

    <div v-else-if="booking" class="row g-4">
      <div class="col-lg-7">
        <div class="card shadow-sm">
          <div class="card-body">
            <h3>{{ booking.apartment.title }} <span class="badge bg-secondary align-middle">{{ $t('status.' + booking.status) }}</span></h3>
            <table class="table mt-3">
              <tbody>
                <tr><th>{{ $t('staff.guestName') }}</th><td>{{ guestName(booking.user) }}</td></tr>
                <tr><th>{{ $t('staff.guestEmail') }}</th><td>{{ booking.user.email || '—' }}</td></tr>
                <tr><th>{{ $t('staff.guestPhone') }}</th><td>{{ guestPhone(booking.user) }}</td></tr>
                <tr><th>{{ $t('booking.checkIn') }}</th><td>{{ booking.check_in }}</td></tr>
                <tr><th>{{ $t('booking.checkOut') }}</th><td>{{ booking.check_out }}</td></tr>
                <tr><th>{{ $t('dashboard.nights') }}</th><td>{{ booking.nights }}</td></tr>
                <tr><th>{{ $t('dashboard.guests') }}</th><td>{{ booking.guests_count }}</td></tr>
                <tr><th>{{ $t('common.total') }}</th><td class="fw-bold text-primary">{{ booking.total_price }} {{ config.currencySymbol }}</td></tr>
                <tr v-if="booking.notes"><th>{{ $t('booking.notes') }}</th><td>{{ booking.notes }}</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div class="col-lg-5">
        <div class="card shadow-sm mb-4">
          <div class="card-body">
            <h5 class="card-title">{{ $t('staff.updateStatus') }}</h5>
            <div class="d-grid gap-2">
              <button class="btn btn-success" :disabled="acting || booking.status === 'CONFIRMED'" @click="setStatus('CONFIRMED')">
                <i class="bi bi-check-circle"></i> {{ $t('staff.confirmBooking') }}
              </button>
              <button class="btn btn-outline-danger" :disabled="acting" @click="setStatus('CANCELLED_BY_ADMIN')">
                <i class="bi bi-x-circle"></i> {{ $t('staff.cancelBooking') }}
              </button>
            </div>
          </div>
        </div>

        <div class="card shadow-sm">
          <div class="card-body">
            <h5 class="card-title">{{ $t('staff.editBooking') }}</h5>
            <div class="mb-2">
              <label class="form-label small">{{ $t('booking.checkIn') }}</label>
              <input type="date" class="form-control" v-model="edit.check_in" />
            </div>
            <div class="mb-2">
              <label class="form-label small">{{ $t('booking.checkOut') }}</label>
              <input type="date" class="form-control" v-model="edit.check_out" />
            </div>
            <div class="mb-3">
              <label class="form-label small">{{ $t('dashboard.guests') }}</label>
              <input type="number" min="1" class="form-control" v-model="edit.guests_count" />
            </div>
            <button class="btn btn-primary w-100" :disabled="acting" @click="saveEdit">{{ $t('common.save') }}</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
