# Variant 指南 (Font Variants Guide) — FontFusionLab / 字体融合实验室

本文档对照 FontFusionLab 当前的多套 production Variant，并给出配置与人工验收流程。每个 Variant 由 `recipes/<id>.json` 唯一确定；新增 Variant 的流程与门禁见 [README「添加新 Variant」](../README.md#添加新-variant)。

## Variant 对照表

| | **FiraCode Sarasa Mono** | **FiraCode Maple Mono** |
|---|---|---|
| Recipe ID | `firacode-sarasa`（默认） | `firacode-maple` |
| 文件前缀 | `FiraCodeSarasaMono` | `FiraCodeMapleMono` |
| 输出目录 | `build/firacode-sarasa/` | `build/firacode-maple/` |
| 正体基底 | FiraCode Nerd Font Mono | FiraCode Nerd Font Mono |
| 正体 CJK 来源 | Sarasa Fixed SC（注入缺失 CJK 码位） | Maple Mono CN（注入缺失 CJK 码位） |
| 斜体基底 | MapleItalic（Maple 手写斜体骨架） | MapleItalic（同左） |
| 斜体 CJK 策略 | 用 Sarasa Fixed SC 对应风格**替换**约 8.2k 个 CJK 码位 | **不替换**（base 与注入源同文件 → 注入集为空，passthrough） |
| CJK 缩放 | 1.035×（围绕排版框中心；Sarasa 字面率较高，无需 1.05×） | 1.05×（围绕排版框中心） |
| 正体 hinting | 注入 CJK 经 `ttfautohint`；拉丁与 Box-Drawing 保留 FiraCode 原程序逐字节还原 | 同左 |
| 斜体 hinting 差异 | 基底保留 Maple 原 hint；**注入的 Sarasa CJK 为无 hint 轮廓**（不做整字体 autohint，避免改写非 CJK） | 基底保留 Maple 原 hint，全部字形与旧产线一致 |
| 质量门禁 | `verify.py` + `check-cjk-layout.py`（含 OVERLAP_SIMPLE OTS gate）全部 PASS | 同左，且斜体与旧产物逐字节等价对比通过 |

共性不变式（全部 Variant）：

- 严格 RIBBI 四字面（Regular/Bold/Italic/Bold Italic），ID1/ID2/ID16/ID17 由配方 `family` 驱动。
- 注入 CJK advance 恒为 2 倍当前字面拉丁格宽（2400/1000 UPM 语境下即 2:1）。
- 注入字形按源字符格居中、`hmtx.lsb` 等于变换后真实轮廓 `xmin`。
- Box-Drawing 区 (U+2500–U+259F) hint 程序与 FiraCode 原版逐字节一致（仅正体路径执行还原；斜体基底自带等价程序）。
- simple glyph 一律不带 OVERLAP_SIMPLE 标志（Chrome/OTS 兼容，见[设计笔记](./design-notes.md#ots-兼容simple-glyph-overlap_simple-标志)）。

## 系统字体家族名

安装后系统识别的家族名即各 Variant 的 `family`：

```text
FiraCode Sarasa Mono
FiraCode Maple Mono
```

两个家族互不覆盖，可同机共存；`scripts/install.ps1` 按 `family` 写注册表值、按 `file_prefix` 命名文件。

## Windows Terminal

设置（`Ctrl + ,`）→ 默认值或具体 Profile → 外观 → 字体面，选 `FiraCode Sarasa Mono` 或 `FiraCode Maple Mono`。JSON 方式：

```json
{
  "profiles": {
    "defaults": {
      "font": {
        "face": "FiraCode Sarasa Mono",
        "size": 12.0
      }
    }
  }
}
```

连字开关（Windows Terminal 1.22+）：

```json
"font": { "face": "FiraCode Sarasa Mono", "features": { "calt": 0 } }
```

## VS Code 及衍生 IDE

```json
{
  "editor.fontFamily": "'FiraCode Maple Mono', Consolas, monospace",
  "terminal.integrated.fontFamily": "FiraCode Maple Mono",
  "editor.fontLigatures": true
}
```

关闭连字：`"editor.fontLigatures": false`。

## 人工验收 Windows Terminal pwsh

以下是对**每个 Variant** 的必做人工验收（自动化门禁不能替代）：

1. 安装：`pwsh -File scripts/install.ps1 -Variant <recipe-id> -WhatIf` 演练后去掉 `-WhatIf` 执行；确认输出中四个注册表项均使用目标 family 名。
2. 完全重启 Windows Terminal，`font.face` 设为目标家族名。
3. 逐项目测：
   - 四样式：`Get-Process | Select-Object -First 3` 分别以 Regular/Bold/Italic/BoldItalic 上下文渲染；
   - 连字：`=> != === == !== <= >= -> <- <=> && || ++ --` 开合正常；
   - 中英混排对齐：`中文对齐 ABC 0123456789`，汉字恰为两个拉丁格宽；
   - Box-Drawing：`┌─┬─┐│ ├─┼─┤└─┴─┘` 相邻无灰度漂移、无断线；
   - 全角标点与 `PS>` 提示符示例行（如 `Get-ChildItem -File | Where-Object { $_.Length -gt 1MB }`）无回退字体痕迹。
4. 两个家族都验收后才可晋升 `production`。

## 常见问题

**安装后应用没有立即识别新字体？** 完全退出并重启该应用；多数应用只在启动时扫描字体表。

**Windows 提示字体文件被占用？** `scripts/install.ps1` 自动尝试备用命名槽位（`-v42`/`-v41`）热替换，并向系统广播 `WM_FONTCHANGE`，无需重启系统。

**浏览器预览显示加载失败？** 预览只加载 `build/<id>/` 下的构建产物：先 `uv run python scripts/build.py --all`，并从仓库根目录（而非 `preview/`）启动 HTTP 服务。

**`sources/` 目录结构？** 字体源文件统一收纳在 `sources/<source-id>/` 下，子目录名与 `manifest.json` 中的 source ID 对应，新增源只需添加子目录和清单条目，不影响根目录。
