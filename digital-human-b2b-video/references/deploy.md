# LiveTalking 服务器部署（一次性，约 30-60 分钟）

目标机器：有 NVIDIA GPU 的 Linux 服务器（实测 3×RTX 3090，部署在 GPU1），ssh 别名以 `qkkj` 为例。

## 1. 代码 + Python 环境

```bash
ssh qkkj
cd /www/wwwroot
git clone --depth 1 https://gitee.com/lipku/LiveTalking.git LiveTalking   # 国内走 gitee，失败换 github
cd LiveTalking
# 不要用 venv（deploy 脚本里 source 失败会静默降级到系统 pip，反而更乱）——直接系统 python3.10
python3.10 -m pip install -U pip -i https://pypi.tuna.tsinghua.edu.cn/simple
python3.10 -m pip install torch==2.9.1 torchvision==0.24.1 torchaudio==2.9.1 \
  -i https://pypi.tuna.tsinghua.edu/simple   # PyPI wheel 自带 cu12x，驱动 580/CUDA13 兼容
# ↑ 不要用 --index-url https://download.pytorch.org/whl/...（直连只有 ~94KB/s）
python3.10 -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
# blinker 报 distutils 无法卸载时: python3.10 -m pip install --ignore-installed blinker 再重跑
```

## 2. 权重（Google Drive → Mac 中转）

服务器直连 gdrive/夸克都不方便，Mac 通常能直连：

```bash
# Mac 上：
python3 -m pip install --user gdown
gdown --folder "https://drive.google.com/drive/folders/1FOC_MD6wdogyyX_7V1d4NDIO7P9NlSAJ" -O /tmp/lt_weights --remaining-ok
scp /tmp/lt_weights/wav2lip/wav2lip256.pth      qkkj:/www/wwwroot/LiveTalking/models/wav2lip.pth
scp /tmp/lt_weights/wav2lip/wav2lip256_avatar1.tar.gz qkkj:/www/wwwroot/LiveTalking/data/avatars/
ssh qkkj 'cd /www/wwwroot/LiveTalking && tar xzf data/avatars/wav2lip256_avatar1.tar.gz -C data/avatars/'
```

s3fd 人脸检测权重（avatar 预处理时自动从 adrianbulat.com 下载，服务器很慢）——Mac 预置：

```bash
curl -L -o s3fd.pth "https://www.adrianbulat.com/downloads/python-fan/s3fd-619a316812.pth"
ssh qkkj 'mkdir -p /root/.cache/torch/hub/checkpoints/'
scp s3fd.pth qkkj:/root/.cache/torch/hub/checkpoints/s3fd-619a316812.pth
```

## 3. 启动（webrtc 传输 + GPU1）

```bash
ssh qkkj 'cd /www/wwwroot/LiveTalking && CUDA_VISIBLE_DEVICES=1 \
  nohup python3.10 app.py --model wav2lip --transport webrtc \
  --avatar_id wav2lip256_avatar1 --listenport 8010 > /www/wwwroot/lt.log 2>&1 & sleep 20; tail lt.log'
# 看到 "start http server" + warmup 完成即就绪
```

- `--model musetalk` 是升级选项（口型更细），需额外下载 musetalk v1.5 权重（同 gdrive 文件夹），3090 上 45fps。
- rtmp/rtcpush 传输需要额外装 `rtmp_streaming`（pypi 没有，别折腾）或 SRS 媒体服务器——**无头录制方案不需要它们**，webrtc + 本机客户端即可。

## 4. 防火墙（关键！）

```bash
ssh qkkj 'ufw allow 8010/tcp && ufw allow 8010/udp && ufw allow 10000:59999/udp'
```

WebRTC 信令走 TCP 8010，**媒体走 UDP 动态端口**——只放行 TCP 会 ICE failed。
若 Mac 与服务器跨网段（如 192.168.19.x → 192.168.18.x），UDP 打洞仍可能被路由器拦：
**客户端脚本放到服务器本机跑 loopback（127.0.0.1）**，录好的 mp4 scp 回来。

## 5. 部署本人的客户端脚本

```bash
scp ~/.agents/skills/digital-human-b2b-video/scripts/lt_client.py qkkj:/www/wwwroot/LiveTalking/
```

已知实现细节（改代码前读）：
- urllib 会读 macOS 系统代理 → 内网请求用 `build_opener(ProxyHandler({}))` 直连
- `av.Fraction` 不存在，用 `from fractions import Fraction`
- 嵌套函数改写流变量用 `nonlocal`
- `/humanaudio` 收 24kHz wav 会自动重采样 16k，无需预转
