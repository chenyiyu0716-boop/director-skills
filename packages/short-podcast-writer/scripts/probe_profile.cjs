// 探测睡莲主页的视频网格 DOM 结构，找出「作品网格」容器，以便只采集她自己的视频
const { chromium } = require('playwright');
const endpoint = process.env.DOUYIN_CDP_URL || 'http://127.0.0.1:9223';
const sec = process.argv[2] || 'MS4wLjABAAAAuMHALmSkriuJg555upSQp4UJzhA0kJVrPqwZw8ON9scz0T8k66h-NpK_TKgKRfEJ';

(async () => {
  const browser = await chromium.connectOverCDP(endpoint);
  const context = browser.contexts()[0] || await browser.newContext();
  await context.addInitScript(() => { Object.defineProperty(navigator, 'webdriver', { configurable: true, get: () => false }); });
  const page = await context.newPage();
  const url = `https://www.douyin.com/user/${sec}`;
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForSelector("a[href*='/video/']", { timeout: 20000 }).catch(() => {});
  await page.waitForTimeout(2500);
  for (let i = 0; i < 3; i += 1) { await page.evaluate(() => window.scrollBy(0, window.innerHeight * 0.9)); await page.waitForTimeout(800); }

  const info = await page.evaluate(() => {
    const links = [...document.querySelectorAll("a[href*='/video/']")];
    const out = [];
    for (const a of links.slice(0, 18)) {
      // 向上找 4 层祖先的 class
      const chain = [];
      let el = a.parentElement;
      for (let k = 0; k < 4 && el; k += 1) { chain.push((el.className && el.className.toString().slice(0, 40)) || el.tagName); el = el.parentElement; }
      // 祖先里是否含推荐类文字
      let ancText = '';
      let e2 = a.parentElement;
      for (let k = 0; k < 6 && e2; k += 1) { ancText += (e2.getAttribute && e2.getAttribute('class') || '') + ' '; e2 = e2.parentElement; }
      const rec = /推荐|猜你|相关|更多|感兴趣/.test(ancText);
      out.push({ href: (a.getAttribute('href') || '').slice(0, 50), chain, rec });
    }
    return { count: links.length, samples: out };
  });
  console.log(JSON.stringify(info, null, 2));
  await page.close().catch(() => {});
})().catch((e) => { console.error('ERR', e && e.message); process.exit(0); });
