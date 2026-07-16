import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import HomeView from './HomeView.vue'

const PROFILE = {
  as_of: '2026-07-16',
  exam_date: '2026-12-26',
  days_to_exam: 163,
  overall_mastery: 42.5,
  overall_coverage: 0.31,
  subjects: [
    {
      subject_id: 'math',
      subject_name: '数学一',
      target_score: 120,
      full_score: 150,
      knowledge_point_total: 100,
      studied_points: 40,
      coverage: 0.4,
      mastery: 55.0,
      estimated_score: 82.5,
      studied_minutes: 1200,
      problem_count: 12,
      wrong_count: 8,
      weak_points: [
        {
          knowledge_point_id: 'kp-1',
          knowledge_point_name: '泰勒公式',
          mastery: 20.0,
          problem_count: 3,
          forgot_reviews: 2,
        },
      ],
    },
    {
      subject_id: 'english',
      subject_name: '英语一',
      target_score: null,
      full_score: null,
      knowledge_point_total: 0,
      studied_points: 0,
      coverage: 0,
      mastery: 0,
      estimated_score: null,
      studied_minutes: 0,
      problem_count: 0,
      wrong_count: 0,
      weak_points: [],
    },
  ],
}

const WEEKLY = {
  start_date: '2026-07-13',
  end_date: '2026-07-19',
  weeks: [
    {
      week_start: '2026-07-13',
      week_end: '2026-07-19',
      planned_minutes: 600,
      completed_minutes: 480,
      target_minutes: null,
      total_tasks: 10,
      completed_tasks: 8,
      execution_rate: 0.8,
    },
  ],
  total_planned_minutes: 600,
  total_completed_minutes: 480,
  overall_execution_rate: 0.8,
}

function stubFetch(): void {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/api/profile')) {
        return { ok: true, status: 200, json: async () => PROFILE }
      }
      if (url.includes('/api/stats/weekly')) {
        return { ok: true, status: 200, json: async () => WEEKLY }
      }
      return { ok: true, status: 200, json: async () => ({ status: 'ok' }) }
    }),
  )
}

describe('HomeView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders dashboard metrics and subject cards', async () => {
    stubFetch()
    const wrapper = mount(HomeView, {
      global: {
        stubs: {
          RouterLink: {
            template: '<a><slot /></a>',
          },
        },
      },
    })
    await flushPromises()

    const text = wrapper.text()
    expect(text).toContain('备考驾驶舱')
    expect(text).toContain('163 天')
    expect(text).toContain('42.5%')
    expect(text).toContain('80%')
    expect(text).toContain('83 / 120')

    const mathCard = wrapper.find('[data-testid="subject-card-数学一"]')
    expect(mathCard.exists()).toBe(true)
    expect(mathCard.text()).toContain('预估 82.5 / 目标 120')
    expect(mathCard.text()).toContain('覆盖 40/100')
    expect(mathCard.text()).toContain('泰勒公式')

    const englishCard = wrapper.find('[data-testid="subject-card-英语一"]')
    expect(englishCard.text()).toContain('未设目标')
  })
})
