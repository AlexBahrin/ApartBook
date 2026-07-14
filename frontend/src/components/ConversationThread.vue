<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import api, { extractError } from '@/api/client'
import { useToastStore } from '@/stores/toast'

const props = defineProps({
  // API base for this conversation, e.g. '/my/conversations' or '/staff/conversations'
  basePath: { type: String, required: true },
  conversationId: { type: [String, Number], required: true },
  backTo: { type: Object, required: true },
})

const toast = useToastStore()
const conversation = ref(null)
const loading = ref(true)
const body = ref('')
const sending = ref(false)
const listEnd = ref(null)

async function load() {
  loading.value = true
  try {
    const { data } = await api.get(`${props.basePath}/${props.conversationId}/`)
    conversation.value = data
    await scrollToBottom()
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    loading.value = false
  }
}

async function scrollToBottom() {
  await nextTick()
  listEnd.value?.scrollIntoView({ behavior: 'smooth' })
}

async function send() {
  const text = body.value.trim()
  if (!text) return
  sending.value = true
  try {
    const { data } = await api.post(`${props.basePath}/${props.conversationId}/send/`, { body: text })
    conversation.value.messages.push(data)
    body.value = ''
    await scrollToBottom()
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    sending.value = false
  }
}

watch(() => props.conversationId, load)
onMounted(load)
</script>

<template>
  <div class="container py-4">
    <RouterLink :to="backTo" class="btn btn-link ps-0 mb-2"><i class="bi bi-arrow-left"></i> {{ $t('common.back') }}</RouterLink>

    <div v-if="loading" class="text-center py-5"><div class="spinner-border text-primary"></div></div>

    <div v-else-if="conversation" class="card shadow-sm">
      <div class="card-header">
        <strong>{{ conversation.apartment_title || 'Conversation' }}</strong>
        <span class="text-muted small ms-2" v-if="conversation.user">· {{ conversation.user.username }}</span>
      </div>
      <div class="card-body" style="max-height: 55vh; overflow-y: auto">
        <div v-if="!conversation.messages.length" class="text-center text-muted py-4">—</div>
        <div v-for="m in conversation.messages" :key="m.id" class="d-flex mb-3" :class="m.is_mine ? 'justify-content-end' : 'justify-content-start'">
          <div class="p-2 px-3 rounded-3" :class="m.is_mine ? 'bg-primary text-white' : 'bg-light'" style="max-width: 75%">
            <div class="small fw-bold mb-1" v-if="!m.is_mine">{{ m.sender.username }}</div>
            <div style="white-space: pre-line">{{ m.body }}</div>
            <div class="small text-end mt-1" :class="m.is_mine ? 'text-white-50' : 'text-muted'">
              {{ new Date(m.created_at).toLocaleString() }}
            </div>
          </div>
        </div>
        <div ref="listEnd"></div>
      </div>
      <div class="card-footer">
        <form @submit.prevent="send" class="d-flex gap-2">
          <textarea class="form-control" rows="1" v-model="body" :placeholder="$t('dashboard.typeMessage')" @keydown.enter.exact.prevent="send"></textarea>
          <button class="btn btn-primary" type="submit" :disabled="sending || !body.trim()">
            <i class="bi bi-send"></i>
          </button>
        </form>
      </div>
    </div>
  </div>
</template>
