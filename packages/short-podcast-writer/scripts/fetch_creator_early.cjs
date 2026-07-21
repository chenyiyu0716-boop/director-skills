// 采集某个抖音创作者的「早期内容」：搜到主页 -> 进主页滚动到最底（旧内容在底部）-> 抓最早的一批视频
// 复用真实 Chrome 的 CDP（9223），不关闭浏览器本身。
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const endpoint = process.env.DOUYIN_CDP_URL || 'http://127.0.0.1:9223';
const keyword = process.argv[2] || '睡莲';
const outDir = process.argv[3] || path.join(__dirname, '..', 'logs');
const takeN = parseInt(process.argv[4] || '12', 10);
fs.mkdirSync(outDir, { recursive: true });

function parseLikes(txt) {
  const m = txt.match(/([\d.]+)\s*(万|w|W)?\s*(赞|喜欢|播放)/);
  if (!m) return null;
  let n = parseFloat(m[1]);
  if (m[2]) n *= 10000;
  return Math.round(n);
}
function parseTime(txt) {
  if (/(\d+)\s*年前/.test(txt)) return txt.match(/(\d+)\s*年前/)[0];
  if (/(\d+)\s*个月前/.test(txt)) return txt.match(/(\d+)\s*个月前/)[0];
  if (/(\d+)\s*天前/.test(txt)) return txt.match(/(\d+)\s*天前/)[0];
  if (/(\d{4})[-/.年](\d{1,2})[-/.月](\d{1,2})/.test(txt)) return txt.match(/(\d{4})[-/.年](\d{1,2})[-/.月](\d{1,2})/)[0];
  return null;
}

