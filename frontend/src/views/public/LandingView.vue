<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api, { extractError } from '@/api/client'
import ApartmentCard from '@/components/ApartmentCard.vue'
import { useToastStore } from '@/stores/toast'

const apartments = ref([])
const loading = ref(true)
const toast = useToastStore()
const router = useRouter()

const search = reactive({ check_in: '', check_out: '', guests: '' })

function submitSearch() {
  const query = {}
  for (const [k, v] of Object.entries(search)) {
    if (v) query[k] = v
  }
  router.push({ name: 'apartments', query })
}

const features = [
  { icon: 'bi-lightning-charge', title: 'landing.feature1Title', text: 'landing.feature1Text' },
  { icon: 'bi-tag', title: 'landing.feature2Title', text: 'landing.feature2Text' },
  { icon: 'bi-patch-check', title: 'landing.feature3Title', text: 'landing.feature3Text' },
  { icon: 'bi-chat-dots', title: 'landing.feature4Title', text: 'landing.feature4Text' },
]

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
  <!-- Hero -->
  <section class="hero-section text-white">
    <div class="hero-overlay"></div>
    <div class="container position-relative py-5">
      <div class="row justify-content-center text-center">
        <div class="col-lg-9">
          <h1 class="display-3 fw-bold mb-3">{{ $t('landing.heroTitle') }}</h1>
          <p class="lead mb-4 opacity-90">{{ $t('landing.heroSubtitle') }}</p>
        </div>
      </div>

      <!-- Search bar -->
      <div class="row justify-content-center">
        <div class="col-xl-10">
          <form class="search-card shadow-lg" @submit.prevent="submitSearch">
            <div class="row g-2 align-items-end">
              <div class="col-6 col-md">
                <label class="form-label small fw-semibold text-muted mb-1">{{ $t('apartments.checkIn') }}</label>
                <input type="date" class="form-control form-control-lg" v-model="search.check_in" />
              </div>
              <div class="col-6 col-md">
                <label class="form-label small fw-semibold text-muted mb-1">{{ $t('apartments.checkOut') }}</label>
                <input type="date" class="form-control form-control-lg" v-model="search.check_out" />
              </div>
              <div class="col-6 col-md-2">
                <label class="form-label small fw-semibold text-muted mb-1">
                  <i class="bi bi-people"></i> {{ $t('apartments.guests') }}
                </label>
                <input type="number" min="1" class="form-control form-control-lg" v-model="search.guests" placeholder="1" />
              </div>
              <div class="col-6 col-md-auto d-grid">
                <button type="submit" class="btn btn-primary btn-lg px-4">
                  <i class="bi bi-search"></i> {{ $t('landing.searchButton') }}
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>
  </section>

  <!-- Features -->
  <section class="container py-5">
    <div class="text-center mb-5">
      <h2 class="fw-bold">{{ $t('landing.featuresTitle') }}</h2>
      <p class="text-muted">{{ $t('landing.featuresSubtitle') }}</p>
    </div>
    <div class="row g-4">
      <div v-for="f in features" :key="f.title" class="col-sm-6 col-lg-3">
        <div class="feature-card text-center h-100">
          <div class="feature-icon mb-3">
            <i class="bi" :class="f.icon"></i>
          </div>
          <h5 class="fw-semibold">{{ $t(f.title) }}</h5>
          <p class="text-muted small mb-0">{{ $t(f.text) }}</p>
        </div>
      </div>
    </div>
  </section>

  <!-- Featured apartments -->
  <section class="bg-light py-5">
    <div class="container">
      <div class="d-flex justify-content-between align-items-end mb-4 flex-wrap gap-2">
        <div>
          <h2 class="fw-bold mb-1">{{ $t('landing.featured') }}</h2>
          <p class="text-muted mb-0">{{ $t('landing.featuredSubtitle') }}</p>
        </div>
        <RouterLink :to="{ name: 'apartments' }" class="btn btn-outline-primary">
          {{ $t('landing.viewAll') }} <i class="bi bi-arrow-right"></i>
        </RouterLink>
      </div>

      <div v-if="loading" class="text-center py-5">
        <div class="spinner-border text-primary"></div>
      </div>

      <div v-else-if="!apartments.length" class="text-center text-muted py-5">
        <i class="bi bi-houses fs-1 d-block mb-2 opacity-50"></i>
        {{ $t('landing.noFeatured') }}
      </div>

      <div v-else class="row g-4">
        <div v-for="apartment in apartments" :key="apartment.id" class="col-sm-6 col-lg-4">
          <ApartmentCard :apartment="apartment" />
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.hero-section {
  position: relative;
  background:
    linear-gradient(135deg, rgba(255, 56, 92, 0.92) 0%, rgba(227, 28, 95, 0.92) 100%),
    url('https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?auto=format&fit=crop&w=1600&q=80');
  background-size: cover;
  background-position: center;
  padding-top: 2rem;
  padding-bottom: 5rem;
}

.hero-overlay {
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at top right, rgba(0, 166, 153, 0.25), transparent 55%);
  pointer-events: none;
}

.opacity-90 {
  opacity: 0.92;
}

.search-card {
  background: #fff;
  border-radius: 1rem;
  padding: 1.25rem;
  margin-top: 1.5rem;
}

.search-card .form-control {
  border-radius: 0.6rem;
}

.feature-card {
  padding: 2rem 1.25rem;
  border-radius: 1rem;
  background: #fff;
  border: 1px solid #f0f0f0;
  transition: transform 0.25s ease, box-shadow 0.25s ease;
}

.feature-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.08);
}

.feature-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-size: 1.6rem;
  color: var(--primary-color);
  background: rgba(255, 56, 92, 0.1);
}

.cta-band {
  background: linear-gradient(135deg, #00a699 0%, #007d74 100%);
}

.rounded-4 {
  border-radius: 1.25rem;
}

@media (max-width: 767.98px) {
  .hero-section {
    padding-bottom: 3rem;
  }
  .display-3 {
    font-size: 2.4rem;
  }
}
</style>
