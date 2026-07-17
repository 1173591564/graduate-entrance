import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import PapersView from './PapersView.vue'

const READING_ID = '11111111-1111-1111-1111-111111111111'
const UNREAD_ID = '22222222-2222-2222-2222-222222222222'

function listResponse() {
  return {
    groups: [
      {
        category: 'RAG',
        papers: [
          {
            id: READING_ID,
            rel_path: 'RAG/survey.pdf',
            title: 'RAG Survey',
            category: 'RAG',
            size_bytes: 1200,
            status: 'reading',
            has_file: true,
            started_on: '2026-07-20',
            finished_on: null,
          },
          {
            id: UNREAD_ID,
            rel_path: 'RAG/self-rag.pdf',
            title: 'Self-RAG',
            category: 'RAG',
            size_bytes: 800,
            status: 'unread',
            has_file: false,
            started_on: null,
            finished_on: null,
          },
        ],
      },
    ],
    stats: {
      total_count: 2,
      unread_count: 1,
      reading_count: 1,
      done_count: 0,
    },
  }
}

function todayResponse() {
  return {
    date: '2026-07-20',
    paper: listResponse().groups[0].papers[0],
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

describe('PapersView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows today pick and reading status', async () => {
    stubFetch({
      'GET /api/papers': () => listResponse(),
      'GET /api/papers/today': () => todayResponse(),
    })
    const wrapper = mount(PapersView)
    await flushPromises()

    const card = wrapper.get('[data-testid="today-card"]')
    expect(card.text()).toContain('RAG Survey')
    expect(card.text()).toContain('在读')
    expect(wrapper.text()).toContain('Self-RAG')
  })

  it('marks a paper done and reloads', async () => {
    const fetchMock = stubFetch({
      'GET /api/papers': () => listResponse(),
      'GET /api/papers/today': () => todayResponse(),
      [`POST /api/papers/${READING_ID}/status`]: () => ({
        paper: { ...listResponse().groups[0].papers[0], status: 'done' },
      }),
    })
    const wrapper = mount(PapersView)
    await flushPromises()

    await wrapper.get('[data-testid="today-card"] button').trigger('click')
    await flushPromises()

    const statusCall = fetchMock.mock.calls.find(
      ([url, init]) =>
        url === `/api/papers/${READING_ID}/status` && init?.method === 'POST',
    )
    expect(statusCall).toBeTruthy()
    expect(JSON.parse((statusCall?.[1] as RequestInit).body as string)).toEqual({
      status: 'done',
    })
  })
})
