import { describe, expect, it } from 'vitest'
import { createElement } from 'react'
import { render, screen } from '@testing-library/react'
import PageFallback from './PageFallback'

describe('PageFallback', () => {
  it('shows loading status', () => {
    render(createElement(PageFallback))
    expect(screen.getByRole('status').textContent).toContain('加载中')
  })
})
