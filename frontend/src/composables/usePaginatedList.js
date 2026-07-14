import { ref, computed } from 'vue'
import { extractError } from '@/api/client'
import { useToastStore } from '@/stores/toast'

/**
 * Reusable helper for DRF page-number paginated list endpoints.
 *
 * @param {(params: object) => Promise} fetcher - receives query params (incl. `page`)
 *   and returns an axios response promise.
 * @param {object} [options]
 * @param {number} [options.pageSize=12] - page size sent to the API.
 * @param {boolean} [options.showErrors=true] - toast API errors automatically.
 */
export function usePaginatedList(fetcher, options = {}) {
  const { pageSize = 12, showErrors = true } = options
  const toast = useToastStore()

  const items = ref([])
  const count = ref(0)
  const page = ref(1)
  const loading = ref(false)
  const hasNext = ref(false)
  const hasPrev = ref(false)

  const totalPages = computed(() =>
    count.value ? Math.max(1, Math.ceil(count.value / pageSize)) : 1
  )

  async function load(extraParams = {}) {
    loading.value = true
    try {
      const params = { page: page.value, page_size: pageSize, ...extraParams }
      const { data } = await fetcher(params)
      if (Array.isArray(data)) {
        // Non-paginated fallback.
        items.value = data
        count.value = data.length
        hasNext.value = false
        hasPrev.value = false
      } else {
        items.value = data.results || []
        count.value = data.count || 0
        hasNext.value = !!data.next
        hasPrev.value = !!data.previous
      }
    } catch (e) {
      if (showErrors) toast.error(extractError(e))
      throw e
    } finally {
      loading.value = false
    }
  }

  async function goToPage(newPage, extraParams = {}) {
    if (newPage < 1) return
    page.value = newPage
    await load(extraParams)
  }

  function nextPage(extraParams = {}) {
    if (hasNext.value) return goToPage(page.value + 1, extraParams)
  }

  function prevPage(extraParams = {}) {
    if (hasPrev.value) return goToPage(page.value - 1, extraParams)
  }

  function reset() {
    page.value = 1
  }

  return {
    items,
    count,
    page,
    loading,
    hasNext,
    hasPrev,
    totalPages,
    load,
    goToPage,
    nextPage,
    prevPage,
    reset,
  }
}
