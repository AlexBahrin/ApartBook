<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api, { extractError } from '@/api/client'
import { useToastStore } from '@/stores/toast'

const route = useRoute()
const toast = useToastStore()
const entries = ref([])
const loading = ref(true)
const blocking = ref(false)

const form = reactive({ start_date: '', end_date: '', note: '' })

async function load() {
  loading.value = true
  try {
    const { data } = await api.get(`/staff/apartments/${route.params.id}/availability/`)
    entries.value = data
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    loading.value = false
  }
}

async function block() {
  if (!form.start_date || !form.end_date) return
  blocking.value = true
  try {
    await api.post(`/staff/apartments/${route.params.id}/block/`, { ...form })
    toast.success('Dates blocked!')
    form.note = ''
    await load()
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    blocking.value = false
  }
}

async function unblock(entry) {
  try {
    await api.delete(`/staff/apartments/${route.params.id}/availability/${entry.id}/`)
    entries.value = entries.value.filter((e) => e.id !== entry.id)
    toast.success('Unblocked!')
  } catch (e) {
    toast.error(extractError(e))
  }
}

onMounted(load)
</script>

<template>
  <div class="container py-4">
    <RouterLink :to="{ name: 'staff-apartment-manage', params: { id: route.params.id } }" class="btn btn-link ps-0 mb-2"><i class="bi bi-arrow-left"></i> {{ $t('common.back') }}</RouterLink>
    <h1 class="mb-4">{{ $t('staff.availability') }}</h1>

    <div class="row g-4">
      <div class="col-lg-4">
        <div class="card shadow-sm">
          <div class="card-body">
            <h5 class="card-title">{{ $t('staff.blockDates') }}</h5>
            <div class="mb-2">
              <label class="form-label small">{{ $t('staff.startDate') }}</label>
              <input type="date" class="form-control" v-model="form.start_date" />
            </div>
            <div class="mb-2">
              <label class="form-label small">{{ $t('staff.endDate') }}</label>
              <input type="date" class="form-control" v-model="form.end_date" />
            </div>
            <div class="mb-3">
              <label class="form-label small">{{ $t('staff.note') }}</label>
              <input type="text" class="form-control" v-model="form.note" />
            </div>
            <button class="btn btn-primary w-100" :disabled="blocking" @click="block">{{ $t('staff.block') }}</button>
          </div>
        </div>
      </div>

      <div class="col-lg-8">
        <div class="card shadow-sm">
          <div class="card-body">
            <h5 class="card-title">{{ $t('staff.blocked') }}</h5>
            <div v-if="loading" class="text-center py-4"><div class="spinner-border text-primary"></div></div>
            <div v-else-if="!entries.filter(e => !e.is_available).length" class="text-muted">{{ $t('staff.noBlocked') }}</div>
            <table v-else class="table">
              <tbody>
                <tr v-for="e in entries.filter(e => !e.is_available)" :key="e.id">
                  <td>{{ e.date }}</td>
                  <td>{{ e.note }}</td>
                  <td><span class="badge bg-secondary">{{ e.source }}</span></td>
                  <td class="text-end">
                    <button class="btn btn-sm btn-outline-danger" @click="unblock(e)">{{ $t('staff.unblock') }}</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
