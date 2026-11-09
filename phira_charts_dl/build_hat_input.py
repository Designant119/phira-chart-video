#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ハテ（Frums）：采音候选 → 单线分线 → 排键输入。BPM 恒定 220.5。"""
import json, os
from collections import defaultdict

BASE = "/home/user/Doubao/chats/38445055719679234/phira_charts_dl"
SRC = "/home/user/Doubao/chats/38447255748799234/audio_notes_hat.json"
FID = "hat"
HATJSON = "/home/user/Doubao/chats/38447255748799234/hat_song/hat.json"

chart = json.load(open(HATJSON))
segs = [[int(b["startTime"][0]), float(b["bpm"])] for b in chart["BPMList"]]

notes = json.load(open(SRC))["notes"]
notes.sort(key=lambda n: n["t"])
lines = defaultdict(list)
for n in notes:
    t = round(n["t"], 4)
    cnt = 2 if n["chord"] == 2 else 1
    for _ in range(cnt):
        lines[0].append(t)

all_notes = []
for lid, ts in lines.items():
    for t in sorted(ts):
        all_notes.append({"t": t, "x": 0.0, "type": 1, "dur": 0.0, "line_id": lid})

out = os.path.join(BASE, "parsed", f"{FID}.json")
json.dump({"bpm": segs, "notes": all_notes}, open(out, "w"))
print(f"总音符 {len(all_notes)} | BPM segs {len(segs)} 段 | 每线 {len(lines[0])}")
