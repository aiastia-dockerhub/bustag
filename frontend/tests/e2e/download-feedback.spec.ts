import { test, expect } from '@playwright/test'

test('download actions show success and failure notices inside the page', async ({ page, context }) => {
  await context.request.post('/api/auth/login', { data: { password: 'smoke-test-password' } })
  await context.addInitScript(() => localStorage.setItem('bustag_aria2_rpc_url', 'http://aria2.test'))
  let cloudError = false
  await page.route('**/api/115/push/*', route => route.fulfill({
    json: cloudError ? { error: '云下载配额已用完' } : { success: true },
  }))
  await page.route('**/api/magnet/*', route => route.fulfill({
    json: { magnet: 'magnet:?xt=urn:btih:0000000000000000000000000000000000000000' },
  }))
  let rpcError = false
  await page.route('http://aria2.test/jsonrpc', route => route.fulfill({
    headers: { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'content-type' },
    json: rpcError ? { error: { code: 1, message: '下载目录不可写' } } : { result: 'test-task-id' },
  }))
  page.on('dialog', () => { throw new Error('Download feedback must stay inside the page') })
  await page.goto('/')
  const actions = page.locator('.action-buttons').first()
  const cloud = actions.getByRole('button', { name: '☁️ 115', exact: true })
  await cloud.click()
  await expect(page.getByText(/已提交到 115 云下载/)).toBeVisible()
  await page.getByRole('button', { name: '关闭提醒' }).click()
  await expect(page.locator('.download-notice')).toHaveCount(0)

  cloudError = true
  await expect(cloud).toBeEnabled()
  await cloud.click()
  await expect(page.getByText(/115 提交失败：云下载配额已用完/)).toBeVisible()
  await page.getByRole('button', { name: '关闭提醒' }).click()

  const aria = actions.getByRole('button', { name: '⬇️ Aria2', exact: true })
  await aria.click()
  await expect(page.getByText(/已提交到 Aria2/)).toBeVisible()
  await page.getByRole('button', { name: '关闭提醒' }).click()

  rpcError = true
  await expect(aria).toBeEnabled()
  await aria.click()
  await expect(page.getByText(/Aria2 拒绝任务：下载目录不可写/)).toBeVisible()
})
