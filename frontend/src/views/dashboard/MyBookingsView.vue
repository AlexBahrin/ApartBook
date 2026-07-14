<script setup>
import { onMounted } from 'vue'
import api from '@/api/client'
import { useConfigStore } from '@/stores/config'
import { usePaginatedList } from '@/composables/usePaginatedList'
import PaginationNav from '@/components/PaginationNav.vue'

const config = useConfigStore()

const badgeClass = {
  PENDING: 'badge-pending',
  CONFIRMED: 'badge-confirmed',
  CANCELLED_BY_USER: 'badge-cancelled',
  CANCELLED_BY_ADMIN: 'badge-cancelled',
  COMPLETED: 'badge-completed',
}

const {
  items: bookings,
  loading,
  page,
  totalPages,
  hasNext,
  hasPrev,
  load,
  nextPage,
  prevPage,
} = usePaginatedList((params) => api.get('/my/bookings/', { params }))

onMounted(() => load())
</script>

<template>
  <div class="container py-4">
    <h1 class="mb-4">{{ $t('dashboard.myBookings') }}</h1>

    <div v-if="loading" class="text-center py-5"><div class="spinner-border text-primary"></div></div>
    <div v-else-if="!bookings.length" class="text-center text-muted py-5">
      <i class="bi bi-calendar-x fs-1 d-block mb-2"></i>
      {{ $t('dashboard.noBookings') }}
    </div>

    <div v-else class="row g-3">
      <div v-for="b in bookings" :key="b.id" class="col-12">
        <RouterLink :to="{ name: 'my-booking-detail', params: { id: b.id } }" class="text-reset">
          <div class="card shadow-sm">
            <div class="row g-0">
              <div class="col-md-3">
                <img :src="b.apartment.main_image || 'https://via.placeholder.com/300x200?text=No+Image'" class="img-fluid rounded-start h-100" style="object-fit: cover" />
              </div>
              <div class="col-md-9">
                <div class="card-body">
                  <div class="d-flex justify-content-between align-items-start">
                    <h5 class="card-title">{{ b.apartment.title }}</h5>
                    <span class="badge" :class="badgeClass[b.status]">{{ $t('status.' + b.status) }}</span>
                  </div>
                  <p class="mb-1 text-muted">
                    <i class="bi bi-calendar"></i> {{ b.check_in }} → {{ b.check_out }} ({{ b.nights }} {{ $t('common.nights') }})
                  </p>
                  <p class="mb-1"><i class="bi bi-people"></i> {{ b.guests_count }} {{ $t('common.guests') }}</p>
                  <p class="mb-0 fw-bold text-primary">{{ b.total_price }} {{ config.currencySymbol }}</p>
                </div>
              </div>
            </div>
          </div>
        </RouterLink>
      </div>
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
