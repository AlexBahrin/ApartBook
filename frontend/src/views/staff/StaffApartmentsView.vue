<script setup>
import { ref, onMounted } from 'vue'
import api, { extractError } from '@/api/client'
import { useConfigStore } from '@/stores/config'
import { useToastStore } from '@/stores/toast'

const config = useConfigStore()
const toast = useToastStore()
const apartments = ref([])
const loading = ref(true)

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/staff/apartments/')
    apartments.value = data.results || data
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    loading.value = false
  }
}

async function remove(apartment) {
  if (!confirm('Are you sure you want to delete this apartment?')) return
  try {
    await api.delete(`/staff/apartments/${apartment.id}/`)
    apartments.value = apartments.value.filter((a) => a.id !== apartment.id)
    toast.success('Deleted successfully!')
  } catch (e) {
    toast.error(extractError(e))
  }
}

onMounted(load)
</script>

<template>
  <div class="container py-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h1 class="mb-0">{{ $t('staff.apartments') }}</h1>
      <RouterLink :to="{ name: 'staff-apartment-new' }" class="btn btn-primary">
        <i class="bi bi-plus-lg"></i> {{ $t('staff.addApartment') }}
      </RouterLink>
    </div>

    <div v-if="loading" class="text-center py-5"><div class="spinner-border text-primary"></div></div>

    <div v-else class="table-responsive">
      <table class="table align-middle shadow-sm bg-white">
        <thead class="table-light">
          <tr>
            <th></th>
            <th>{{ $t('staff.title') }}</th>
            <th>{{ $t('staff.capacity') }}</th>
            <th>{{ $t('staff.basePrice') }}</th>
            <th>{{ $t('staff.isActive') }}</th>
            <th class="text-end">{{ $t('common.actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="a in apartments" :key="a.id">
            <td style="width: 80px">
              <img :src="(a.images && a.images[0] && a.images[0].image) || 'https://via.placeholder.com/60'" class="rounded" width="60" height="45" style="object-fit: cover" />
            </td>
            <td>{{ a.title }}</td>
            <td>{{ a.capacity }}</td>
            <td>{{ a.base_price_per_night }} {{ config.currencySymbol }}</td>
            <td>
              <span class="badge" :class="a.is_active ? 'bg-success' : 'bg-secondary'">
                {{ a.is_active ? $t('common.yes') : $t('common.no') }}
              </span>
            </td>
            <td class="text-end">
              <div class="btn-group btn-group-sm">
                <RouterLink :to="{ name: 'staff-apartment-edit', params: { id: a.id } }" class="btn btn-outline-secondary" :title="$t('common.edit')"><i class="bi bi-pencil"></i></RouterLink>
                <RouterLink :to="{ name: 'staff-apartment-images', params: { id: a.id } }" class="btn btn-outline-secondary" :title="$t('staff.manageImages')"><i class="bi bi-images"></i></RouterLink>
                <RouterLink :to="{ name: 'staff-availability', params: { id: a.id } }" class="btn btn-outline-secondary" :title="$t('staff.availability')"><i class="bi bi-calendar-week"></i></RouterLink>
                <RouterLink :to="{ name: 'staff-calendar', params: { id: a.id } }" class="btn btn-outline-secondary" :title="$t('staff.calendar')"><i class="bi bi-calendar3"></i></RouterLink>
                <RouterLink :to="{ name: 'staff-ical', params: { id: a.id } }" class="btn btn-outline-secondary" :title="$t('staff.icalFeeds')"><i class="bi bi-rss"></i></RouterLink>
                <button class="btn btn-outline-danger" @click="remove(a)" :title="$t('common.delete')"><i class="bi bi-trash"></i></button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
