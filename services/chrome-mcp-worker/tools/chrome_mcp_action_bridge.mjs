#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import process from 'node:process';
import puppeteer from 'puppeteer-core';

const REMOTE_URL = process.env.CHROME_REMOTE_URL || 'http://127.0.0.1:9222';
const ACTION = process.argv[2];

async function readPayload() {
  const chunks = [];
  for await (const chunk of process.stdin) {
    chunks.push(chunk);
  }
  const raw = Buffer.concat(chunks).toString('utf8').trim();
  if (!raw) return {};
  try {
    return JSON.parse(raw);
  } catch (err) {
    throw new Error(`invalid JSON payload: ${String(err)}`);
  }
}

function selectorsFromNode(node) {
  if (!node || typeof node !== 'object') return [];
  const arr = [];
  if (node.primary) arr.push(String(node.primary));
  if (Array.isArray(node.fallback)) {
    for (const x of node.fallback) arr.push(String(x));
  }
  return arr.filter(Boolean);
}

async function connectPage() {
  const browser = await puppeteer.connect({ browserURL: REMOTE_URL });
  let pages = await browser.pages();
  let page = pages.find((p) => !p.url().startsWith('chrome://'));

  if (!page) {
    page = await browser.newPage();
  }

  return { browser, page };
}

async function resolveElement(page, selectorNode) {
  const selectors = selectorsFromNode(selectorNode);
  let lastError = null;

  for (const selector of selectors) {
    try {
      const el = await page.$(selector);
      if (el) {
        return { el, selector };
      }
    } catch (err) {
      lastError = err;
    }
  }

  throw new Error(
    `no selector matched: ${JSON.stringify(selectors)}${
      lastError ? `, lastError=${String(lastError)}` : ''
    }`
  );
}

async function clearAndType(page, selectorNode, value) {
  const { selector } = await resolveElement(page, selectorNode);
  await page.waitForSelector(selector, { timeout: 15000 });
  await page.click(selector, { clickCount: 3 });
  await page.keyboard.press('Backspace');
  await page.type(selector, String(value), { delay: 20 });
}

async function clickSelector(page, selectorNode) {
  const { selector } = await resolveElement(page, selectorNode);
  await page.waitForSelector(selector, { timeout: 15000 });
  await page.click(selector);
  return selector;
}

async function readToast(page) {
  const text = await page.evaluate(() => {
    const candidates = [
      '.ant-message-notice-content',
      '.ant-notification-notice-message',
      '[class*=toast]',
      '[role="alert"]'
    ];
    for (const c of candidates) {
      const node = document.querySelector(c);
      if (node && node.textContent) {
        return node.textContent.trim();
      }
    }
    return '';
  });
  return text || 'save_draft called';
}

async function downloadImages(imageUrls) {
  const tmpRoot = path.join(os.tmpdir(), 'xhs-upload-bridge', Date.now().toString());
  await fs.mkdir(tmpRoot, { recursive: true });

  const localPaths = [];
  let idx = 0;
  for (const url of imageUrls || []) {
    idx += 1;
    const res = await fetch(url);
    if (!res.ok) {
      throw new Error(`failed to download image: ${url}, status=${res.status}`);
    }

    const contentType = res.headers.get('content-type') || 'image/jpeg';
    const ext = contentType.includes('png') ? 'png' : contentType.includes('webp') ? 'webp' : 'jpg';
    const filePath = path.join(tmpRoot, `img_${idx}.${ext}`);
    const bytes = Buffer.from(await res.arrayBuffer());
    await fs.writeFile(filePath, bytes);
    localPaths.push(filePath);
  }

  return localPaths;
}

async function actionOpenNewProductPage(page, payload) {
  if (!payload.url) throw new Error('open_new_product_page requires url');
  await page.goto(payload.url, { waitUntil: 'domcontentloaded', timeout: 45000 });
  return { url: page.url() };
}

