# Win95 提示窗口 音符皮肤

Windows 95 提示音风格的音乐游戏音符皮肤（用于 Phira / prpr 渲染），配 Win95 经典提示音做打击音效。

## 内容

| 文件 | 说明 | 尺寸 |
|---|---|---|
| `click.png` / `click_mh.png` | tap 音符（蓝底白边，X 图标） | 1148×250 |
| `drag.png` / `drag_mh.png` | drag 音符（金底，? 图标） | 1098×200 |
| `flick.png` / `flick_mh.png` | flick 音符（红底，! 图标） | 1148×322 |
| `hold.png` / `hold_mh.png` | 长条图集（沿用上游原版，未改） | 1000×1100 |
| `hit_fx.png` | 打击特效图集（沿用上游原版） | 1000×875 |
| `info.yml` | 资源包元信息 | — |

`*_mh` 是多押（双押）版本：在单押基础上把白描边换成金色并加金色光晕，贴图尺寸与单押**完全一致**。

## 设计要点

- 造型取自 Windows 95 提示窗口图标：信息（蓝 X）、问号（金 ?）、警告（红 !）
- 单押与多押贴图尺寸严格相同 —— 渲染器按 `height / width` 决定音符厚度，尺寸不同会让多押看起来变厚 2.5 倍
- `info.yml` 的 `holdAtlas` / `holdAtlasMH` 为 50/50，未改图集切分

## 用法

把本目录内容覆盖到渲染器的 `assets/respack/` 下即可（prpr 默认读取该目录）。
若用 `phira-render`，也可以通过渲染参数里的 `resPackPath` 指向本目录。

## 音效

本仓库不含音效文件。打击音效固定读 `assets/click.ogg` / `drag.ogg` / `flick.ogg`（必须 44100Hz），
音量可用渲染参数 `volumeSfx` 调整（只作用于音符音效，不影响 BGM）。
