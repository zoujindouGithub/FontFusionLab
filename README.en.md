# FontFusionLab / 字体融合实验室

[简体中文](./README.md) | [English](./README.en.md)

**A recipe-driven multi-Variant font fusion platform.** JSON recipes combine programming-oriented Latin glyphs, ligatures and Nerd Fonts icons with selected CJK glyphs into monospaced fonts for terminals and code editors. The project identity is **FontFusionLab / 字体融合实验室**; each production Variant installs under its own font family name.

## Two production Variants

| Recipe ID | Installed family | CJK source | Default output directory |
|---|---|---|---|
| `firacode-sarasa` (default) | **FiraCode Sarasa Mono** | Sarasa Fixed SC | `build/firacode-sarasa/` |
| `firacode-maple` | **FiraCode Maple Mono** | Maple Mono CN | `build/firacode-maple/` |

Each provides `Regular`, `Bold`, `Italic` and `BoldItalic`. They are peer production recipes in one project, not separate release branches; their build directories and installed families never overwrite each other.

Style composition:

- **FiraCode Sarasa Mono**: uprights are FiraCode Nerd Font Mono Latin + Sarasa Fixed SC upright CJK; italics keep the handwritten Maple italic skeleton (MapleItalic base) with their CJK replaced by the matching Sarasa Fixed SC style.
- **FiraCode Maple Mono**: uprights are FiraCode Latin + Maple Mono CN CJK; italics keep the MapleItalic base entirely (its CJK are the source's own outlines), equivalent to the legacy merged-v4 pipeline.
- Injected glyph advances always equal two Latin cells of the current style; this is not a guarantee of seamless rendering or absence of fallback in every application, size or display.

See the [Variant guide](./docs/variants.md) for style boundaries and manual acceptance, and the [design notes](./docs/design-notes.md) for the source/recipe model, OTS compatibility and hinting decisions.

## Quick start

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/). All commands run from the repository root:

```powershell
# 1. Install pinned dependencies (fontTools, FreeType, ttfautohint bindings, jsonschema, pytest)
uv sync

# 2. Build every production Variant (isolated under build/<recipe-id>/)
uv run python scripts/build.py --all

# 3. Run the quality gate per Variant (naming/metrics/box-byte/FreeType render/OT flags)
uv run python scripts/verify.py --recipe firacode-sarasa
uv run python scripts/verify.py --recipe firacode-maple

# 4. Install (dry-run first; registry family names come from the recipe)
pwsh -File scripts/install.ps1 -Variant firacode-sarasa -WhatIf
pwsh -File scripts/install.ps1 -Variant firacode-sarasa
# Optional: -ConfigureEditors also syncs IDE font settings (user config untouched by default)

# 5. Browser preview (serve from the repository root, never file://)
uv run python -m http.server 8137 --bind 127.0.0.1
# Open http://127.0.0.1:8137/preview/
```

`build.py` without arguments uses the explicit default recipe `firacode-sarasa`; `--recipe <ID or JSON path>` builds one Variant. `install.ps1` accepts `-Variant <ID>` or `-Recipe <ID or JSON path>` (never both) plus `-OutputRoot`.

## Release model: one Release, separate ZIPs

