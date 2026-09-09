# FiraCode Maple Mono

FiraCode 与 Maple Mono 的高品质融合等宽字体（Surgical Selective Hinting & Visual-Tuned Edition）。

## 核心设计理念

* **完美分工**：
  * **拉丁字符、数字、符号、连字、Nerd Font 图标**：100% 继承自 [FiraCode Nerd Font Mono](https://github.com/ryanoasis/nerd-fonts)。
  * **中日文字形 (CJK)、全角标点符号**：100% 继承自 [Maple Mono NF CN](https://github.com/subframe7536/maple-font)。
* **精确居中与 2:1 等宽**：
  * 中文字形 advance 严格设定为 2 倍拉丁格宽 (2400 设计单位)，杜绝终端错位与表格漂移。
  * **源字符格居中**：正体构建按 Maple Mono 源 advance (1200) 对齐居中，彻底消除左偏，同时保留非对称字形与全角标点的原生设计习惯。
  * **5% 等比字面饱满放大**：Regular / Bold 的注入 CJK 字形等比放大 5%（围绕排版框中心变换），缩小汉字视觉间距，解决字符偏小、空旷的问题，保持汉字宽高比与笔画粗细均衡协调。
* **外科手术式 Hinting 注入**：
  * 仅对注入的 CJK 字形使用 `ttfautohint` 重建 TrueType 指令，大幅提升小字号屏幕锐利度。
  * 拉丁字形完全保留 FiraCode 原始高品质 hinting 指令。
  * 制表符区 (U+2500-U+259F) 160 个字形程序与 FiraCode 原版 100% 逐字节完全一致，保证终端框线无灰度漂移与断裂。
* **严格规范的 RIBBI 四字面**：
  * 提供 `Regular`、`Bold`、`Italic`、`Bold Italic` 全套四字面。
  * 斜体垂直度量比例与正体严格对齐 (0.923)，消除终端与编辑器中切换斜体时的基线跳动。
  * 补齐 Windows 与 Unicode 全套 CMap 子表，保证各种 IDE 与终端完美识别。

## 目录结构

```text
fonts/
├── FiraCode-src/       # FiraCode Nerd Font Mono 原始源字体
├── MapleMono-src/      # Maple Mono NF CN 正体源字体
├── MapleItalic-src/    # Maple Mono NF CN 斜体源字体
├── merged-v4/          # 最终生产构建产物 (*.ttf)
├── scripts/
│   ├── build.py        # 完整端到端自动化构建管线 (默认集成 5% 放大与居中)
│   ├── verify.py       # 自动化质量门禁与渲染审计套件
│   ├── check-cjk-layout.py # CJK 字面布局与居中自动化检验工具
│   ├── install.ps1     # 用户级自动安装与 IDE 环境同步脚本
│   └── audit-sources.py# 字形归属与度量审计工具
├── specs/              # 需求与规约文档
└── docs/               # 字体变体说明与配置指南
```

## 快速使用

### 1. 全量构建
```bash
python scripts/build.py
```

### 2. 运行质量门禁验证
```bash
python scripts/check-cjk-layout.py merged-v4
python scripts/verify.py
```

### 3. 安装并同步至终端与 IDE
```powershell
powershell -ExecutionPolicy Bypass -File scripts/install.ps1
```
