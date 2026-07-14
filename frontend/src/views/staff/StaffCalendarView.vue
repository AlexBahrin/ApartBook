<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api, { extractError } from '@/api/client'
import { useToastStore } from '@/stores/toast'
import CalendarBoard from '@/components/CalendarBoard.vue'

const route = useRoute()
const toast = useToastStore()
const events = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const { data } = await api.get(`/staff/apartments/${route.params.id}/calendar-events/`)
    events.value = data
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="container py-4">
    <RouterLink :to="{ name: 'staff-apartments' }" class="btn btn-link ps-0 mb-2"><i class="bi bi-arrow-left"></i> {{ $t('common.back') }}</RouterLink>
    <h1 class="mb-4">{{ $t('staff.calendar') }}</h1>
    <div v-if="loading" class="text-center py-5"><div class="spinner-border text-primary"></div></div>
    <div v-else class="card shadow-sm"><div class="card-body"><CalendarBoard :events="events" /></div></div>
  </div>
</template>
