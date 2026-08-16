import { describe, expect, it } from 'vitest'
import { displayName } from './displayName'

describe('displayName', () => {
  it('strips -perspective suffix', () => {
    expect(displayName('Steve Jobs-perspective')).toBe('Steve Jobs')
  })

  it('keeps plain names', () => {
    expect(displayName('Ada')).toBe('Ada')
  })

  it('handles empty', () => {
    expect(displayName(null)).toBe('')
    expect(displayName(undefined)).toBe('')
  })
})
