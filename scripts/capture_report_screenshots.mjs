import { createRequire } from 'node:module';
import { mkdirSync } from 'node:fs';

const require = createRequire('C:/Users/Guche/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/');
const { chromium } = require('playwright');

const outDir = 'D:/Project/Intelligent-Meeting-Cloud/report_assets';
mkdirSync(outDir, { recursive: true });

const pages = [
  ['http://127.0.0.1:5173/face-access', 'ui_face_access.png', 1800],
  ['http://127.0.0.1:5173/booking', 'ui_booking.png', 1400],
  ['http://127.0.0.1:5173/room-3d', 'ui_room3d_live.png', 2800],
  ['http://127.0.0.1:5173/control', 'ui_control_live.png', 1600],
];

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1365, height: 768 },
  deviceScaleFactor: 1,
});
const page = await context.newPage();

for (const [url, fileName, delay] of pages) {
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 20000 });
    await page.waitForTimeout(delay);
    await page.screenshot({ path: `${outDir}/${fileName}`, fullPage: false });
    console.log(`${fileName}\tOK`);
  } catch (error) {
    console.log(`${fileName}\tFAILED\t${error.message}`);
  }
}

await browser.close();
