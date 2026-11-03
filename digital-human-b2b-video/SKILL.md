---
name: digital-human-b2b-video
description: 真人数字人 B2B 产品介绍视频完整流水线：底片拍摄要求 → DashScope 声音克隆 → 口型驱动（GPU 服务器 LiveTalking 或本机离线 wav2lip，两条路径都实测）→ 混合走位拼装 + 强字幕。适用于"用真人员工/老板的形象做产品讲解视频"、"数字人口播"、"声音克隆配音"、"真人出镜宣传片"等需求。核心原则：真人底片只重绘嘴部（身份 100% 保真），绝不用生成模型画脸。
---

# 真人数字人 B2B 视频流水线

## 铁律（先读这个）

1. **绝不用生成模型画人脸**（图生视频模型如 MiniMax-H3/Wan 会重画每一帧 → 换发型、改五官、加衣服，"同事"直接消失）。正确姿势：**真人底片 + 音频驱动口型**（wav2lip/musetalk 只重绘嘴部区域，脸是原样搬运）。
2. **成片必须完整多模态看片验收**（Read 视频 MP4），截帧只能辅助定位问题——静态帧看不出换脸漂移、口型错位、构图跑偏。
3. **分层解耦**：脚本、配音、截图 B-roll、数字人 avatar 是四个独立资产。改台词只重做 TTS+口播录制；换人只重做 avatar。不要把任何一层焊死。

## 前置条件

| 依赖 | 位置/获取 | 用途 |
|---|---|---|
| GPU 服务器（ssh 免密） | 如 `ssh qkkj`，3×3090 | LiveTalking 口型推理 |
| LiveTalking 部署 | 服务器 `/www/wwwroot/LiveTalking` | 见 `references/deploy.md`（一次性） |
| 百炼 API key | 配置在 `~/.bailian/config.json`（bl CLI） | TTS / ASR / 声音克隆 |
| bl CLI ≥2.5 | `bl --version` | `speech synthesize / recognize` |
| ffmpeg-full | `/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg` | 拼装+drawtext（**brew 默认 ffmpeg 是精简版无 drawtext**） |
| python3 (Mac) | 系统 python3 即可 | 客户端脚本（aiortc 在服务器上跑，Mac 不需要） |

## SOP 九阶段

### P1 底片拍摄（给拍摄者的要求清单）

- 手机横屏或竖屏均可（竖屏正好做侧边栏/画中画），**半身入镜，脸占画面 1/3 左右**
- 光线均匀正面、背景干净、**不开美颜**、不要大角度侧脸
- **必须"正在自然说话"的状态**（随便聊天 30-60 秒，内容无所谓——嘴最后会被替换；我们只要说话时的自然头动/眨眼/呼吸）
- 一次性资产：录一次永久复用（avatar 化后任何脚本都能驱动）
- 收到后先用 `ffprobe` 查时长/分辨率，抽帧确认无手持道具遮挡、镜片反光不严重，选出"干净窗口"（如 100-140s）

### P2 声音克隆（他本人的声音）

从底片挑 10-25 秒最清晰的语音（响度最高窗口），降噪+归一化：
```bash
ffmpeg -y -i base_full_16k.wav -ss 112 -t 15 -af "afftdn=nf=-25,loudnorm=I=-20:TP=-2:LRA=7" clone_sample_15s.wav
```
注册克隆音色（脚本在 `scripts/enroll_voice.py`）：
```bash
python3 scripts/enroll_voice.py --sample clone_sample_15s.wav --prefix yuejian
# 输出 voice_id 形如 cosyvoice-v3.5-flash-<prefix>-<hash>，存入 voice_id.txt（90 天过期）
```
原理（踩坑换来的，勿改接口形态）：新接口 `POST /api/v1/services/audio/tts/customization`，`model=voice-enrollment`，`action=create_voice`，`target_model=cosyvoice-v3.5-flash`，**audio 必须是 URL**——先走 `GET /api/v1/uploads?action=getPolicy&model=cosyvoice-v3.5-flash` 拿 policy，multipart POST 到 `upload_host`，拼 `oss://<upload_dir>/<filename>`（bucket 名就含在 upload_dir 开头），请求头带 `X-DashScope-OssResourceResolve: enable`。旧 voice-enrollment base64 接口对 v3.5 无效（Model not exist）。prefix **≤10 字符**。

