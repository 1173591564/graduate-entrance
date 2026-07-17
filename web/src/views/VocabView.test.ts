import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import VocabView from './VocabView.vue'

const DUE_ID = '11111111-1111-1111-1111-111111111111'
const NEW_ID = '22222222-2222-2222-2222-222222222222'

function todayResponse() {
  return {
    date: '2026-07-20',
    due_words: [
      {
        id: DUE_ID,
        word: 'abandon',
        meaning: 'vt. 放弃',
        book_page: 1,
        ef: 2.5,
        interval_days: 1,
        due_date: '2026-07-20',
        reps: 1,
      },
    ],
    new_words: [
      {
        id: NEW_ID,
        word: 'radiate',
        meaning: 'vt. 散发',
        book_page: 1,
        ef: 2.5,
        interval_days: 0,
        due_date: null,
        reps: 0,
      },
    ],
    due_count: 1,
    learned_count: 5,
    total_count: 6547,
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

describe('VocabView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows the due word first and reveals its meaning', async () => {
    stubFetch({
      'GET /api/vocab/today?new_limit=50': () => todayResponse(),
    })
    const wrapper = mount(VocabView)
    await flushPromises()

    const card = wrapper.get('[data-testid="word-card"]')
    expect(card.text()).toContain('abandon')
    expect(card.text()).not.toContain('vt. 放弃')

    await card.get('button.reveal-button').trigger('click')
    expect(wrapper.get('[data-testid="meaning"]').text()).toContain('vt. 放弃')
  })

  it('grades a word and advances to the next one', async () => {
    stubFetch({
      'GET /api/vocab/today?new_limit=50': () => todayResponse(),
      [`POST /api/vocab/${DUE_ID}/grade`]: () => ({
        word: { ...todayResponse().due_words[0], reps: 2, due_date: '2026-07-26' },
        grade: 'mastered',
        due_date: '2026-07-26',
      }),
    })
    const wrapper = mount(VocabView)
    await flushPromises()

    await wrapper.get('button.reveal-button').trigger('click')
    await wrapper.get('button.grade-button.mastered').trigger('click')
    await flushPromises()

    const card = wrapper.get('[data-testid="word-card"]')
    expect(card.text()).toContain('radiate')
    expect(card.text()).toContain('新词')
  })
})
