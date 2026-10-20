/**
 * Screenshot tool (development only): renders the board to png for the README.
 *
 *   1) start the server: cd app && uv run python main.py --port 8011 --no-reload
 *   2) node scripts/screenshot.mjs [output dir] [base url]
 *
 * Uses a **headless** browser that renders only this page: no desktop capture and no
 * synthetic keyboard/mouse input. Prefers the locally installed Chrome, because
 * playwright-core ships without a browser binary.
 */
import fs from 'node:fs/promises'
import path from 'node:path'
import { chromium } from 'playwright-core'

const OUT_DIR = path.resolve(process.argv[2] ?? path.join(import.meta.dirname, '..', 'docs'))
const BASE = process.argv[3] ?? 'http://127.0.0.1:8011'

const CANDIDATES = [
  process.env.CHROME_PATH,
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/usr/bin/google-chrome',
].filter(Boolean)

await fs.mkdir(OUT_DIR, { recursive: true })

const browser = await chromium.launch({ executablePath: CANDIDATES[0], headless: true })
const page = await browser.newPage({ viewport: { width: 1500, height: 980 }, deviceScaleFactor: 1.5 })

async function shot(file) {
  await page.screenshot({ path: path.join(OUT_DIR, file) })
  console.log('saved', file)
}

await page.goto(BASE, { waitUntil: 'networkidle' })
await page.waitForTimeout(400)
await shot('screenshot-board.png')

for (const [tab, file] of [
  ['Focus', 'screenshot-focus.png'],
  ['someday', 'screenshot-someday.png'],
]) {
  const el = page.getByRole('button', { name: tab, exact: false }).first()
  if (await el.count()) {
    await el.click()
    await page.waitForTimeout(500)
    await shot(file)
  }
}

await browser.close()