### P3 语速校准（关键！必须用 VAD 扣除静默）

**禁止**用"总时长÷总字数"——底片里停顿+空镜通常占 30%+，会把语速低估 30-48%（实测案例：209s 底片有 68.5s 静默，粗算 3.1 字/秒，真实 4.62 字/秒，导致 rate 0.85 把人物放慢了 21%）。

正确做法 = ASR 字数 + VAD（silencedetect）扣除静默：

```bash
# 1) ASR 拿字数
ffmpeg -y -i 底片.mp4 -vn -ac 1 -ar 16000 base_16k.wav
bl speech recognize --url base_16k.wav --model qwen-audio-3.0-asr-flash   # 统计汉字数 W

# 2) VAD 测有效语音时长（阈值按信噪比调：底片音量低用 -32dB，正常 TTS 用 -38dB；最短静默 0.4-0.6s）
ffmpeg -hide_banner -i 底片.mp4 -af silencedetect=noise=-32dB:d=0.6 -f null - 2>&1 | grep silence_
# 有效语音 T = 总时长 - Σ(静默段)

# 3) 底片真实语速 = W / T
```

若手头已有一版成片，用比例法一步修正（最准）：
```
新 rate = 旧 rate × (底片语速 / 成片语速)
```
实测案例：0.85 × (4.62/3.66) = 1.07——即该人物接近 TTS 默认语速，最终建议 rate **1.05**。

简化替代（无成片时）：截底片中一段"连续稳定说话、无停顿"的 20-30 秒，字数÷该段时长。VAD 法更准，优先 VAD。

### P4 TTS 配音（克隆音色）

```bash
BAILIAN_CALLER_TYPE=agent BAILIAN_CALLER_NAME=codex BAILIAN_SKILL_NAME=bailian-gen BAILIAN_SKILL_VERSION=2.5.0 \
bl speech synthesize --model cosyvoice-v3.5-flash --voice "$(cat voice_id.txt)" \
  --rate 0.85 --format wav --sample-rate 24000 --text "台词..." --out tts/seg1.wav
```
脚本文案注意：数字转汉字（"1到30天"→"一到三十天"）、去掉引号括号。合并成连续驱动音频（段间 0.45-0.55s 停顿）：
```bash
ffmpeg -y -i tts/seg1.wav -i tts/seg2.wav ... -filter_complex \
  "aevalsrc=0:d=0.45[s1];...;[0:a][s1][1:a]...concat=n=N:v=0:a=1[out]" -map "[out]" -ar 24000 vo_full.wav
```

### P5 部署检查（已有部署则跳过）

```bash
bash scripts/deploy_check.sh qkkj
# 任何一项失败 → 按 references/deploy.md 完整部署（约 30-60 分钟，多数时间在下权重）
```

### P5.5 无 GPU 服务器：本机离线 wav2lip 推理（2026-11 实测走通，Mac CPU 全程可跑）

服务器不可达（下线/无 VPN）时的替代路径。**不要在 Mac 上跑 LiveTalking 全套**——WebRTC 实时流要求实时帧率，CPU 推理跟不上；正确姿势是用官方 Wav2Lip repo 做**离线推理**（逐帧出片，不要求实时）：

```bash
mkdir ~/work-dh && cd ~/work-dh
git clone --depth 1 https://github.com/Rudrabha/Wav2Lip.git
python3.11 -m venv venv
venv/bin/pip install torch torchvision "numpy==1.23.5" "librosa==0.8.1" "scipy==1.10.1" opencv-python tqdm -i https://pypi.tuna.tsinghua.edu.cn/simple
# 权重：wav2lip256.pth（LiveTalking gdrive 文件夹）+ s3fd.pth（adrianbulat 直连）
```

**256 权重 × 官方 repo 的四处不对齐，逐一修**（任何一处没修都会崩，报错位置互不指向根因）：

