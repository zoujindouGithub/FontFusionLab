# 设计笔记与演进历程 (Design Notes & Evolution)

本项目起源于将 **FiraCode**（优秀的代码连字与 Nerd Fonts 符号）与 **Maple Mono**（高质量圆角风格 CJK 字符）融合成单一套等宽字体的需求，历经多次迭代优化。本文档记录核心设计决策与技术演进路径。

---

## 原始需求与演进 (Requirements & Iterations)

- **R1-R4 源字体选型**：
  - 拉丁与图标采用 [FiraCode Nerd Font Mono](https://github.com/ryanoasis/nerd-fonts/tree/master/patched-fonts/FiraCode)。
  - CJK 字符采用 [Maple Mono NF CN](https://github.com/subframe7536/maple-font)。
- **R5 字体合并方案**：
  - FiraCode UPM=1950，Maple Mono UPM=1000。FontForge `MergeFonts` 因度量不兼容崩溃，最终采用 `fontTools` 字形级抽取、坐标变换重构与复合字形扁平化。
- **R6 命名与 RIBBI 规范**：
  - 命名确立为 `FiraCode Maple Mono`。四字面（Regular, Bold, Italic, Bold Italic）严格遵循 OpenType RIBBI 规范，确保各类编辑器与终端能够标准归组。
- **R7-R8 选择性 Hinting 架构**：
  - 确立「仅对注入的 CJK 字形使用 `ttfautohint` 生成指令，拉丁部分保留原版指令」的外科手术式策略。
  - 制表符区 (U+2500-U+259F) 160 个字形程序与 FiraCode 原版 100% 逐字节完全一致，保证终端框线无灰度漂移与断裂。
- **R9 终端与 IDE 兼容**：
  - Windows Terminal、VSCode、Trae、Antigravity、Kiro 等 IDE 均能开箱即用。

---

## 关键技术坑点与攻克记录 (Key Milestones)

1. **左边距 (LSB) 与贴边 Bug**：
   - 早期版本将注入 CJK 字符的 `hmtx.lsb` 设为 0，导致 21,264 个汉字靠左贴边且字符变窄。随后修复为真实轮廓 `round(xmin)`。
2. **源字符格居中 (Source-Cell Centering)**：
   - Maple Mono 的字符格 advance 为 1200，而非 UPM 1000。基于源字符格计算水平偏移，彻底消除了汉字整体偏左的问题，并保留了标点与非对称笔画的原生设计。
3. **5% 等比字面微调**：
   - 将注入的 CJK 字形围绕排版框中心等比放大 5%，在保持 2:1 (2400 格宽) 的前提下有效缩小视觉间距，使字符更加饱满自然。
4. **斜体度量与基线对齐**：
   - 斜体 `hhea.ascender` 比例与正体严格对齐为 0.923，消除终端切换斜体时的基线垂直跳动。
