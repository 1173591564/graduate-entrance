import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import SyllabusView from './SyllabusView.vue'

describe('SyllabusView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders the imported syllabus tree and switches subjects', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          source_row_count: 3,
          knowledge_point_count: 2,
          exam_blueprint_count: 1,
          versions: [
            {
              id: 'version',
              source_name: 'mock.csv',
              source_checksum: 'checksum',
              row_count: 3,
              imported_at: '2026-07-15T00:00:00Z',
            },
          ],
          subjects: [
            {
              id: 'math',
              code: '数学一',
              name: '数学一',
              order: 1,
              source_row_count: 1,
              knowledge_point_count: 1,
              exam_blueprints: [],
              modules: [
                {
                  id: 'higher-math',
                  name: '高等数学',
                  order: 1,
                  chapters: [
                    {
                      id: 'limit',
                      name: '函数极限连续',
                      order: 1,
                      knowledge_points: [],
                      sections: [
                        {
                          id: 'function',
                          name: '函数',
                          order: 1,
                          knowledge_points: [
                            {
                              id: 'function-concept',
                              name: '函数的概念与表示法',
                              requirement_raw: '理解',
                              requirement_level: 'understanding',
                              requirement_actions: [],
                              common_exam_style: '',
                              note: '',
                              order: 1,
                            },
                          ],
                        },
                      ],
                    },
                  ],
                },
              ],
            },
            {
              id: 'politics',
              code: '政治',
              name: '政治',
              order: 4,
              source_row_count: 2,
              knowledge_point_count: 1,
              exam_blueprints: [
                {
                  id: 'politics-exam',
                  name: '试卷结构',
                  total_score: 100,
                  duration_minutes: null,
                  description: '马原/毛中特/史纲/思修/形策分值约24/30/14/16/16',
                  sections: [
                    {
                      id: 'politics-section',
                      name: '单选16题16分+多选17题34分+分析题5题50分=100分',
                      score: 100,
                      duration_minutes: null,
                      description: '',
                      order: 1,
                    },
                  ],
                },
              ],
              modules: [
                {
                  id: 'marxism',
                  name: '马克思主义基本原理',
                  order: 1,
                  chapters: [
                    {
                      id: 'intro',
                      name: '导论',
                      order: 1,
                      sections: [],
                      knowledge_points: [
                        {
                          id: 'marxism-intro',
                          name: '马克思主义的创立与发展',
                          requirement_raw: '了解',
                          requirement_level: 'awareness',
                          requirement_actions: [],
                          common_exam_style: '',
                          note: '马原约24分',
                          order: 1,
                        },
                      ],
                    },
                  ],
                },
              ],
            },
          ],
        }),
      }),
    )

    const wrapper = mount(SyllabusView)
    await flushPromises()

    expect(wrapper.text()).toContain('3')
    expect(wrapper.text()).toContain('函数的概念与表示法')
    await wrapper.get('button:nth-of-type(2)').trigger('click')

    expect(wrapper.text()).toContain('马克思主义基本原理')
    expect(wrapper.text()).toContain('单选16题16分+多选17题34分+分析题5题50分=100分')
  })
})
