# skills

个人 AI skills 集合——本机制作的 agent skills（SKILL.md 形态）及其配套脚本、参考文献与实战避坑沉淀。

## 约定（唯一源：本仓库）

- **本仓库是全部自制 skill 的唯一源**；`~/.agents/skills/` 只是安装目标，由 `scripts/sync.sh` 写入，不手改。
- 每个 skill 目录**自包含**：`SKILL.md` + `references/`（对应方法论正文）+ 可选 `scripts/`、`assets/`；安装 = 整目录拷贝，无外部依赖（skill 间引用仅限同级 `../<skill>/...`）。
- 方法论正文放各 skill 的 `references/`（如 `dev-process/references/开发过程经验蒸馏.md`——经验库管"为什么"，SKILL.md 管"现在做什么"；badcase 证据查其 §7 证据表）。
- 同步：`scripts/sync.sh install|collect|status [skill名...]`；改动一律在仓库做并 git 提交，`collect` 仅用于回收安装目录的意外改动。

## 同步

```bash
./scripts/sync.sh install   # 仓库 → ~/.agents/skills/（全量）
./scripts/sync.sh status    # 对比差异
```

## 目录索引

| Skill | 用途 | 配套 |
|---|---|---|
| `prototype-builder/` | AI 制作高保真可交互数字产品原型（HTML，可点击演示） | docs/AI原型制作方法论.md |
| `prototype-to-prd-adversarial/` | 从原型/演示生成产品 PRD 并循环对抗性审查直至无问题 | docs/原型转PRD经验总结.md |
| `technical-solution-design/` | 基于项目模板制作技术方案并执行对抗性评审（含 agents 协作配置） | docs/技术方案制作与迭代经验.md |
| `dev-process/` | 开发过程纪律：开工前置→实现→验证→收尾四阶段强制工作流与完成门禁 | references/开发过程经验蒸馏.md |
| `ai-feature/` | LLM 功能链路硬不变量：候选四层分离/校验四连动/流式事件契约/显式结束标记 | 由 dev-process 阶段 0.5 联动加载 |
| `digital-human-b2b-video/` | 真人数字人 B2B 视频流水线：声音克隆→口型驱动（服务器 LiveTalking 或本机离线 wav2lip）→拼装字幕 | scripts/ + references/ + assets/ |
| `html-demo-video/` | HTML 原型或真实系统 → 带旁白字幕的 1080p 演示视频（干跑→单 take→TTS→总装→QC），含真实系统录制增补 | scripts/ |

## 状态

- 2026-11：收录 7 个 skill；方法论正文已归入各 skill `references/`（docs/ 撤销）。
- 唯一源归一（2026-11-03）：`skills蒸馏/` 的 skill 目录已迁入本仓库并删除原目录（该目录仅存经验总结正文归档与业务产物）。