1. **架构**：官方 repo 是 96 模型，wav2lip256.pth 需 256 架构——把 LiveTalking 的 `avatars/wav2lip/models/wav2lip_v2.py` 覆盖到 `Wav2Lip/models/wav2lip.py`，并同步 `models/__init__.py` 的导出（v2 含 `Wav2Lip_disc_qual`）。
2. **conv_384.py 缺失**：v2.py `from .conv_384 import ...`，但 gitee 镜像的 LiveTalking 没有此文件（只有 conv.py，参数语义不同，直接换成 conv 会 forward 崩 "kernel size can't be greater than input"）。从 GitHub 原版 LiveTalking 取 conv_384.py。
3. **checkpoint 解包**：wav2lip256.pth 是训练产物（`{"state_dict":..., "optimizer":...}` 包层），加载后取 `checkpoint['state_dict']`（注意判别"包层"与"裸权重"，两种形态都可能出现）。
4. **img_size**：官方 `inference.py` 硬编码 `args.img_size = 96`，256 模型改为 256，否则 forward 尺寸崩溃。

**其他必踩的坑**：

- **gdown 假 100%**：大权重显示下载完成但尾部截断（torch.load 报 `unexpected EOF`）——下载后必须 `torch.load` 验证一次再进推理；文件坏时删掉重下（`--continue` 会误报 skip）。
- **人脸检测缓存（多段共用底片必做）**：650 帧检测 CPU 约 8 分钟，每段音频不同但底片相同。给 inference.py 打"帧数感知缓存"补丁：写 `{face}.{n}frames.detcache.pkl`，读时取"帧数最小且 ≥ 当前所需"的缓存再截断——固定文件名会让短音频结果覆盖长缓存，长音频段越界 IndexError。
- **`temp/` 目录预建**：inference.py 用 `cv2.VideoWriter('temp/result.avi')`，目录不存在时**静默不产出**，直到最后 ffmpeg 合并报"result.avi 不存在"——错误位置远离根因。
- **每段耗时预期**：检测（无缓存）650 帧 ≈ 8 分钟 @Mac CPU；有缓存后每段推理 ≈ 2-4 分钟。串行批量脚本 + 每段独立 log + `EXIT=$?` 追加写 batch.log。

### P6 Avatar 生成（一次性）

```bash
ssh qkkj 'curl -s -X POST http://127.0.0.1:8010/api/avatar/task \
  -F model=wav2lip -F avatar_id=<名字> -F img_size=256 \
  -F video_file=@/www/wwwroot/LiveTalking/data/tmp/base_clip.mp4'
# 轮询 GET /api/avatar/task/<task_id>，status=completed 即可
# 首次会在服务器下载 s3fd 人脸检测权重（慢，Mac 下载后传到 /root/.cache/torch/hub/checkpoints/ 更快）
```

### P7 口播驱动录制（每次出片都跑）

**客户端必须在服务器本机跑（loopback）**——跨网段 Mac→服务器的 UDP 打洞会被路由器拦，ICE 直接 failed：
```bash
scp scripts/lt_client.py qkkj:/www/wwwroot/LiveTalking/
ssh qkkj 'cd /www/wwwroot/LiveTalking && python3.10 lt_client.py --host 127.0.0.1 \
  --avatar <avatar名> --audio data/tmp/vo_full.wav --out /tmp/dh_out.mp4'
scp qkkj:/tmp/dh_out.mp4 ./dh_out.mp4
```
产出 = 544×960（跟随底片）连续口播视频，时长 = lead 1.5s + 音频 + tail 3s。开头 LiveTalking 左上角有小水印，拼装时人像缩放后基本不可见。

### P8 拼装（混合走位 + 强字幕）

时间轴以 **dh 视频内绝对时间**为准，但锚点必须用 **VAD 实测语音起点**——humanaudio 提交有约 1s 处理延迟，按 lead 理论值 1.5s 排会整体偏早。四步：

1. **背景轨**：人像虚化底（`scale=1920:3413,crop=1920:1080,gblur=sigma=30`）+ 产品截图 Ken Burns 交替，concat 成总长视频。**zoompan 前必须加 `fps=30`**，否则 -loop 1 默认 25fps 输入导致输出时长缩水。
2. **人像走位 overlay**（split 4 路、各段 enable 时间窗）：
   - 开场/结尾全屏：`scale=607:1080, x=(W-w)/2, y=0`（竖屏源）
   - 中段画中画：`scale=-2:540, x=W-w-40, y=H-h-40`
   - 强调段侧位：`scale=-2:720, x=120, y=(H-h)/2`
