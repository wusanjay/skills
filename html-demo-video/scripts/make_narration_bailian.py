#!/usr/bin/env python3
# 百炼 qwen3-tts-flash 配音脚本（DashScope 原生接口）
# 注意：百炼业务空间专属端点（ws-*.maas.aliyuncs.com）没有 /audio/speech（404），
# 但 sk-ws- Key 可直接调 DashScope 主站原生接口；voice 必须放在 input.voice。
# 用法:
#   source .tts-env   # export TTS_API_KEY=sk-...（不入库）
#   python3 make_narration_bailian.py narration-text.json [--voice Cherry] [--atempo 1.09] \
#       [--out audio/] [--silence "15=5,23=9"]
# narration-text.json: {"01": "旁白文案", ...}
# --silence: 无旁白镜头生成指定时长静音（总装需要每镜都有 narration 条目）
# 输出: audio/shot-*.mp3 + narration.json（数组，元素含 shot/text/mp3/dur/lines[{line,t0,t1}]）
import argparse, json, os, re, subprocess, time, urllib.request

API = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"

def tts_wav(text, voice, key, timeout=60):
    body = json.dumps({
        "model": "qwen3-tts-flash",
        "input": {"text": text, "voice": voice},
        "parameters": {"audio": {"format": "wav"}},
    }).encode()
    req = urllib.request.Request(API, data=body, headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.load(r)
    with urllib.request.urlopen(data["output"]["audio"]["url"], timeout=timeout) as r:
        return r.read()

def ffprobe_dur(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", path], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())

def split_sentences(text):
    parts = re.split(r'(?<=[。？！；])', text)
    return [p for p in (s.strip() for s in parts) if p]

def split_long(line, limit=24):
    if len(line) <= limit:
        return [line]
    mid = len(line) // 2
    commas = [i for i, ch in enumerate(line) if ch in '，、：']
    if not commas:
        return [line]
    cut = min(commas, key=lambda i: abs(i - mid))
    return split_long(line[:cut + 1], limit) + split_long(line[cut + 1:], limit)

CLEAN_RE = re.compile(r'[。？！；，、：「」——？…·\s]')

def subtitle_lines(text, dur):
    """无词级时间戳时按去标点字符数比例映射句级字幕时间轴"""
    lines = []
    for sent in split_sentences(text):
        lines.extend(split_long(sent))
    clean = lambda s: CLEAN_RE.sub('', s)
    total = len(clean(text)) or 1
    acc, out = 0, []
    for ln in lines:
        n = len(clean(ln))
        out.append({'line': ln, 't0': round(dur * acc / total, 3),
                    't1': round(dur * (acc + n) / total, 3)})
        acc += n
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('narration')
    ap.add_argument('--voice', default='Cherry')
    ap.add_argument('--out', default='audio')
    ap.add_argument('--atempo', type=float, default=1.0, help='>1 加快语速')
    ap.add_argument('--silence', default='', help='无旁白镜: "15=5,23=9"')
    args = ap.parse_args()
    key = os.environ['TTS_API_KEY']
    os.makedirs(args.out, exist_ok=True)
    silent = dict(kv.split('=') for kv in args.silence.split(',') if kv)
    silent = {k: float(v) for k, v in silent.items()}

    texts = json.load(open(args.narration, encoding='utf-8'))
    result = []
    all_shots = sorted(set(texts) | set(silent), key=lambda s: (0, s) if s in texts else (1, s))
    for shot in all_shots:
        mp3 = os.path.abspath(os.path.join(args.out, f'shot-{shot}.mp3'))
        if shot in silent and shot not in texts:
            dur = silent[shot]
            subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi',
                            '-t', str(dur), '-i', 'anullsrc=r=24000:cl=mono',
                            '-c:a', 'libmp3lame', '-b:a', '96k', mp3], check=True)
            result.append({'shot': shot, 'text': '', 'mp3': mp3, 'dur': dur,
                           'words': [], 'lines': []})
            print(f'shot {shot}: SILENT {dur}s')
            continue
        text = texts[shot]
        print(f'shot {shot}: 合成中...', end=' ', flush=True)
        with open(p := os.path.join(args.out, f'shot-{shot}-raw.wav'), 'wb') as f:
            f.write(tts_wav(text, args.voice, key))
        fc = 'atempo=%.4f' % args.atempo if abs(args.atempo - 1.0) > 1e-3 else 'anull'
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', p, '-af', fc,
                        '-c:a', 'libmp3lame', '-b:a', '128k', mp3], check=True)
        os.remove(p)
        dur = ffprobe_dur(mp3)
        cps = len(CLEAN_RE.sub('', text)) / dur if dur else 0
        result.append({'shot': shot, 'text': text, 'mp3': mp3, 'dur': round(dur, 3),
                       'words': [], 'lines': subtitle_lines(text, dur)})
        print(f'dur={dur:.2f}s {cps:.1f}字/s')
        time.sleep(0.4)

    json.dump(result, open('narration.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    total = sum(r['dur'] for r in result)
    print(f'\n总旁白时长: {total:.1f}s（含静音镜）')
    print('已生成: narration.json + audio/shot-*.mp3')

if __name__ == '__main__':
    main()
