# Skill: html-demo-video

把一个可独立运行的 HTML 原型 / 网页 Demo，或一套**真实前后端系统**，自动化录制成一条 16:9、1080p、中文旁白 + 烧录字幕的产品演示 MP4。管线：**干跑验证 → 单 take 录屏 → 云端 TTS 逐镜配音 → 自动变速总装 → 字幕烧录 → QC**，脚本模板在 `scripts/` 下。真实系统录制的差异见"真实系统录制增补"一节（含数字人嵌入段）。

当用户提到「原型演示视频、产品介绍片、录屏 demo、给客户看的带旁白字幕的 MP4」，或要把 HTML 原型 / 真实系统走一遍业务流程录成视频时使用。TTS 默认走阿里云百炼（qwen3-tts-flash / cosyvoice 克隆音色），不可用时退回 macOS `say`。

若目标仓库自带项目级 `prototype-demo-video` 类 skill（含该原型的分镜与避坑沉淀），优先按它定分镜，但**录制/总装/字幕环节的脚本与机制以本 skill 为准**（它更新）。

## 前置检查（逐项确认）

1. `ffmpeg -version` 可用，并检查文字滤镜：`ffmpeg -hide_banner -filters | grep -E "subtitles|drawtext"`。**很多构建（如 brew ffmpeg 9）没有 libass/drawtext**——查不到就用 `scripts/burn_subs.py` 的 overlay 方案，不要现装软件。
2. `node --version` + playwright：`require('playwright-core')` + 系统 Edge（`chromium.launch({ channel: 'msedge' })`）免下载浏览器；装了完整 `playwright` 也可直接用 chromium。
3. `python3 -c "import PIL"`（字幕条渲染用）。
4. 原型可独立运行：原型目录起 `python -m http.server 8791 --bind 127.0.0.1` 后台服务。
5. TTS Key 放环境变量 `TTS_API_KEY`（如 `video-zcode/.tts-env`，**确认目录被 gitignore，密钥绝不入库**）。

## 工作流

1. **需求确认**（AskUserQuestion）：演示范围与路线、目标时长、音色（qwen3-tts-flash 常用 `Cherry` 女声 / `Ethan` 男声）、是否先出分镜再录制（推荐）。语速基准 4.4 字/秒（约 +8%）；百炼默认语速偏慢（约 4.0 字/秒），总旁白超时长预算就加 `--atempo 1.09`。
2. **读原型出分镜**：大体量单文件原型先派 Explore 代理出「逐视图交互地图」，再写分镜（镜号/画面操作/旁白/时长）。产出目录约定：原型旁建 `video-<工具名>/`（如 `video-zcode/`），确认被 gitignore，所有中间产物只写自己的目录。
3. **旁白逐字对齐 UI**（最重要的一步）：把每句旁白里的名词/数字/分数在原型源码里逐一验证（grep 渲染模板里的实际文案）。**原型自身经常不一致**：方案里写的工具和训练模块用的工具可能不同、人格类型可能由问卷答案动态计算、分数可能写死。旁白说 A 画面显示 B 是成片最大硬伤。
4. **摸清原型隐藏规则**：先完整手动/脚本跑通一次交互再定旁白。常见暗规则：评估类提交可能「首次必驳回、二次才通过」；提问即自动改变阶段状态（按钮消失/出现）；表单答案决定后续展示内容。录制脚本的等待与点击序列必须按真实规则写。
5. **干跑**：复制 `scripts/record.template.js` 改写流程段，`DRY=1 node record.js` 不录像全动线走一遍，逐镜截图到 `dry-shots/` 逐张核对画面。选择器先在源码里 grep 验证存在性；`data-action`/`data-*` 等稳定钩子优先，按钮文案只做兜底。
6. **正式录制**：`node record.js`（可加 `caffeinate -i` 防休眠）。产物 `rec/*.webm` + `marks.json`。
7. **配音**：写 `narration-text.json`（`{"01": "旁白", ...}`），然后：
   ```bash
   source .tts-env && python3 <skill>/scripts/make_narration_bailian.py narration-text.json \
       --voice Cherry --atempo 1.09 --out audio/ --silence "15=5,23=9"
   ```
   无旁白的蒙太奇/结尾镜用 `--silence` 占位（总装要求每镜都有 narration 条目）。
