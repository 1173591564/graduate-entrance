import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import RetroView from './RetroView.vue'

const CONTEXT = {
  week_start: '2026-07-13',
  week_end: '2026-07-19',
  planned_minutes: 600,
  completed_minutes: 480,
  total_tasks: 10,
  completed_tasks: 8,
  execution_rate: 0.8,
  days_to_exam: 160,
  subjects: [],
  weak_points: ['等价无穷小（3 题，遗忘 2/4）'],
}

function stubFetch(): ReturnType<typeof vi.fn> {
  const fetchMock = vi.fn().mockImplementation(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.includes('/api/retro/messages')) {
        const body = JSON.parse(String(init?.body)) as { content: string }
        return {
          ok: true,
          status: 200,
          json: async () => ({
            messages: [
              {
                id: 'm1',
                role: 'user',
                content: body.content,
                created_at: '2026-07-19T10:00:00Z',
              },
              {
                id: 'm2',
                role: 'assistant',
                content: '这周执行不错，下周数学加量。',
                created_at: '2026-07-19T10:00:05Z',
              },
            ],
          }),
        }
      }
      if (url.includes('/api/retro/confirm')) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            plan: {
              plan: {},
              advice: {
                week_start: '2026-07-20',
                summary: '下周以数学薄弱点为主。',
                daily_focus: [{ date: '2026-07-20', focus: '等价无穷小专项' }],
                review_suggestions: [],
                model: 'gpt',
                created_at: '2026-07-19T10:01:00Z',
              },
            },
          }),
        }
      }
      return {
        ok: true,
        status: 200,
        json: async () => ({ context: CONTEXT, messages: [] }),
      }
    },
  )
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

describe('RetroView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows week context and sends chat messages', async () => {
    stubFetch()
    const wrapper = mount(RetroView, {
      global: {
        stubs: {
          RouterLink: { template: '<a><slot /></a>' },
        },
      },
    })
    await flushPromises()

    const contextCard = wrapper.find('[data-testid="retro-context"]')
    expect(contextCard.text()).toContain('80%')
    expect(contextCard.text()).toContain('160 天')
    expect(contextCard.text()).toContain('等价无穷小')

    await wrapper.find('[data-testid="retro-input"]').setValue('这周数学有点吃力')
    await wrapper.find('form.composer').trigger('submit')
    await flushPromises()

    const list = wrapper.find('[data-testid="message-list"]')
    expect(list.text()).toContain('这周数学有点吃力')
    expect(list.text()).toContain('下周数学加量')
  })

  it('confirms next week plan', async () => {
    stubFetch()
    const wrapper = mount(RetroView, {
      global: {
        stubs: {
          RouterLink: { template: '<a><slot /></a>' },
        },
      },
    })
    await flushPromises()

    await wrapper.find('[data-testid="confirm-plan"]').trigger('click')
    await flushPromises()

    const planCard = wrapper.find('[data-testid="confirmed-plan"]')
    expect(planCard.exists()).toBe(true)
    expect(planCard.text()).toContain('下周以数学薄弱点为主。')
    expect(planCard.text()).toContain('等价无穷小专项')
  })
})