3. **强字幕 drawtext**：`fontfile='/System/Library/Fonts/STHeiti Medium.ttc':textfile=subs/sN.txt:fontsize=46:box=1:boxcolor=black@0.55`，**必须用 textfile= 传中文**（防转义地狱）；片头名牌/片尾落版用大号+品牌深色底。首尾 fade，音频用 dh 的音轨（内含克隆配音）+ afade 收尾。
4. **元视频/对比类内容**：数字人恒为大画面主说话者；底片等含人素材一律做成**小窗+白框+文字标签**（如"你录的视频"，竖屏约 420×748 置右上），绝不全屏——全屏画面里任何动嘴的人都会被观众当成配音来源，产生"音画不同步"的错觉。成片自指展示素材竖屏化用"横屏居中 + 上下虚化填充"。

**看板预检（首版合成后、定稿前必做）**——抽关键帧拼成看板自检，只修最严重的 3 个问题后重合成，比成片后完整看片更前置省轮次：
```bash
ffmpeg -i 首版.mp4 -vf "select='eq(n,60)+eq(n,300)+eq(n,630)+eq(n,1080)',scale=270:-1,tile=2x2" -frames:v 1 board.png
```
检查清单：缩到手机尺寸字幕清不清；画面里有没有其他动嘴的人被当成说话者；语音起点与首句字幕对位（VAD 实测）；前 2 秒有没有钩子；末帧能否当封面；有无水印/乱入内容。

**多画幅同源（一次内容出横竖双版）**——素材（dh 口播、B-roll、字幕文本）与时间轴（语音锚点/切点/字幕 enable）完全共用，只有布局参数按画幅各配一套：
| 参数 | 横屏 1920×1080 | 竖屏 1080×1920 |
|---|---|---|
| 人像全屏 | scale=607:1080 居中（竖屏源模糊底补边） | scale=1080:1920 原生直铺 |
| 人像画中画 | scale=-2:540 右下 | scale=-2:680 右上 |
| 字幕 | fontsize=46，y=950 | fontsize=60，y=1500 |

各画幅分别出看板确认后再出片，**禁止拿横屏硬裁竖屏**。方法论参考：Eian《6 步构建视频工作流》（X @EianLu）、开源实现 Lemo Opuscar（已 star）。

**B-roll 动效层（可选升级，替代静态截图 Ken Burns）**——确定性代码渲染：HTML 页面暴露 `window.DUR`（总时长）和 `window.render(t)`（给时间 t 画那一帧），渲染器逐帧截图喂 ffmpeg，帧率精确、改参数即改画面：
```bash
node scripts/render_broll.mjs assets/tpl_focus.html --fps 30 --size 1920x1080 --out bg_focus.mp4   # 界面聚焦（截图+运镜+聚焦框，改页内 FOCl/cam 坐标适配新截图）
node scripts/render_broll.mjs assets/tpl_counter.html --fps 30 --size 1920x1080 --out bg_counter.mp4  # 数字滚动（改 cards 数组的 target/文案）
```
依赖：Node + 全局 playwright（`channel:'chrome'` 驱动系统 Chrome）+ ffmpeg-full；渲染近实时（12s 片约 13s）。产出 mp4 直接替换 P8 背景轨里的静态 Ken Burns 段（concat 前先统一到与背景轨相同的 fps/尺寸/pix_fmt）。新动效 = 复制模板改页面里的 `window.render(t)`，保持纯函数（同一 t 必须出同一画面）。

完整 filter_complex 模板见 `references/assembly.md`。

### P9 验收（不可跳过）

1. `Read` 成片 MP4 **完整看片**：身份？口型跟字？走位切换是否突兀？字幕错别字/越界？
2. 抽帧只用于回看定位具体秒数。
3. 音频抽 3 个时间点 `volumedetect` 确认配音在位。

## 坑速查表（全是实测踩过）

