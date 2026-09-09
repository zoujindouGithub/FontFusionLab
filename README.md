# FiraCode Maple Mono

<p align="center">
  <b>FiraCode 的现代编程连字与图标，遇上 Maple Mono 的温润中文字形</b><br>
  <i>专为终端与代码编辑器打造的高品质等宽融合字体</i>
</p>

<p align="center">
  <a href="./README.md">简体中文</a> | <a href="./README.en.md">English</a>
</p>

<p align="center">
  <a href="https://github.com/zoujindouGithub/FiraCodeMapleMono/releases"><img src="https://img.shields.io/github/v/release/zoujindouGithub/FiraCodeMapleMono?include_prereleases&color=brightgreen" alt="Release"></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/License-OFL--1.1-blue.svg" alt="License: OFL-1.1"></a>
  <img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg" alt="PRs Welcome">
</p>

---

## 项目简介

许多开发者钟爱 **[Fira Code](https://github.com/tonsky/FiraCode)** 的编程连字与符号设计，但在混排中文环境（终端注释、文档、输出日志）时，常受困于系统默认回退字体的视觉断裂感。

**FiraCode Maple Mono** 采用外科手术式的字形级重构方案：
- **西文字符、数字、代码连字、Nerd Fonts 图标**：100% 保留自原版 FiraCode Nerd Font Mono。
- **CJK 中日文字形与全角标点**：100% 抽取自 [Maple Mono CN](https://github.com/subframe7536/maple-font)。
- **四字面完整覆盖**：提供 `Regular`（正体）、`Bold`（粗体）、`Italic`（斜体）、`Bold Italic`（粗斜体）。

---

## 核心设计特性

### 1. 严格 2:1 等宽，终端对齐不漂移
1 个中文字符宽度精确等于 2 个英文字符宽度（2400 设计单位）。命令行表格、TUI 界面（如 `lazygit`、`htop`）、框线（Box-Drawing）在任何字号下均不发生左右漂移或错位。

### 2. 源字符格居中与 5% 字面微调
- **源字符格居中**：按 Maple Mono 原生字符格（advance=1200）计算居中平移量，彻底解决中西文拼接时汉字偏左贴边的问题，同时完美保留逗号、句号、引号等标点的原生排版留白。
- **5% 等比字面微调**：将注入的 CJK 字形围绕排版框中心等比放大 5%，有效收缩字符间距并提升饱满度，解决汉字偏小、空旷的违和感。

### 3. 选择性 Hinting 架构 (Selective Hinting)
- **西文零劣化**：完全保留 FiraCode 原版 TrueType hinting 指令，小字号渲染无模糊、无形变。
- **CJK 注入重建**：仅对注入的 21,266 个 CJK 字形执行 `ttfautohint` 重建指令，在 Windows ClearType 与普通 1080P 显示屏下保持笔画清晰锐利。
- **框线无缝衔接**：制表符区 (U+2500-U+259F) 的 160 个字形程序与 FiraCode 原版 100% 逐字节完全一致，保证终端边框灰度一致、绝不断线。

### 4. 垂直度量一致与标准 RIBBI 规范
- 正斜体垂直度量比例统一对齐为 0.923，消除终端或编辑器在正斜体混排时的基线跳动。
- 完整兼容 OpenType RIBBI 标准命名，各大 IDE 与终端均能正确将其归为同一个字体家族。

---

## 快速下载与安装

### 方案 A：直接下载安装（推荐）

1. 前往 **[Releases](https://github.com/zoujindouGithub/FiraCodeMapleMono/releases)** 页面下载最新发布的 `FiraCodeMapleMono-v1.0.zip`。
2. 解压压缩包，得到 4 个 `.ttf` 字体文件：
   - `FiraCodeMapleMono-Regular.ttf`
   - `FiraCodeMapleMono-Bold.ttf`
   - `FiraCodeMapleMono-Italic.ttf`
   - `FiraCodeMapleMono-BoldItalic.ttf`
3. **系统安装**：
   - **Windows**：全选 4 个文件 -> 右键 -> 点击「安装」或「为所有用户安装」。
   - **macOS**：双击字体文件 -> 点击「安装字体」。
   - **Linux**：将字体文件复制到 `~/.local/share/fonts/`，然后运行 `fc-cache -f -v`。

### 方案 B：Windows 一键免杀安装脚本

如果你使用 Windows，并希望在字体被当前终端或 IDE 锁定时平滑热更新：

```powershell
# 在克隆或解压的目录内运行
powershell -ExecutionPolicy Bypass -File scripts/install.ps1
```
脚本会自动处理候选版本槽位切换、向 GDI 注册并广播 `WM_FONTCHANGE` 系统事件，同时自动同步 VSCode / Cursor 等衍生 IDE 的字体配置。

---

## 编辑器与终端配置

系统安装完成后，识别的字体名称统一为：
```text
FiraCode Maple Mono
```

### Windows Terminal
在 `settings.json` 中配置：
```json
{
  "profiles": {
    "defaults": {
      "font": {
        "face": "FiraCode Maple Mono",
        "size": 12.0
      }
    }
  }
}
```

### VSCode / Cursor / Trae 等 IDE
在 `settings.json` 中配置：
```json
{
  "editor.fontFamily": "'FiraCode Maple Mono', Consolas, monospace",
  "terminal.integrated.fontFamily": "FiraCode Maple Mono",
  "editor.fontLigatures": true
}
```

---

## 从源码构建 (Build from Source)

本项目提供完全幂等、自包含的端到端构建工具链。

### 依赖环境
- Python 3.10+
- 依赖库：
  ```bash
  pip install fonttools ttfautohint-py freetype-py Pillow
  ```

### 构建步骤
```bash
# 1. 克隆仓库
git clone https://github.com/zoujindouGithub/FiraCodeMapleMono.git
cd FiraCodeMapleMono

# 2. 执行全量构建 (自动生成 4 个字面到 merged-v4 目录)
python scripts/build.py

# 3. 运行自动化质量门禁与布局校验
python scripts/check-cjk-layout.py merged-v4
python scripts/verify.py
```

---

## 致谢与上游开源项目

本项目为字形级融合衍生作品，衷心感谢以下开源字体项目及其作者的卓越工作：

- **[Fira Code](https://github.com/tonsky/FiraCode)** by Nikita Prokopov (OFL-1.1)
- **[Maple Mono](https://github.com/subframe7536/maple-font)** by subframe7536 (OFL-1.1)
- **[Nerd Fonts](https://github.com/ryanoasis/nerd-fonts)** by Ryan Gosse (MIT)
- **[Fusion-JetBrainsMapleMono](https://github.com/SpaceTimee/Fusion-JetBrainsMapleMono)** by SpaceTimee 提供合并思路与启发

## 开源协议

本项目产物及相关代码遵循 **[SIL Open Font License, Version 1.1](./LICENSE)**。任何人均可免费使用、学习、合并与重新分发本字体软件。
