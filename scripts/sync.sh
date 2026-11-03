#!/usr/bin/env zsh
# skills 仓库同步工具：仓库是唯一源（single source of truth）。
#   ./scripts/sync.sh install [skill名...]   仓库 → ~/.agents/skills/（整目录覆盖安装；缺省装全部）
#   ./scripts/sync.sh collect [skill名...]   ~/.agents/skills/ → 仓库（回收安装版的改动；缺省收全部）
#   ./scripts/sync.sh status                 对比两侧差异
# 约定：只在仓库里改 skill；安装目录是产物，不手改。回收后须 git 提交。
set -e
REPO="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="$HOME/.agents/skills"
SKILLS=(prototype-builder prototype-to-prd-adversarial technical-solution-design dev-process ai-feature digital-human-b2b-video html-demo-video)

pick() {  # $@ 为空则取全部
  if [ $# -gt 0 ]; then printf '%s\n' "$@"; else printf '%s\n' "${SKILLS[@]}"; fi
}

case "${1:-status}" in
  install)
    for s in $(pick "${@:2}"); do
      [ -d "$REPO/$s" ] || { echo "skip (repo 无此 skill): $s"; continue; }
      rm -rf "$TARGET/$s" && cp -R "$REPO/$s" "$TARGET/$s"
      echo "installed: $s"
    done ;;
  collect)
    for s in $(pick "${@:2}"); do
      [ -d "$TARGET/$s" ] || { echo "skip (未安装): $s"; continue; }
      if diff -rq "$REPO/$s" "$TARGET/$s" >/dev/null 2>&1; then echo "same: $s"; continue; fi
      rm -rf "$REPO/$s" && cp -R "$TARGET/$s" "$REPO/$s"
      echo "collected (记得 git 提交): $s"
    done ;;
  status)
    for s in "${SKILLS[@]}"; do
      if [ ! -d "$REPO/$s" ]; then echo "repo 缺: $s"; continue; fi
      if [ ! -d "$TARGET/$s" ]; then echo "未安装: $s"; continue; fi
      if diff -rq "$REPO/$s" "$TARGET/$s" >/dev/null 2>&1; then echo "same: $s"; else echo "diff: $s"; fi
    done ;;
  *) echo "用法: $0 {install|collect|status} [skill名...]"; exit 1 ;;
esac
