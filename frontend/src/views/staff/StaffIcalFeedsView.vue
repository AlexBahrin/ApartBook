<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api, { extractError } from '@/api/client'
import { useToastStore } from '@/stores/toast'

const route = useRoute()
const toast = useToastStore()
const feeds = ref([])
const exportUrl = ref('')
const loading = ref(true)
const adding = ref(false)
const form = reactive({ name: '', url: '' })

async function load() {
  loading.value = true
  try {
    const { data } = await api.get(`/staff/apartments/${route.params.id}/ical-feeds/`)
    feeds.value = data.feeds
    exportUrl.value = data.export_url
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    loading.value = false
  }
}

async function addFeed() {
  if (!form.name || !form.url) return
  adding.value = true
  try {
    const { data } = await api.post(`/staff/apartments/${route.params.id}/ical-feeds/`, { ...form })
    toast[data.sync_success ? 'success' : 'info'](data.sync_message || 'Feed added')
    form.name = ''
    form.url = ''
    await load()
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    adding.value = false
  }
}

async function sync(feed) {
  try {
    const { data } = await api.post(`/staff/apartments/${route.params.id}/ical-feeds/${feed.id}/sync/`)
    toast[data.success ? 'success' : 'error'](data.message)
    await load()
  } catch (e) {
    toast.error(extractError(e))
  }
}

async function remove(feed) {
  if (!confirm('Delete this feed?')) return
  try {
    await api.delete(`/staff/apartments/${route.params.id}/ical-feeds/${feed.id}/`)
    feeds.value = feeds.value.filter((f) => f.id !== feed.id)
    toast.success('Deleted!')
  } catch (e) {
    toast.error(extractError(e))
  }
}

function copyExport() {
  navigator.clipboard.writeText(exportUrl.value)
  toast.info('Copied!')
}

onMounted(load)
</script>

<template>
  <div class="container py-4">
    <RouterLink :to="{ name: 'staff-apartment-manage', params: { id: route.params.id } }" class="btn btn-link ps-0 mb-2"><i class="bi bi-arrow-left"></i> {{ $t('common.back') }}</RouterLink>
    <h1 class="mb-4">{{ $t('staff.icalFeeds') }}</h1>

    <div class="card shadow-sm mb-4">
      <div class="card-body">
        <label class="form-label">{{ $t('staff.exportUrl') }}</label>
        <div class="input-group">
          <input type="text" class="form-control" :value="exportUrl" readonly />
          <button class="btn btn-outline-secondary" @click="copyExport"><i class="bi bi-clipboard"></i></button>
        </div>
      </div>
    </div>

    <div class="card shadow-sm mb-4">
      <div class="card-body">
        <h5 class="card-title">{{ $t('staff.addFeed') }}</h5>
        <div class="row g-2">
          <div class="col-md-4"><input type="text" class="form-control" :placeholder="$t('staff.feedName')" v-model="form.name" /></div>
          <div class="col-md-6"><input type="url" class="form-control" :placeholder="$t('staff.feedUrl')" v-model="form.url" /></div>
          <div class="col-md-2 d-grid"><button class="btn btn-primary" :disabled="adding" @click="addFeed">{{ $t('staff.addFeed') }}</button></div>
        </div>
      </div>
    </div>

    <div v-if="loading" class="text-center py-5"><div class="spinner-border text-primary"></div></div>
    <div v-else class="card shadow-sm">
      <div class="card-body">
        <table class="table align-middle">
          <thead class="table-light">
            <tr><th>{{ $t('staff.feedName') }}</th><th>{{ $t('staff.lastSynced') }}</th><th>{{ $t('common.status') }}</th><th class="text-end">{{ $t('common.actions') }}</th></tr>
          </thead>
          <tbody>
            <tr v-for="f in feeds" :key="f.id">
              <td>{{ f.name }}<br /><span class="small text-muted text-truncate d-inline-block" style="max-width: 300px">{{ f.url }}</span></td>
              <td>{{ f.last_synced ? new Date(f.last_synced).toLocaleString() : $t('staff.never') }}</td>
              <td><span class="badge" :class="f.last_sync_status === 'SUCCESS' ? 'bg-success' : 'bg-secondary'">{{ f.last_sync_status || '—' }}</span></td>
              <td class="text-end">
                <button class="btn btn-sm btn-outline-primary me-1" @click="sync(f)"><i class="bi bi-arrow-repeat"></i> {{ $t('staff.sync') }}</button>
                <button class="btn btn-sm btn-outline-danger" @click="remove(f)"><i class="bi bi-trash"></i></button>
              </td>
            </tr>
            <tr v-if="!feeds.length"><td colspan="4" class="text-muted text-center">—</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
