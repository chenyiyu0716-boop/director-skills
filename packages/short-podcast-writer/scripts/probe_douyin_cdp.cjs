/**
 * probe_douyin_cdp.cjs
 * 用 Playwright.connectOverCDP 连到 reference:chrome 起的真实 Chrome（端口 9223），
 * 打开抖音搜索页，检测是否仍弹安全验证。
 * 目的：验证「Playwright-over-真实Chrome(CDP)」这套路径能否绕开抖音的反爬验证。
 * 复用 memory-B 的 playwright（NODE_PATH 注入），不安装任何新依赖。
 */
const { chromium } = require('playwright');

const CDP_URL = process.env.DOUYIN_CDP_URL || 'http://localhost:9223';
const KEYWORD = process.env.PROBE_KEYWORD || 'AI';

async function main() {
  let browser;
  try {
    browser = await chromium.connectOverCDP(CDP_URL);
  } catch (e) {
    console.log(JSON.stringify({ status: 'CDP_CONNECT_FAIL', error: String(e).slice(0, 300) }, null, 2));
    process.exit(2);
  }

  const context = browser.contexts()[0];
  if (!context) {
    console.log(JSON.stringify({ status: 'NO_CONTEXT', note: 'real Chrome 没有可用 context' }, null, 2));
    await browser.close();
    process.exit(3);
  }

  const page = await context.newPage();
  const url = `https://www.douyin.com/search/${encodeURIComponent(KEYWORD)}?type=video`;
  console.log('[probe] navigate ->', url);
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
  } catch (e) {
    console.log(JSON.stringify({ status: 'GOTO_FAIL', error: String(e).slice(0, 200) }, null, 2));
    await page.close();
    process.exit(4);
  }

  // 给抖音一点渲染/异步加载时间
  await page.waitForTimeout(9000);

  const finalUrl = page.url();
  const title = await page.title().catch(() => '');

  // 1) 验证标记：抖音安全验证页常见文案（仅正文，排除后台埋点）
  const bodyText = await page.evaluate(() => document.body ? document.body.innerText : '').catch(() => '');
  const verifyTextHit = /安全验证|请输入验证码|滑动验证|请完成|人机验证|captcha/i.test(bodyText);

  // 2) 打印所有 iframe URL，便于区分「后台安全埋点 iframe」与「挡人验证码」
  const iframeUrls = page.frames()
    .slice(1)
    .map((f) => f.url())
    .filter(Boolean);

  // 3) 搜索结果卡片：命中说明页面主体未被验证墙替换
  const cardCount = await page.evaluate(() => {
    const sel = '[data-e2e="search-card"], .search-card-video, .video-card, [class*="search-result"]';
    return document.querySelectorAll(sel).length;
  }).catch(() => 0);

  // 判读：以「结果卡是否加载」为主信号（验证墙会替换主体，cardCount=0）
  let verdict;
  if (verifyTextHit) verdict = 'BLOCKED';
  else if (cardCount > 0) verdict = 'CLEAN';
  else if (iframeUrls.some((u) => /verify|captcha|slider|secsdk/.test(u.toLowerCase()))) verdict = 'BLOCKED';
  else verdict = 'UNCERTAIN';

  const report = {
    status: 'OK',
    verdict,
    finalUrl,
    title,
    verifyTextHit,
    cardCount,
    iframeCount: iframeUrls.length,
    iframeUrls,
    bodyTextSample: bodyText.slice(0, 160),
  };
  console.log(JSON.stringify(report, null, 2));

  await page.close();
  // CDP 模式：真实 Chrome 不由探针关闭
  process.exit(verdict === 'BLOCKED' ? 10 : 0);
}

main().catch((e) => {
  console.log(JSON.stringify({ status: 'FATAL', error: String(e).slice(0, 400) }, null, 2));
  process.exit(1);
});
