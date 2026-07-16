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
})
