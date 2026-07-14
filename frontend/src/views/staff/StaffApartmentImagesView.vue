<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api, { extractError } from '@/api/client'
import { useToastStore } from '@/stores/toast'

const route = useRoute()
const toast = useToastStore()
const images = ref([])
const loading = ref(true)
const uploading = ref(false)
const dragover = ref(false)
const fileInput = ref(null)

async function load() {
  loading.value = true
  try {
    const { data } = await api.get(`/staff/apartments/${route.params.id}/images/`)
    images.value = data
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    loading.value = false
  }
}

async function upload(files) {
  if (!files.length) return
  uploading.value = true
  const fd = new FormData()
  for (const f of files) fd.append('images', f)
  try {
    const { data } = await api.post(`/staff/apartments/${route.params.id}/images/upload/`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    images.value = data.images
    toast.success('Uploaded successfully!')
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    uploading.value = false
  }
}

function onDrop(e) {
  dragover.value = false
  upload([...e.dataTransfer.files])
}
function onSelect(e) {
  upload([...e.target.files])
  e.target.value = ''
}

async function remove(img) {
  if (!confirm('Delete this image?')) return
  try {
    await api.delete(`/staff/apartments/${route.params.id}/images/${img.id}/`)
    images.value = images.value.filter((i) => i.id !== img.id)
    toast.success('Deleted!')
  } catch (e) {
    toast.error(extractError(e))
  }
}

async function makeMain(img) {
  // Reorder so this image is first (becomes main)
  const ids = [img.id, ...images.value.filter((i) => i.id !== img.id).map((i) => i.id)]
  try {
    await api.post(`/staff/apartments/${route.params.id}/images/reorder/`, { order: ids })
    await load()
  } catch (e) {
    toast.error(extractError(e))
  }
}

// ---- Drag & drop reordering ----
const dragIndex = ref(null)

function onDragStart(index) {
  dragIndex.value = index
}

function onDragEnter(index) {
  if (dragIndex.value === null || dragIndex.value === index) return
  const arr = images.value
  const [moved] = arr.splice(dragIndex.value, 1)
  arr.splice(index, 0, moved)
  dragIndex.value = index
}

async function onDragEnd() {
  if (dragIndex.value === null) return
  dragIndex.value = null
  const ids = images.value.map((i) => i.id)
  try {
    await api.post(`/staff/apartments/${route.params.id}/images/reorder/`, { order: ids })
    images.value.forEach((im, idx) => { im.is_main = idx === 0 })
    toast.success('Order updated!')
  } catch (e) {
    toast.error(extractError(e))
    await load()
  }
}

onMounted(load)
</script>

<template>
  <div class="container py-4">
    <RouterLink :to="{ name: 'staff-apartment-manage', params: { id: route.params.id } }" class="btn btn-link ps-0 mb-2"><i class="bi bi-arrow-left"></i> {{ $t('common.back') }}</RouterLink>
    <h1 class="mb-4">{{ $t('staff.manageImages') }}</h1>

    <div
      class="upload-zone mb-4"
      :class="{ dragover }"
      @click="fileInput.click()"
      @dragover.prevent="dragover = true"
      @dragleave.prevent="dragover = false"
      @drop.prevent="onDrop"
    >
      <input ref="fileInput" type="file" accept="image/*" multiple class="d-none" @change="onSelect" />
      <div v-if="uploading">
        <div class="spinner-border text-primary"></div>
      </div>
      <div v-else>
        <i class="bi bi-cloud-arrow-up fs-1 text-muted"></i>
        <p class="mb-0">{{ $t('staff.dropImages') }}</p>
      </div>
    </div>

    <div v-if="loading" class="text-center py-5"><div class="spinner-border text-primary"></div></div>
    <div v-else>
      <p class="text-muted small mb-2"><i class="bi bi-arrows-move"></i> {{ $t('staff.dragToReorder') }}</p>
      <div class="row g-3">
        <div
          v-for="(img, index) in images"
          :key="img.id"
          class="col-6 col-md-3"
          draggable="true"
          @dragstart="onDragStart(index)"
          @dragenter.prevent="onDragEnter(index)"
          @dragover.prevent
          @dragend="onDragEnd"
        >
          <div class="card h-100" :class="{ 'opacity-50': dragIndex === index }" style="cursor: move">
            <img :src="img.image" class="card-img-top" style="height: 160px; object-fit: cover" draggable="false" />
            <span v-if="img.is_main" class="badge bg-primary position-absolute top-0 start-0 m-2">Main</span>
            <div class="card-body p-2 d-flex gap-1">
              <button class="btn btn-sm btn-outline-primary flex-grow-1" @click="makeMain(img)" :disabled="img.is_main">
                <i class="bi bi-star"></i>
              </button>
              <button class="btn btn-sm btn-outline-danger" @click="remove(img)"><i class="bi bi-trash"></i></button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
