#!/usr/bin/env python3
"""DashScope cosyvoice-v3.5 声音克隆注册（voice enrollment）。

用法:
  python3 enroll_voice.py --sample clone_sample_15s.wav [--prefix yuejian] \
      [--target-model cosyvoice-v3.5-flash] [--out voice_id.txt]
  API key 从环境变量 BL_API_KEY / DASHSCOPE_API_KEY 读取。

流程（2026-10 实测有效）:
  1. GET  /api/v1/uploads?action=getPolicy&model=<target>   拿 OSS 上传 policy
  2. POST multipart 到 upload_host                          上传参考音频
  3. POST /api/v1/services/audio/tts/customization
       model=voice-enrollment, action=create_voice,
       target_model=<target>, prefix=..., audio=oss://<upload_dir>/<fn>
       头: X-DashScope-OssResourceResolve: enable
  4. 返回 voice_id（90 天有效期）
注意: prefix 必须 ≤10 字符；旧 voice-enrollment base64 接口对 v3.5 无效。
"""
import argparse
import base64
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
import uuid

BASE = "https://dashscope.aliyuncs.com/api/v1"


def api_key():
    k = os.environ.get("BL_API_KEY") or os.environ.get("DASHSCOPE_API_KEY")
    if not k:
        sys.exit("需要环境变量 BL_API_KEY 或 DASHSCOPE_API_KEY")
    return k


def http_json(req, timeout=120):
    try:
        return json.load(urllib.request.urlopen(req, timeout=timeout))
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode()[:400]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", required=True, help="参考音频 wav（10-25s 降噪归一化后）")
    ap.add_argument("--prefix", default="myvoice", help="音色名前缀，≤10 字符")
    ap.add_argument("--target-model", default="cosyvoice-v3.5-flash")
    ap.add_argument("--out", default="voice_id.txt")
    a = ap.parse_args()
    if len(a.prefix) > 10:
        sys.exit("prefix 必须 ≤10 字符")
    key = api_key()
    hdr = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    # 1) 上传 policy
    pol = http_json(urllib.request.Request(
        f"{BASE}/uploads?action=getPolicy&model={a.target_model}",
        headers={"Authorization": f"Bearer {key}"}))
    d = pol["data"]

    # 2) OSS multipart 上传
    fn = f"{a.prefix}_{uuid.uuid4().hex[:8]}.wav"
    key_oss = f"{d['upload_dir']}/{fn}"
    fields = {
        "OSSAccessKeyId": d.get("oss_access_key_id"),
        "Signature": d.get("signature"),
        "policy": d.get("policy"),
        "x-oss-object-acl": d.get("x_oss_object_acl"),
        "x-oss-forbid-overwrite": d.get("x_oss_forbid_overwrite"),
        "key": key_oss,
        "success_action_status": "200",
    }
    fields = {k: v for k, v in fields.items() if v}
    boundary = uuid.uuid4().hex
    parts = [f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
             for k, v in fields.items()]
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{fn}\"\r\n"
                 f"Content-Type: {mimetypes.guess_type(fn)[0]}\r\n\r\n".encode())
    parts.append(open(a.sample, "rb").read())
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    r = urllib.request.urlopen(urllib.request.Request(
        d["upload_host"], data=b"".join(parts),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}), timeout=60)
    assert r.status == 200, f"OSS upload failed: {r.status}"
    oss_url = f"oss://{key_oss}"

    # 3) 声音注册
    body = {"model": "voice-enrollment",
            "input": {"action": "create_voice", "target_model": a.target_model,
                      "prefix": a.prefix, "audio": oss_url},
            "parameters": {}}
    resp = http_json(urllib.request.Request(
        f"{BASE}/services/audio/tts/customization", data=json.dumps(body).encode(),
        headers={**hdr, "X-DashScope-OssResourceResolve": "enable"}))
    voice_id = resp["output"]["voice_id"]
    open(a.out, "w").write(voice_id + "\n")
    print(f"voice_id: {voice_id}")
    print(f"saved to {a.out} (90 天有效期，过期重跑)")


if __name__ == "__main__":
    main()
