#!/usr/bin/env python3
"""LiveTalking 无头 WebRTC 客户端：连接 → 喂音频 → 录制数字人口播 MP4"""
import asyncio, argparse, json, sys, time
import av
from fractions import Fraction
from aiortc import RTCPeerConnection, RTCSessionDescription

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--host', default='192.168.18.79')
    ap.add_argument('--port', type=int, default=8010)
    ap.add_argument('--avatar', default='wav2lip256_avatar1')
    ap.add_argument('--audio', required=True, help='驱动音频 wav')
    ap.add_argument('--out', required=True, help='输出 mp4')
    ap.add_argument('--lead', type=float, default=1.5, help='开场静默秒数')
    ap.add_argument('--tail', type=float, default=3.0, help='结尾缓冲秒数')
    a = ap.parse_args()

    probe = av.open(a.audio)
    adur = probe.duration / av.time_base if probe.duration else 60.0
    probe.close()
    total = a.lead + adur + a.tail
    print(f"audio {adur:.1f}s → record {total:.1f}s")

    pc = RTCPeerConnection()
    pc.addTransceiver('video', direction='recvonly')
    pc.addTransceiver('audio', direction='recvonly')

    container = av.open(a.out, 'w')
    vstream = astream = None
    resampler = av.AudioResampler(format='s16', layout='stereo', rate=48000)
    frame_count = [0]

    def save_frame(frame):
        nonlocal vstream, astream
        if isinstance(frame, av.VideoFrame):
            if vstream is None:
                vstream = container.add_stream('libx264', rate=25)
                vstream.width, vstream.height = frame.width, frame.height
                vstream.pix_fmt = 'yuv420p'
                vstream.options = {'preset': 'veryfast', 'crf': '18'}
                vstream.time_base = Fraction(1, 25)
            for pkt in vstream.encode(frame):
                container.mux(pkt)
            frame_count[0] += 1
        elif isinstance(frame, av.AudioFrame):
            frames = resampler.resample(frame)
            for f in frames:
                if astream is None:
                    astream = container.add_stream('aac', rate=48000)
                    astream.layout = 'stereo'
                for pkt in astream.encode(f):
                    container.mux(pkt)

    @pc.on('track')
    def on_track(track):
        print('track:', track.kind)
        async def consume():
            while True:
                try:
                    frame = await track.recv()
                except Exception:
                    break
                save_frame(frame)
        asyncio.ensure_future(consume())

    offer = await pc.createOffer()
    await pc.setLocalDescription(offer)
    offer_sdp = pc.localDescription.sdp
    import urllib.request, urllib.error
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    body = json.dumps({'sdp': offer_sdp, 'type': 'offer', 'avatar': a.avatar}).encode()
    req = urllib.request.Request(f'http://{a.host}:{a.port}/offer', data=body,
                                 headers={'Content-Type': 'application/json'})
    try:
        resp = json.load(opener.open(req, timeout=30))
    except urllib.error.HTTPError as e:
        print('OFFER FAIL:', e.code, e.read().decode()[:300]); sys.exit(1)
    sessionid = resp.get('sessionid')
    await pc.setRemoteDescription(RTCSessionDescription(resp['sdp'], resp['type']))
    print('remote set, sessionid:', sessionid)

    @pc.on('iceconnectionstatechange')
    def on_ice():
        print('ICE state:', pc.iceConnectionState)
    @pc.on('connectionstatechange')
    def on_conn():
        print('CONN state:', pc.connectionState)
    @pc.on('icegatheringstatechange')
    def on_iceg():
        print('ICE gather:', pc.iceGatheringState)
    @pc.on('icecandidateerror')
    def on_iceerr(ev):
        print('ICE err:', getattr(ev, 'error_code', '?'), getattr(ev, 'url', ''))
    # 打印远端 SDP 中的候选，确认对端给了什么地址
    for line in resp['sdp'].splitlines():
        if 'candidate' in line.lower():
            print('remote-cand:', line.strip()[:120])

    await asyncio.sleep(a.lead)

    # multipart 上传音频
    boundary = '----ltdh' + str(int(time.time()))
    data = open(a.audio, 'rb').read()
    mp = (f'--{boundary}\r\nContent-Disposition: form-data; name="sessionid"\r\n\r\n{sessionid}\r\n'
          f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="vo.wav"\r\n'
          f'Content-Type: audio/wav\r\n\r\n').encode() + data + f'\r\n--{boundary}--\r\n'.encode()
    req2 = urllib.request.Request(f'http://{a.host}:{a.port}/humanaudio', data=mp,
        headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
    r2 = json.load(opener.open(req2, timeout=30))
    print('humanaudio:', r2)

    await asyncio.sleep(adur + a.tail)

    await pc.close()
    if vstream:
        for pkt in vstream.encode(None): container.mux(pkt)
    if astream:
        for pkt in astream.encode(None): container.mux(pkt)
    container.close()
    print(f'done: {a.out}, video frames {frame_count[0]}')

asyncio.run(main())
