#!/usr/bin/env python3
# 成片 QC：按每镜中段抽帧拼九宫格 + 各镜旁白窗口音量检查 + 成片参数核对。
# 用法: python3 qc.py [成片.mp4]   （需先有 assemble-config.json + narration.json）
import json, os, subprocess, sys, math

def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)

def main():
    final = sys.argv[1] if len(sys.argv) > 1 else '产品演示-1080p.mp4'
    cfg = json.load(open('assemble-config.json', encoding='utf-8'))
    narr = {n['shot']: n for n in json.load(open('narration.json', encoding='utf-8'))}
    os.makedirs('qc', exist_ok=True)

    # 1) 成片参数
    p = sh(['ffprobe', '-v', 'error', '-show_entries',
            'stream=codec_name,width,height,r_frame_rate:format=duration', '-of', 'json', final])
    info = json.loads(p.stdout)
    v = next(s for s in info['streams'] if s.get('width'))
    dur = float(info['format']['duration'])
    print(f"成片: {v['width']}x{v['height']} {v['codec_name']} {v['r_frame_rate']} 时长 {dur:.1f}s")

    # 2) 逐镜中段抽帧 → 九宫格（每张 4x2，帧序即镜序）
    starts, acc = [], 0.0
    for s in cfg['shots']:
        target = s.get('lead', .35) + narr[s['id']]['dur'] + s.get('tail', .55)
        starts.append((s['id'], acc + target * 0.55))
        acc += target
    frames = []
    for sid, t in starts:
        out = f'qc/f-{sid}.png'
        sh(['ffmpeg', '-y', '-v', 'error', '-ss', f'{t:.2f}', '-i', final, '-frames:v', '1', out])
        frames.append(out)

    per, cols = 8, 4
    for g in range(math.ceil(len(frames) / per)):
        group = frames[g * per:(g + 1) * per]
        inputs, fc = [], ''
        for i, f in enumerate(group):
            inputs += ['-i', f]
            fc += f"[{i}:v]scale=640:360[v{i}];"
        for i in range(len(group)):
            fc += f"[v{i}]"
        fc += f"xstack=inputs={len(group)}:layout=" + "|".join(
            f"{(i % cols)*640}_{(i // cols)*360}" for i in range(len(group)))
        sh(['ffmpeg', '-y', '-v', 'error', *inputs, '-filter_complex', fc, f'qc/grid-{g+1}.png'])
        print(f"qc/grid-{g+1}.png ← {', '.join(os.path.basename(f) for f in group)}")

    # 3) 各镜旁白窗口音量（静音镜跳过）
    quiet = []
    for s in cfg['shots']:
        n = narr[s['id']]
        if not n['text']:
            continue
        lead = s.get('lead', .35)
        start = next(t for sid, t in starts if sid == s['id']) - (n['dur'] + lead) * 0.55 + lead
        p = sh(['ffmpeg', '-ss', f'{start:.2f}', '-t', f"{n['dur']:.2f}", '-i', final,
                '-af', 'volumedetect', '-f', 'null', '-'])
        mean = [l for l in p.stderr.splitlines() if 'mean_volume' in l]
        db = float(mean[0].split(':')[1].replace(' dB', '')) if mean else -99
        if db < -40:
            quiet.append((s['id'], round(db, 1)))
    print('旁白音量异常镜头:', quiet if quiet else '无（全部 > -40dB）')

if __name__ == '__main__':
    main()