**v2.0.0 is one unified GitHub Release** on the [Releases page](https://github.com/zoujindouGithub/FiraCodeMapleMono/releases), containing one independent ZIP asset per Variant — not separate Releases per Variant:

- `FiraCodeSarasaMono-v2.0.0.zip`
- `FiraCodeMapleMono-v2.0.0.zip`
- `variants.json` (Variant identification and SHA256 of every font and archive) and `SHA256SUMS.txt`

Each ZIP contains that Variant's four TTFs (`<file_prefix>-<Style>.ttf`), `LICENSE`, a Variant `README.md` and `recipe.json` provenance.

**Generated TTFs/ZIPs never enter Git**: `build/`, `release/` and font binaries are gitignored and distributed only through Releases; building from source reproduces the same recipe-driven pipeline and checksum workflow.

Installation: Windows — select the four TTFs and install (or use `install.ps1` above); macOS — Font Book; Linux — copy to `~/.local/share/fonts/` then `fc-cache -f -v`. Restart applications that use the font afterwards.

## Sources and recipes

- `sources/manifest.json` registers the four existing sources: `firacode`, `maple-cn`, `maple-italic`, `sarasa-sc` (12 TTFs, each with SHA256). This project adds no new source fonts.
- Public sources support two registrations: **Git-managed** repository-relative `path`, or **URL + SHA256** (downloaded into `.cache/sources/`, hash-verified, cache file named by hash).
- `recipes/*.json` define family name, file prefix, CJK source and scale, and per-style `base`/`cjk_source`/`autohint`; `recipes/schema.json` is strict (unknown fields rejected). `production` recipes participate in `--all` and release packaging; `experimental` recipes may be committed publicly and built explicitly via `--recipe`.
- Private source locations belong only in the uncommitted `sources/local.json` (template: `sources/local.example.json`, already gitignored). A `production` recipe is refused unless every referenced source/style is in the public manifest; experimental recipes may reference private source IDs but only build on machines that configured them. Never publish private fonts, host-specific absolute paths or download credentials.

Fields and extension rules: [design notes, Source/Recipe model](./docs/design-notes.md#sourcerecipe-模型).

## Adding a new Variant

1. Copy `recipes/firacode-maple.json` to `recipes/<new-id>.json`; adjust `id`, `family`, `file_prefix`, `cjk.source/scale` and per-style `base`/`cjk_source`/`autohint`. Start with `"status": "experimental"`.
2. Register new public sources in `sources/manifest.json` (Git `path` or `url`+`sha256`); keep private sources in your local `sources/local.json`, never committed.
3. Every tool works with `--recipe`/`--variant` directly, no code changes:

```powershell
uv run python scripts/build.py --recipe <new-id>
uv run python scripts/verify.py --recipe <new-id>
uv run python scripts/check-cjk-layout.py --recipe <new-id>
pwsh -File scripts/install.ps1 -Recipe <new-id> -WhatIf
uv run python scripts/package-release.py   # packages all production Variants together
```

Gate checklist before promoting to `production` (all required):

- [ ] `uv run pytest -q` green
- [ ] `build.py --recipe <id>` builds all four faces (and `--all` stays green)
- [ ] `verify.py --recipe <id>` fully PASS, including the OVERLAP_SIMPLE OTS gate
- [ ] `check-cjk-layout.py --recipe <id>` PASS (centering/scale/LSB/2:1)
- [ ] `package-release.py` deterministic (identical bytes for identical input); `SHA256SUMS.txt` reproducible
- [ ] Real browser loads every face; manual Windows Terminal + pwsh acceptance passes

## Layout and quality checks

```powershell
uv run python scripts/check-cjk-layout.py --recipe firacode-sarasa
uv run python scripts/check-cjk-layout.py --recipe firacode-maple
uv run python scripts/audit-sources.py --recipe firacode-sarasa   # per-codepoint attribution
uv run python scripts/package-release.py                          # default release/v2.0.0/
```

Automated checks cover machine-checkable font properties (structure, naming, advances, layout, OT flags). They **do not prove** installation, actual Windows Terminal family selection, ligature shaping or visual quality on a particular display.

## Browser preview

The page lives in `preview/` and is driven by `preview/variants.json`: Variants stack top-to-bottom with independent visibility toggles, shared adjustable size and ligature switches, and editable sample text (defaults cover 26 upper/lowercase letters, 10 digits, every visible ASCII punctuation, Chinese, fullwidth punctuation, `=> != ===` ligatures, Box-Drawing and PowerShell examples). Font URLs are relative (e.g. `../build/firacode-sarasa/FiraCodeSarasaMono-Regular.ttf`) — no host paths; load failures surface explicitly and never masquerade as system-font samples.

```powershell
uv run python -m http.server 8137 --bind 127.0.0.1
```

Open <http://127.0.0.1:8137/preview/>. Build the Variants first; the browser loads build output without system installation, which cannot replace manual terminal acceptance.

## Editor and terminal configuration

Set Windows Terminal's `font.face` to `FiraCode Sarasa Mono` or `FiraCode Maple Mono`:

```json
{
  "profiles": {
    "defaults": {
      "font": { "face": "FiraCode Sarasa Mono", "size": 12 }
    }
  }
}
```

For VS Code / Cursor:

```json
{
  "editor.fontFamily": "'FiraCode Sarasa Mono', Consolas, monospace",
  "terminal.integrated.fontFamily": "FiraCode Sarasa Mono",
  "editor.fontLigatures": true
}
```

Replace the family with `FiraCode Maple Mono` for the Maple Variant. Follow the [manual acceptance procedure](./docs/variants.md#人工验收-windows-terminal-pwsh) for **both families**, covering all four styles, ligatures, mixed Latin/CJK text and box drawing.

## Upstream credits and licensing

- [Fira Code](https://github.com/tonsky/FiraCode), Nikita Prokopov and project authors, OFL-1.1.
- [Maple Mono](https://github.com/subframe7536/maple-font), subframe7536 and project authors, OFL-1.1; supplies Maple CJK and the italic bases for both Variants.
- [Sarasa Gothic](https://github.com/be5invis/Sarasa-Gothic), Renzhi Li (Belleve Invis), OFL-1.1; supplies Sarasa Fixed SC, with portions attributed to the Inter Project, Adobe (Reserved Font Name `Source`) and Google. The upstream notice is merged into [LICENSE](./LICENSE), and `SarasaFixedSC-src/LICENSE` is preserved.
- [Nerd Fonts](https://github.com/ryanoasis/nerd-fonts), Ryan Gosse and contributors; project tools MIT, source fonts and icons retain their own licenses.
- [Fusion-JetBrainsMapleMono](https://github.com/SpaceTimee/Fusion-JetBrainsMapleMono), SpaceTimee, fusion design inspiration.

This Font Software is distributed under the [SIL Open Font License 1.1](./LICENSE). Preserve the license and every upstream attribution when redistributing; derivative fonts must not use reserved font names.
