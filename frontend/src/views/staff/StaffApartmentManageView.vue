<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api, { extractError } from '@/api/client'
import { useToastStore } from '@/stores/toast'

const route = useRoute()
const router = useRouter()
const toast = useToastStore()

const apartment = ref(null)
const loading = ref(true)
const deleting = ref(false)

const options = computed(() => [
  {
    icon: 'bi-sliders',
    title: 'staff.editApartment',
    description: 'staff.manageGeneralDesc',
    to: { name: 'staff-apartment-edit', params: { id: route.params.id } },
  },
  {
    icon: 'bi-images',
    title: 'staff.manageImages',
    description: 'staff.manageImagesDesc',
    to: { name: 'staff-apartment-images', params: { id: route.params.id } },
  },
  {
    icon: 'bi-calendar-week',
    title: 'staff.availability',
    description: 'staff.manageAvailabilityDesc',
    to: { name: 'staff-availability', params: { id: route.params.id } },
  },
  {
    icon: 'bi-calendar3',
    title: 'staff.calendar',
    description: 'staff.manageCalendarDesc',
    to: { name: 'staff-calendar', params: { id: route.params.id } },
  },
  {
    icon: 'bi-rss',
    title: 'staff.icalFeeds',
    description: 'staff.manageIcalDesc',
    to: { name: 'staff-ical', params: { id: route.params.id } },
  },
])

async function loadApartment() {
  loading.value = true
  try {
    const { data } = await api.get(`/staff/apartments/${route.params.id}/`)
    apartment.value = data
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    loading.value = false
  }
}

async function removeApartment() {
  if (!confirm('Are you sure you want to delete this apartment?')) return
  deleting.value = true
  try {
    await api.delete(`/staff/apartments/${route.params.id}/`)
    toast.success('Deleted successfully!')
    router.push({ name: 'staff-apartments' })
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    deleting.value = false
  }
}

onMounted(loadApartment)
</script>

<template>
  <div class="container py-4">
    <RouterLink :to="{ name: 'staff-apartments' }" class="btn btn-link ps-0 mb-2">
      <i class="bi bi-arrow-left"></i> {{ $t('common.back') }}
    </RouterLink>

    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary"></div>
    </div>

    <div v-else-if="apartment">
      <div class="d-flex justify-content-between align-items-start flex-wrap gap-3 mb-4">
        <div>
          <h1 class="mb-1">{{ $t('staff.manageApartmentTitle') }}</h1>
          <p class="text-muted mb-0">
            {{ apartment.title }} · {{ $t('staff.manageApartmentSubtitle') }}
          </p>
        </div>
      </div>

      <div class="row g-3">
        <div v-for="opt in options" :key="opt.title" class="col-12 col-md-6 col-xl-4">
          <RouterLink :to="opt.to" class="text-reset">
            <div class="card h-100 shadow-sm border-0">
              <div class="card-body">
                <div class="d-flex align-items-center gap-2 mb-2">
                  <span class="badge rounded-pill bg-light text-dark border">
                    <i class="bi" :class="opt.icon"></i>
                  </span>
                  <h5 class="mb-0">{{ $t(opt.title) }}</h5>
                </div>
                <p class="text-muted mb-0 small">{{ $t(opt.description) }}</p>
              </div>
              <div class="card-footer bg-white border-0 pt-0">
                <span class="btn btn-outline-primary btn-sm">{{ $t('staff.goToSetting') }}</span>
              </div>
            </div>
          </RouterLink>
        </div>
      </div>

      <div class="mt-4 pt-3 border-top">
        <button class="btn btn-outline-danger" :disabled="deleting" @click="removeApartment">
          <span v-if="deleting" class="spinner-border spinner-border-sm me-1"></span>
          {{ $t('staff.deleteApartment') }}
        </button>
      </div>
    </div>
  </div>
</template>
