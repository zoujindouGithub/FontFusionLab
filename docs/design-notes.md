# 设计笔记 (Design Notes) — FontFusionLab / 字体融合实验室

本项目起源于将 **FiraCode**（代码连字与 Nerd Fonts 符号）与 **Maple Mono**（圆角风格 CJK）融合的需求，现已演进为 **Recipe 驱动的多 Variant 字体融合平台**：同一构建核心由 JSON 配方实例化出多个 production Variant。本文记录核心设计决策与技术演进。

---

## 历史演进（单 Variant 时期，R1–R9）

- **R1-R4 源字体选型**：拉丁与图标采用 [FiraCode Nerd Font Mono](https://github.com/ryanoasis/nerd-fonts/tree/master/patched-fonts/FiraCode)；CJK 采用 [Maple Mono NF CN](https://github.com/subframe7536/maple-font)。
- **R5 字体合并方案**：FiraCode UPM=1950、Maple UPM=1000，FontForge `MergeFonts` 因度量不兼容崩溃，改用 `fontTools` 字形级抽取、坐标变换与复合字形扁平化。
- **R6 命名与 RIBBI 规范**：四字面严格遵循 OpenType RIBBI，保证编辑器与终端标准归组。家族名现由配方 `family` 字段驱动（不再全局硬编码）。
- **R7-R8 选择性 Hinting**：仅对注入 CJK 用 `ttfautohint` 生成指令，拉丁保留原版指令；制表符区 (U+2500-U+259F) 160 个字形程序与 FiraCode 原版逐字节一致，终端框线无灰度漂移。
- **R9 终端与 IDE 兼容**：Windows Terminal、VS Code 及衍生 IDE 开箱即用。

### 关键技术坑点

1. **LSB 贴边 Bug**：早期注入 CJK 的 `hmtx.lsb` 设 0 导致 21,264 个汉字靠左贴边；修复为变换后真实轮廓 `round(xmin)`。
2. **源字符格居中**：Maple 字符格 advance=1200 而非 UPM 1000；按源字符格计算水平偏移，保留标点与非对称笔画的原生留白。
3. **5% 等比字面微调**：注入 CJK 围绕排版框中心放大 5%（配方 `cjk.scale=1.05`），保持 2:1（2400 格宽）下更饱满。
4. **斜体度量与基线对齐**：斜体 `hhea.ascender/upem` 与正体严格对齐 0.923，消除终端切斜体的基线跳动。

---

## Source/Recipe 模型

v2.0.0 起构建核心不再绑定任何单一 Variant；一切差异数据化：

- **Source manifest（`sources/manifest.json`，schema 同目录）**：`sources.<id>.files.<Style>` 二选一登记 `{path, sha256}`（Git 内置）或 `{url, sha256}`（HTTPS + 强制校验，缓存 `.cache/sources/<sha256>.ttf`）。SHA256 是唯一的来源同一性判据，构建前逐文件校验，篡改即拒构建。
- **私有来源**：只写未提交的 `sources/local.json`（模板 `sources/local.example.json`）。`production` 配方引用的来源必须出现在公开 manifest，catalog 加载时强制（防私有来源经 production 配方外泄）；`experimental` 配方可引用私有源 ID，仅配置了该源的机器可构建。
- **Recipe（`recipes/<id>.json`）**：`family`（安装家族名，注册表值即用它）、`file_prefix`、`cjk.source`/`cjk.scale`、`styles.<Style>.{base, source_style, cjk_source?, autohint}`。`base` 与 `cjk_source` 同文件时注入集为空，该字面走 passthrough——这保证 firacode-maple 斜体与旧产线行为等价（已由逐字节对比与回归测试锁定）。
- **输出隔离**：`build/<recipe-id>/<file_prefix>-<Style>.ttf`；verify / check-cjk-layout / install / package 全部经 `--recipe`/`--variant` 或 `-Variant`/`-Recipe` 从配方解析路径，无本机绝对路径。
- **发布**：`package-release.py` 一次产出 `release/v2.0.0/`——每个 production Variant 一个独立 ZIP（四 TTF + LICENSE + 变体 README + recipe.json 溯源）、`variants.json`、`SHA256SUMS.txt`；GitHub 上是一个 Release 多资产，不是每 Variant 一个 Release。任何缺件或私有引用在任何写出前失败；同输入重复打包字节一致。

## OTS 兼容：simple glyph OVERLAP_SIMPLE 标志

**根因**：TrueType `glyf` simple 轮廓的 flags 含 `OVERLAP_SIMPLE (0x40)` 时，Chrome 的 OTS 净化器会对该字形执行昂贵的 overlap 检查，检出真实自交/重叠即**拒绝整个字体**。Sarasa Fixed SC 源字形普遍置位该标志（Regular 即 5.1 万+），注入变换（缩放+取整）后部分轮廓产生实际自交，导致修复前的 Sarasa 构建产物在 Chrome 中 `FontFace.load` 直接失败（NetworkError）；MapleItalic 基底亦自带约 2.2 万个带标志字形，同样影响两个 Variant 的斜体。

**管线级双重清除（生产修复，非网页 workaround）**：

1. `inject_cjk` 复制注入字形、展开 composite 后，仅清除 flags 的 `0x40` 位（保留 on-curve 等其余位），坐标/endPts/advance/LSB 一律不动——`tests/test_inject_cjk.py` 逐点锁定该不变式。
2. 保存前 `strip_overlap_flags` 对**全字体** simple glyph 再扫一遍（覆盖未经注入路径的基底字形，如斜体的 2.2 万个）——`tests/test_strip_overlap.py` 锁定"只动标志位、几何与度量逐字节不变"。
3. `verify.py` 设常驻门禁：四个生产字面全部 simple glyph 不得残留 `0x40`；真实浏览器对照验证修复前产物 REJECTED、修复后 8 字面全部 LOADED。

**为何不做网页 fallback**：在预览页掩盖只是把损坏的发行物藏起来——用户安装到系统的同名 TTF 在浏览器内嵌、WebFont 自托管、Office 等其他走 OTS 的管线仍会被拒。清除该标志不改变任何轮廓与度量，是对产物本身的正确修复。

## Box-Drawing 与 2:1 宽度不变式

正体路径在 `ttfautohint` 之后从 FiraCode 原字体逐字节还原 U+2500-U+259F 共 160 个字形的 hint 程序（无程序字形显式置空程序），保证终端框线与 FiraCode 原版渲染 100% 一致；全部注入 CJK 的 advance 恒等于 2 倍拉丁格宽，`check-cjk-layout.py` 按配方源字体逐字形核验居中、1.05× 等比缩放、LSB 与 2:1。
