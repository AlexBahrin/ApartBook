<script setup>
import { ref, onMounted } from 'vue'
import api, { extractError } from '@/api/client'
import { useToastStore } from '@/stores/toast'

const toast = useToastStore()
const conversations = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const { data } = await api.get('/staff/conversations/')
    conversations.value = data.results || data
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="container py-4">
    <h1 class="mb-4">{{ $t('staff.messages') }}</h1>

    <div v-if="loading" class="text-center py-5"><div class="spinner-border text-primary"></div></div>
    <div v-else-if="!conversations.length" class="text-center text-muted py-5">—</div>

    <div v-else class="list-group shadow-sm">
      <RouterLink
        v-for="c in conversations"
        :key="c.id"
        :to="{ name: 'staff-conversation', params: { id: c.id } }"
        class="list-group-item list-group-item-action"
      >
        <div class="d-flex justify-content-between">
          <h6 class="mb-1">{{ c.user.username }} <span class="text-muted small">· {{ c.apartment_title || '—' }}</span></h6>
          <span v-if="c.unread_count" class="badge bg-danger rounded-pill">{{ c.unread_count }}</span>
        </div>
        <p class="mb-1 text-muted small text-truncate" v-if="c.last_message">{{ c.last_message.sender }}: {{ c.last_message.body }}</p>
      </RouterLink>
    </div>
  </div>
</template>
