import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { usePaginatedList } from '@/composables/usePaginatedList'

describe('usePaginatedList', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('loads paginated results and derives page metadata', async () => {
    const fetcher = vi.fn().mockResolvedValue({
      data: { results: [{ id: 1 }, { id: 2 }], count: 30, next: 'x', previous: null },
    })
    const list = usePaginatedList(fetcher, { pageSize: 12 })

    await list.load()

    expect(fetcher).toHaveBeenCalledWith({ page: 1, page_size: 12 })
    expect(list.items.value).toHaveLength(2)
    expect(list.count.value).toBe(30)
    expect(list.totalPages.value).toBe(3)
    expect(list.hasNext.value).toBe(true)
    expect(list.hasPrev.value).toBe(false)
  })

  it('advances to the next page only when available', async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce({ data: { results: [{ id: 1 }], count: 24, next: 'x', previous: null } })
      .mockResolvedValueOnce({ data: { results: [{ id: 2 }], count: 24, next: null, previous: 'y' } })
    const list = usePaginatedList(fetcher)

    await list.load()
    await list.nextPage()

    expect(list.page.value).toBe(2)
    expect(fetcher).toHaveBeenLastCalledWith({ page: 2, page_size: 12 })
    expect(list.hasNext.value).toBe(false)
  })

  it('handles non-paginated array responses', async () => {
    const fetcher = vi.fn().mockResolvedValue({ data: [{ id: 1 }, { id: 2 }, { id: 3 }] })
    const list = usePaginatedList(fetcher)

    await list.load()

    expect(list.items.value).toHaveLength(3)
    expect(list.count.value).toBe(3)
    expect(list.hasNext.value).toBe(false)
  })

  it('merges extra params into the request', async () => {
    const fetcher = vi.fn().mockResolvedValue({ data: { results: [], count: 0, next: null, previous: null } })
    const list = usePaginatedList(fetcher)

    await list.load({ status: 'CONFIRMED' })

    expect(fetcher).toHaveBeenCalledWith({ page: 1, page_size: 12, status: 'CONFIRMED' })
  })
})
