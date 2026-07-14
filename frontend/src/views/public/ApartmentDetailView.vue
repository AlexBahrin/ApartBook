<script setup>
import { ref, reactive, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import flatpickr from 'flatpickr'
import 'flatpickr/dist/flatpickr.min.css'
import api, { extractError } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useConfigStore } from '@/stores/config'
import { useToastStore } from '@/stores/toast'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const config = useConfigStore()
const toast = useToastStore()

const apartment = ref(null)
const loading = ref(true)
const activeImage = ref(null)

const form = reactive({ check_in: '', check_out: '', guests_count: 1, notes: '' })
const price = ref(null)
const priceLoading = ref(false)
const submitting = ref(false)

const canBook = computed(() => auth.isAuthenticated && !auth.isStaff)

const unavailableCheckin = computed(() => new Set(apartment.value?.calendar?.unavailable_for_checkin || []))
const unavailableCheckout = computed(() => new Set(apartment.value?.calendar?.unavailable_for_checkout || []))

// --- Interactive date pickers (flatpickr) ---
const checkInInput = ref(null)
const checkOutInput = ref(null)
let fpCheckIn = null
let fpCheckOut = null

function addDays(dateStr, n) {
  const [y, m, d] = dateStr.split('-').map(Number)
  const dt = new Date(Date.UTC(y, m - 1, d))
  dt.setUTCDate(dt.getUTCDate() + n)
  return dt.toISOString().slice(0, 10)
}

function firstUnavailableOnOrAfter(dateStr) {
  const nights = Array.from(unavailableCheckin.value).sort()
  for (const d of nights) {
    if (d >= dateStr) return d
  }
  return null
}

function syncCheckoutBounds() {
  if (!fpCheckOut) return
  if (form.check_in) {
    // Check-out must be strictly after check-in and cannot cross an unavailable night.
    fpCheckOut.set('minDate', addDays(form.check_in, 1))
    const maxNight = firstUnavailableOnOrAfter(form.check_in)
    fpCheckOut.set('maxDate', maxNight || null)
    if (form.check_out && (form.check_out <= form.check_in || (maxNight && form.check_out > maxNight))) {
      fpCheckOut.clear()
      form.check_out = ''
    }
  } else {
    fpCheckOut.set('minDate', 'today')
    fpCheckOut.set('maxDate', null)
  }
}

function destroyPickers() {
  if (fpCheckIn) { fpCheckIn.destroy(); fpCheckIn = null }
  if (fpCheckOut) { fpCheckOut.destroy(); fpCheckOut = null }
}

function initPickers() {
  destroyPickers()
  if (!checkInInput.value || !checkOutInput.value) return

  const common = { dateFormat: 'Y-m-d', altInput: true, altFormat: 'M j, Y' }

  fpCheckIn = flatpickr(checkInInput.value, {
    ...common,
    minDate: 'today',
    disable: Array.from(unavailableCheckin.value),
    onChange(_, dateStr) {
      form.check_in = dateStr
      syncCheckoutBounds()
    },
  })

  fpCheckOut = flatpickr(checkOutInput.value, {
    ...common,
    minDate: 'today',
    disable: Array.from(unavailableCheckout.value),
    onChange(_, dateStr) {
      form.check_out = dateStr
    },
  })

  syncCheckoutBounds()
}

async function load() {
  loading.value = true
  try {
    const { data } = await api.get(`/apartments/${route.params.slug}/`)
    apartment.value = data
    const main = data.images.find((i) => i.is_main) || data.images[0]
    activeImage.value = main ? main.image : null
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    loading.value = false
  }
  // Initialize the pickers only after the booking card is rendered (loading=false).
  await nextTick()
  if (apartment.value) initPickers()
}

function datesValid() {
  if (!form.check_in || !form.check_out) return false
  if (form.check_out <= form.check_in) return false
  return true
}

async function fetchPrice() {
  price.value = null
  if (!datesValid()) return
  priceLoading.value = true
  try {
    const { data } = await api.get(`/apartments/${route.params.slug}/price/`, {
      params: { check_in: form.check_in, check_out: form.check_out, guests_count: form.guests_count },
    })
    price.value = data
  } catch (e) {
    price.value = null
  } finally {
    priceLoading.value = false
  }
}

watch(() => [form.check_in, form.check_out, form.guests_count], fetchPrice)

async function submitBooking() {
  if (!canBook.value) {
    router.push({ name: 'login', query: { next: route.fullPath } })
    return
  }
  if (!datesValid()) {
    toast.error(t('booking.unavailable'))
    return
  }
  submitting.value = true
  try {
    await api.post(`/my/bookings/create-for/${route.params.slug}/`, {
      check_in: form.check_in,
      check_out: form.check_out,
      guests_count: Number(form.guests_count),
      notes: form.notes,
    })
    toast.success(bookingSuccess.value)
    router.push({ name: 'my-bookings' })
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    submitting.value = false
  }
}

import { useI18n } from 'vue-i18n'
const { t } = useI18n()
const bookingSuccess = computed(() => t('booking.success'))

