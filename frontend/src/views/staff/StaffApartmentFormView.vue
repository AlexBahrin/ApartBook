<script setup>
import { reactive, ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api, { extractError } from '@/api/client'
import { useToastStore } from '@/stores/toast'

const route = useRoute()
const router = useRouter()
const toast = useToastStore()

const isEdit = computed(() => !!route.params.id)
const backRoute = computed(() => (isEdit.value
  ? { name: 'staff-apartment-manage', params: { id: route.params.id } }
  : { name: 'staff-apartments' }))
const loading = ref(false)
const saving = ref(false)
const errors = ref({})

const form = reactive({
  title: '',
  description: '',
  address: '',
  city: '',
  country: '',
  capacity: 1,
  bedrooms: 1,
  bathrooms: 1,
  amenities: '',
  pricing_type: 'APARTMENT',
  base_price_per_night: '',
  price_per_guest: {},
  is_active: true,
})

// Guest pricing rows
const guestPrices = ref([{ guests: 1, price: '' }])

async function load() {
  if (!isEdit.value) return
  loading.value = true
  try {
    const { data } = await api.get(`/staff/apartments/${route.params.id}/`)
    Object.assign(form, {
      title: data.title,
      description: data.description,
      address: data.address,
      city: data.city,
      country: data.country,
      capacity: data.capacity,
      bedrooms: data.bedrooms,
      bathrooms: data.bathrooms,
      amenities: (data.amenities || []).join(', '),
      pricing_type: data.pricing_type,
      base_price_per_night: data.base_price_per_night,
      price_per_guest: data.price_per_guest || {},
      is_active: data.is_active,
    })
    if (data.pricing_type === 'GUEST' && data.price_per_guest) {
      guestPrices.value = Object.entries(data.price_per_guest).map(([g, p]) => ({ guests: Number(g), price: p }))
      if (!guestPrices.value.length) guestPrices.value = [{ guests: 1, price: '' }]
    }
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    loading.value = false
  }
}

function addGuestRow() {
  guestPrices.value.push({ guests: guestPrices.value.length + 1, price: '' })
}
function removeGuestRow(i) {
  guestPrices.value.splice(i, 1)
}

async function save() {
  saving.value = true
  errors.value = {}
  const payload = {
    ...form,
    capacity: Number(form.capacity),
    bedrooms: Number(form.bedrooms),
    bathrooms: Number(form.bathrooms),
    amenities: form.amenities ? form.amenities.split(',').map((s) => s.trim()).filter(Boolean) : [],
  }
  if (form.pricing_type === 'GUEST') {
    const map = {}
    for (const row of guestPrices.value) {
      if (row.guests && row.price !== '') map[row.guests] = row.price
    }
    payload.price_per_guest = map
  } else {
    payload.base_price_per_night = form.base_price_per_night
  }

  try {
    if (isEdit.value) {
      await api.put(`/staff/apartments/${route.params.id}/`, payload)
    } else {
      await api.post('/staff/apartments/', payload)
    }
    toast.success('Saved successfully!')
    router.push({ name: 'staff-apartments' })
  } catch (e) {
    errors.value = e.response?.data || {}
    toast.error(extractError(e))
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="container py-4">
    <RouterLink :to="backRoute" class="btn btn-link ps-0 mb-2"><i class="bi bi-arrow-left"></i> {{ $t('common.back') }}</RouterLink>
    <h1 class="mb-4">{{ isEdit ? $t('staff.editApartment') : $t('staff.newApartment') }}</h1>

    <div v-if="loading" class="text-center py-5"><div class="spinner-border text-primary"></div></div>

    <form v-else @submit.prevent="save" class="card shadow-sm">
      <div class="card-body">
        <div class="mb-3">
          <label class="form-label">{{ $t('staff.title') }}</label>
          <input type="text" class="form-control" :class="{ 'is-invalid': errors.title }" v-model="form.title" required />
          <div class="invalid-feedback">{{ errors.title?.[0] }}</div>
        </div>
        <div class="mb-3">
          <label class="form-label">{{ $t('staff.description') }}</label>
          <textarea class="form-control" rows="4" v-model="form.description" required></textarea>
        </div>
        <div class="row">
          <div class="col-md-6 mb-3">
            <label class="form-label">{{ $t('staff.address') }}</label>
            <input type="text" class="form-control" v-model="form.address" required />
          </div>
          <div class="col-md-3 mb-3">
            <label class="form-label">{{ $t('apartments.city') }}</label>
            <input type="text" class="form-control" v-model="form.city" />
          </div>
          <div class="col-md-3 mb-3">
            <label class="form-label">{{ $t('apartments.country') }}</label>
            <input type="text" class="form-control" v-model="form.country" />
          </div>
        </div>
        <div class="row">
          <div class="col-md-4 mb-3">
            <label class="form-label">{{ $t('staff.capacity') }}</label>
            <input type="number" min="1" class="form-control" v-model="form.capacity" required />
          </div>
          <div class="col-md-4 mb-3">
            <label class="form-label">{{ $t('staff.bedrooms') }}</label>
            <input type="number" min="0" class="form-control" v-model="form.bedrooms" />
          </div>
          <div class="col-md-4 mb-3">
            <label class="form-label">{{ $t('staff.bathrooms') }}</label>
            <input type="number" min="0" class="form-control" v-model="form.bathrooms" />
          </div>
        </div>
        <div class="mb-3">
          <label class="form-label">{{ $t('staff.amenities') }}</label>
          <textarea class="form-control" rows="2" v-model="form.amenities" placeholder="WiFi, Air Conditioning, Parking"></textarea>
        </div>

        <div class="mb-3">
          <label class="form-label d-block">{{ $t('staff.pricingType') }}</label>
          <div class="form-check form-check-inline">
            <input class="form-check-input" type="radio" value="APARTMENT" v-model="form.pricing_type" id="pt-apt" />
            <label class="form-check-label" for="pt-apt">{{ $t('staff.perApartment') }}</label>
          </div>
          <div class="form-check form-check-inline">
            <input class="form-check-input" type="radio" value="GUEST" v-model="form.pricing_type" id="pt-guest" />
            <label class="form-check-label" for="pt-guest">{{ $t('staff.perGuest') }}</label>
          </div>
        </div>

        <div v-if="form.pricing_type === 'APARTMENT'" class="mb-3">
          <label class="form-label">{{ $t('staff.basePrice') }}</label>
          <input type="number" min="0" step="0.01" class="form-control" :class="{ 'is-invalid': errors.base_price_per_night }" v-model="form.base_price_per_night" />
          <div class="invalid-feedback">{{ errors.base_price_per_night?.[0] }}</div>
        </div>

        <div v-else class="mb-3">
          <label class="form-label">{{ $t('staff.perGuest') }}</label>
          <div v-for="(row, i) in guestPrices" :key="i" class="input-group mb-2">
            <span class="input-group-text">{{ $t('common.guests') }}</span>
            <input type="number" min="1" class="form-control" v-model.number="row.guests" style="max-width: 90px" />
            <span class="input-group-text">→</span>
            <input type="number" min="0" step="0.01" class="form-control" v-model="row.price" placeholder="price" />
            <button type="button" class="btn btn-outline-danger" @click="removeGuestRow(i)"><i class="bi bi-x"></i></button>
          </div>
          <button type="button" class="btn btn-sm btn-outline-secondary" @click="addGuestRow"><i class="bi bi-plus"></i></button>
        </div>

        <div class="form-check mb-3">
          <input class="form-check-input" type="checkbox" v-model="form.is_active" id="is-active" />
          <label class="form-check-label" for="is-active">{{ $t('staff.isActive') }}</label>
        </div>

        <button type="submit" class="btn btn-primary" :disabled="saving">
          <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>
          {{ $t('common.save') }}
        </button>
      </div>
    </form>
  </div>
</template>
