#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""两遍推理（9维：7基线 + chord_x + level_norm）：
第一遍 chord_x=0 粗排 → 第二遍用同刻其他线粗排 x 均值精排；第9维 level_norm=level/25 常量。
用法：python3 infer_chord.py <fid> [--ckpt layout_ckpt_chord9_full] [--seed 7] [--out xxx.json]
输出与 infer_layout_ckpt.py 一致（notes 含 t/type/x/line_id/dur），仅 tap/hold。
"""
import json, os, sys, argparse, re, zipfile, glob
import numpy as np
import torch
from collections import defaultdict
from train_chord import GRUCls9
from infer_layout_ckpt import beat_at, build_features, infer_line, enforce_chord_gaps

BASE = "/home/user/Doubao/chats/38445055719679234/phira_charts_dl"
W = 128


def get_level(fid):
    """level: level_cache.json 优先 → 回扫 subsets 里 {fid}_*.pez 的 META.level → 0"""
    cache_p = os.path.join(BASE, "level_cache.json")
    if os.path.exists(cache_p):
        try:
            c = json.load(open(cache_p))
            if str(fid) in c:
                return float(c[str(fid)])
        except Exception:
            pass
    for pez in glob.glob(os.path.join(BASE, "subsets", "*", f"{fid}_*.pez")):
        try:
            z = zipfile.ZipFile(pez)
            for name in z.namelist():
                if not name.endswith(".json"):
                    continue
                d = json.loads(z.read(name).decode("utf-8"))
                if isinstance(d, dict) and "META" in d:
                    m = re.search(r"Lv\.?([\d.]+)", str(d["META"].get("level", "")))
                    if m:
                        return float(m.group(1))
        except Exception:
            continue
    return 0.0


def build_features_chord(lnotes, bpm, chord_map, level_norm):
    """在 7 维特征上追加第8维 chord_x、第9维 level_norm（常量）。"""
    X7 = build_features(lnotes, bpm)
    N = X7.shape[0]
    chord_x = np.zeros(N, dtype=np.float32)
    for i, n in enumerate(lnotes):
        m = chord_map.get(round(n["t"], 3))
        if m is not None:
            chord_x[i] = float(np.clip(m / 675.0, -1.2, 1.2))
    lev = np.full(N, level_norm, dtype=np.float32)
    return np.concatenate([X7, chord_x[:, None], lev[:, None]], axis=1).astype(np.float32)


def infer_song(fid, model, seed, two_pass=True, nb=None, temperature=1.0, greedy=False):
    d = json.load(open(os.path.join(BASE, "parsed", f"{fid}.json")))
    bpm_path = os.path.join(BASE, "bpm", f"{fid}.json")
    bpm = json.load(open(bpm_path))["segs"] if os.path.exists(bpm_path) else None
    level_norm = get_level(fid) / 25.0
    print(f"[level] fid={fid} level_norm={level_norm:.3f} nb={nb}")
    lines = defaultdict(list)
    for n in d["notes"]:
        lines[n["line_id"]].append(n)

    def run(chord_map):
        out = []
        for lid in sorted(lines.keys()):
            lnotes = sorted(lines[lid], key=lambda n: n["t"])
            if len(lnotes) < 4:
                for n in lnotes:
                    out.append({"t": n["t"], "type": n.get("type", 1), "x": n["x"],
                                "line_id": lid, "dur": n.get("dur", 0.0)})
                continue
            Xw = build_features_chord(lnotes, bpm, chord_map, level_norm)
            pred = infer_line(model, Xw, np.random.RandomState(seed), nb=nb, temperature=temperature, greedy=greedy)
            for j, n in enumerate(lnotes):
                out.append({"t": n["t"], "type": n.get("type", 1), "x": float(pred[j]),
                            "line_id": lid, "dur": n.get("dur", 0.0)})
        return out

    # 第一遍：无双押上下文
    pass1 = run({})
    if not two_pass:
        return pass1
    # 第二遍：同刻其他线粗排 x 均值作为 chord_x
    by_t = defaultdict(list)
    for n in pass1:
        by_t[round(n["t"], 3)].append(n["x"])
    chord_map = {t: float(np.mean(xs)) for t, xs in by_t.items() if len(xs) >= 2}
    pass2 = run(chord_map)
    return pass2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fid", type=str)
    ap.add_argument("--ckpt", type=str, default="layout_ckpt_chord9_full")
    ap.add_argument("--nb", type=int, default=None, help="桶数（默认从权重头自动推断）")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", type=str, default=None)
    ap.add_argument("--pass1", action="store_true", help="只跑第一遍(无上下文)，作对照")
    ap.add_argument("--temperature", type=float, default=1.0, help="采样温度，<1 锐化趋近argmax（平滑轨迹）")
    ap.add_argument("--greedy", action="store_true", help="完全确定性：每次取最可能的位移")
    ap.add_argument("--gap", action="store_true", help="启用 enforce_chord_gaps(min_gap=200) 后处理（默认关，已证伪固定间距）")
    args = ap.parse_args()

    ck = torch.load(os.path.join(BASE, args.ckpt, "model.pth"), map_location="cpu")
    nb = args.nb or ck["model"]["head.weight"].shape[0]
    feat = ck["model"]["gru.weight_ih_l0"].shape[1]
    model = GRUCls9(feat=feat, nb=nb); model.load_state_dict(ck["model"]); model.eval()
    print(f"加载 {args.ckpt}: feat={feat} nb={nb}")

    notes = infer_song(args.fid, model, args.seed, two_pass=not args.pass1, nb=nb, temperature=args.temperature, greedy=args.greedy)
    notes = [n for n in notes if n.get("type", 1) in {1, 2}]
    if args.gap:
        notes = enforce_chord_gaps(notes)
    notes.sort(key=lambda n: (n["line_id"], n["t"]))
    result = {"fid": args.fid, "mode": "sample", "seed": args.seed, "ckpt": args.ckpt,
              "two_pass": not args.pass1, "temperature": args.temperature, "greedy": args.greedy, "n_notes": len(notes), "notes": notes}
    if args.out:
        json.dump(result, open(args.out, "w"), ensure_ascii=False, indent=1)
        print(f"已写入 {args.out}: {len(notes)} 个音符")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=1)[:2000])


if __name__ == "__main__":
    main()
