import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import PlanningView from './PlanningView.vue'

describe('PlanningView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders phases, availability, materials, and task templates', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          subjects: [
            { id: 'math', code: '数学一', name: '数学一', order: 1 },
            { id: 'cs', code: '408', name: '408', order: 2 },
            { id: 'english', code: '英语一', name: '英语一', order: 3 },
            { id: 'politics', code: '政治', name: '政治', order: 4 },
          ],
          phases: [
            {
              id: 'foundation',
              name: '基础期',
              start_date: '2026-07-15',
              end_date: '2026-08-31',
              description: '完成数学与 408 一轮',
              milestones: ['王道数据结构完成'],
              allow_new_tasks: true,
              order: 1,
              subject_ratios: [
                { subject_id: 'math', percentage: 40 },
                { subject_id: 'cs', percentage: 35 },
                { subject_id: 'english', percentage: 15 },
                { subject_id: 'politics', percentage: 10 },
              ],
            },
          ],
          availability_periods: [
            {
              id: 'summer',
              name: '暑假',
              start_date: '2026-07-15',
              end_date: '2026-08-31',
              weekly_target_minutes: 3300,
              order: 1,
              rules: Array.from({ length: 7 }, (_, weekday) => ({
                weekday,
                available_minutes: weekday < 5 ? 480 : 660,
              })),
            },
          ],
          availability_exceptions: [
            {
              id: 'leave',
              date: '2026-07-20',
              available_minutes: 0,
              reason: '请假',
            },
          ],
          materials: [
            {
              id: 'wangdao',
              subject_id: 'cs',
              name: '王道数据结构',
              material_type: 'textbook',
              source: '王道',
              description: '',
              active: true,
              order: 1,
            },
          ],
          task_templates: [
            {
              id: 'chapter-reading',
              subject_id: 'cs',
              material_id: 'wangdao',
              name: '王道章节学习',
              task_type: 'reading',
              default_est_minutes: 90,
              description: '阅读并完成章节例题',
              active: true,
              order: 1,
              phase_ids: ['foundation'],
            },
          ],
        }),
      }),
    )

    const wrapper = mount(PlanningView, {
      global: {
        stubs: {
          RouterLink: {
            template: '<a><slot /></a>',
          },
        },
      },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('基础期')
    expect(wrapper.text()).toContain('数学一 40%')
    expect(wrapper.text()).toContain('暑假')
    expect(wrapper.text()).toContain('请假')
    expect(wrapper.text()).toContain('王道数据结构')
    expect(wrapper.text()).toContain('王道章节学习')
  })
})
