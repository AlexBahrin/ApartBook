<script setup>
import { ref, onMounted } from 'vue'
import api, { extractError } from '@/api/client'
import ApartmentCard from '@/components/ApartmentCard.vue'
import { useToastStore } from '@/stores/toast'

const apartments = ref([])
const loading = ref(true)
const toast = useToastStore()

onMounted(async () => {
  try {
    const { data } = await api.get('/apartments/featured/')
    apartments.value = data
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <section class="hero text-center">
    <div class="container">
      <h1 class="display-4 fw-bold">{{ $t('landing.heroTitle') }}</h1>
      <p class="lead mb-4">{{ $t('landing.heroSubtitle') }}</p>
      <RouterLink :to="{ name: 'apartments' }" class="btn btn-light btn-lg">
        <i class="bi bi-search"></i> {{ $t('landing.browseAll') }}
      </RouterLink>
    </div>
  </section>

  <div class="container py-5">
    <h2 class="mb-4">{{ $t('landing.featured') }}</h2>

    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary"></div>
    </div>

    <div v-else-if="!apartments.length" class="text-center text-muted py-5">
      {{ $t('landing.noFeatured') }}
    </div>

    <div v-else class="row g-4">
      <div v-for="apartment in apartments" :key="apartment.id" class="col-sm-6 col-lg-4">
        <ApartmentCard :apartment="apartment" />
      </div>
    </div>

    <div class="text-center mt-5 p-5 bg-light rounded-3">
      <h3>{{ $t('landing.ctaTitle') }}</h3>
      <RouterLink :to="{ name: 'apartments' }" class="btn btn-primary btn-lg mt-3">
        {{ $t('landing.ctaButton') }}
      </RouterLink>
    </div>
  </div>
</template>
