# 总装：逐镜裁切/变速/补帧 → 音画对齐 → 拼接 → ASS 字幕 → 成片
# 用法: python assemble.py --config assemble-config.json
# 配置示例（segments 起止可为 mark 名或绝对秒数；stretch 为时长拉伸系数，>1 慢放 <1 快进）：
# {
#   "raw": "rec/page.webm", "marks": "marks.json", "narration": "narration.json",
#   "output": "../产品演示-1080p.mp4",
#   "shots": [
#     {"id": "01", "segments": [["01", "02", 1.25]], "lead": 0.8, "tail": 0.6},
#     {"id": "16", "segments": [["16", "16b", 0.1818], ["16b", "17", 1.0]], "lead": 0.35, "tail": 0.55}
#   ]
# }
import argparse, json, os, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"cmd failed: {' '.join(cmd)}\n{r.stderr[-1500:]}")

def probe_dur(path):
    return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                                 '-of', 'csv=p=0', path], capture_output=True, text=True).stdout.strip())

def build_shot_video(raw, segments, target, marks, out):
    parts, fc = [], []
    for i, (a, b, stretch) in enumerate(segments):
        ta = marks[a] if isinstance(a, str) else a
        tb = marks[b] if isinstance(b, str) else b
        fc.append(f"[0:v]trim=start={ta:.3f}:end={tb:.3f},setpts={stretch:.4f}*(PTS-STARTPTS)[v{i}]")
        parts.append(f"[v{i}]")
    if len(segments) > 1:
        fc.append(f"{''.join(parts)}concat=n={len(segments)}:v=1:a=0[vcat]")
        chain = "[vcat]"
    else:
        chain = parts[0]
    # tpad 克隆末帧补齐 → 统一 30fps/yuv420p（保证 concat -c copy 可行）
    fc.append(f"{chain}tpad=stop_mode=clone:stop_duration={target:.3f},trim=duration={target:.3f},"
              f"fps=30,format=yuv420p,setsar=1[vout]")
    run(['ffmpeg', '-y', '-v', 'error', '-i', raw, '-filter_complex', ';'.join(fc),
         '-map', '[vout]', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-an', out])

def build_shot_audio(shot, lead, tail, mp3, target, out):
    fc = (f"[0:a]atrim=duration={lead:.3f}[s0];[2:a]atrim=duration={tail:.3f}[s2];"
          f"[s0][1:a][s2]concat=n=3:v=0:a=1,aresample=24000,apad=whole_dur={target:.3f}[aout]")
    run(['ffmpeg', '-y', '-v', 'error',
         '-f', 'lavfi', '-t', str(lead + 0.5), '-i', 'anullsrc=r=24000:cl=mono',
         '-i', mp3, '-f', 'lavfi', '-t', str(tail + 0.5), '-i', 'anullsrc=r=24000:cl=mono',
         '-filter_complex', fc, '-map', '[aout]', '-c:a', 'aac', '-b:a', '64k', out])

def fmt_ts(sec):
    h = int(sec // 3600); m = int(sec % 3600 // 60); s = sec % 60
    return f'{h}:{m:02d}:{s:05.2f}'

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', required=True)
    args = ap.parse_args()
    cfg = json.load(open(args.config, encoding='utf-8'))
    base_dir = os.path.dirname(os.path.abspath(args.config))
    raw = os.path.join(base_dir, cfg['raw'])
    marks = {m['shot']: m['t'] for m in json.load(open(os.path.join(base_dir, cfg['marks']), encoding='utf-8'))['marks']}
    narr = {n['shot']: n for n in json.load(open(os.path.join(base_dir, cfg['narration']), encoding='utf-8'))}
    raw_dur = probe_dur(raw)
    shots_dir = os.path.join(base_dir, 'shots')
    os.makedirs(shots_dir, exist_ok=True)

    # 字幕样式：白字 66px 加粗 + 深色底条 + 投影（用户确认的"更显眼"基准）
    style = ("Style: Main,PingFang SC,66,&H00FFFFFF,&H00FFFFFF,&H46000000,&H82000000,"
             "-1,0,0,0,100,100,0,0,3,5,2,2,130,130,58,1")

    concat_list, timing, shot_start = [], [], 0.0
    for s in cfg['shots']:
        sid = s['id']
        dur = narr[sid]['dur']
        target = s.get('lead', 0.35) + dur + s.get('tail', 0.55)
        v = os.path.join(shots_dir, f'shot-{sid}.mp4')
        a = os.path.join(shots_dir, f'audio-{sid}.m4a')
        build_shot_video(raw, s['segments'], target, marks, v)
        build_shot_audio(sid, s.get('lead', 0.35), s.get('tail', 0.55), narr[sid]['mp3'], target, a)
        withav = os.path.join(shots_dir, f'av-{sid}.mp4')
        run(['ffmpeg', '-y', '-v', 'error', '-i', v, '-i', a, '-c:v', 'copy', '-c:a', 'copy', '-shortest', withav])
        concat_list.append(withav)
        timing.append({'shot': sid, 'start': round(shot_start, 3), 'target': round(target, 3),
                       'lead': s.get('lead', 0.35), 'tail': s.get('tail', 0.55)})
        shot_start += target
        print(f"shot {sid}: target={target:.2f}s start={timing[-1]['start']:.2f}s")
    total = shot_start

    lst = os.path.join(shots_dir, 'concat.txt')
    with open(lst, 'w', encoding='utf-8') as f:
        for f_ in concat_list:
            f.write(f"file '{f_.replace(chr(92), '/')}'\n")
    base_mp4 = os.path.join(base_dir, 'base.mp4')
    run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', base_mp4])
    print(f"base: {probe_dur(base_mp4):.2f}s (plan {total:.2f}s)")

    subs = os.path.join(base_dir, 'subs.ass')
    with open(subs, 'w', encoding='utf-8') as f:
        f.write('[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\nWrapStyle: 0\nScaledBorderAndShadow: yes\n\n')
        f.write('[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n')
        f.write(style + '\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n')
        for item in timing:
            p = next(x for x in cfg['shots'] if x['id'] == item['shot'])
            for ln in narr[item['shot']]['lines']:
                a0 = item['start'] + item['lead'] + ln['t0']
                a1 = min(item['start'] + item['lead'] + ln['t1'] + 0.30, item['start'] + item['target'] - 0.15)
                if a1 <= a0:
                    a1 = a0 + 0.4
                f.write(f"Dialogue: 0,{fmt_ts(a0)},{fmt_ts(a1)},Main,,0,0,0,,{{\\fad(110,110)}}{ln['line']}\n")

    final = os.path.join(base_dir, cfg['output'])
    fade_out = max(total - 1.4, 0)
    subs_esc = subs.replace(chr(92), '/').replace(':', '\\\\:')
    vf = f"ass={subs_esc},fade=t=in:st=0:d=0.6,fade=t=out:st={fade_out:.2f}:d=1.3,format=yuv420p"
    run(['ffmpeg', '-y', '-v', 'error', '-i', base_mp4, '-vf', vf,
         '-af', f"afade=t=out:st={fade_out:.2f}:d=1.3",
         '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-c:a', 'aac', '-b:a', '96k', '-ac', '2',
         '-movflags', '+faststart', final])
    print('final:', final, f'{probe_dur(final):.2f}s')

if __name__ == '__main__':
    main()
