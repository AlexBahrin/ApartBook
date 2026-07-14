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

function shiftBookingBar(info) {
  if (info.event.extendedProps?.type !== 'booking') return

  const dayCell = info.el.closest('td')
  if (!dayCell) return

  const cellWidth = dayCell.getBoundingClientRect().width
  const naturalWidth = info.el.getBoundingClientRect().width
  if (!cellWidth || !naturalWidth) return

  const quarter = cellWidth / 4

  // The booking event spans check_in .. check_out+1 (one extra day) so the
  // checkout morning is always renderable, even when it wraps to the next week row.
  //  - the first segment starts a quarter-day later  => afternoon check-in
  //  - the last segment ends after only a quarter-day => morning check-out
  const leftTrim = info.isStart ? quarter : 0
  const rightTrim = info.isEnd ? cellWidth - quarter : 0

  const newWidth = Math.max(quarter, naturalWidth - leftTrim - rightTrim)

  info.el.style.transform = `translateX(${leftTrim}px)`
  info.el.style.width = `${newWidth}px`
}

const options = ref({
  plugins: [dayGridPlugin, interactionPlugin],
  initialView: 'dayGridMonth',
  headerToolbar: { left: 'prev,next today', center: 'title', right: 'dayGridMonth' },
  height: 'auto',
  events: props.events,
  eventDidMount: shiftBookingBar,
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
