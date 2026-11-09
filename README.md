# Phira Chart Video Generator

自动从音游谱面/音频生成下落式音游风格的可视化视频：
- 音频 onset 检测（BeatFCN）→ 音符时间点
- 9 维排键模型 → 音符 x 位置
- PIL + OpenCV 渲染音符下落 + 标注 + 连击
- ffmpeg 拼接 + 打击音混音

## 文件说明

| 文件 | 作用 |
|---|---|
| `audio_to_notes.py` | 音频 onset 检测，输出音符时间点 JSON |
| `make_hit_sfx.py` | 生成打击音效轨 |
| `render_*.py` | 各曲渲染脚本（PIL 逐帧画音符下落） |
| `phira_charts_dl/infer_chord.py` | 9 维模型排 x 位置 |
| `phira_charts_dl/build_*_input.py` | 分线/分轨道构建排键输入 |
| `rerender_all.sh` | 批量重渲染 |

## 用法

```bash
# 1. 采音（128分网格，阈值0.4）
python audio_to_notes.py --zip song.pez --th 0.4 --th2 0.4 --grid 32 --out notes.json

# 2. 排键
python phira_charts_dl/infer_chord.py song --ckpt layout_ckpt_chord_full9 --seed 7 --out infer.json

# 3. 渲染
python render_td.py 0 75 out_a.mp4

# 4. 拼接 + 混音
ffmpeg -i out_a.mp4 -i out_b.mp4 -filter_complex concat ...
```

## 标注格式

每个音符下方标注 `{累计拍号}:{拍内位置}/32`，拍号从曲首累计。
