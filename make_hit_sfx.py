#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成打击音效音轨：每个音符判定时刻叠加 Phira 官方 click 打击音效。
用法: python3 make_hit_sfx.py <notes.json> <out.wav> [click_wav]
输出: 44100Hz 16bit 单声道（覆盖全曲）
多押响度：每多一押 +30%（单押 1.0 / 双押 1.3 / 三押 1.6）
"""
import json, sys, wave
import numpy as np

SR = 44100

def load_click(path):
    """读取 Phira click wav → float64（归一化到峰值 1.0）"""
    with wave.open(path, "rb") as w:
        nch, sw, sr, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        assert sr == SR, f"采样率必须 44100Hz，实际 {sr}"
        raw = w.readframes(n)
    data = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32767.0
    if nch > 1:
        data = data.reshape(-1, nch).mean(axis=1)
    peak = np.abs(data).max()
    if peak > 0:
        data = data / peak
    return data

def main():
    notes_path, out = sys.argv[1], sys.argv[2]
    click_path = sys.argv[3] if len(sys.argv) > 3 else "click_phira.wav"
    notes = json.load(open(notes_path))["notes"]
    DUR = max(n["t"] for n in notes) + 1.0  # 按音符时刻自动推导，覆盖全曲
    sfx = np.zeros(int(DUR * SR), dtype=np.float64)
    clicks = {}
    for n in notes:
        t = round(n["t"], 3)
        if t < 0 or t >= DUR:
            continue
        clicks[t] = clicks.get(t, 0) + 1  # 同刻多音：计数
    click = load_click(click_path)
    for t, cnt in clicks.items():
        i = int(t * SR)
        if i >= len(sfx):
            continue
        amp = 1.0 + 0.3 * (cnt - 1)  # 多押每多一押响度 +30%
        j = min(i + len(click), len(sfx))
        sfx[i:j] += click[: j - i] * amp
    # 归一化到满幅（更响）
    peak = np.abs(sfx).max()
    if peak > 0:
        sfx = sfx / peak * 1.0
    pcm = (sfx * 32767).astype(np.int16)
    with wave.open(out, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f"打击音轨已生成: {out} | 判定时刻 {len(clicks)} 个（多押含在内）| 音效源: {click_path}")

if __name__ == "__main__":
    main()
