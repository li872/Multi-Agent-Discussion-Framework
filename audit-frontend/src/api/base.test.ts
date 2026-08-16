import { afterEach, describe, expect, it } from 'vitest'
import { auditApiBase, auditBasename, auditLoginPath } from './base'

describe('audit api base', () => {
  afterEach(() => {
    // jsdom location is sticky; reset via history when possible
  })

  it('uses /api/v1 on audit-frontend ports', () => {
    Object.defineProperty(window, 'location', {
      value: new URL('http://localhost:5174/'),
      writable: true,
    })
    expect(auditApiBase()).toBe('/api/v1')
    expect(auditBasename()).toBe('')
  })

  it('uses /audit/api/v1 on single-container host port', () => {
    Object.defineProperty(window, 'location', {
      value: new URL('http://localhost/audit/login'),
      writable: true,
    })
    expect(auditApiBase()).toBe('/audit/api/v1')
    expect(auditBasename()).toBe('/audit')
    expect(auditLoginPath()).toBe('/audit/login')
  })
})