(async () => {
  const browser = await chromium.connectOverCDP(endpoint);
  // 用真实 Chrome 已登录的 context[0]，只开新 page，不关 context/浏览器
  const context = browser.contexts()[0] || await browser.newContext();
  await context.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { configurable: true, get: () => false });
  });
  const page0 = await context.newPage();
  let page = page0;

  // 1) 搜用户，找到睡莲主页
  await page.goto('https://www.douyin.com/search/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(2500);
  const inp = await page.$("input[type='search']") || await page.$("input[placeholder*='搜索']") || await page.$('.search-input input') || await page.$('input.ef');
  if (!inp) {
    console.log('NO_SEARCH_INPUT');
    await page.close().catch(() => {});
    if (page0 !== page) await page0.close().catch(() => {});
    throw new Error('NO_SEARCH_INPUT');
  }
  await inp.click();
  await inp.fill('');
  await inp.type(keyword, { delay: 40 });
  await page.waitForTimeout(800);
  // 尝试点击搜索提交按钮（按 aria-label/type=submit/文字 定位）
  const btnInfo = await page.evaluate(() => {
    const btns = [...document.querySelectorAll('button')];
    const b = btns.find((x) => /搜索/.test(x.getAttribute('aria-label') || '') || x.getAttribute('type') === 'submit' || /搜索/.test((x.innerText || '').trim()));
    if (b) { b.click(); return 'clicked:' + ((b.getAttribute('aria-label') || b.innerText || '').trim().slice(0, 20)); }
    return false;
  });
  console.log('btnInfo', btnInfo);
  await page.waitForTimeout(3500);
  let cur = page.url();
  console.log('url-after-btn', cur);
  if (cur === 'https://www.douyin.com/search/' || !/\/search\//.test(cur)) {
    // 兜底：点第一条联想词（已知可跳转），并重新获取活动页避免脱钩
    await page.evaluate((kw) => {
      const nodes = [...document.querySelectorAll('*')];
      const sug = nodes.find((n) => { const t = (n.innerText || '').trim(); return t === kw || (t.startsWith(kw) && t.length <= kw.length + 6 && n.children.length === 0); });
      if (sug) sug.click();
    }, keyword);
    await page.waitForTimeout(3000);
    const pages = context.pages();
    const active = pages[pages.length - 1];
    if (active && active !== page) {
      try { await active.waitForLoadState('domcontentloaded', { timeout: 5000 }); } catch {}
      page = active;
    }
    console.log('url-after-sug', page.url());
  }
  // 在已渲染的搜索结果页上，清空重输干净关键词并回车（避免 ✔ 历史标记污染查询）
  const inp2 = await page.$("input[type='search']") || await page.$("input[placeholder*='搜索']") || await page.$('.search-input input');
  if (inp2) {
    await inp2.click();
    await inp2.fill('');
    await inp2.type(keyword, { delay: 40 });
    await page.keyboard.press('Enter');
    await page.waitForTimeout(3500);
    const ps = context.pages();
    if (ps.length && ps[ps.length - 1] !== page) page = ps[ps.length - 1];
    console.log('url-after-clean', page.url());
  }
  // 点「用户」标签（此时结果页已渲染，标签可点）
  const tabClicked = await page.evaluate(() => {
    const tabs = [...document.querySelectorAll('div, span, a, button')];
    const t = tabs.find((n) => { const s = (n.innerText || '').trim(); return s === '用户' && (n.innerText || '').length <= 4 && n.children.length === 0; });
    if (t) { t.click(); return true; }
    return false;
  });
  console.log('userTabClicked', tabClicked);
  await page.waitForTimeout(4000);
  // 滚动加载更多用户结果
  for (let i = 0; i < 6; i += 1) {
    await page.evaluate(() => window.scrollBy(0, window.innerHeight * 0.8));
    await page.waitForTimeout(1200);
  }
  await page.waitForTimeout(1500);
  const users = await page.$$eval("a[href*='/user/']", (els) =>
    els.map((e) => {
      const href = e.getAttribute('href') || '';
      const m = href.match(/\/user\/([^?&#]+)/);
      const txt = (e.innerText || '').replace(/\s+/g, ' ').trim();
      return { sec: m ? m[1] : '', href, text: txt.slice(0, 80) };
    })
  );
  const real = users.filter((u) => u.sec && u.sec !== 'self');
  const cand = real.filter((u) => /睡莲/.test(u.text));
  let chosen = cand.find((u) => u.text.trim() === keyword) || cand.sort((a, b) => a.text.length - b.text.length)[0];
  if (!chosen) {
    console.log('NO_USER_FOUND', JSON.stringify(real.slice(0, 25), null, 2));
    const body = await page.evaluate(() => document.body.innerText.replace(/\s+/g, ' ').slice(0, 1500)).catch(() => '');
    console.log('PAGE_TEXT', JSON.stringify(body));
    await page.close().catch(() => {});
    if (page0 !== page) await page0.close().catch(() => {});
    throw new Error('NO_USER_FOUND');
  }
  console.log('CHOSEN', JSON.stringify(chosen));

  // 2) 进主页（修正协议相对地址 //www.douyin.com/... 的拼接）
  let profileUrl = chosen.href;
  if (profileUrl.startsWith('//')) profileUrl = 'https:' + profileUrl;
  else if (!profileUrl.startsWith('http')) profileUrl = 'https://www.douyin.com' + profileUrl;
  await page.goto(profileUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForSelector("a[href*='/video/']", { timeout: 20000 }).catch(() => {});
  await page.waitForTimeout(2000);

  // 尝试点「最早发布」排序（部分账号有）
  const sortClicked = await page.evaluate(() => {
    const all = [...document.querySelectorAll('div,button,span,a')];
    const el = all.find((n) => /最早发布|最早/.test(n.innerText || '') && (n.innerText || '').length < 24);
    if (el) { try { el.click(); return true; } catch { return false; } }
    return false;
  });
  console.log('sortClicked', sortClicked);
  await page.waitForTimeout(1500);

  // 3) 滚到底（旧内容在底部）；若已按最早排序则少滚省内存
  const maxScrolls = sortClicked ? 2 : 9;
  for (let i = 0; i < maxScrolls; i += 1) {
    await page.evaluate(() => window.scrollBy(0, window.innerHeight * 0.95));
    await page.waitForTimeout(700);
  }

  const videos = await page.$$eval("a[href*='/video/']", (els) => {
    const seen = new Map();
    const RECR = /推荐|猜你|相关|感兴趣|更多作品|更多视频|广告/;
    const isRec = (a) => {
      let e = a.parentElement;
      for (let k = 0; k < 6 && e; k += 1) {
        const t = e.innerText || '';
        const c = (e.className && e.className.toString()) || '';
        if (RECR.test(t) || RECR.test(c)) return true;
        e = e.parentElement;
      }
      return false;
    };
    for (const e of els) {
      const href = e.getAttribute('href') || '';
      const m = href.match(/\/video\/(\d+)/);
      if (!m) continue;
      if (isRec(e)) continue;
      const id = m[1];
      if (seen.has(id)) continue;
      const txt = (e.innerText || '').replace(/\s+/g, ' ').trim();
      seen.set(id, { videoId: id, url: 'https://www.douyin.com/video/' + id, text: txt.slice(0, 240) });
    }
    return [...seen.values()];
  });

  // 取最早的一批（列表末尾 = 旧）
  const early = videos.slice(-takeN);
  if (early.length === 0) {
    console.log('NO_VIDEOS_COLLECTED total', videos.length);
    const diag = await page.evaluate(() => {
      const as = [...document.querySelectorAll('a')].slice(0, 30).map((a) => a.getAttribute('href') || '');
      const body = document.body.innerText.replace(/\s+/g, ' ').slice(0, 600);
      return { hrefs: as, body };
    }).catch(() => ({}));
    console.log('PROFILE_DIAG', JSON.stringify(diag));
    await page.close().catch(() => {});
    if (page0 !== page) await page0.close().catch(() => {});
    throw new Error('NO_VIDEOS_COLLECTED');
  }

  const out = {
    ok: true,
    status: 'ok',
    topic: '睡莲早期内容',
    searchedKeywords: [keyword],
    minLikes: 0,
    lookbackDays: 2000,
    generatedAt: new Date().toISOString(),
    platform: '抖音',
    videos: early.map((v, i) => {
      const likes = parseLikes(v.text);
      const t = parseTime(v.text) || '2年前';
      return {
        keyword,
        title: v.text.split(/[。\n]/)[0].slice(0, 60) || '未命名视频',
        videoUrl: v.url,
        likeCountRaw: likes != null ? String(likes) : '',
        likeCountNumber: likes,
        publishTimeRaw: t,
        cardTextPreview: v.text,
        rankScore: i,
      };
    }),
    jsonPath: '',
    markdownPath: '',
    nextStep: '',
  };

  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  const f = path.join(outDir, `${stamp}_睡莲早期内容_douyin_reference.json`);
  fs.writeFileSync(f, JSON.stringify(out, null, 2));
  console.log('WROTE', f, 'total', videos.length, 'early', early.length);
  await page.close().catch(() => {});
  if (page0 !== page) await page0.close().catch(() => {});
})().catch((e) => {
  console.error('ERR', e && e.message ? e.message : e);
  try { page.close().catch(() => {}); } catch {}
  try { if (typeof page0 !== 'undefined' && page0 !== page) page0.close().catch(() => {}); } catch {}
  // 不调用 process.exit，避免缓冲日志在崩溃时丢失
});
