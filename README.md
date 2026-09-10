# FontFusionLab / 字体融合实验室

[简体中文](./README.md) | [English](./README.en.md)

**Recipe 驱动的多 Variant 字体融合平台**：以 JSON 配方把西文编程字形、连字和 Nerd Fonts 图标与所选 CJK 字形融合成等宽字体，面向终端与代码编辑器。项目名称是 **FontFusionLab / 字体融合实验室**；安装到系统中的字体族使用各自的 Variant 家族名。

## 当前两个生产 Variant

| 配方 ID | 系统字体族名 | CJK 来源 | 默认输出目录 |
|---|---|---|---|
| `firacode-sarasa`（默认） | **FiraCode Sarasa Mono** | Sarasa Fixed SC / 更纱等宽黑体 SC | `build/firacode-sarasa/` |
| `firacode-maple` | **FiraCode Maple Mono** | Maple Mono CN | `build/firacode-maple/` |

每个 Variant 提供 `Regular`、`Bold`、`Italic`、`BoldItalic` 四个字面，是同一项目中的并列生产配方，输出目录与安装家族互不覆盖。

风格构成：

- **FiraCode Sarasa Mono**：正体为 FiraCode Nerd Font Mono 拉丁 + Sarasa Fixed SC 正体 CJK；斜体沿用 Maple 手写斜体骨架（MapleItalic 基底），其 CJK 由 Sarasa Fixed SC 对应风格替换。
- **FiraCode Maple Mono**：正体为 FiraCode 拉丁 + Maple Mono CN CJK；斜体完全沿用 MapleItalic 基底（其 CJK 即源内字形），与历史 merged-v4 产线等价。
- 注入字形的 advance 恒为当前字面两个拉丁格宽；这不是对所有应用、字号与显示设备都无回退的保证。

字面边界与人工验收见 [Variant 指南](./docs/variants.md)；配方模型、OTS 兼容与 hinting 决策见 [设计笔记](./docs/design-notes.md)。

## 快速开始

