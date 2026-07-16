import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import InsightsView from './InsightsView.vue'

const POINT_A = '11111111-1111-1111-1111-111111111111'
const POINT_B = '22222222-2222-2222-2222-222222222222'
const POINT_C = '33333333-3333-3333-3333-333333333333'
const SUBJECT_ID = '44444444-4444-4444-4444-444444444444'

function insights() {
  return {
    as_of: '2026-07-16',
    total_problems: 5,
    confirmed_problems: 4,
    knowledge_points: [
      {
        knowledge_point_id: POINT_A,
        knowledge_point_name: '重要极限',
        problem_count: 3,
        weighted_errors: 2.1,
        forgot_reviews: 2,
        total_reviews: 4,
        weakness_score: 3.15,
      },
      {
        knowledge_point_id: POINT_B,
        knowledge_point_name: '泰勒公式',
        problem_count: 2,
        weighted_errors: 1.2,
        forgot_reviews: 0,
        total_reviews: 2,
        weakness_score: 1.2,
      },
      {
        knowledge_point_id: POINT_C,
        knowledge_point_name: '中值定理',
        problem_count: 1,
        weighted_errors: 0.5,
        forgot_reviews: 0,
        total_reviews: 0,
        weakness_score: 0.5,
      },
    ],
    causes: [
      { cause: 'concept', count: 3 },
      { cause: 'calculation', count: 1 },
    ],
    subjects: [
      {
        subject_id: SUBJECT_ID,
        subject_name: '数学一',
        problem_count: 5,
        wrong_count: 4,
      },
    ],
    weekly_trend: Array.from({ length: 8 }, (_, index) => ({
      week_start: `2026-0${index < 4 ? 6 : 7}-0${(index % 4) + 1}`,
      new_problems: index,
      reviews: index * 2,
      forgot: index > 4 ? 1 : 0,
      vague: 0,
      mastered: index,
    })),
  }
}

function stubFetch(body: unknown) {
  const fetchMock = vi.fn(async () => ({
    ok: true,
    status: 200,
    json: async () => body,
  }))
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

describe('InsightsView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders summary, radar, causes, and trend', async () => {
    stubFetch(insights())

    const wrapper = mount(InsightsView)
    await flushPromises()

    expect(wrapper.text()).toContain('弱点雷达')
    expect(wrapper.find('.radar-chart').exists()).toBe(true)
    expect(wrapper.findAll('.weakness-list li')).toHaveLength(3)
    expect(wrapper.text()).toContain('重要极限')
    expect(wrapper.text()).toContain('概念不清')
    expect(wrapper.text()).toContain('计算失误')
    expect(wrapper.text()).toContain('数学一')
    expect(wrapper.findAll('.trend-column')).toHaveLength(8)
  })

  it('hides radar when fewer than three knowledge points', async () => {
    const data = insights()
    data.knowledge_points = data.knowledge_points.slice(0, 2)
    stubFetch(data)

    const wrapper = mount(InsightsView)
    await flushPromises()

    expect(wrapper.find('.radar-chart').exists()).toBe(false)
    expect(wrapper.text()).toContain('知识点数据不足')
  })

  it('shows an error message when loading fails', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: false,
        status: 500,
        json: async () => ({}),
      })),
    )

    const wrapper = mount(InsightsView)
    await flushPromises()

    expect(wrapper.text()).toContain('错因统计加载失败')
  })
})
