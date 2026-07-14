<script setup>
import { useToastStore } from '@/stores/toast'
const toast = useToastStore()
</script>

<template>
  <div class="toast-container position-fixed bottom-0 end-0 p-3">
    <div
      v-for="t in toast.toasts"
      :key="t.id"
      class="toast show align-items-center text-white border-0 mb-2"
      :class="`bg-${t.type}`"
      role="alert"
    >
      <div class="d-flex">
        <div class="toast-body">{{ t.message }}</div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" @click="toast.remove(t.id)"></button>
      </div>
    </div>
  </div>
</template>