需要 Python 3.11+ 与 [uv](https://docs.astral.sh/uv/)。以下命令均从仓库根目录运行：

```powershell
# 1. 安装固定依赖（fontTools、FreeType、ttfautohint 绑定、jsonschema、pytest）
uv sync

# 2. 构建全部 production Variant（输出隔离在 build/<recipe-id>/）
uv run python scripts/build.py --all

# 3. 逐个 Variant 过质量门禁（命名/度量/box 逐字节/FreeType 渲染/OTS 标志）
uv run python scripts/verify.py --recipe firacode-sarasa
uv run python scripts/verify.py --recipe firacode-maple

# 4. 安装（先演练再执行；家族名注册来自配方）
pwsh -File scripts/install.ps1 -Variant firacode-sarasa -WhatIf
pwsh -File scripts/install.ps1 -Variant firacode-sarasa
# 可选：-ConfigureEditors 显式同步 IDE 字体配置（默认不动用户配置）

# 5. 浏览器预览（不要从 preview/ 子目录启动，不要 file:// 直开）
uv run python -m http.server 8137 --bind 127.0.0.1
# 打开 http://127.0.0.1:8137/preview/
```

`build.py` 不带参数时默认 `firacode-sarasa`（显式默认），也可 `--recipe <ID或JSON路径>` 单独构建；`install.ps1` 支持 `-Variant <ID>` 或 `-Recipe <ID或JSON路径>`（二选一）与 `-OutputRoot`。

## 发布模型：一个 Release，多个 ZIP

**v2.0.0 是一个统一 GitHub Release**，在 [Releases](https://github.com/zoujindouGithub/FiraCodeMapleMono/releases) 中包含每个 Variant 的独立 ZIP 资产，而不是每个 Variant 单独建 Release：

- `FiraCodeSarasaMono-v2.0.0.zip`
- `FiraCodeMapleMono-v2.0.0.zip`
- `variants.json`（Variant 识别与各字体/压缩包 SHA256）与 `SHA256SUMS.txt`

每个 ZIP 内含该 Variant 的四个 TTF（`<file_prefix>-<Style>.ttf`）、`LICENSE`、对应变体 `README.md` 与 `recipe.json` 溯源。

**生成的 TTF/ZIP 不入库**：`build/`、`release/` 与 `*.ttf` 产物由 `.gitignore` 管理，只通过 Release 分发；从源码构建可复现同一配方与校验和流程。

安装方式：Windows 选中四个 TTF 右键安装（或用上面的 `install.ps1`）；macOS 用字体册；Linux 复制到 `~/.local/share/fonts/` 后 `fc-cache -f -v`。安装后重启使用字体的应用。

## 源字体与配方

- `sources/manifest.json` 登记现有四类来源：`firacode`、`maple-cn`、`maple-italic`、`sarasa-sc`（共 12 个 TTF，全部带 SHA256）。本项目不引入新字体来源。
- 公开来源支持两种登记方式：**Git 内置**（仓库相对 `path`）或 **URL + SHA256**（下载到 `.cache/sources/` 并强制校验，缓存文件按哈希命名）。
- `recipes/*.json` 定义家族名、文件前缀、CJK 源与缩放、每个字面的基底与 `autohint` 开关；格式见 `recipes/schema.json`（严格模式，拒绝未知字段）。`production` 配方参与 `--all` 与打包，`experimental` 配方可公开提交并用 `--recipe` 单独构建。
- 私有字体来源只写进**不提交**的 `sources/local.json`（模板 `sources/local.example.json`，规则已入 `.gitignore`）。production 配方的引用来源必须在公开 manifest 中登记，否则 catalog 拒载；实验配方可引用私有源 ID，但未配置该源的机器不能构建它。绝不提交私有字体、本机绝对路径或下载凭据。

字段与扩展规则见 [设计笔记的 Source/Recipe 模型](./docs/design-notes.md#sourcerecipe-模型)。

## 添加新 Variant

1. 复制 `recipes/firacode-maple.json` 为 `recipes/<新-id>.json`，改 `id`、`family`、`file_prefix`、`cjk.source/scale` 与逐字面的 `base`/`cjk_source`/`autohint`；先标 `"status": "experimental"`。
2. 在 `sources/manifest.json` 登记新的公开来源（Git `path` 或 `url`+`sha256`）；私有来源写到本机 `sources/local.json`，绝不入库。
3. 现有工具链全部按 `--recipe`/`--variant` 直接生效，无需改代码：

```powershell
uv run python scripts/build.py --recipe <新-id>
uv run python scripts/verify.py --recipe <新-id>
uv run python scripts/check-cjk-layout.py --recipe <新-id>
pwsh -File scripts/install.ps1 -Recipe <新-id> -WhatIf
uv run python scripts/package-release.py   # 自动打包全部 production Variant
```

晋升 `production` 前的门禁清单（缺一不可）：

- [ ] `uv run pytest -q` 全绿
- [ ] `build.py --recipe <id>` 八字面构建成功（含双 Variant 时 `--all`）
- [ ] `verify.py --recipe <id>` 全部 PASS（含 OVERLAP_SIMPLE OTS 门禁）
- [ ] `check-cjk-layout.py --recipe <id>` PASS（居中/缩放/LSB/2:1）
- [ ] `package-release.py` 通过确定性打包（同输入字节一致），`SHA256SUMS.txt` 可复核
- [ ] 真实浏览器可加载全部字面；Windows Terminal + pwsh 人工验收通过

## 布局与质量检查

```powershell
uv run python scripts/check-cjk-layout.py --recipe firacode-sarasa
uv run python scripts/check-cjk-layout.py --recipe firacode-maple
uv run python scripts/audit-sources.py --recipe firacode-sarasa   # 逐码位来源归因
uv run python scripts/package-release.py                          # 默认输出 release/v2.0.0/
```

自动检查覆盖字体结构、命名、字宽、布局、OTS 标志等程序可检查的性质；它们**不证明**系统安装、Windows Terminal 实际选字、连字 shaping 或特定显示设备的视觉质量已通过。

## 浏览器预览

预览页在仓库 `preview/` 内，由 `preview/variants.json` 驱动：Variant 上下排列、各自独立显隐开关，共享可调字号、连字开关与可编辑测试文本（默认含 26 大小写字母、10 数字、全部可见 ASCII 标点、中文、全角标点、`=> != ===` 连字、Box-Drawing 与 PowerShell 示例）。字体 URL 为相对路径（如 `../build/firacode-sarasa/FiraCodeSarasaMono-Regular.ttf`），不写本机绝对路径；加载失败会显式报错，不会用系统字体冒充样本。

```powershell
uv run python -m http.server 8137 --bind 127.0.0.1
```

打开 <http://127.0.0.1:8137/preview/>。需先从仓库根构建对应 Variant；浏览器预览不要求系统安装字体，但不能替代终端人工验收。

## 编辑器与终端配置

Windows Terminal 的 `font.face` 填 `FiraCode Sarasa Mono` 或 `FiraCode Maple Mono`：

```json
{
  "profiles": {
    "defaults": {
      "font": { "face": "FiraCode Sarasa Mono", "size": 12 }
    }
  }
}
```

VS Code / Cursor：

```json
{
  "editor.fontFamily": "'FiraCode Sarasa Mono', Consolas, monospace",
  "terminal.integrated.fontFamily": "FiraCode Sarasa Mono",
  "editor.fontLigatures": true
}
```

切换 Maple Variant 时替换为 `FiraCode Maple Mono`。请按 [人工验收步骤](./docs/variants.md#人工验收-windows-terminal-pwsh) 分别检查两个家族的四字面、连字、中英混排与框线。

## 上游与许可证

- [Fira Code](https://github.com/tonsky/FiraCode)，Nikita Prokopov 与项目作者，OFL-1.1。
- [Maple Mono](https://github.com/subframe7536/maple-font)，subframe7536 与项目作者，OFL-1.1；提供 Maple CJK 与两个 Variant 的斜体基底。
- [Sarasa Gothic / 更纱黑体](https://github.com/be5invis/Sarasa-Gothic)，Renzhi Li（Belleve Invis），OFL-1.1；提供 Sarasa Fixed SC，其中包含 Inter 项目、Adobe（保留字体名 `Source`）与 Google 的部分版权。上游声明已并入 [LICENSE](./LICENSE)，源目录亦保留 `SarasaFixedSC-src/LICENSE`。
- [Nerd Fonts](https://github.com/ryanoasis/nerd-fonts)，Ryan Gosse 与贡献者；项目工具 MIT，源字体与图标仍受各自许可证约束。
- [Fusion-JetBrainsMapleMono](https://github.com/SpaceTimee/Fusion-JetBrainsMapleMono)，SpaceTimee，融合思路启发。

本字体软件遵循 [SIL Open Font License 1.1](./LICENSE)。再分发时保留许可证与全部上游归属，衍生字体不得使用上游保留字体名。