| 坑 | 症状 | 解法 |
|---|---|---|
| B-roll 里出现其他说话者 | 观众把全屏 B-roll 里动嘴的人当成配音来源 → "音画不同步"（音画技术上其实是同步的） | **说话者永远只有数字人**：数字人保持大画面主位，其他含人素材一律缩小成带白框+文字标签的"展示物"小窗 |
| humanaudio 处理延迟 ~1s | 按理论 lead 排的切点/字幕全部提前，音画错位感 | 拼装时间轴以**录制成片的 VAD 实测语音起点**为准，不用 lead 理论值；切点/字幕整体平移 |
| drawbox 坐标变量 | `x=W-434` 报 Error evaluating expression | drawbox 用 `iw/ih`（overlay 才用 `W/H`） |
| LiveTalking 水印暴露 | 竖屏/全屏段左上角水印清晰可见 | 人像层先 `crop=宽:高-44:0:44` 裁掉顶部水印带，再等比缩放居中（模糊底自动补边），不要硬拉伸 |
| 语速被停顿稀释 | 成片人物说话偏慢（粗算 3.1 实为 4.6 字/秒） | P3 必须 VAD 扣静默；已有成片用比例法修正 |
| 生成模型画人 | 数字人越长越不像（v1 事故） | 只用音频驱动口型，底片锁身份 |
| 旧克隆接口 | `Model not exist` | 用 customization 新接口 + oss:// URL |
| prefix 超长 | `prefix should not be longer than 10 characters` | ≤10 字符 |
| pkill 自杀 | ssh 命令 255 断连 | kill 与 start 分开两条 ssh；模式用 `ap[p].py` 防自匹配 |
| ufw 拦 WebRTC | ICE state: failed | 放行 8010/tcp + 8010/udp + 10000:59999/udp |
| 跨网段 UDP | Mac→服务器 ICE failed（TCP 通） | 客户端在服务器本机 loopback 跑 |
| 系统代理劫持 | urllib 502（服务器日志无请求） | ProxyHandler({}) 强制直连 |
| av API | `module 'av' has no attribute 'Fraction'` | `from fractions import Fraction` |
| 作用域 | `name 'vstream' is not defined` | 内嵌函数用 `nonlocal` 非 `global` |
| zoompan 吃帧 | 段时长 10.4s≠12.5s | zoompan 前加 `fps=30` |
| 精简 ffmpeg | `No such filter: 'drawtext'` | 用 ffmpeg-full |
| drawtext 转义 | filter 解析报错 | `textfile=` 传文本 |
| zsh 不分词 | `set -- $var` 拆不开 | `while read` 或分开跑 |
| pytorch 下载慢 | 94KB/s 下 8 小时 | tuna PyPI 镜像（torch wheel 自带 cu12x） |
| s3fd 下载慢 | avatar 任务卡 40% | Mac 下载后 scp 到 `/root/.cache/torch/hub/checkpoints/` |
| gdown 假 100%（本机路径） | torch.load 报 unexpected EOF 但进度条显示完成 | 下载后 torch.load 验证；坏文件删除重下，`--continue` 会误报 skip |
| 256 权重载入后 forward 崩 | "kernel size can't be greater than actual input" 或 size mismatch | 四处对齐：v2 架构 + conv_384.py（gitee 缺）+ state_dict 解包 + img_size=256（见 P5.5） |
| 检测缓存越界 IndexError | `face_det_results[idx]` out of range（换更长音频的段时） | 缓存文件名带帧数，读时取"帧数最小且 ≥ 所需"的缓存再截断 |
| temp/ 缺失静默失败 | 最后 ffmpeg 报 result.avi 不存在（真实根因是 VideoWriter 无输出） | 推理前 `mkdir -p temp` |
| 拼接段音轨参数不一 | concat 后 burn/aresample 报 Invalid argument（报错远离根因） | 全部段统一 aac 24000 mono（与旁白段一致） |
| 画中画压卡面文案 | 卡背景+PIP 时副标题被遮 | PIP 放右上角（`overlay=W-w-44:44`，470px 高），卡面下部留给主/副标题 |
| 静帧收尾过长 | 品牌落版卡整段 16s 静帧拖沓 | 拼接前按需截短（如 -t 4.5） |

## 资产管理

- `voice_id.txt`：克隆音色 ID（90 天过期，过期重跑 P2）
- avatar（服务器 `data/avatars/<id>/`）：一次生成永久复用
- 底片原视频 + 干净窗口 clip：换脚本/换发型时段重做 avatar 时还要用
- 成片工程目录约定：`film/<项目>/`（tts/ shots/ subs/ 中间件与成片）
