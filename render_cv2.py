#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cv2 直写版渲染：numpy 合成 → VideoWriter 直接写 mp4（无中间帧）。
720×1280@24fps，2 进程并行（0-114 / 114-228），各输出一个 mp4，最后 concat。
用法: render_cv2.py <start> <dur> <out.mp4>
"""
import json, os, sys, time
import numpy as np
import cv2
from PIL import Image

W, H = 720, 1280
FPS = 24
BPM = 133.0
SEC_PER_BEAT = 60.0 / BPM
BASE = "/home/user/Doubao/chats/38447255748799234"
LINE_Y = 0.72

_bg = None
_tap = None
_grad = None

def init():
    global _bg, _tap, _grad
    tap = Image.open(os.path.join(BASE, "Tap.png")).convert("RGBA")
    tw = int(W * 0.1224)
    th = max(int(tw * tap.height / tap.width), 4)
    tap = tap.resize((tw, th), Image.LANCZOS)
    _tap = np.array(tap).astype(np.float32)  # RGB 0-255（与背景一致）
    bg = Image.open(os.path.join(BASE, "rb_song", "87039153.jpg")).convert("RGB")
    bg = bg.resize((W, H), Image.LANCZOS)
    bg = Image.blend(bg, Image.new("RGB", (W, H), (5, 8, 20)), 0.62)
    _bg = np.array(bg).astype(np.float32)
    g = np.zeros((H, W, 1), np.float32)
    g[:240, :, 0] = np.linspace(0, 0.92, 240)[:, None]
    _grad = g

def load_notes(path):
    d = json.load(open(path))
    return [{"t": n["t"], "x": n["x"]} for n in d["notes"]]

def blend(dst, src, px, py):
    th, tw = src.shape[:2]
    x0, y0 = int(px - tw / 2), int(py - th / 2)
    if x0 >= W or y0 >= H or x0 + tw <= 0 or y0 + th <= 0:
        return
    sx0, sy0 = max(0, -x0), max(0, -y0)
    sx1, sy1 = min(tw, W - x0), min(th, H - y0)
    if sx1 <= sx0 or sy1 <= sy0:
        return
    dx0, dy0 = x0 + sx0, y0 + sy0
    region = dst[dy0:dy0 + sy1 - sy0, dx0:dx0 + sx1 - sx0]
    s = src[sy0:sy1, sx0:sx1]
    a = s[:, :, 3:4] / 255.0  # alpha 0-1
    region[...] = region * (1 - a) + s[:, :, :3] * a

def render(start, dur, out_path):
    init()
    notes = load_notes(os.path.join(BASE, "infer_rb_1line.json"))
    notes = [n for n in notes if start - 0.01 <= n["t"] < start + dur + 2.5]
    line_y = LINE_Y * H
    nframes = int(dur * FPS)
    vw = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    t0 = time.time()
    for f in range(nframes):
        t = start + f / FPS
        img = _bg.copy()
        ly = int(line_y)
        img[ly - 3:ly + 3, int(W * 0.06):int(W * 0.94), :] = 255.0
        for n in notes:
            dt = n["t"] - t
            if dt <= 0 or dt > 3.0:
                continue
            gap = dt / SEC_PER_BEAT
            if gap > 2.6:
                continue
            ny = line_y - 0.4 * H * gap  # 流速=0.4H/格（官方0.6H，调慢约33%）
            if ny < -10 or ny > H + 10:
                continue
            dx = (W / 1340.0) * n["x"]
            dx = max(-0.49 * W, min(0.49 * W, dx))
            blend(img, _tap, W / 2 + dx, ny)
        img *= (1 - _grad)
        frame = np.clip(img, 0, 255).astype(np.uint8)
        vw.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
        if f % 1000 == 0:
            spd = (f + 1) / (time.time() - t0)
            print(f"{os.path.basename(out_path)} frame {f}/{nframes} t={t:.0f}s @{spd:.1f}fps", flush=True)
    vw.release()
    print(f"DONE {out_path} {nframes}帧 用时{time.time()-t0:.0f}s", flush=True)

if __name__ == "__main__":
    render(float(sys.argv[1]), float(sys.argv[2]), sys.argv[3])
