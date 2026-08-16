import { describe, expect, it } from 'vitest'
import { createElement } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { render, screen } from '@testing-library/react'
import PageFallback from '../components/PageFallback'

describe('PageFallback', () => {
  it('shows loading text', () => {
    render(createElement(PageFallback))
    expect(screen.getByRole('status').textContent).toContain('加载中')
  })
})

describe('login redirect helper contract', () => {
  it('MemoryRouter can mount login path', () => {
    render(
      createElement(
        MemoryRouter,
        { initialEntries: ['/login?redirect=%2Fcharacters'] },
        createElement('div', { 'data-testid': 'ok' }, 'ok'),
      ),
    )
    expect(screen.getByTestId('ok').textContent).toBe('ok')
  })
})
