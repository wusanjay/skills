#!/bin/bash
# LiveTalking 部署健康检查。用法: bash deploy_check.sh [ssh别名，默认 qkkj]
HOST="${1:-qkkj}"
ok=0; fail=0
chk() { # chk <说明> <命令> 
  if ssh -o BatchMode=yes -o ConnectTimeout=8 "$HOST" "$2" >/dev/null 2>&1; then
    echo "  [OK] $1"; ok=$((ok+1))
  else
    echo "  [FAIL] $1"; fail=$((fail+1))
  fi
}
echo "== LiveTalking 部署检查 ($HOST) =="
chk "ssh 免密连通"            "true"
chk "代码目录存在"            "test -d /www/wwwroot/LiveTalking"
chk "wav2lip 权重"            "test -f /www/wwwroot/LiveTalking/models/wav2lip.pth"
chk "python3.10 + torch+cuda" "python3.10 -c 'import torch; assert torch.cuda.is_available()'"
chk "flask/aiortc 依赖"       "python3.10 -c 'import flask, aiortc'"
chk "服务进程存活"            "pgrep -f 'ap[p].py --model'"
chk "8010 端口监听"           "ss -tln | grep -q 8010"
chk "HTTP 探活"               "curl -s --max-time 5 http://127.0.0.1:8010/index.html | grep -qi html"
chk "本地 WebRTC 通路(ufw)"   "ufw status | grep -q '8010/tcp'"
chk "客户端脚本在位"          "test -f /www/wwwroot/LiveTalking/lt_client.py"
echo "== 结果: $ok 项通过, $fail 项失败 =="
[ $fail -eq 0 ] && echo "可以直接跑 P6/P7（avatar 生成 / 口播驱动录制）" \
              || echo "失败项按 references/deploy.md 对应章节修复"
exit $fail
