# 拼装详解：混合走位 + 强字幕（filter_complex 模板）

时间轴基准 = **数字人视频（dh_out.mp4）内的绝对时间**。
dh 视频结构 = lead 1.5s 静默 + 驱动音频 + tail 3s 静默，所以配音段 N 在视频内的起点 =
`1.5 + (前面所有段时长 + 段间停顿之和) + 0.3(可选的段内起始偏移)`。

## 变量约定

- `DH` 数字人视频（竖屏，如 544×960，含克隆配音音轨）
- `BG` 背景轨（1920×1080@30，与 DH 等长，见下文构建）
- 走位时间窗（默认混合走位，可按片长等比调）：
  - S1 全屏 `0 ~ 6.4`
  - S2 画中画右下 `6.4 ~ 42.7`
  - S3 侧位放大 `42.7 ~ 54.1`
  - S4 全屏 `54.1 ~ 结尾`

## 第一步：背景轨

```bash
# 人像虚化底（竖屏源 cover 成横屏再高斯模糊）
ffmpeg -y -i $DH -vf "scale=1920:3413:force_original_aspect_ratio=increase,crop=1920:1080,gblur=sigma=30,trim=duration=12,setpts=PTS-STARTPTS,format=yuv420p" -an bg_blur.mp4

# 截图 Ken Burns 段——注意 zoompan 前必须 fps=30！
ffmpeg -y -loop 1 -t 12.5 -i shot.png -vf \
  "fps=30,scale=2880:1620,zoompan=z='1+0.0005*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1920x1080:fps=30,format=yuv420p" -an bg_x.mp4

# 按时间轴顺序 concat（各段时长之和 = DH 总长）
printf "file 'bg_blur1.mp4'\nfile 'bg_clinic.mp4'\n..." > bg_list.txt
ffmpeg -y -f concat -safe 0 -i bg_list.txt -c copy bg_track.mp4
```

## 第二步：走位 + 字幕 + 成片

```bash
FF=/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg   # 必须 ffmpeg-full，brew 默认版无 drawtext
FONT="/System/Library/Fonts/STHeiti Medium.ttc"

$FF -y -i bg_track.mp4 -i $DH -filter_complex "\
[1:v]split=4[d1][d2][d3][d4];\
[d1]scale=607:1080,setsar=1[v1];\
[d2]scale=-2:540,setsar=1[v2];\
[d3]scale=-2:720,setsar=1[v3];\
[d4]scale=607:1080,setsar=1[v4];\
[0:v][v1]overlay=x=(W-w)/2:y=0:enable='between(t,0,6.4)'[o1];\
[o1][v2]overlay=x=W-w-40:y=H-h-40:enable='between(t,6.4,42.7)'[o2];\
[o2][v3]overlay=x=120:y=(H-h)/2:enable='between(t,42.7,54.1)'[o3];\
[o3][v4]overlay=x=(W-w)/2:y=0:enable='between(t,54.1,70)'[o4];\
[o4]drawtext=fontfile='$FONT':textfile=subs/title.txt:fontsize=64:fontcolor=white:x=(w-text_w)/2:y=790:box=1:boxcolor=0x2b1810@0.72:boxborderw=26:enable='between(t,0.5,5.2)'[t1];\
[t1]drawtext=fontfile='$FONT':textfile=subs/s1.txt:fontsize=46:fontcolor=white:x=(w-text_w)/2:y=950:box=1:boxcolor=black@0.55:boxborderw=18:enable='between(t,1.8,6.2)'[t2];\
[t2]drawtext=fontfile='$FONT':textfile=subs/s5.txt:fontsize=46:fontcolor=white:x=(w-text_w)/2:y=950:box=1:boxcolor=black@0.55:boxborderw=18:enable='between(t,54.3,62.9)'[t3];\
[t3]drawtext=fontfile='$FONT':textfile=subs/ending.txt:fontsize=56:fontcolor=white:x=(w-text_w)/2:y=460:box=1:boxcolor=0x2b1810@0.72:boxborderw=24:enable='between(t,63.2,65.4)'[t4];\
[t4]fade=t=in:st=0:d=0.5,fade=t=out:st=64.9:d=0.6,format=yuv420p[vout]" \
-map "[vout]" -map 1:a -af "afade=t=out:st=64.5:d=0.9" \
-c:v libx264 -preset medium -crf 18 -c:a aac -b:a 192k -movflags +faststart out.mp4
```

要点：
- 每条 drawtext 一个 `textfile=`（中文放文件里，绕开 filter 转义地狱）
- 字幕样式：底部 `y=950`、`fontsize=46`、`box=black@0.55`（强字幕）；片头名牌/片尾落版用 `fontsize=56-64` + 品牌深色底 `0x2b1810@0.72`
- 音频直接用 DH 的音轨（内含克隆配音），不需要单独混音；只在结尾加 afade
- 段数按台词多少增减 drawtext 层与背景段

## 时间轴速算

```
视频内语音起点 = 1.5 + Σ(前段时长 + 停顿)
例: seg1=4.3s, seg2=12.0s, 停顿0.45s
  seg1 起点 = 1.5 + 0.3   = 1.8
  seg2 起点 = 1.8 + 4.3 + 0.45 = 6.55
走位切换点尽量落在停顿处，不要切断一句话。
```
