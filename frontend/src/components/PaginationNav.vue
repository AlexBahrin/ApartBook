<script setup>
defineProps({
  page: { type: Number, required: true },
  totalPages: { type: Number, required: true },
  hasNext: { type: Boolean, default: false },
  hasPrev: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['prev', 'next'])
</script>

<template>
  <nav v-if="totalPages > 1" class="d-flex justify-content-center align-items-center gap-3 mt-4">
    <button
      class="btn btn-outline-secondary btn-sm"
      :disabled="!hasPrev || loading"
      @click="emit('prev')"
    >
      <i class="bi bi-chevron-left"></i> {{ $t('common.prev') }}
    </button>
    <span class="text-muted small">{{ $t('common.pageOf', { page, total: totalPages }) }}</span>
    <button
      class="btn btn-outline-secondary btn-sm"
      :disabled="!hasNext || loading"
      @click="emit('next')"
    >
      {{ $t('common.next') }} <i class="bi bi-chevron-right"></i>
    </button>
  </nav>
</template>
