#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lost Requiem 渲染：支持 BPM 多段变速。
格差 = beat(t_note) - beat(t_now)，beat(t) 按 BPMList 分段积分。
流速 0.4H/格（慢速），单条判定线，cv2 直写。
用法: render_lr.py <start> <dur> <out.mp4>
"""
import json, os, sys, time, bisect, math
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720   # 16:9 横屏
FPS = 24
BASE = "/home/user/Doubao/chats/38447255748799234"
LINE_Y = 0.90   # 判定线在屏幕底部
NOTES_JSON = os.path.join(BASE, "infer_td.json")
LRJSON = os.path.join(BASE, "td_song", "td.json")

# --- BPM 分段：[(start_beat, bpm)] → 构建分段秒表 ---
chart = json.load(open(LRJSON))
_bpm_items = [(int(b["startTime"][0]), float(b["bpm"])) for b in chart["BPMList"]]
_seg_sec = []   # (start_sec, start_beat, bpm)
_cur_sec, _cur_beat = 0.0, 0.0
for sb, bpm in _bpm_items:
    _seg_sec.append((_cur_sec, _cur_beat, bpm))
    _cur_sec += (sb - _cur_beat) * 60.0 / bpm
    _cur_beat = sb

def beat_of(t):
    """秒 t → beat（按 BPM 分段积分）"""
    for i in range(len(_seg_sec) - 1, -1, -1):
        s0, b0, bpm = _seg_sec[i]
        if t >= s0:
            return b0 + (t - s0) * bpm / 60.0
    return t * _seg_sec[0][2] / 60.0

_bg = _tap = _grad = _font = _font_small = _font_tiny = None

def init():
    global _bg, _tap, _grad, _font, _font_small, _font_tiny
    _font = ImageFont.truetype(os.path.join(BASE, "phigros.ttf"), 96)
    _font_small = ImageFont.truetype(os.path.join(BASE, "phigros.ttf"), 58)
    _font_tiny = ImageFont.truetype(os.path.join(BASE, "phigros.ttf"), 30)
    tap = Image.open(os.path.join(BASE, "Tap.png")).convert("RGBA")
    tw = int(W * 0.1224)
    th = max(int(tw * tap.height / tap.width), 4)
    tap = tap.resize((tw, th), Image.LANCZOS)
    _tap = np.array(tap).astype(np.float32)
    bg = Image.open(os.path.join(BASE, "td_song", "1531887704423.jpg")).convert("RGB")
    # 16:9 cover 裁剪（不拉伸变形）
    bg_ratio = bg.width / bg.height
    target = W / H
    if bg_ratio > target:
        new_w = int(bg.height * target)
        x0 = (bg.width - new_w) // 2
        bg = bg.crop((x0, 0, x0 + new_w, bg.height))
    else:
        new_h = int(bg.width / target)
        y0 = (bg.height - new_h) // 2
        bg = bg.crop((0, y0, bg.width, y0 + new_h))
    bg = bg.resize((W, H), Image.LANCZOS)
    bg = Image.blend(bg, Image.new("RGB", (W, H), (5, 8, 20)), 0.62)
    _bg = np.array(bg).astype(np.float32)
    g = np.zeros((H, W, 1), np.float32)
    g[:150, :, 0] = np.linspace(0, 0.92, 150)[:, None]
    _grad = g

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
    a = s[:, :, 3:4] / 255.0
    region[...] = region * (1 - a) + s[:, :, :3] * a

def draw_combo(dst, combo, top_y=70):
    """屏幕顶部中央绘制连击数；动态测量文本宽度保证完整显示（含四位数）"""
    if combo <= 0:
        return
    s = str(combo)
    bbox = _font.getbbox(s)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad = 26
    tmp = Image.new("RGBA", (tw + 2 * pad, th + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    cx, cy = pad - bbox[0], pad - bbox[1]
    for ox, oy in [(-3, 0), (3, 0), (0, -3), (0, 3), (-2, -2), (-2, 2), (2, -2), (2, 2)]:
        d.text((cx + ox, cy + oy), s, font=_font, fill=(0, 0, 0, 220))
    d.text((cx, cy), s, font=_font, fill=(255, 255, 255, 255))
    blend(dst, np.array(tmp).astype(np.float32), W / 2, top_y)

def note_grid(t):
    """音符时刻 t → (累计拍号, 当拍内 32 分位置)"""
    b = beat_of(t)
    beat_num = int(math.floor(b))
    grid = round((b - math.floor(b)) * 32) % 32
    return beat_num, grid

def draw_gridnum(dst, grid, line_y):
    """判定线下方显示当前音符的 16 分网格位置（实时）"""
    s = f"beats:{grid}/32"
    tmp = Image.new("RGBA", (340, 110), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    cx, cy = 170, 55
    for ox, oy in [(-2, 0), (2, 0), (0, -2), (0, 2), (-1, -1), (-1, 1), (1, -1), (1, 1)]:
        d.text((cx + ox, cy + oy), s, font=_font_small, fill=(0, 0, 0, 200))
    d.text((cx, cy), s, font=_font_small, fill=(255, 255, 255, 255))
    blend(dst, np.array(tmp).astype(np.float32), W / 2, line_y + 45)   # 紧贴判定线下方（屏内）

def draw_note_grid(dst, beat_num, grid, px, py):
    """单个音符贴图正下方标注：{累计拍号}:{拍内位置}/32（动态测宽，不截断）"""
    s = f"{beat_num}:{grid}/32"
    bbox = _font_tiny.getbbox(s)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad = 8
    tmp = Image.new("RGBA", (tw + 2 * pad, th + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    cx, cy = pad - bbox[0], pad - bbox[1]
    for ox, oy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        d.text((cx + ox, cy + oy), s, font=_font_tiny, fill=(0, 0, 0, 190))
    d.text((cx, cy), s, font=_font_tiny, fill=(255, 255, 255, 255))
    blend(dst, np.array(tmp).astype(np.float32), px, py)

def render(start, dur, out_path):
    init()
    all_notes = json.load(open(NOTES_JSON))["notes"]
    ts_all = sorted(n["t"] for n in all_notes)   # 全局连击：曲首累计
    grid_map = {n["t"]: note_grid(n["t"]) for n in all_notes}   # 预计算每音符 128 分位置
    notes = [n for n in all_notes if start - 0.01 <= n["t"] < start + dur + 4.0]
    line_y = LINE_Y * H
    nframes = int(dur * FPS)
    vw = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    t0 = time.time()
    for f in range(nframes):
        t = start + f / FPS
        img = _bg.copy()
        ly = int(line_y)
        img[ly - 3:ly + 3, int(W * 0.06):int(W * 0.94), :] = 255.0
        combo = bisect.bisect_right(ts_all, t)   # 已过判定线的音符数
        idx = combo - 1                          # 最新判定的音符
        if idx >= 0:
            tn = ts_all[idx]
            b = beat_of(tn)
            grid = round((b - math.floor(b)) * 32) % 32   # 当拍内 16 分位置
        bt = beat_of(t)
        for n in notes:
            dt = n["t"] - t
            if dt <= 0 or dt > 3.0:
                continue
            gap = beat_of(n["t"]) - bt  # 格差按 BPM 分段积分
            if gap > 2.6:
                continue
            ny = line_y - 0.48 * H * gap   # 流速 0.48H/格（比 0.4 快 20%）
            if ny < -10 or ny > H + 10:
                continue
            dx = (W / 1340.0) * n["x"]
            dx = max(-0.49 * W, min(0.49 * W, dx))
            blend(img, _tap, W / 2 + dx, ny)
            _bn, _gd = grid_map[n["t"]]
            draw_note_grid(img, _bn, _gd, W / 2 + dx, ny + 42)   # 音符正下方 {拍号}:{位置}/32
        img *= (1 - _grad)
        draw_combo(img, combo)          # 渐变后绘制连击，避免被顶部渐变压暗
        frame = np.clip(img, 0, 255).astype(np.uint8)
        vw.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
        if f % 1500 == 0:
            spd = (f + 1) / (time.time() - t0)
            print(f"{os.path.basename(out_path)} frame {f}/{nframes} t={t:.0f}s @{spd:.1f}fps", flush=True)
    vw.release()
    print(f"DONE {out_path} {nframes}帧 用时{time.time()-t0:.0f}s", flush=True)

if __name__ == "__main__":
    render(float(sys.argv[1]), float(sys.argv[2]), sys.argv[3])
