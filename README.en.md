# FiraCode Maple Mono

<p align="center">
  <b>Modern coding ligatures and icons of FiraCode meet warm, elegant CJK glyphs of Maple Mono</b><br>
  <i>A high-quality hybrid monospaced font tailored for terminals and code editors</i>
</p>

<p align="center">
  <a href="./README.md">简体中文</a> | <a href="./README.en.md">English</a>
</p>

<p align="center">
  <a href="https://github.com/zouji/FiraCodeMapleMono/releases"><img src="https://img.shields.io/github/v/release/zouji/FiraCodeMapleMono?include_prereleases&color=brightgreen" alt="Release"></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/License-OFL--1.1-blue.svg" alt="License: OFL-1.1"></a>
  <img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg" alt="PRs Welcome">
</p>

---

## Overview

Many developers love **[Fira Code](https://github.com/tonsky/FiraCode)** for its exquisite programming ligatures and clean character forms. However, when working in multilingual or mixed English-Chinese environments (comments, docs, CLI output logs), system fallback fonts often introduce visual fragmentation and misalignment.

**FiraCode Maple Mono** uses surgical glyph-level fusion:
- **Latin, Digits, Ligatures, Nerd Fonts Icons**: 100% preserved from original FiraCode Nerd Font Mono.
- **CJK Ideographs & Full-width Punctuation**: 100% sourced from [Maple Mono CN](https://github.com/subframe7536/maple-font).
- **Full RIBBI Coverage**: Provides `Regular`, `Bold`, `Italic`, and `Bold Italic`.

---

## Key Features

### 1. Strict 2:1 Monospaced Grid Alignment
Each full-width CJK character occupies exactly 2 standard Latin cells (2400 design units). CLI tables, TUI interfaces (e.g. `lazygit`, `htop`), and box-drawing lines remain perfectly aligned without jitter or horizontal drift at any font size.

### 2. Source-Cell Centering & 5% Visual Scaling
- **Source-Cell Centering**: Horizontal shift is calculated based on Maple Mono's native cell advance (1200), eliminating left-edge clipping while faithfully preserving the native layout whitespace for punctuation (commas, periods, quotes).
- **5% Uniform CJK Scaling**: Injected CJK glyphs are uniformly scaled up by 5% around their bounding box center, effectively tightening character spacing and providing a more solid, balanced visual weight alongside Latin letters.

### 3. Selective Hinting Architecture
- **Zero Latin Degradation**: Preserves original FiraCode TrueType hinting bytecode verbatim; rendering remains sharp and undistorted at small sizes.
- **CJK Hinting Rebuilt**: Automatically generates hinting instructions for all 21,266 CJK glyphs via `ttfautohint`, ensuring stroke clarity under Windows ClearType and standard 1080P screens.
- **Seamless Box-Drawing**: Restores 160 box-drawing glyphs (U+2500–U+259F) byte-for-byte to match FiraCode, guaranteeing consistent grayscale and continuous border lines in terminal TUIs.

### 4. Consistent Vertical Metrics & Standard RIBBI
- Aligns vertical metric ratios (`hhea.ascender` ratio = 0.923) between upright and italic styles, eliminating baseline jumping when mixing styles.
- Fully conforms to OpenType RIBBI naming conventions, ensuring proper grouping across editors and operating systems.

---

## Download & Installation

### Option A: Direct Download (Recommended)

1. Go to the **[Releases](https://github.com/zouji/FiraCodeMapleMono/releases)** page and download `FiraCodeMapleMono-v1.0.zip`.
2. Extract the archive to get four `.ttf` files:
   - `FiraCodeMapleMono-Regular.ttf`
   - `FiraCodeMapleMono-Bold.ttf`
   - `FiraCodeMapleMono-Italic.ttf`
   - `FiraCodeMapleMono-BoldItalic.ttf`
3. **Install on your system**:
   - **Windows**: Select all 4 files -> Right click -> Click "Install" or "Install for all users".
   - **macOS**: Double-click each font file -> Click "Install Font".
   - **Linux**: Copy files to `~/.local/share/fonts/` and run `fc-cache -f -v`.

### Option B: Windows One-Click Script

If you are on Windows and want to avoid file-lock errors while your editor/terminal is running:

```powershell
# Run from the repository or extracted root
powershell -ExecutionPolicy Bypass -File scripts/install.ps1
```
The script handles slot-based hot swapping, registers font resources with GDI, broadcasts `WM_FONTCHANGE`, and syncs configurations for VSCode, Cursor, and other IDEs.

---

## Editor & Terminal Configuration

After installation, the font family name is recognized as:
```text
FiraCode Maple Mono
```

### Windows Terminal
In `settings.json`:
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

### VSCode / Cursor / Other IDEs
In `settings.json`:
```json
{
  "editor.fontFamily": "'FiraCode Maple Mono', Consolas, monospace",
  "terminal.integrated.fontFamily": "FiraCode Maple Mono",
  "editor.fontLigatures": true
}
```

---

## Building from Source

This project provides a fully reproducible and self-contained build pipeline.

### Prerequisites
- Python 3.10+
- Required libraries:
  ```bash
  pip install fonttools ttfautohint-py freetype-py Pillow
  ```

### Build Steps
```bash
# 1. Clone the repository
git clone https://github.com/zouji/FiraCodeMapleMono.git
cd FiraCodeMapleMono

# 2. Run the build script (generates 4 fonts into merged-v4/)
python scripts/build.py

# 3. Run automated verification and layout checks
python scripts/check-cjk-layout.py merged-v4
python scripts/verify.py
```

---

## Upstream Credits & Acknowledgements

This font is a derivative work based on the following outstanding open-source projects:

- **[Fira Code](https://github.com/tonsky/FiraCode)** by Nikita Prokopov (OFL-1.1)
- **[Maple Mono](https://github.com/subframe7536/maple-font)** by subframe7536 (OFL-1.1)
- **[Nerd Fonts](https://github.com/ryanoasis/nerd-fonts)** by Ryan Gosse (MIT)
- **[Fusion-JetBrainsMapleMono](https://github.com/SpaceTimee/Fusion-JetBrainsMapleMono)** by SpaceTimee for structural inspiration

## License

This Font Software and accompanying scripts are licensed under the **[SIL Open Font License, Version 1.1](./LICENSE)**. Anyone is free to use, study, modify, and redistribute this font software.
