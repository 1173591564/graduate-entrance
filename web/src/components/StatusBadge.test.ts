import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import StatusBadge from './StatusBadge.vue'

describe('StatusBadge', () => {
  it('renders the connected state', () => {
    const wrapper = mount(StatusBadge, {
      props: {
        state: 'online',
      },
    })

    expect(wrapper.text()).toContain('后端已连接')
    expect(wrapper.classes()).toContain('status-online')
  })
})
