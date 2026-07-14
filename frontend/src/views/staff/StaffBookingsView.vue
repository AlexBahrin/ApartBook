<script setup>
import { ref, reactive, onMounted } from 'vue'
import api, { extractError } from '@/api/client'
import { useConfigStore } from '@/stores/config'
import { useToastStore } from '@/stores/toast'

const config = useConfigStore()
const toast = useToastStore()
const bookings = ref([])
const apartments = ref([])
const loading = ref(true)
const filters = reactive({ status: '', apartment: '' })

const statuses = ['PENDING', 'CONFIRMED', 'CANCELLED_BY_USER', 'CANCELLED_BY_ADMIN', 'COMPLETED']
const badgeClass = {
  PENDING: 'badge-pending', CONFIRMED: 'badge-confirmed',
  CANCELLED_BY_USER: 'badge-cancelled', CANCELLED_BY_ADMIN: 'badge-cancelled', COMPLETED: 'badge-completed',
}

async function load() {
  loading.value = true
  const params = {}
  if (filters.status) params.status = filters.status
  if (filters.apartment) params.apartment = filters.apartment
  try {
    const { data } = await api.get('/staff/bookings/', { params })
    bookings.value = data.results || data
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  try {
    const { data } = await api.get('/staff/apartments/')
    apartments.value = data.results || data
  } catch (e) { /* ignore */ }
  load()
})
</script>

<template>
  <div class="container py-4">
    <h1 class="mb-4">{{ $t('staff.bookings') }}</h1>

    <div class="row g-2 mb-4">
      <div class="col-md-4">
        <select class="form-select" v-model="filters.status" @change="load">
          <option value="">{{ $t('staff.allStatuses') }}</option>
          <option v-for="s in statuses" :key="s" :value="s">{{ $t('status.' + s) }}</option>
        </select>
      </div>
      <div class="col-md-4">
        <select class="form-select" v-model="filters.apartment" @change="load">
          <option value="">{{ $t('staff.allApartments') }}</option>
          <option v-for="a in apartments" :key="a.id" :value="a.id">{{ a.title }}</option>
        </select>
      </div>
    </div>

    <div v-if="loading" class="text-center py-5"><div class="spinner-border text-primary"></div></div>
    <div v-else class="table-responsive">
      <table class="table align-middle shadow-sm bg-white">
        <thead class="table-light">
          <tr><th>#</th><th>{{ $t('staff.title') }}</th><th>{{ $t('staff.guest') }}</th><th>{{ $t('booking.checkIn') }}</th><th>{{ $t('booking.checkOut') }}</th><th>{{ $t('common.total') }}</th><th>{{ $t('common.status') }}</th></tr>
        </thead>
        <tbody>
          <tr v-for="b in bookings" :key="b.id" style="cursor: pointer" @click="$router.push({ name: 'staff-booking-detail', params: { id: b.id } })">
            <td>{{ b.id }}</td>
            <td>{{ b.apartment.title }}</td>
            <td>{{ b.user.username }}</td>
            <td>{{ b.check_in }}</td>
            <td>{{ b.check_out }}</td>
            <td>{{ b.total_price }} {{ config.currencySymbol }}</td>
            <td><span class="badge" :class="badgeClass[b.status]">{{ $t('status.' + b.status) }}</span></td>
          </tr>
          <tr v-if="!bookings.length"><td colspan="7" class="text-center text-muted">—</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
