import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import RecitationView from './RecitationView.vue'

const ITEM_ID = '11111111-1111-1111-1111-111111111111'

function item() {
  return {
    id: ITEM_ID,
    subject: 'politics',
    category: '马原·辩证法',
    title: '对立统一规律',
    content_md: '矛盾是事物发展的根本动力。',
    recite_count: 2,
    last_recited_on: null,
    recited_today: false,
  }
}

function listResponse() {
  return {
    groups: [{ category: '马原·辩证法', items: [item()] }],
    stats: { total_count: 1, recited_today: 0, never_recited: 0 },
  }
}

function todayResponse() {
  return {
    date: '2026-07-17',
    item: item(),
    stats: listResponse().stats,
  }
}

function stubFetch(handlers: Record<string, (init?: RequestInit) => unknown>) {
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    const method = init?.method ?? 'GET'
    const key = `${method} ${url}`
    const handler = handlers[key]
    if (!handler) {
      throw new Error(`Unexpected request: ${key}`)
    }
    return {
      ok: true,
      status: 200,
      json: async () => handler(init),
    }
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

describe('RecitationView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows today pick with content and count', async () => {
    stubFetch({
      'GET /api/recitations?subject=politics': () => listResponse(),
      'GET /api/recitations/today?subject=politics': () => todayResponse(),
    })
    const wrapper = mount(RecitationView)
    await flushPromises()

    const card = wrapper.get('[data-testid="today-card"]')
    expect(card.text()).toContain('对立统一规律')
    expect(card.text()).toContain('矛盾是事物发展的根本动力。')
    expect(card.text()).toContain('已背 2 次')
    expect(card.text()).toContain('背完打卡')
  })

  it('recites today item and reloads', async () => {
    const fetchMock = stubFetch({
      'GET /api/recitations?subject=politics': () => listResponse(),
      'GET /api/recitations/today?subject=politics': () => todayResponse(),
      [`POST /api/recitations/${ITEM_ID}/recite`]: () => ({
        item: { ...item(), recite_count: 3, recited_today: true },
      }),
    })
    const wrapper = mount(RecitationView)
    await flushPromises()

    await wrapper.get('[data-testid="today-card"] button').trigger('click')
    await flushPromises()

    const reciteCall = fetchMock.mock.calls.find(
      ([url, init]) =>
        url === `/api/recitations/${ITEM_ID}/recite` && init?.method === 'POST',
    )
    expect(reciteCall).toBeTruthy()
    expect(JSON.parse((reciteCall?.[1] as RequestInit).body as string)).toEqual({
      undo: false,
    })
  })
})
