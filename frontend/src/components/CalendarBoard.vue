<script setup>
import { ref, watch } from 'vue'
import FullCalendar from '@fullcalendar/vue3'
import dayGridPlugin from '@fullcalendar/daygrid'
import interactionPlugin from '@fullcalendar/interaction'
import { useRouter } from 'vue-router'

const props = defineProps({
  events: { type: Array, default: () => [] },
})

const router = useRouter()

const options = ref({
  plugins: [dayGridPlugin, interactionPlugin],
  initialView: 'dayGridMonth',
  headerToolbar: { left: 'prev,next today', center: 'title', right: 'dayGridMonth' },
  height: 'auto',
  events: props.events,
  eventClick(info) {
    if (info.event.url) {
      info.jsEvent.preventDefault()
      router.push(info.event.url)
    }
  },
})

watch(() => props.events, (val) => {
  options.value = { ...options.value, events: val }
})
</script>

<template>
  <FullCalendar :options="options" />
</template>
