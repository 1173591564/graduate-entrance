import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import ProblemsView from './ProblemsView.vue'

const POINT_A = '11111111-1111-1111-1111-111111111111'
const POINT_B = '22222222-2222-2222-2222-222222222222'
const PROBLEM_ID = '33333333-3333-3333-3333-333333333333'
const SUBJECT_ID = '44444444-4444-4444-4444-444444444444'

const syllabusPayload = {
  source_row_count: 2,
  knowledge_point_count: 2,
  exam_blueprint_count: 0,
  versions: [],
  subjects: [
    {
      id: SUBJECT_ID,
      code: 'math1',
      name: '数学一',
      order: 1,
      exam_blueprints: [],
      source_row_count: 2,
      knowledge_point_count: 2,
      modules: [
        {
          id: 'm1',
          name: '高数',
          order: 1,
          chapters: [
            {
              id: 'c1',
              name: '极限',
              order: 1,
              sections: [],
              knowledge_points: [
                {
                  id: POINT_A,
                  name: '重要极限',
                  requirement_raw: '掌握',
                  requirement_level: 'mastery',
                  requirement_actions: [],
                  common_exam_style: '',
                  note: '',
                  order: 1,
                },
                {
                  id: POINT_B,
                  name: '等价无穷小',
                  requirement_raw: '掌握',
                  requirement_level: 'mastery',
                  requirement_actions: [],
                  common_exam_style: '',
                  note: '',
                  order: 2,
                },
              ],
            },
          ],
        },
      ],
    },
  ],
}

function draftProblem() {
  return {
    id: PROBLEM_ID,
    subject_id: SUBJECT_ID,
    subject_name: '数学一',
    content_md: '求极限',
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
    knowledge_points: [],
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

describe('ProblemsView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders the pending queue with drafts', async () => {
    stubFetch({
      'GET /api/problems/pending': () => ({ total: 1, problems: [draftProblem()] }),
      'GET /api/syllabus': () => syllabusPayload,
    })

    const wrapper = mount(ProblemsView)
    await flushPromises()

    expect(wrapper.text()).toContain('待审核 1')
    expect(wrapper.text()).toContain('错题 · 数学一')
    expect(wrapper.findAll('.review-card')).toHaveLength(1)
  })

  it('shows an empty state when nothing is pending', async () => {
    stubFetch({
      'GET /api/problems/pending': () => ({ total: 0, problems: [] }),
      'GET /api/syllabus': () => syllabusPayload,
    })

    const wrapper = mount(ProblemsView)
    await flushPromises()

    expect(wrapper.text()).toContain('暂无待审核题目')
  })

  it('validates mappings before confirming', async () => {
    stubFetch({
      'GET /api/problems/pending': () => ({ total: 1, problems: [draftProblem()] }),
      'GET /api/syllabus': () => syllabusPayload,
    })

    const wrapper = mount(ProblemsView)
    await flushPromises()

    await wrapper.get('.confirm-button').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('请为每条映射选择知识点')
  })

  it('confirms a draft and removes it from the queue', async () => {
    let confirmBody: Record<string, unknown> | null = null
    stubFetch({
      'GET /api/problems/pending': () => ({ total: 1, problems: [draftProblem()] }),
      'GET /api/syllabus': () => syllabusPayload,
      [`POST /api/problems/${PROBLEM_ID}/confirm`]: (init) => {
        confirmBody = JSON.parse(String(init?.body)) as Record<string, unknown>
        return {
          ...draftProblem(),
          status: 'confirmed',
          confirmed_at: '2026-07-16T02:00:00Z',
        }
      },
    })

    const wrapper = mount(ProblemsView)
    await flushPromises()

    const mappingSelects = wrapper.get('.mapping-row').findAll('select')
    await mappingSelects[0].setValue(POINT_A)
    await mappingSelects[1].setValue('primary')
    await wrapper.get('.mapping-row input[type="number"]').setValue(1)

    await wrapper.get('.confirm-button').trigger('click')
    await flushPromises()

    expect(confirmBody).toMatchObject({
      knowledge_points: [
        { knowledge_point_id: POINT_A, role: 'primary', weight: 1 },
      ],
    })
    expect(wrapper.text()).toContain('题目已定稿入库')
    expect(wrapper.text()).toContain('暂无待审核题目')
  })

  it('submits a new draft through the intake form', async () => {
    let pendingCalls = 0
    let submitForm: FormData | null = null
    stubFetch({
      'GET /api/problems/pending': () => {
        pendingCalls += 1
        return pendingCalls === 1
          ? { total: 0, problems: [] }
          : { total: 1, problems: [draftProblem()] }
      },
      'GET /api/syllabus': () => syllabusPayload,
      'POST /api/problems': (init) => {
        submitForm = init?.body as FormData
        return draftProblem()
      },
    })

    const wrapper = mount(ProblemsView)
    await flushPromises()

    await wrapper.get('.intake-content textarea').setValue('求极限')
    await wrapper.get('form.intake-card').trigger('submit')
    await flushPromises()

    expect(submitForm).not.toBeNull()
    expect((submitForm as unknown as FormData).get('content_md')).toBe('求极限')
    expect(wrapper.text()).toContain('题目已录入待审核队列')
    expect(wrapper.text()).toContain('待审核 1')
  })

  it('rejects an intake submission without content or images', async () => {
    stubFetch({
      'GET /api/problems/pending': () => ({ total: 0, problems: [] }),
      'GET /api/syllabus': () => syllabusPayload,
    })

    const wrapper = mount(ProblemsView)
    await flushPromises()

    await wrapper.get('form.intake-card').trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toContain('题面文本与图片至少提供一个')
  })

  it('shows an error message when loading fails', async () => {
    const fetchMock = vi.fn(async () => ({
      ok: false,
      status: 500,
      json: async () => ({}),
    }))
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mount(ProblemsView)
    await flushPromises()

    expect(wrapper.text()).toContain('待审核题目加载失败')
  })
})
