<script setup>
import { useConfigStore } from '@/stores/config'
const props = defineProps({ apartment: { type: Object, required: true } })
const config = useConfigStore()
</script>

<template>
  <RouterLink :to="{ name: 'apartment-detail', params: { slug: apartment.slug } }" class="text-reset">
    <div class="card apartment-card shadow-sm">
      <img
        :src="apartment.main_image || 'https://via.placeholder.com/400x200?text=No+Image'"
        class="card-img-top"
        :alt="apartment.title"
      />
      <div class="card-body">
        <h5 class="card-title mb-1">{{ apartment.title }}</h5>
        <p class="text-muted small mb-2" v-if="apartment.city || apartment.country">
          <i class="bi bi-geo-alt"></i>
          {{ [apartment.city, apartment.country].filter(Boolean).join(', ') }}
        </p>
        <p class="small text-muted mb-2">
          <i class="bi bi-people"></i> {{ apartment.capacity }} ·
          <i class="bi bi-door-closed"></i> {{ apartment.bedrooms }} ·
          <i class="bi bi-droplet"></i> {{ apartment.bathrooms }}
        </p>
        <div class="d-flex justify-content-between align-items-center">
          <span class="price-tag">{{ apartment.display_price }} {{ config.currencySymbol }}</span>
          <span class="text-muted small">{{ $t('common.perNight') }}</span>
        </div>
      </div>
    </div>
  </RouterLink>
</template>
