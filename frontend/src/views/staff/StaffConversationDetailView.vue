<script setup>
import { useRoute } from 'vue-router'
import ConversationThread from '@/components/ConversationThread.vue'
const route = useRoute()
</script>

<template>
  <ConversationThread
    base-path="/staff/conversations"
    :conversation-id="route.params.id"
    :back-to="{ name: 'staff-messages' }"
  />
</template>
