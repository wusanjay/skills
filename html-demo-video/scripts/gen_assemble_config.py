#!/usr/bin/env python3
# 生成 assemble-config.json：按 marks.json 实际时间戳 + narration.json 时长，
# 自动计算每镜分段与变速系数，交给 assemble.py 总装。
# 变速规则（实测沉淀）：
#   - 实拍 ≤ 目标：原速，总装 tpad 克隆末帧补齐（静态画面补 2-3s 不可见）
#   - 超长 ≤1.15 倍：慢放精确吸收（变速在输出里几乎不可察觉）
#   - 超长 >1.15 倍：原速保留前段、裁尾（慢放再裁会丢更多内容）
# 用法:
#   python3 gen_assemble_config.py [--marks marks.json] \
#       [--stretch 03,15,23] [--split "21=21b"]
#   --stretch: 整镜快进的蒙太奇镜（压到旁白时长）
#   --split:   镜内分段“前段正常+后段快进”，值为分段点 mark 名（如 21 镜里 mark('21b')）
import argparse, json, os, glob

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--marks', default='marks.json')
    ap.add_argument('--out', default='assemble-config.json')
    ap.add_argument('--stretch', default='', help='整镜快进镜号，逗号分隔')
    ap.add_argument('--split', default='', help='分段镜: "镜号=分段mark"，逗号分隔')
    args = ap.parse_args()
    stretch_shots = set(s.strip() for s in args.stretch.split(',') if s.strip())
    split_shots = dict(kv.split('=') for kv in args.split.split(',') if kv.strip())

    marks_data = json.load(open(args.marks, encoding='utf-8'))
    raw_marks = {m['shot']: m['t'] for m in marks_data['marks']}
    narr = {n['shot']: n for n in json.load(open('narration.json', encoding='utf-8'))}
    raw = marks_data.get('video') or sorted(glob.glob('rec/*.webm'))[-1]
    raw = os.path.relpath(raw, '.')

    # 镜头序列 = 有旁白条目的 mark（分段 mark / END 只作边界）
    order = sorted((s for s in narr if s in raw_marks), key=lambda s: raw_marks[s])
    shots = []
    for i, sid in enumerate(order):
        nxt_mark = order[i + 1] if i + 1 < len(order) else 'END'
        avail = raw_marks[nxt_mark] - raw_marks[sid]
        dur = narr[sid]['dur']
        # 首镜 lead 加大（观众入场），末镜 tail 加大（配淡出），纯静音镜不留白
        if sid in stretch_shots or sid in split_shots:
            lead, tail = 0.0, 0.0
        elif i == 0:
            lead, tail = 0.8, 0.55
        elif i == len(order) - 1:
            lead, tail = 0.6, 1.0
        else:
            lead, tail = 0.35, 0.55
        target = lead + dur + tail
        if sid in split_shots:
            split_mark = split_shots[sid]
            head = raw_marks[split_mark] - raw_marks[sid]
            keep = min(head, target * 0.5)
            stretch2 = max((target - keep) / max(avail - head, 0.1), 0.15)
            segments = [[sid, split_mark, 1.0], [split_mark, nxt_mark, round(stretch2, 4)]]
        elif sid in stretch_shots:
            segments = [[sid, nxt_mark, round(target / avail, 4)]]
        elif avail > target:
            ratio = avail / target
            stretch = round(ratio, 4) if ratio <= 1.15 else 1.0
            segments = [[sid, nxt_mark, stretch]]
        else:
            segments = [[sid, nxt_mark, 1.0]]
        shots.append({'id': sid, 'segments': segments, 'lead': lead, 'tail': tail})
        est = sum(((raw_marks[b] if isinstance(b, str) else b) - (raw_marks[a] if isinstance(a, str) else a)) * st
                  for a, b, st in segments)
        flag = '⚠️裁尾' if est > target + 0.05 else ''
        print(f"shot {sid}: avail={avail:6.2f}s target={target:6.2f}s est={est:6.2f}s {flag}")

    json.dump({'raw': raw, 'marks': args.marks, 'narration': 'narration.json',
               'output': '产品演示-1080p.mp4', 'shots': shots},
              open(args.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    total = sum(s['lead'] + narr[s['id']]['dur'] + s['tail'] for s in shots)
    print(f"\n计划总时长: {total:.1f}s → {args.out} (raw={raw})")

if __name__ == '__main__':
    main()