async function actionSetCategory(page, payload) {
  await clearAndType(page, payload.selector, payload.category_path || '');
  await page.keyboard.press('Enter');
  await page.waitForTimeout(500);
  return { ok: true };
}

async function actionSetBrand(page, payload) {
  await clearAndType(page, payload.selector, payload.brand_name || '');
  await page.keyboard.press('Enter');
  await page.waitForTimeout(500);
  return { ok: true };
}

async function actionSetProductNames(page, payload) {
  await clearAndType(page, payload.selectors?.product_name, payload.product_name || '');
  await clearAndType(page, payload.selectors?.short_name, payload.short_name || '');
  return { ok: true };
}

async function actionSetPrimarySpec(page, payload) {
  await clearAndType(page, payload.selectors?.spec_name, payload.spec_name_1 || '');
  await clearAndType(page, payload.selectors?.spec_value, payload.spec_value_1 || '');
  await clearAndType(page, payload.selectors?.barcode, payload.barcode || '');
  return { ok: true };
}

async function actionSetPrices(page, payload) {
  await clearAndType(page, payload.selectors?.price, payload.price ?? '');
  await clearAndType(page, payload.selectors?.original_price, payload.original_price ?? '');
  return { ok: true };
}

async function actionUploadMainImages(page, payload) {
  const imageUrls = payload.image_urls || [];
  if (!imageUrls.length) throw new Error('upload_main_images requires image_urls');

  const localPaths = await downloadImages(imageUrls);
  const { selector } = await resolveElement(page, payload.selector);
  const input = await page.$(selector);
  if (!input) throw new Error('image upload input not found');

  await input.uploadFile(...localPaths);
  await page.waitForTimeout(1000);
  return { uploaded: localPaths.length };
}

async function actionSetDescription(page, payload) {
  await clearAndType(page, payload.selector, payload.desc_text || '');
  return { ok: true };
}

async function actionSaveDraft(page, payload) {
  await clickSelector(page, payload.selector);
  await page.waitForTimeout(1200);
  const toast = await readToast(page);
  return { toast };
}

async function actionCaptureScreenshot(page, payload) {
  const outputDir = payload.output_dir || '.';
  const name = payload.name || 'step';
  await fs.mkdir(outputDir, { recursive: true });
  const screenshotPath = path.join(outputDir, `${name}.png`);
  await page.screenshot({ path: screenshotPath, fullPage: false });
  return { path: screenshotPath };
}

const ACTIONS = {
  open_new_product_page: actionOpenNewProductPage,
  set_category: actionSetCategory,
  set_brand: actionSetBrand,
  set_product_names: actionSetProductNames,
  set_primary_spec: actionSetPrimarySpec,
  set_prices: actionSetPrices,
  upload_main_images: actionUploadMainImages,
  set_description: actionSetDescription,
  save_draft: actionSaveDraft,
  capture_screenshot: actionCaptureScreenshot,
};

async function main() {
  if (!ACTION) {
    console.error('missing action name');
    process.exit(2);
  }

  const handler = ACTIONS[ACTION];
  if (!handler) {
    console.error(`unsupported action: ${ACTION}`);
    process.exit(2);
  }

  const payload = await readPayload();
  let browser;
  let page;

  try {
    const connected = await connectPage();
    browser = connected.browser;
    page = connected.page;
  } catch (err) {
    console.error(
      `failed to connect Chrome remote debugging endpoint (${REMOTE_URL}). ` +
      'Start Chrome with --remote-debugging-port=9222 or set CHROME_REMOTE_URL.'
    );
    console.error(String(err?.message || err));
    process.exit(1);
  }

  try {
    const result = await handler(page, payload);
    process.stdout.write(JSON.stringify(result || {}));
    await browser.disconnect();
  } catch (err) {
    await browser.disconnect();
    console.error(String(err?.stack || err));
    process.exit(1);
  }
}

main();
