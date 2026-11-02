import { test, expect } from '@playwright/test'

test('library shell, shared cards and forms remain usable across tablet and phone widths', async ({ page, context }, testInfo) => {
  await context.request.post('/api/auth/login', { data: { password: 'smoke-test-password' } })
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  for (const path of ['/', '/tagit', '/search', '/local', '/local_fanhao', '/model', '/load_db']) {
    const response = await page.goto(path)
    expect(response?.status()).toBe(200)
    await expect(page.locator('h1')).toBeVisible()
    await expect(page.locator('.app-sidebar')).toHaveCount(1)
    if (path === '/tagit') await page.getByRole('button', { name: '喜欢', exact: true }).first().click()
    if (path === '/search') {
      await page.getByLabel('番号搜索').fill('SMOKE-0241')
      await page.getByRole('button', { name: '搜索', exact: true }).first().click()
      await expect(page.locator('.movie-card')).toHaveCount(1)
    }
    for (const width of [320, 390, 768, 820, 1024, 1180, 1366, 1920]) {
      await page.setViewportSize({ width, height: 1024 })
      await page.evaluate(() => new Promise<void>(resolve => requestAnimationFrame(() => resolve())))
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${path} at ${width}px`).toBe(true)
      const clipped = await page.locator('.movie-actions button').evaluateAll(buttons => buttons.some(button => {
        const box = button.getBoundingClientRect()
        return box.height < 44 || button.scrollWidth > button.clientWidth
      }))
      expect(clipped, `${path} actions at ${width}px`).toBe(false)
      if ((path === '/' || path === '/search' || path === '/model') && [390, 820, 1366].includes(width)) {
        await page.screenshot({ path: testInfo.outputPath(`${path === '/' ? 'recommendations' : path.slice(1)}-${width}.png`), fullPage: false })
      }
    }
  }
  await page.setViewportSize({ width: 820, height: 1180 })
  await page.getByRole('button', { name: 'Aria2 下载设置', exact: true }).click()
  await expect(page.getByRole('dialog', { name: 'Aria2 下载设置', exact: true })).toBeVisible()
  await page.getByRole('button', { name: '关闭 Aria2 设置' }).click()
  await page.getByRole('button', { name: '115 云下载设置', exact: true }).click()
  await expect(page.getByRole('dialog', { name: '115 云下载设置', exact: true })).toBeVisible()
  await page.getByRole('button', { name: '关闭 115 设置' }).click()
  expect(errors).toEqual([])
})

test('rating uses reactive card state and persists the selected preference', async ({ page, context }) => {
  await context.request.post('/api/auth/login', { data: { password: 'smoke-test-password' } })
  await page.goto('/search')
  await page.getByLabel('番号搜索').fill('SMOKE-0241')
  await page.getByRole('button', { name: '搜索', exact: true }).first().click()
  await expect(page.locator('.movie-card')).toHaveCount(1)
  const tagged = page.waitForResponse(response => response.url().includes('/api/tag/SMOKE-0241') && response.request().method() === 'POST')
  await page.locator('.rating-actions').getByRole('button', { name: '喜欢', exact: true }).click()
  expect((await tagged).status()).toBe(200)
  await expect(page.locator('.status-pill')).toHaveText('已喜欢')
  await page.locator('.movie-cover').click()
  await expect(page.getByRole('dialog', { name: '影片封面大图' })).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog', { name: '影片封面大图' })).toBeHidden()
})
