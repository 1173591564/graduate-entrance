import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import TodayView from './TodayView.vue'

const plannedTask = {
  id: 'task-1',
  phase_name: '基础期',
  subject_name: '数学一',
  knowledge_point_name: '极限',
  material_name: '高等数学',
  title: '极限 · 章节学习',
  task_type: 'reading',
  planned_date: '2026-07-20',
  est_minutes: 60,
  status: 'planned',
  actual_minutes: null,
  done_at: null,
  carry_count: 0,
  order: 0,
}

describe('TodayView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders the daily summary and completes a task', async () => {
    let completed = false
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      if (String(_input).startsWith('/api/plan/ai-week')) {
        return { ok: false, status: 404, json: async () => ({}) }
      }
      if (init?.method === 'POST') {
        completed = true
        return {
          ok: true,
          status: 200,
          json: async () => ({
            ...plannedTask,
            status: 'completed',
            actual_minutes: 55,
            done_at: '2026-07-20T10:00:00Z',
          }),
        }
      }
      return {
        ok: true,
        status: 200,
        json: async () => ({
          date: '2026-07-20',
          planned_minutes: 60,
          completed_minutes: completed ? 55 : 0,
          remaining_minutes: completed ? 0 : 60,
          tasks: [
            completed
              ? {
                  ...plannedTask,
                  status: 'completed',
                  actual_minutes: 55,
                  done_at: '2026-07-20T10:00:00Z',
                }
              : plannedTask,
          ],
        }),
      }
    })
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mount(TodayView)
    await flushPromises()

    expect(wrapper.text()).toContain('极限 · 章节学习')
    expect(wrapper.text()).toContain('剩余任务')
    expect(wrapper.text()).toContain('1 小时')

    await wrapper.get('input[type="number"]').setValue(55)
    await wrapper.get('.complete-button').trigger('click')
    await flushPromises()

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/tasks/task-1/done',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ actual_minutes: 55 }),
      }),
    )
    expect(wrapper.text()).toContain('已完成 55 分钟')
    expect(wrapper.text()).toContain('极限 · 章节学习 已打卡')
  })

  it('reschedules overdue tasks and marks leave days', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input).startsWith('/api/plan/ai-week')) {
        return { ok: false, status: 404, json: async () => ({}) }
      }
      if (String(input) === '/api/plan/reschedule' && init?.method === 'POST') {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            start_date: '2026-07-20',
            end_date: '2026-11-30',
            carried_over: 3,
            warnings: [],
          }),
        }
      }
      return {
        ok: true,
        status: 200,
        json: async () => ({
          date: '2026-07-20',
          planned_minutes: 60,
          completed_minutes: 0,
          remaining_minutes: 60,
          tasks: [plannedTask],
        }),
      }
    })
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mount(TodayView)
    await flushPromises()

    await wrapper.get('.reschedule-button').trigger('click')
    await flushPromises()

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/plan/reschedule',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ start_date: '2026-07-20', leave_dates: [] }),
      }),
    )
    expect(wrapper.text()).toContain('已从 2026-07-20 重排至 2026-11-30，顺延 3 项任务')

    await wrapper.get('.leave-button').trigger('click')
    await flushPromises()

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/plan/reschedule',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          start_date: '2026-07-20',
          leave_dates: ['2026-07-20'],
        }),
      }),
    )
    expect(wrapper.text()).toContain('2026-07-20 已请假，顺延 3 项任务并重排至 2026-11-30')
  })

  it('generates an AI week plan and shows the advice card', async () => {
    const advice = {
      week_start: '2026-07-20',
      summary: '先补数学薄弱点，再推进 408。',
      daily_focus: [
        { date: '2026-07-20', focus: '上午攻克重要极限' },
        { date: '2026-07-21', focus: '408 数据结构复习' },
      ],
      review_suggestions: ['每天 20 分钟复盘错题'],
      model: 'gpt-test',
      created_at: '2026-07-16T08:00:00Z',
    }
    let generated = false
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.startsWith('/api/plan/ai-week') && init?.method === 'POST') {
        generated = true
        return {
          ok: true,
          status: 200,
          json: async () => ({
            plan: {
              start_date: '2026-07-20',
              end_date: '2026-07-26',
              persisted: true,
              tasks: [],
              days: [],
              warnings: [],
            },
            advice,
          }),
        }
      }
      if (url.startsWith('/api/plan/ai-week')) {
        return generated
          ? { ok: true, status: 200, json: async () => advice }
          : { ok: false, status: 404, json: async () => ({}) }
      }
      return {
        ok: true,
        status: 200,
        json: async () => ({
          date: '2026-07-20',
          planned_minutes: 60,
          completed_minutes: 0,
          remaining_minutes: 60,
          tasks: [plannedTask],
        }),
      }
    })
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mount(TodayView)
    await flushPromises()

    expect(wrapper.find('.ai-advice-card').exists()).toBe(false)

    await wrapper.get('.ai-week-button').trigger('click')
    await flushPromises()

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/plan/ai-week',
      expect.objectContaining({ method: 'POST' }),
    )
    expect(wrapper.find('.ai-advice-card').exists()).toBe(true)
    expect(wrapper.text()).toContain('先补数学薄弱点，再推进 408。')
    expect(wrapper.text()).toContain('今日重点：上午攻克重要极限')
    expect(wrapper.text()).toContain('已生成 2026-07-20 ~ 2026-07-26 计划并排入日历')
  })
})
