<script setup>
import { ref, onMounted } from 'vue'
import api, { extractError } from '@/api/client'
import { useToastStore } from '@/stores/toast'
import CalendarBoard from '@/components/CalendarBoard.vue'

const toast = useToastStore()
const events = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const { data } = await api.get('/staff/calendar-events/')
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
    <h1 class="mb-4">{{ $t('staff.globalCalendar') }}</h1>
    <div v-if="loading" class="text-center py-5"><div class="spinner-border text-primary"></div></div>
    <div v-else class="card shadow-sm"><div class="card-body"><CalendarBoard :events="events" /></div></div>
  </div>
</template>
