import { expect, test } from '@playwright/test'

test.describe('main login page', () => {
  test('should show login form and fail with invalid credentials', async ({ page }) => {
    await page.route('**/api/v1/auth/login', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 2004, message: 'Invalid username or password', data: null }),
      })
    })

    await page.goto('/login')
    await expect(page.getByRole('heading', { name: 'MADF 登录' })).toBeVisible()
    await page.locator('input').nth(0).fill('nobody')
    await page.locator('input[type="password"]').fill('badpass1')
    await page.getByRole('button', { name: /登录/ }).click()
    await expect(page.locator('.error')).toBeVisible()
    await expect(page).toHaveURL(/\/login/)
  })

  test('should store token and redirect after successful login', async ({ page }) => {
    await page.route('**/api/v1/auth/login', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 200,
          message: 'success',
          data: {
            token: { token: 'e2e-token', token_type: 'bearer' },
            user: { id: 'u1', username: 'e2e', phone: null, created_at: '2026-01-01T00:00:00Z' },
          },
        }),
      })
    })
    await page.route('**/api/v1/characters', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 200, message: 'success', data: { items: [], total: 0 } }),
      })
    })
    await page.route('**/api/v1/discussions', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 200, message: 'success', data: { items: [], total: 0 } }),
      })
    })

    await page.goto('/login?redirect=%2Fcharacters')
    await page.locator('input').nth(0).fill('e2e')
    await page.locator('input[type="password"]').fill('secret12')
    await page.getByRole('button', { name: /登录/ }).click()
    await expect(page).toHaveURL(/\/characters/)
    const token = await page.evaluate(() => localStorage.getItem('token'))
    expect(token).toBe('e2e-token')
  })

  test('should redirect unauthenticated home to login', async ({ page }) => {
    await page.addInitScript(() => localStorage.removeItem('token'))
    await page.goto('/')
    await expect(page).toHaveURL(/\/login\?redirect=/)
  })
})