8. **总装**：
   ```bash
   python3 <skill>/scripts/gen_assemble_config.py --stretch 03,15,23 --split "21=21b"
   python3 <skill>/scripts/assemble.py --config assemble-config.json   # 见下方"总装脚本"
   python3 <skill>/scripts/burn_subs.py base.mp4 subs.ass 成片.mp4      # 无 libass 时
   python3 <skill>/scripts/qc.py 成片.mp4
   ```
9. **QC**：九宫格抽帧逐张核对（画面状态正确/字幕无乱码无遮挡/品牌名统一）、`volumedetect` 逐镜旁白窗口（应 ≈ -20dB，< -40dB 即异常）、末段全分辨率抽帧（淡出时机、收尾镜头是否被吞）、ffprobe 参数（1920×1080、30fps、h264+aac）。不通过只改配置/脚本重跑总装，**不必重录**。

## 真实系统录制增补（2026-11 真实前后端项目三轮实战沉淀）

真实系统与 HTML 原型的差异决定了几个额外动作：

- **录制脚本按想象写必翻车**：分镜里的每个路由、页面卡片、提醒类型，先在真实系统逐镜截图确认存在（旁白就是"可验证断言"——说的每个功能/数字必须在成片画面里真实可见）。本项目曾写出三个不存在的功能入口（不存在的路由、没有的卡片、系统里没有的提醒类型），干跑截图逐镜核对才暴露。
- **外部服务延迟不可控时拆段变速**：真实大模型首字延迟 20-60 秒波动，整镜按旁白时长裁尾会把核心画面（如思考链流式）裁没。干跑后用抽帧定位关键画面的实际时间窗，assemble-config 手工拆段：输入段原速 + 关键段慢放 1.5-2×（打字机效果反而更有观感）+ 末帧停格收尾。
- **注入浮层必须 `pointer-events:none`**：讲解卡、光标徽标等录制期浮层不加会拦截被点击的页面按钮（表现为"按钮点不到"超时，极难归因到浮层）。
- **审批类推进硬校验**：用 API 推进审批状态后，立刻用 API 反查目标状态（如越级解锁 `unlocked`），失败即中止录制——残留脏数据会让"取列表第一条"批错旧单，静默错位。
- **演示数据包录制前重置**：真实系统有 seed/造数脚本时，正式录制前必跑一次重置（历次干跑/调试的残留单据会出现在镜头里、污染"取最新一条"类定位）；重置脚本要跨月安全（时间锚定"应用时区今天固定时刻"，不用 `now()-N days`，跨月夜整批数据掉回上月）。
- **marks 轴必须与画面内容轴对齐**：拼接 raw 用**输出级** `-ss`（输入级 seek 在 webm/vp9 有关键帧粒度漂移，marks 与实际内容错位 1-2s → 卡画面配上一镜字幕的"音画不同步"假象）；marks 用 ffprobe **实测段长**累计，不用请求边界差值。
- **拼接段音轨参数必须一致**（aac 24000 mono）：参数不一致的段 concat 后烧字幕时 aresample 报 Invalid argument，报错位置远离根因。
- **静态资产段截短**：品牌落版卡等静帧视频（16s）拼接前按需 `-t 4.5` 截短，长静帧收尾拖沓。
- **音画同步专项 QC（用户可感知的最后一关）**：成片轴上按段结构抽点做"语音能量探针"——语音活跃窗应 ≈ -20dB（静默窗 < -30dB），段边界错位时探针立刻暴露；数字人段（见 digital-human-b2b-video skill）另做多帧嘴型目检。
- **数字人嵌入段**：真人出镜串场（开场/章节引入/收尾）走 digital-human-b2b-video skill 的口型驱动；布局合成、按叙事序拼接、全片字幕时间轴按段累计偏移——参考差旅项目 `video-recording/` 的 dh_compose.py + build-final.py 模式。
- **模型对话类产品的录制前置**：录屏脚本若含多轮对话，先手动验证"第二条消息能发出去"（SSE 流式产品的流关闭信号在 dev 代理下可能丢失，表现为发送按钮永久 disabled——修法见 ai-feature 类纪律：显式 [DONE] 结束标记）。

