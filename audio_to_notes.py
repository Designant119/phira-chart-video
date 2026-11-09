#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""纯听音采音 wrapper：输入 歌(音频+仅取BPM/offset) → BeatFCN v16 预测候选音符。
输出: {fid, bpm, offset, notes:[{t, type, score}]}，type=1 单押 / 2 双押(同刻2音)。
只用谱面 json 的 BPMList/META.offset（歌的元属性），不用任何原谱音符。
"""
import json, os, sys, zipfile, argparse
import numpy as np

PKG = "/home/user/Doubao/chats/38447255470430466/BeatFCN_pack_v2"
sys.path.insert(0, PKG)
from extract_npz_v13 import parse_chart, chart_sec, beat_grid, beats_of, beat_to_sec
from extract_pitch import decode_audio, extract_pitch
from beat_fcn_train_v16 import BeatFCNContext, compute_flux
from infer_multi_div_v16 import load_zip, make_model_input, make_grid, snap_scores

SR = 22050; HOP = 256; HR = SR / HOP
GRID_DIV = 32  # 128 分 = 每拍 32 格

def sec_to_beat(t, segs):
    """秒 → beat（按 BPM 分段反推，与 beat_to_sec 互逆）"""
    for i in range(len(segs) - 1, -1, -1):
        sb, bpm, ss = segs[i]
        if t >= ss:
            return sb + (t - ss) * bpm / 60.0
    sb0, bpm0, ss0 = segs[0]
    return sb0 + (t - ss0) * bpm0 / 60.0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", required=True, help="谱面 zip（只需音频+BPM/offset，音符全由模型预测）")
    ap.add_argument("--weights", default=os.path.join(PKG, "beat_fcn_best_v16test.pt"))
    ap.add_argument("--th", type=float, default=0.5, help="单押阈值")
    ap.add_argument("--th2", type=float, default=0.5, help="双押阈值")
    ap.add_argument("--out", default="audio_notes.json")
    ap.add_argument("--grid", type=int, default=32, help="候选吸附网格：每拍份数（32=128分/默认，16=16分）")
    args = ap.parse_args()

    load = load_zip(args.zip)
    if load is None:
        print("加载失败（无谱面或无音频）"); sys.exit(1)
    chart, wav, _orig_notes = load  # _orig_notes 不用！音符全靠模型
    bpm = chart.get('BPMList', [])
    offset = float(chart.get('META', {}).get('offset', 0)) / 1000.0
    segs = chart_sec(chart)   # [(起始beat, bpm, 起始秒)]
    print(f"歌: {os.path.basename(args.zip)} | 音频 {len(wav)/SR:.1f}s | BPM {bpm} | offset {offset*1000:.0f}ms")
    print(f"(只用元信息，原谱 {len(_orig_notes)} 个音符全部丢弃，音符由模型预测)")

    model = BeatFCNContext(n_mels=82, ch=48, ctx_off=True, n_pitch=46)
    d = torch_load(args.weights)
    model.load_state_dict(d["model"]); model.eval()
    print(f"权重: best={d.get('best','?')} ep={d.get('ep','?')}")

    g128 = make_grid(wav, chart, GRID_DIV)
    x = make_model_input(wav, chart, g128)
    import torch
    with torch.no_grad():
        o1, o2 = model(torch.from_numpy(x).unsqueeze(0), torch.from_numpy(g128), None)
        s1 = torch.sigmoid(o1)[0].detach().numpy()  # 单押
        s2 = torch.sigmoid(o2)[0].detach().numpy()  # 双押
    print(f"128分网格 {len(g128)} 格 | 单押≥{args.th}: {(s1>=args.th).sum()} | 双押≥{args.th2}: {(s2>=args.th2).sum()}")

    # 候选：合并单/双押候选，吸附到指定网格（--grid 每拍份数），同格合并（双押优先、取最强分）
    grid_n = args.grid
    cand = {}
    for i, t in enumerate(g128):
        a, b = float(s1[i]), float(s2[i])
        if a < args.th and b < args.th2:
            continue
        # t(秒) → beat → 吸附到每拍 grid_n 份 → 秒
        beat = sec_to_beat(float(t), segs)
        tb = round(beat * grid_n) / grid_n
        t16 = beat_to_sec(tb, segs)
        key = round(float(t16), 4)
        cur = cand.get(key)
        new = (2, max(b, 0.0)) if b >= args.th2 else (1, a)
        if cur is None:
            cand[key] = new
        else:
            # 双押优先；同类型取强分
            if new[0] == 2 or cur[0] == 2:
                if cur[0] == 2 and new[0] == 2:
                    cand[key] = (2, max(cur[1], new[1]))
                else:
                    cand[key] = (2, new[1] if new[0] == 2 else cur[1])
            else:
                cand[key] = (1, max(cur[1], new[1]))
    print(f"吸附网格：每拍 {grid_n} 份（{'16分' if grid_n==16 else '128分'}）| 候选 {len(cand)} 个")
    notes = [{"t": t, "type": tp, "score": sc} for t, (tp, sc) in sorted(cand.items())]
    # 双押时刻自动拆 2 音（2 条线），单押 1 音
    final = []
    for n in notes:
        if n["type"] == 2:
            final.append({"t": n["t"], "type": 1, "score": n["score"], "chord": 2})
        else:
            final.append({"t": n["t"], "type": 1, "score": n["score"], "chord": 1})
    out = {"fid": os.path.basename(args.zip).split('_')[0], "bpm": bpm, "offset": offset,
           "th": args.th, "th2": args.th2, "n_notes": len(final), "notes": final}
    json.dump(out, open(args.out, "w"), ensure_ascii=False, indent=1)
    print(f"已写入 {args.out}: {len(final)} 个音符（{sum(1 for n in final if n['chord']==2)} 个双押）")
    print("前10个:", [(round(n['t'],2), n['chord']) for n in final[:10]])

def torch_load(p):
    import torch
    return torch.load(p, map_location="cpu", weights_only=False)

if __name__ == "__main__":
    main()
