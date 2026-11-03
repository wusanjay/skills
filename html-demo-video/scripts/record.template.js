// 录制骨架模板：按目标原型改写「流程段」，helper 原样复用
// 用法：
//   DRY=1 node record.js  → 干跑：不录像，每镜结束自动截图到 dry-shots/，写 marks-dry.json
//   node record.js        → 正式录制：rec/*.webm + marks.json（单次连续 take）
const { chromium } = require('playwright-core');
const path = require('path');
const fs = require('fs');

const BASE = 'http://127.0.0.1:8791/index.html'; // 原型地址（先起 http.server）
const ASSETS = path.join(__dirname, 'assets');    // filechooser 注入用的占位文件
const REC_DIR = path.join(__dirname, 'rec');
const DRY = process.env.DRY === '1';
const EVIDENCE = ['作品A.pdf', '作品B.pdf'];       // 命名贴合业务；不足会循环取用

const log = (...a) => console.log(...a);
const marks = [];
let t0 = 0;
let curShot = null;

(async () => {
  fs.mkdirSync(REC_DIR, { recursive: true });
  if (DRY) fs.mkdirSync(path.join(__dirname, 'dry-shots'), { recursive: true });
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
    ...(DRY ? {} : { recordVideo: { dir: REC_DIR, size: { width: 1920, height: 1080 } } }),
  });
  t0 = Date.now();

  // 演示光标：蓝色圆环跟随鼠标，按下收缩（无头浏览器无系统光标，必须注入）
  await context.addInitScript(() => {
    const ready = () => {
      if (document.getElementById('zc-cursor')) return;
      const c = document.createElement('div');
      c.id = 'zc-cursor';
      c.style.cssText = 'position:fixed;left:0;top:0;width:22px;height:22px;margin:-11px 0 0 -11px;border-radius:50%;border:2.5px solid #2563eb;background:rgba(37,99,235,.18);box-shadow:0 1px 8px rgba(37,99,235,.35);pointer-events:none;z-index:2147483647;transition:transform .07s linear,width .12s,height .12s,margin .12s;';
      document.documentElement.appendChild(c);
      const move = (e) => { c.style.transform = `translate(${e.clientX}px,${e.clientY}px)`; };
      document.addEventListener('mousemove', move, true);
      document.addEventListener('mousedown', () => { c.style.width = '15px'; c.style.height = '15px'; c.style.margin = '-7.5px 0 0 -7.5px'; }, true);
      document.addEventListener('mouseup', () => { c.style.width = '22px'; c.style.height = '22px'; c.style.margin = '-11px 0 0 -11px'; }, true);
      c.style.transform = `translate(${innerWidth / 2}px,${innerHeight / 2}px)`;
    };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', ready); else ready();
  });

  const page = await context.newPage();
  let evidenceIdx = 0;
  // 原生文件选择器拦截：回形针等按钮会触发 <input type=file>.click()
  page.on('filechooser', async (fc) => {
    const file = path.join(ASSETS, EVIDENCE[evidenceIdx % EVIDENCE.length]);
    evidenceIdx += 1;
    await fc.setFiles(file);
  });

  const wait = (ms) => page.waitForTimeout(ms);
  // mark 在镜头开始时打点；干跑时顺手把上一镜结束帧截图存档（mark('END') 前补最后一镜）
  const mark = (shot) => {
    if (DRY && curShot) {
      page.screenshot({ path: path.join(__dirname, 'dry-shots', `${curShot}.png`) }).catch(() => {});
    }
    curShot = shot;
    const t = (Date.now() - t0) / 1000; marks.push({ shot, t: Math.round(t * 100) / 100 }); log(`🎬 ${shot} @ ${t.toFixed(2)}s`);
  };
  // 关键：多视图并存同名按钮，必须取第一个“可见实例”，否则命中隐藏元素漏点
  const visibleLocator = (sel) => page.locator(sel).and(page.locator(':visible')).first();
  async function humanClick(sel) {
    const loc = visibleLocator(sel);
    await loc.waitFor({ state: 'visible', timeout: 10000 });
    const box = await loc.boundingBox();
    if (box) { await page.mouse.move(box.x + box.width * 0.5, box.y + box.height * 0.5, { steps: 10 }); await wait(230); }
    await loc.click();
    await wait(400);
  }
  // 鼠标缓移：浏览画面的“视线引导”
  async function drift(x, y, steps = 18) { await page.mouse.move(x, y, { steps }); await wait(250); }
  // 单步失败不中断整个 take（旅程状态在内存，中断即全部作废）。
  // 注意：只包裹“失败后画面仍成立”的步骤；关键推进步骤（无它则后续全错）不要包，让它炸出来。
  async function safe(fn, label) { try { await fn(); } catch (e) { log(`⚠️ ${label}: ${String(e).split('\n')[0]}`); } }

  await page.goto(BASE, { waitUntil: 'load' });
  await wait(2200);

  /* ===================== 流程段：按目标原型改写 =====================
   * 每镜模式：mark('01') → 交互（humanClick/drift/keyboard.type）→ wait 定格浏览。
   * 节奏基准：旁白约 4.4 字/秒；画面宁短勿长（总装 tpad 克隆末帧补齐，超长只能裁尾，
   * 超长 >15% 时总装会直接原速裁尾）。结算动画（toast/评估/进度条）wait ≥ 2.1s。
   * 有状态主线必须单 take 顺序推进；无状态镜头可放 take 末尾补拍，总装时重排。
   * 快进蒙太奇镜：整镜录完，总装用 stretch 压缩；镜内需要“前段正常+后段快进”
   * 时，在分界点加 mark('NNb')，总装 --split "NN=NNb" 分两段变速。
   * 例：
   * mark('01');
   * await drift(1100, 420); await wait(4500);
   * mark('02');
   * await humanClick('[data-action="open-opportunity"]');
   * await wait(1200);
   * ================================================================ */

  // ===== 收尾：固定写法 =====
  mark('END');
  if (DRY && curShot !== 'END') {
    await page.screenshot({ path: path.join(__dirname, 'dry-shots', `${curShot}.png`) }).catch(() => {});
  }
  let videoPath = null;
  if (!DRY) {
    videoPath = await page.video().path();
  }
  await context.close();
  await browser.close();
  fs.writeFileSync(path.join(__dirname, DRY ? 'marks-dry.json' : 'marks.json'),
    JSON.stringify({ video: videoPath, marks }, null, 2));
  log('\n===== 录制完成 =====');
  log('视频:', videoPath);
  marks.forEach((m) => log(`  ${m.shot} @ ${m.t}s`));
})().catch((e) => {
  console.error('FATAL', e);
  fs.writeFileSync(path.join(__dirname, DRY ? 'marks-dry.json' : 'marks.json'),
    JSON.stringify({ marks, error: String(e) }, null, 2));
  process.exit(1);
});
