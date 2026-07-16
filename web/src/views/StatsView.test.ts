import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import StatsView from './StatsView.vue'

const statsPayload = {
  start_date: '2026-07-20',
  end_date: '2026-08-02',
  weeks: [
    {
      week_start: '2026-07-20',
      week_end: '2026-07-26',
      planned_minutes: 240,
      completed_minutes: 45,
      target_minutes: 3000,
      total_tasks: 4,
      completed_tasks: 1,
      execution_rate: 0.1875,
    },
    {
      week_start: '2026-07-27',
      week_end: '2026-08-02',
      planned_minutes: 0,
      completed_minutes: 0,
      target_minutes: null,
      total_tasks: 0,
      completed_tasks: 0,
      execution_rate: 0,
    },
  ],
  total_planned_minutes: 240,
  total_completed_minutes: 45,
  overall_execution_rate: 0.1875,
}

describe('StatsView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders weekly stats with execution rates and target warnings', async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => statsPayload,
    }))
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mount(StatsView)
    await flushPromises()

    expect(fetchMock).toHaveBeenCalledWith('/api/stats/weekly', expect.anything())
    expect(wrapper.text()).toContain('2026-07-20 ~ 2026-08-02')
    expect(wrapper.text()).toContain('执行率 18.8%')
    expect(wrapper.text()).toContain('任务 1 / 4')
    expect(wrapper.text()).toContain('周目标 50 小时')
    expect(wrapper.text()).toContain('低于周目标')
    expect(wrapper.findAll('.week-card')).toHaveLength(2)
  })

  it('reloads stats for an explicit date range', async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => statsPayload,
    }))
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mount(StatsView)
    await flushPromises()

    const inputs = wrapper.findAll('input[type="date"]')
    await inputs[0].setValue('2026-07-20')
    await inputs[1].setValue('2026-08-02')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/stats/weekly?start=2026-07-20&end=2026-08-02',
      expect.anything(),
    )
  })

  it('shows an error message when loading fails', async () => {
    const fetchMock = vi.fn(async () => ({
      ok: false,
      status: 500,
      json: async () => ({}),
    }))
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mount(StatsView)
    await flushPromises()

    expect(wrapper.text()).toContain('周统计加载失败')
  })
})
