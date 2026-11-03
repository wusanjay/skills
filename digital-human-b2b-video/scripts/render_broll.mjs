#!/usr/bin/env node
// 动效 B-roll 渲染器：确定性逐帧渲染 HTML 动画页 → mp4
// 用法: NODE_PATH 不需要；直接 node render_broll.mjs <page.html> [--fps 30] [--size 1920x1080] [--out out.mp4] [--q 'k=v']
// 页面约定: window.DUR = 总时长秒; window.render(t) = 确定性渲染第 t 秒画面
// 借鉴 Lemo Opuscar core/render 的确定性截帧思路，轻量单 worker 版。
import { createRequire } from 'module';
import { spawn } from 'child_process';
import path from 'path';
import fs from 'fs';
const require = createRequire(import.meta.url);
const { chromium } = require('/Users/mac/.local/lib/node_modules/playwright');

const args = process.argv.slice(2);
const html = path.resolve(args[0]);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const FPS = +opt('--fps', 30);
const [W, H] = (opt('--size', '1920x1080')).split('x').map(Number);
const out = path.resolve(opt('--out', 'broll_out.mp4'));
fs.mkdirSync(path.dirname(out), { recursive: true });

const browser = await chromium.launch({ channel: 'chrome', args: ['--force-device-scale-factor=1'] });
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
await page.goto('file://' + html);
await page.waitForFunction(() => window.DUR > 0 && typeof window.render === 'function', null, { timeout: 15000 });
const DUR = await page.evaluate(() => window.DUR);
const TOTAL = Math.round(DUR * FPS);
console.error(`render: ${path.basename(html)} DUR=${DUR}s ${TOTAL} frames @${FPS}fps ${W}x${H}`);

const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS),
  '-c:v', 'mjpeg', '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '16',
  '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out], { stdio: ['pipe', 'inherit', 'inherit'] });
let dead = null;
ff.on('close', c => { if (c) dead = `ffmpeg exit ${c}`; });
ff.stdin.on('error', () => { dead ??= 'ffmpeg stdin closed'; });

const t0 = Date.now();
for (let f = 0; f < TOTAL && !dead; f++) {
  await page.evaluate(t => window.render(t), f / FPS);
  const buf = await page.screenshot({ type: 'jpeg', quality: 95 });
  if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
  if (f % 60 === 0) console.error(`  ${f}/${TOTAL} ${( (Date.now()-t0)/1000 ).toFixed(0)}s`);
}
await browser.close();
ff.stdin.end();
await new Promise(r => ff.on('close', r));
if (dead) { console.error('FAILED:', dead); process.exit(1); }
console.error(`done: ${out} (${((Date.now()-t0)/1000).toFixed(0)}s)`);
