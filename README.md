# skills

个人 AI skills 集合——本机制作的 agent skills（SKILL.md 形态）及其配套脚本、参考文献与实战避坑沉淀。

## 约定

- 每个 skill 一个顶层目录：`<skill-name>/SKILL.md` + 可选的 `scripts/`、`references/`、`assets/`。
- `SKILL.md` frontmatter 至少含 `name` 与 `description`（description 写清"什么任务该用我、什么任务不该"）。
- `开发过程经验蒸馏.md` 位于仓库根：dev-process / ai-feature 以 `../开发过程经验蒸馏.md` 相对引用它，回答"为什么"；skill 正文回答"现在做什么、怎么算做完"。badcase 证据查其 §7 证据表。
- 方法论正文（蒸馏产物）统一放 `docs/`。

## 目录索引

| Skill | 用途 | 配套 |
|---|---|---|
| `prototype-builder/` | AI 制作高保真可交互数字产品原型（HTML，可点击演示） | docs/AI原型制作方法论.md |
| `prototype-to-prd-adversarial/` | 从原型/演示生成产品 PRD 并循环对抗性审查直至无问题 | docs/原型转PRD经验总结.md |
| `technical-solution-design/` | 基于项目模板制作技术方案并执行对抗性评审（含 agents 协作配置） | docs/技术方案制作与迭代经验.md |
| `dev-process/` | 开发过程纪律：开工前置→实现→验证→收尾四阶段强制工作流与完成门禁 | ../开发过程经验蒸馏.md |
| `ai-feature/` | LLM 功能链路硬不变量：候选四层分离/校验四连动/流式事件契约/显式结束标记 | 由 dev-process 阶段 0.5 联动加载 |
| `digital-human-b2b-video/` | 真人数字人 B2B 视频流水线：声音克隆→口型驱动（服务器 LiveTalking 或本机离线 wav2lip）→拼装字幕 | scripts/ + references/ + assets/ |
| `html-demo-video/` | HTML 原型或真实系统 → 带旁白字幕的 1080p 演示视频（干跑→单 take→TTS→总装→QC），含真实系统录制增补 | scripts/ |
| `docs/` | 各 skill 对应的方法论蒸馏正文 | — |

## 状态

- 2026-11：初版收录 7 个 skill + 3 篇方法论正文 + 经验蒸馏源文档。
- 本机安装位置约定：`~/.agents/skills/<skill-name>/`（与仓库同名目录同步）。
