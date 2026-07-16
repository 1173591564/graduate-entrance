import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import EssayView from './EssayView.vue'

const MATERIAL_ID = '11111111-1111-1111-1111-111111111111'

function material(overrides: Record<string, unknown> = {}) {
  return {
    id: MATERIAL_ID,
    title: '环保话题金句',
    category: 'sentence',
    topic: 'environment',
    content_md: 'Only by acting now can we protect the environment.',
    translation_md: '只有现在行动才能保护环境。',
    source: '范文 2024',
    due_date: '2026-07-16',
    interval_days: 0,
    recite_count: 0,
    created_at: '2026-07-16T00:00:00Z',
    updated_at: '2026-07-16T00:00:00Z',
    ...overrides,
  }
}

type FetchCall = { url: string; init?: RequestInit }

function stubFetch(handler: (call: FetchCall) => unknown) {
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    const body = handler({ url, init })
    return {
      ok: true,
      status: 200,
      json: async () => body,
    }
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

describe('EssayView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders due panel and material list', async () => {
    stubFetch(({ url }) => {
      if (url.includes('due_only=true')) {
        return { total: 1, materials: [material()] }
      }
      return {
        total: 2,
        materials: [
          material(),
          material({
            id: '22222222-2222-2222-2222-222222222222',
            title: '科技模板',
            category: 'template',
            topic: 'technology',
            due_date: '2026-07-20',
          }),
        ],
      }
    })

    const wrapper = mount(EssayView)
    await flushPromises()

    expect(wrapper.text()).toContain('今日待背诵（1）')
    expect(wrapper.findAll('.material-card')).toHaveLength(2)
    expect(wrapper.text()).toContain('环保话题金句')
    expect(wrapper.text()).toContain('科技模板')
    expect(wrapper.text()).toContain('模板')
  })

  it('submits a new material and reloads', async () => {
    const calls: FetchCall[] = []
    stubFetch((call) => {
      calls.push(call)
      if (call.init?.method === 'POST') {
        return material()
      }
      return { total: 0, materials: [] }
    })

    const wrapper = mount(EssayView)
    await flushPromises()

    await wrapper.find('.page-header button').trigger('click')
    await wrapper.find('input[type="text"]').setValue('环保话题金句')
    await wrapper.find('textarea').setValue('Only by acting now.')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    const post = calls.find((call) => call.init?.method === 'POST')
    expect(post).toBeDefined()
    expect(post?.url).toContain('/api/essay/materials')
    expect(JSON.parse(String(post?.init?.body))).toMatchObject({
      title: '环保话题金句',
      content_md: 'Only by acting now.',
    })
    expect(wrapper.text()).toContain('素材已添加')
  })

  it('recites a due material', async () => {
    const calls: FetchCall[] = []
    stubFetch((call) => {
      calls.push(call)
      if (call.url.includes('/recite')) {
        return {
          material: material({ due_date: '2026-07-18', interval_days: 2, recite_count: 1 }),
          next_due: '2026-07-18',
        }
      }
      if (call.url.includes('due_only=true') && calls.length <= 2) {
        return { total: 1, materials: [material()] }
      }
      if (call.url.includes('due_only=true')) {
        return { total: 0, materials: [] }
      }
      return { total: 1, materials: [material()] }
    })

    const wrapper = mount(EssayView)
    await flushPromises()

    await wrapper.find('.due-card button.primary').trigger('click')
    await flushPromises()

    const recite = calls.find((call) => call.url.includes('/recite'))
    expect(recite).toBeDefined()
    expect(JSON.parse(String(recite?.init?.body))).toEqual({ result: 'remembered' })
    expect(wrapper.text()).toContain('下次背诵 2026-07-18')
  })

  it('shows an error when loading fails', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: false,
        status: 500,
        json: async () => ({}),
      })),
    )

    const wrapper = mount(EssayView)
    await flushPromises()

    expect(wrapper.text()).toContain('加载素材失败')
  })
})
