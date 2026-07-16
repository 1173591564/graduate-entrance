import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import ReviewsView from './ReviewsView.vue'

const POINT_A = '11111111-1111-1111-1111-111111111111'
const PROBLEM_ID = '33333333-3333-3333-3333-333333333333'
const SUBJECT_ID = '44444444-4444-4444-4444-444444444444'

function dueProblem() {
  return {
    id: PROBLEM_ID,
    subject_id: SUBJECT_ID,
    subject_name: '数学一',
    content_md: '求 lim sin x / x',
    images: [],
    source_ref: '真题 2020-3',
    kind: 'wrong',
    my_answer_md: '',
    cause: '',
    note: '',
    status: 'draft',
    due_date: '2026-07-16',
    reps: 0,
    confirmed_at: null,
    created_at: '2026-07-16T01:00:00Z',
    knowledge_points: [
      {
        knowledge_point_id: POINT_A,
        knowledge_point_name: '重要极限',
        role: 'primary',
        weight: 1,
      },
    ],
    solutions: [],
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
    const body = handler(init)
    return {
      ok: true,
      status: 200,
      json: async () => body,
    }
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

describe('ReviewsView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders the due deck', async () => {
    stubFetch({
      'GET /api/problems/reviews/due': () => ({
        total: 1,
        as_of: '2026-07-16',
        problems: [dueProblem()],
      }),
    })

    const wrapper = mount(ReviewsView)
    await flushPromises()

    expect(wrapper.text()).toContain('到期 1')
    expect(wrapper.text()).toContain('错题 · 数学一')
    expect(wrapper.findAll('.review-card')).toHaveLength(1)
    expect(wrapper.findAll('.grade-button')).toHaveLength(3)
  })

  it('shows an empty state when nothing is due', async () => {
    stubFetch({
      'GET /api/problems/reviews/due': () => ({
        total: 0,
        as_of: '2026-07-16',
        problems: [],
      }),
    })

    const wrapper = mount(ReviewsView)
    await flushPromises()

    expect(wrapper.text()).toContain('今天没有到期复习卡片')
  })

  it('grades a card and removes it from the deck', async () => {
    let reviewBody: Record<string, unknown> | null = null
    stubFetch({
      'GET /api/problems/reviews/due': () => ({
        total: 1,
        as_of: '2026-07-16',
        problems: [dueProblem()],
      }),
      [`POST /api/problems/${PROBLEM_ID}/review`]: (init) => {
        reviewBody = JSON.parse(String(init?.body)) as Record<string, unknown>
        return {
          problem: { ...dueProblem(), reps: 1, due_date: '2026-07-17' },
          grade: 'mastered',
          ef: 2.6,
          interval_days: 1,
          reps: 1,
          due_date: '2026-07-17',
        }
      },
    })

    const wrapper = mount(ReviewsView)
    await flushPromises()

    await wrapper.get('.grade-button.mastered').trigger('click')
    await flushPromises()

    expect(reviewBody).toMatchObject({ grade: 'mastered' })
    expect(wrapper.text()).toContain('下次复习 2026-07-17')
    expect(wrapper.text()).toContain('今天没有到期复习卡片')
  })

  it('shows an error message when loading fails', async () => {
    const fetchMock = vi.fn(async () => ({
      ok: false,
      status: 500,
      json: async () => ({}),
    }))
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mount(ReviewsView)
    await flushPromises()

    expect(wrapper.text()).toContain('到期复习卡片加载失败')
  })
})
