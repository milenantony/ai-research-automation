import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { chromium } from 'playwright'
import { createServer } from 'vite'

const [fixturePath, pdfPath] = process.argv.slice(2)
const responses = JSON.parse(await readFile(fixturePath, 'utf8'))
const [job] = responses['/research-jobs']
const server = await createServer({ server: { host: '127.0.0.1', port: 0, proxy: {} } })
await server.listen()

let browser
try {
  browser = await chromium.launch({ executablePath: process.env.PAPERX_CHROMIUM_PATH })
  const page = await browser.newPage()
  await page.route(/\/research-jobs(?:\/|\?|$)/, (route) => {
    const resource = new URL(route.request().url()).pathname
    return route.fulfill({ status: resource in responses ? 200 : 404, json: responses[resource] ?? {} })
  })
  await page.addInitScript(() => {
    window.print = () => { window.printRequested = true }
  })
  await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/#/workspace/jobs/${job.id}`)
  const report = page.locator('.printable-report')
  await report.getByText('solar forecasts from satellite imagery', { exact: true }).waitFor()
  await page.reload()
  await report.getByText('solar forecasts from satellite imagery', { exact: true }).waitFor()
  assert.equal(await report.getByText('Rejected control gap.', { exact: false }).count(), 0)
  await report.getByRole('button', { name: 'Save report as PDF' }).click()
  assert.equal(await page.evaluate(() => window.printRequested), true)
  await page.pdf({ path: pdfPath, preferCSSPageSize: true })
} finally {
  await browser?.close()
  await server.close()
}
