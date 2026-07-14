<script setup>
import { useRoute } from 'vue-router'
import ConversationThread from '@/components/ConversationThread.vue'
const route = useRoute()
</script>

<template>
  <ConversationThread
    base-path="/my/conversations"
    :conversation-id="route.params.id"
    :back-to="{ name: 'my-messages' }"
  />
</template>
