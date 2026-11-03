#!/usr/bin/env python3
# 字幕烧录（本机 ffmpeg 无 libass/drawtext 时的替代方案；有 libass 时直接用 ass= 滤镜更快）：
# 解析 assemble.py 产出的 subs.ass 时间轴 → Pillow 逐条渲染字幕条 PNG
# → ffmpeg overlay 链按 enable 窗口叠加 → 淡入淡出 → 成片。
# 两个实战坑（已修）：
#   1) 必须 -map 0:a，否则 filter_complex 只映射视频、成片无声
#   2) 淡出起点要用成片总长，不能用最后一条字幕结束时间（会提前黑屏吞掉尾镜）
# 用法: python3 burn_subs.py [base.mp4] [subs.ass] [成片.mp4]
import re, subprocess, sys, os
from PIL import Image, ImageDraw, ImageFont

MARGIN_V_1080 = 58  # 1080p 下的底部留白，其他分辨率按比例缩放
FONT_CANDIDATES = [
    '/System/Library/Fonts/Hiragino Sans GB.ttc',      # macOS（PingFang.ttc PIL 打不开）
    '/System/Library/Fonts/STHeiti Medium.ttc',
    '/System/Library/Fonts/Supplemental/Songti.ttc',
    '/Library/Fonts/Arial Unicode.ttf',
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',  # Linux
]

TS = re.compile(r'(\d+):(\d+):(\d+)\.(\d+)')

def parse_ts(s):
    h, m, sec, cs = TS.match(s).groups()
    return int(h) * 3600 + int(m) * 60 + int(sec) + int(cs) / 100

def pick_font(size):
    for p in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(p, size, index=0)
        except Exception:
            continue
    raise SystemExit('未找到可用中文字体，请把字体路径加进 FONT_CANDIDATES')

def main():
    base = sys.argv[1] if len(sys.argv) > 1 else 'base.mp4'
    ass = sys.argv[2] if len(sys.argv) > 2 else 'subs.ass'
    out = sys.argv[3] if len(sys.argv) > 3 else '产品演示-1080p.mp4'

    lines = []
    for row in open(ass, encoding='utf-8'):
        if not row.startswith('Dialogue:'):
            continue
        parts = row.split(',', 9)
        a0, a1 = parse_ts(parts[1]), parse_ts(parts[2])
        text = re.sub(r'\{[^}]*\}', '', parts[9]).rstrip('\n').strip()
        if text:
            lines.append((a0, a1, text))
    # 相邻条窗口不得重叠（时间轴来源的 +0.3s 尾延可能压到下一条开头，同屏叠两条）
    lines.sort(key=lambda x: x[0])
    for i in range(len(lines) - 1):
        if lines[i][1] > lines[i + 1][0] - 0.08:
            lines[i] = (lines[i][0], max(lines[i + 1][0] - 0.08, lines[i][0] + 0.4), lines[i][2])
    print(f'字幕 {len(lines)} 条')

    # 按底片分辨率缩放字号与底部留白（1080p 基准）
    probe_out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
                                'stream=height', '-of', 'csv=p=0', base],
                               capture_output=True, text=True).stdout.strip().splitlines()
    video_h = next(int(h) for h in probe_out if h.strip().isdigit())
    scale = video_h / 1080
    font = pick_font(max(round(62 * scale), 12))
    margin_v = max(round(MARGIN_V_1080 * scale), 4)
    probe = ImageDraw.Draw(Image.new('RGBA', (8, 8)))
    strips = []
    os.makedirs('build-subs', exist_ok=True)
    for i, (a0, a1, text) in enumerate(lines):
        box = probe.textbbox((0, 0), text, font=font)
        tw, th = box[2] - box[0], box[3] - box[1]
        pad_x, pad_y = 26, 12
        W, H = tw + pad_x * 2, th + pad_y * 2
        img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([0, 0, W - 1, H - 1], radius=12, fill=(10, 14, 22, 186))
        x, y = pad_x - box[0], pad_y - box[1]
        d.text((x + 3, y + 3), text, font=font, fill=(0, 0, 0, 150),
               stroke_width=3, stroke_fill=(0, 0, 0, 150))
        d.text((x, y), text, font=font, fill=(255, 255, 255, 255),
               stroke_width=3, stroke_fill=(0, 0, 0, 255))
        p = f'build-subs/sub-{i:03d}.png'
        img.save(p)
        strips.append((a0, a1, p, H))
    print('字幕条渲染完成')

    cmd = ['ffmpeg', '-y', '-v', 'error', '-i', base]
    for _, _, p, _ in strips:
        cmd += ['-i', p]
    fc, prev = [], '0:v'
    for i, (a0, a1, _, H) in enumerate(strips):
        outl = f'v{i+1}'
        fc.append(f"[{prev}][{i+1}:v]overlay=x=(W-w)/2:y={video_h - margin_v - H}:"
                  f"enable='between(t,{a0:.3f},{a1:.3f})'[{outl}]")
        prev = outl
    total = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                                  '-of', 'csv=p=0', base], capture_output=True,
                                 text=True).stdout.strip())
    fade_out = max(total - 1.4, 0)
    fc.append(f"[{prev}]fade=t=in:st=0:d=0.6,fade=t=out:st={fade_out:.2f}:d=1.3,format=yuv420p[vout]")
    cmd += ['-filter_complex', ';'.join(fc), '-map', '[vout]', '-map', '0:a',
            '-af', f'afade=t=out:st={fade_out:.2f}:d=1.3',
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
            '-c:a', 'aac', '-b:a', '96k', '-ac', '2', '-movflags', '+faststart', out]
    print('开始烧录合成...')
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-2000:])
        sys.exit(1)
    d = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                        '-of', 'csv=p=0', out], capture_output=True, text=True).stdout.strip()
    print(f'完成: {out} ({float(d):.1f}s)')

if __name__ == '__main__':
    main()