## 关键机制与避坑（多次实战沉淀）

- **单次连续 take**：原型旅程状态只在内存，重启即清零。有状态主线一口气录完；无状态镜头（门户浏览）可在 take 末尾补拍、总装重排。录制中途任何一步失败通常意味着状态已错，直接修脚本重录整条。
- **多视图同名按钮**：原型可能同时渲染多个视图的 HTML。定位必须取"第一个可见实例"：`page.locator(sel).and(page.locator(':visible')).first()`，用 `.first().isVisible()` 会命中隐藏元素。
- **safe 包裹要有判断**：只包"失败后画面仍成立"的步骤；关键推进步骤别包——包了会让错误级联到几镜之后才炸，排查成本翻倍。
- **危险动作**：留意"会清零状态"的按钮（如侧栏「新建方案」重置整个旅程），录制中禁止点击；收尾要展示完成态时改用无副作用的入口（如点方案卡）。
- **原生文件选择器**：上传按钮必须 `page.on('filechooser', fc => fc.setFiles(文件))` 拦截，提前造命名贴合业务的占位文件。
- **变速语义**：stretch 是时长拉伸系数（>1 慢放）。实拍 vs 旁白目标：短了 tpad 补帧（静态画面补 2-3s 不可见），超长 ≤1.15 倍慢放吸收，>1.15 倍原速裁尾（慢放再裁会丢更多内容）。蒙太奇整镜压到 0.13-0.3；"前正常后快进"用镜内分段 mark（如 `21b`）+ `--split`。
- **assemble.py**（总装）：逐镜裁切/变速/补帧 → 音画按构造严格等长 → concat → 生成 `subs.ass`。样式：白字加粗 + 深色底条 + 投影，底部居中。⚠️ 它最后一烧字幕的 `ass=` 滤镜在无 libass 构建上会失败——base.mp4 生成成功即可，改用 `burn_subs.py` 接力（解析同一个 subs.ass）。字体别写「微软雅黑」（macOS 没有），用 Hiragino Sans GB 等实际存在的中文字体。
- **burn_subs.py 三个坑（已内置修复）**：① `-map 0:a` 必须显式给，否则 filter_complex 输出无声；② 淡出起点用成片总长而非最后一条字幕的结束时间，否则提前黑屏吞尾镜；③ 相邻字幕条时间窗要 clamp 防同屏重叠。
- **百炼 TTS 接法**：业务空间专属端点（`ws-*.maas.aliyuncs.com`）**没有** `/audio/speech`（404），但 `sk-ws-` Key 可直接调 `https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation`，`model=qwen3-tts-flash`，**voice 放 `input.voice`**（不是 parameters），返回 OSS wav URL 下载转 mp3。该 API 无词级时间戳，句级字幕按去标点字符数比例映射（够用）。edge-tts 经常被微软端点封（403），macOS `say -v Ting-Ting -r 200` 是兜底。
- **品牌/文案变更 = 全量重录**：品牌名贯穿全片 UI；仅改旁白时只需重跑配音 + 总装 + 字幕。

## QC 抽查清单

- [ ] 每镜中段抽帧：画面状态正确、字幕清晰无乱码无遮挡、品牌名统一
- [ ] 快进镜无可接受度问题（拖影/糊成一团）
- [ ] 各镜旁白窗口 `volumedetect` 有声（约 -20dB 均值）
- [ ] ffprobe：1920×1080、30fps、h264+aac、时长与计划一致（±0.5s）
- [ ] 首尾淡入淡出正常，尾镜内容完整（未被提前黑屏吞掉）
