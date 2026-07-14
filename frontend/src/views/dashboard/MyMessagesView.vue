<script setup>
import { onMounted } from 'vue'
import api from '@/api/client'
import { usePaginatedList } from '@/composables/usePaginatedList'
import PaginationNav from '@/components/PaginationNav.vue'

const {
  items: conversations,
  loading,
  page,
  totalPages,
  hasNext,
  hasPrev,
  load,
  nextPage,
  prevPage,
} = usePaginatedList((params) => api.get('/my/conversations/', { params }))

onMounted(() => load())
</script>

<template>
  <div class="container py-4">
    <h1 class="mb-4">{{ $t('dashboard.myMessages') }}</h1>

    <div v-if="loading" class="text-center py-5"><div class="spinner-border text-primary"></div></div>
    <div v-else-if="!conversations.length" class="text-center text-muted py-5">
      <i class="bi bi-chat-square-dots fs-1 d-block mb-2"></i>
      {{ $t('dashboard.noMessages') }}
    </div>

    <div v-else class="list-group shadow-sm">
      <RouterLink
        v-for="c in conversations"
        :key="c.id"
        :to="{ name: 'my-conversation', params: { id: c.id } }"
        class="list-group-item list-group-item-action"
      >
        <div class="d-flex justify-content-between">
          <h6 class="mb-1">{{ c.apartment_title || 'Conversation' }}</h6>
          <span v-if="c.unread_count" class="badge bg-danger rounded-pill">{{ c.unread_count }}</span>
        </div>
        <p class="mb-1 text-muted small text-truncate" v-if="c.last_message">
          {{ c.last_message.sender }}: {{ c.last_message.body }}
        </p>
      </RouterLink>
    </div>

    <PaginationNav
      :page="page"
      :total-pages="totalPages"
      :has-next="hasNext"
      :has-prev="hasPrev"
      :loading="loading"
      @prev="prevPage()"
      @next="nextPage()"
    />
  </div>
</template>
