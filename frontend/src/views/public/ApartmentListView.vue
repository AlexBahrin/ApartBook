<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api, { extractError } from '@/api/client'
import ApartmentCard from '@/components/ApartmentCard.vue'
import PaginationNav from '@/components/PaginationNav.vue'
import { useToastStore } from '@/stores/toast'

const route = useRoute()
const router = useRouter()
const toast = useToastStore()

const PAGE_SIZE = 12
const apartments = ref([])
const loading = ref(true)
const count = ref(0)
const page = ref(1)
const hasNext = ref(false)
const hasPrev = ref(false)

const totalPages = computed(() =>
  count.value ? Math.max(1, Math.ceil(count.value / PAGE_SIZE)) : 1
)

const filters = reactive({
  check_in: route.query.check_in || '',
  check_out: route.query.check_out || '',
  guests: route.query.guests || '',
})

async function load() {
  loading.value = true
  const params = { page: page.value, page_size: PAGE_SIZE }
  for (const [k, v] of Object.entries(filters)) {
    if (v) params[k] = v
  }
  try {
    const { data } = await api.get('/apartments/', { params })
    apartments.value = data.results
    count.value = data.count
    hasNext.value = !!data.next
    hasPrev.value = !!data.previous
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  page.value = 1
  const query = {}
  for (const [k, v] of Object.entries(filters)) {
    if (v) query[k] = v
  }
  router.replace({ query })
  load()
}

function resetFilters() {
  for (const k of Object.keys(filters)) filters[k] = ''
  page.value = 1
  router.replace({ query: {} })
  load()
}

function nextPage() {
  if (hasNext.value) {
    page.value += 1
    load()
  }
}

function prevPage() {
  if (hasPrev.value && page.value > 1) {
    page.value -= 1
    load()
  }
}

onMounted(load)
</script>

<template>
  <div class="container py-4">
    <h1 class="mb-4">{{ $t('apartments.title') }}</h1>

    <div class="row">
      <!-- Filters -->
      <div class="col-lg-3 mb-4">
        <div class="card shadow-sm">
          <div class="card-body">
            <h5 class="card-title"><i class="bi bi-funnel"></i> {{ $t('apartments.filters') }}</h5>
            <div class="mb-2">
              <label class="form-label small">{{ $t('apartments.checkIn') }}</label>
              <input type="date" class="form-control" v-model="filters.check_in" />
            </div>
            <div class="mb-2">
              <label class="form-label small">{{ $t('apartments.checkOut') }}</label>
              <input type="date" class="form-control" v-model="filters.check_out" />
            </div>
            <div class="mb-2">
              <label class="form-label small">{{ $t('apartments.guests') }}</label>
              <input type="number" min="1" class="form-control" v-model="filters.guests" />
            </div>
            <button class="btn btn-primary w-100 mb-2" @click="applyFilters">{{ $t('apartments.apply') }}</button>
            <button class="btn btn-outline-secondary w-100" @click="resetFilters">{{ $t('apartments.reset') }}</button>
          </div>
        </div>
      </div>

      <!-- Results -->
      <div class="col-lg-9">
        <div v-if="loading" class="text-center py-5">
          <div class="spinner-border text-primary"></div>
        </div>
        <div v-else-if="!apartments.length" class="text-center text-muted py-5">
          {{ $t('apartments.none') }}
        </div>
        <div v-else class="row g-4">
          <div v-for="apartment in apartments" :key="apartment.id" class="col-sm-6 col-xl-4">
            <ApartmentCard :apartment="apartment" />
          </div>
        </div>

        <PaginationNav
          :page="page"
          :total-pages="totalPages"
          :has-next="hasNext"
          :has-prev="hasPrev"
          :loading="loading"
          @prev="prevPage"
          @next="nextPage"
        />
      </div>
    </div>
  </div>
</template>