onMounted(load)
onBeforeUnmount(destroyPickers)
</script>

<template>
  <div v-if="loading" class="text-center py-5">
    <div class="spinner-border text-primary"></div>
  </div>

  <div v-else-if="apartment" class="container py-4">
    <RouterLink :to="{ name: 'apartments' }" class="btn btn-link ps-0 mb-2">
      <i class="bi bi-arrow-left"></i> {{ $t('common.back') }}
    </RouterLink>

    <h1 class="mb-1">{{ apartment.title }}</h1>
    <p class="text-muted" v-if="apartment.city || apartment.country">
      <i class="bi bi-geo-alt"></i> {{ apartment.address }}, {{ [apartment.city, apartment.country].filter(Boolean).join(', ') }}
    </p>

    <div class="row g-4">
      <div class="col-lg-8">
        <!-- Gallery -->
        <img
          v-if="activeImage"
          :src="activeImage"
          class="gallery-main mb-3"
          :alt="apartment.title"
        />
        <div v-else class="gallery-main mb-3 bg-light d-flex align-items-center justify-content-center text-muted">
          <i class="bi bi-image fs-1"></i>
        </div>
        <div class="row g-2 mb-4" v-if="apartment.images.length > 1">
          <div v-for="img in apartment.images" :key="img.id" class="col-3 col-md-2">
            <img :src="img.image" class="image-thumb" :class="{ 'border border-primary border-2': activeImage === img.image }" @click="activeImage = img.image" />
          </div>
        </div>

        <div class="d-flex gap-4 mb-4">
          <span><i class="bi bi-people"></i> {{ $t('apartments.capacity', { count: apartment.capacity }) }}</span>
          <span><i class="bi bi-door-closed"></i> {{ $t('apartments.bedrooms', { count: apartment.bedrooms }) }}</span>
          <span><i class="bi bi-droplet"></i> {{ $t('apartments.bathrooms', { count: apartment.bathrooms }) }}</span>
        </div>

        <h4>{{ $t('apartments.description') }}</h4>
        <p style="white-space: pre-line">{{ apartment.description }}</p>

        <div v-if="apartment.amenities && apartment.amenities.length">
          <h4>{{ $t('apartments.amenities') }}</h4>
          <div class="d-flex flex-wrap gap-2">
            <span v-for="a in apartment.amenities" :key="a" class="badge bg-light text-dark border">
              <i class="bi bi-check-circle text-success"></i> {{ a }}
            </span>
          </div>
        </div>
      </div>

      <!-- Booking card -->
      <div class="col-lg-4">
        <div class="card shadow-sm sticky-lg-top" style="top: 90px">
          <div class="card-body">
            <h5 class="card-title">{{ $t('booking.title') }}</h5>
            <div class="mb-2">
              <label class="form-label small">{{ $t('booking.checkIn') }}</label>
              <input ref="checkInInput" type="text" class="form-control" :placeholder="$t('booking.selectDates')" readonly />
            </div>
            <div class="mb-2">
              <label class="form-label small">{{ $t('booking.checkOut') }}</label>
              <input ref="checkOutInput" type="text" class="form-control" :placeholder="$t('booking.selectDates')" readonly />
            </div>
            <div class="mb-2">
              <label class="form-label small">{{ $t('booking.guests') }}</label>
              <input type="number" min="1" :max="apartment.capacity" class="form-control" v-model="form.guests_count" />
              <div class="form-text">{{ $t('booking.maxGuests', { count: apartment.capacity }) }}</div>
            </div>
            <div class="mb-3">
              <label class="form-label small">{{ $t('booking.notes') }}</label>
              <textarea class="form-control" rows="2" v-model="form.notes" :placeholder="$t('booking.notesPlaceholder')"></textarea>
            </div>

            <div class="mb-3">
              <div v-if="priceLoading" class="text-muted small">
                <span class="spinner-border spinner-border-sm"></span>
              </div>
              <div v-else-if="price" class="border-top pt-2">
                <div class="d-flex justify-content-between">
                  <span>{{ $t('booking.nightsCount', { count: price.nights }) }}</span>
                  <span>{{ price.total_price }} {{ config.currencySymbol }}</span>
                </div>
                <div class="d-flex justify-content-between fw-bold fs-5 mt-1">
                  <span>{{ $t('booking.totalPrice') }}</span>
                  <span class="text-primary">{{ price.total_price }} {{ config.currencySymbol }}</span>
                </div>
              </div>
              <div v-else class="text-muted small">{{ $t('booking.selectDates') }}</div>
            </div>

            <button v-if="canBook" class="btn btn-primary w-100" :disabled="submitting || !price" @click="submitBooking">
              <span v-if="submitting" class="spinner-border spinner-border-sm me-1"></span>
              {{ $t('booking.submit') }}
            </button>
            <RouterLink v-else-if="!auth.isAuthenticated" :to="{ name: 'login', query: { next: route.fullPath } }" class="btn btn-primary w-100">
              {{ $t('booking.loginToBook') }}
            </RouterLink>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
