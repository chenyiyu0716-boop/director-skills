#!/usr/bin/env node
/*
 * verify_douyin_profile.cjs
 * One-off helper for the short-podcast-writer workflow.
 *
 * Launches a HEADED Playwright Chromium with memory-B's default douyin-test
 * persistent profile (the exact profile `reference:douyin` uses), opens
 * douyin.com, and keeps the browser open so the user can log in and pass the
 * Douyin safety verification in the SAME browser that will later do the fetch.
 * When done, touch /tmp/douyin_verify_done (or wait for the timeout) and the
 * profile is persisted to disk.
 *
 * Run with:
 *   MEMORY_B_ROOT="$HOME/repos/memory-b" \
 *     NODE_PATH="$MEMORY_B_ROOT/node_modules" node verify_douyin_profile.cjs
 */
const { chromium } = require('playwright');
const { existsSync } = require('node:fs');

const path = require('node:path');
const os = require('node:os');
const memoryBRoot = process.env.MEMORY_B_ROOT || path.join(os.homedir(), 'repos', 'memory-b');
const PROFILE = process.env.DOUYIN_PROFILE_DIR || path.join(memoryBRoot, 'browser-profile', 'douyin-test');
const SENTINEL = '/tmp/douyin_verify_done';
const UA =
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 ' +
  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';
const MAX_MS = 600_000; // 10 min safety cap

(async () => {
  const context = await chromium.launchPersistentContext(PROFILE, {
    headless: false,
    viewport: { width: 1280, height: 900 },
    args: ['--disable-blink-features=AutomationControlled'],
    userAgent: UA,
  });
  // Mirror memory-B's webdriver hiding so the fingerprint matches the fetch run.
  await context.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { configurable: true, get: () => false });
  });

  console.log('[verify] 浏览器已打开 —— 请在里面登录抖音并过掉安全验证。');
  console.log('[verify] 完成后运行：  touch /tmp/douyin_verify_done');
  console.log('[verify] （或等待 600 秒自动关闭。关闭后 profile 已落盘，可跑 --fetch-podcast）');

  const page = await context.newPage();
  await page
    .goto('https://www.douyin.com/', { waitUntil: 'domcontentloaded', timeout: 60000 })
    .catch((e) => console.log('[verify] goto 警告：', e.message));

  const start = Date.now();
  while (Date.now() - start < MAX_MS) {
    if (existsSync(SENTINEL)) {
      console.log('[verify] 检测到 /tmp/douyin_verify_done，准备关闭浏览器。');
      break;
    }
    await new Promise((r) => setTimeout(r, 3000));
  }

  await context.close();
  console.log('[verify] 浏览器已关闭，douyin-test profile 已保存。现在可运行 --fetch-podcast。');
})().catch((err) => {
  console.error('[verify] 出错：', err && err.message ? err.message : err);
  process.exit(1);
});
