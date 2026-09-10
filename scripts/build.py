# FontFusionLab → 构建管线 (recipe 驱动)
#
# 设计不变式 (docs note):
#   1. 输出隔离: 每个 recipe 的产物位于 build/<recipe-id>/, 文件名 <file_prefix>-<Style>.ttf。
#   2. 注入来源: recipe.styles[style].cjk_source 覆盖 recipe.cjk.source; 缺省用全局。
#      同一文件作为 base 与注入源时 (如 firacode-maple 斜体, base=maple-italic 且
#      cjk_source=maple-italic), 注入集为空 (base 自身已含 CJK), 只走 passthrough
#      变换 (ascender/descender 对齐、cmap 子表补齐、命名), 与旧 merged-v4 产线等价。
#   3. 正体: FiraCode base + ttfautohint + U+2500-U+259F box 程序逐字节还原。
#   4. Chrome/OTS 兼容性: simple glyf OVERLAP_SIMPLE (0x40) 会使 OTS 拒绝整个字体。
#      inject_cjk 对注入字形清标志 (tests/test_inject_cjk.py 锁定轮廓与度量不变);
#      strip_overlap_flags 在保存前对全字体统一清除 (maple-italic 基底自带 2.2 万
#      个带标志字形, tests/test_strip_overlap.py 锁定仅动 flags 位不动几何)。
#   5. 斜体: base=maple-italic, autohint=false; 注入字形保持无 hint 程序。

import array
import copy
import io
import os
from pathlib import Path

import ttfautohint
from fontTools.subset import Options as SubOptions, Subsetter
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable
from fontTools.ttLib.tables.ttProgram import Program

import catalog

STYLES = catalog.STYLES

# 合并多上游的版权与授权信息，确保符合 SIL Open Font License 1.1 要求
METADATA_UNIFIED = [
    (0, "Copyright (c) 2014-2021 The Fira Code Project Authors (tonsky/FiraCode), "
        "(c) 2022 The Maple Mono Project Authors (subframe7536/maple-font), "
        "Nerd Fonts patch by Ryan Gosse (ryanoasis/nerd-fonts)"),
    (5, "Version 2.0.0 (FontFusionLab recipe-driven fusion)"),
    (8, "Nikita Prokopov, subframe7536, Ryan Gosse, Renzhi Li; fused build"),
    (9, "FontFusionLab project"),
    (11, "https://github.com/subframe7536/maple-font"),
    (12, "Recipe-driven font fusion; Latin/icon outlines & hinting from FiraCode NF Mono, "
         "CJK outlines per recipe source (Maple Mono NF CN / Sarasa Fixed SC / MapleItalic)"),
    (13, "This Font Software is licensed under the SIL Open Font License, Version 1.1. "
         "This license is available with a FAQ at: https://openfontlicense.org"),
    (14, "https://openfontlicense.org"),
]

# 标准 RIBBI 映射
RIBBI_SUBFAMILIES = {
    "Regular": "Regular",
    "Bold": "Bold",
    "Italic": "Italic",
    "Bold Italic": "Bold Italic",
    "BoldItalic": "Bold Italic",
}


def normalize_subfamily(subfamily: str) -> str:
    if subfamily not in RIBBI_SUBFAMILIES:
        raise ValueError(f"不支持的子族名称: {subfamily}，必须为 Regular/Bold/Italic/Bold Italic 之一")
    return RIBBI_SUBFAMILIES[subfamily]


def apply_family_naming(font: TTFont, family: str, raw_subfamily: str) -> None:
    """写入规范的家族与子族元数据及样式标志位"""
    subfamily = normalize_subfamily(raw_subfamily)
    nid2 = subfamily
    subfamily_ps = family.replace(" ", "") + "-" + subfamily.replace(" ", "")

    for name_id, value in [
        (1, family),
        (2, nid2),
        (3, f"{subfamily_ps};omp"),
        (4, f"{family} {subfamily}"),
        (6, subfamily_ps),
        (16, family),
        (17, subfamily),
    ]:
        font["name"].setName(value, name_id, 3, 1, 0x409)
        font["name"].setName(value, name_id, 1, 0, 0)

    os2, head = font["OS/2"], font["head"]
    style_flags = os2.fsSelection & ~0b11000001
    if "Italic" in subfamily:
        style_flags |= 0x01
    if "Bold" in subfamily:
        style_flags |= 0x20
    if (style_flags & 0x21) == 0:
        style_flags |= 0x40
    os2.fsSelection = style_flags

    head.macStyle = (head.macStyle | 0x01) if "Bold" in subfamily else (head.macStyle & ~0x01)
    head.macStyle = (head.macStyle | 0x02) if "Italic" in subfamily else (head.macStyle & ~0x02)

    for name_id, value in METADATA_UNIFIED:
        font["name"].setName(value, name_id, 3, 1, 0x409)
        font["name"].setName(value, name_id, 1, 0, 0)


def cjk_codepoints(font: TTFont) -> set[int]:
    """提取需要注入或替换的 CJK 码位集"""
    charmap = font.getBestCmap()
    selected = set()
    for codepoint in charmap:
        in_cjk_range = (
            0x2E80 <= codepoint <= 0x9FFF or
            0xF900 <= codepoint <= 0xFAFF or
            0x3000 <= codepoint <= 0x303F or
            0xFF00 <= codepoint <= 0xFF5E
        )
        is_ambiguous_quote = 0x2018 <= codepoint <= 0x201D
        is_common_punct = codepoint in (0x2014, 0x2026, 0x00B7)
        if in_cjk_range or is_ambiguous_quote or is_common_punct:
            selected.add(codepoint)
    return selected

def injection_codepoints(base: TTFont, source: TTFont, base_path, source_path) -> set[int]:
    """按来源文件身份决定 CJK 注入集；不同来源必须覆盖基底已有 CJK。"""
    source_cps = cjk_codepoints(source)
    if Path(base_path).resolve() != Path(source_path).resolve():
        return source_cps
    return source_cps - base.getBestCmap().keys()


def finalize_face(font: TTFont, family: str, style: str, out_path: str) -> None:
    """统一完成命名、OTS overlap 清理与落盘，保持各字面收尾等价。"""
    apply_family_naming(font, family, style)
    cleared = strip_overlap_flags(font)
    print(f"  清除 {cleared} 个 simple 字形的 OVERLAP_SIMPLE 标志 (OTS 兼容)")
    font.save(out_path)



def restore_box_drawing_programs(target: TTFont, orig: TTFont) -> int:
    """恢复 box-drawing 区 (U+2500-U+259F) 的 FiraCode 原始 hinting 程序"""
    charmap_orig = orig.getBestCmap()
    charmap_target = target.getBestCmap()
    restored = 0

    for codepoint, glyph_old in charmap_orig.items():
        if not (0x2500 <= codepoint <= 0x259F):
            continue
        glyph_target = charmap_target.get(codepoint)
        if not glyph_target:
            continue

        program = getattr(orig["glyf"][glyph_old], "program", None)
        has_bytecode = program is not None and bool(program.getBytecode())
        glyph_target_obj = target["glyf"][glyph_target]

        if not has_bytecode:
            empty_prog = Program()
            empty_prog.bytecode = array.array("B", [])
            glyph_target_obj.program = empty_prog
            restored += 1
            continue

        glyph_target_obj.program = copy.deepcopy(program)
        restored += 1

    return restored


def strip_overlap_flags(font: TTFont) -> int:
    """清除全字体 simple glyph 的 OVERLAP_SIMPLE (0x40) 标志 (Chrome/OTS 兼容)。

    仅修改 flags 中的该位; 坐标、endPts、advance/LSB 一律不变。
    maple-italic 基底自带 2.2 万个带标志字形, 必须在保存前统一清除,
    否则整个斜体字面被 OTS 拒绝 (tests/test_strip_overlap.py 锁定不变式)。
    """
    glyf = font["glyf"]
    cleared = 0
    for name in glyf.keys():
        glyph = glyf[name]
        if glyph.isComposite() or not glyph.numberOfContours:
            continue
        flags = glyph.flags
        if any(flag & 0x40 for flag in flags):
            glyph.flags = array.array("B", [flag & ~0x40 for flag in flags])
            cleared += 1
    return cleared


def inject_cjk(font: TTFont, source: TTFont, codepoints: set[int], cjk_scale: float = 1.05) -> None:
    """将注入源的轮廓放入基底的双倍 Latin 字格，不修改非 CJK 字形。

    Chrome/OTS 兼容: 展开 composite 后清除 simple glyf OVERLAP_SIMPLE (0x40)，
    不改变轮廓坐标与度量 (tests/test_inject_cjk.py 锁定该不变式)。
    """
    opt = SubOptions()
    opt.glyph_names = True
    opt.notdef_outline = True
    opt.drop_tables += ["GSUB", "GPOS", "GDEF"]
    subsetter = Subsetter(options=opt)
    subsetter.populate(unicodes=codepoints)
    subsetter.subset(source)

    source_cmap = source.getBestCmap()
    target_cmap = font.getBestCmap()
    target_glyf = font["glyf"]
    target_hmtx = font["hmtx"]
    scale = font["head"].unitsPerEm / source["head"].unitsPerEm
    source_center_y = (source["hhea"].ascender + source["hhea"].descender) / 2
    order_set = set(font.getGlyphOrder())
    gname_to_target = {}
    latin_cell_width = target_hmtx[target_cmap[0x41]][0]
    from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates

    for cp in sorted(codepoints):
        gname = source_cmap.get(cp)
        if gname is None:
            continue

        if gname in gname_to_target:
            target_name = gname_to_target[gname]
        else:
            target_name = "cjk%04X" % cp
            while target_name in order_set:
                target_name = "f" + target_name
            order_set.add(target_name)
            gname_to_target[gname] = target_name

            glyph_copy = copy.deepcopy(source["glyf"][gname])
            source_advance = source["hmtx"][gname][0]
            coords, end_points, flags = glyph_copy.getCoordinates(source["glyf"])
            if glyph_copy.isComposite():
                del glyph_copy.components
            glyph_copy.numberOfContours = len(end_points)
            glyph_copy.endPtsOfContours = end_points
            # 清除 OVERLAP_SIMPLE (0x40): OTS 拒绝带此标志的 simple glyph。
            # 仅影响该标志位，保留 on-curve(0x01)/短坐标/重复等其余位。
            glyph_copy.flags = array.array("B", [flag & ~0x40 for flag in flags])
            glyph_copy.coordinates = GlyphCoordinates([
                (
                    round(latin_cell_width + (x - source_advance / 2) * scale * cjk_scale),
                    round((source_center_y + (y - source_center_y) * cjk_scale) * scale),
                )
                for x, y in coords
            ])

            # 注入源无可靠 hint 表，保持无程序状态。
            glyph_copy.program = Program()
            glyph_copy.program.fromBytecode(b"")
            target_glyf[target_name] = glyph_copy

            coords, _, _ = glyph_copy.getCoordinates(target_glyf)
            real_xmin = min((p[0] for p in coords), default=0)
            target_hmtx[target_name] = (2 * latin_cell_width, round(real_xmin))

        target_cmap[cp] = target_name

    for table in font["cmap"].tables:
        if table.isUnicode():
            table.cmap.update({
                cp: target_cmap[cp] for cp in codepoints
                if cp in target_cmap and (table.format in (12, 13) or cp < 0x10000)
            })


def build_upright(style: str, recipe: dict, base_path, source_path, out_path: str, cjk_scale: float) -> None:
    """端到端构建正体字体 (Regular / Bold): FiraCode base + ttfautohint + box 程序还原"""
    print(f"\n[{recipe['id']}/{style}] === 开始全量构建正体 ===")
    fira = TTFont(base_path)
    with TTFont(source_path) as source:
        inject_cps = injection_codepoints(fira, source, base_path, source_path)
        print(f"  识别并准备注入 CJK 码位: {len(inject_cps)} 个")
        inject_cjk(fira, source, inject_cps, cjk_scale)

    buffer = io.BytesIO()
    fira.save(buffer)
    unhinted_bytes = buffer.getvalue()

    print("  执行 ttfautohint 注入高品质 CJK 渲染指令...")
    hinted_bytes = ttfautohint.ttfautohint(
        in_buffer=unhinted_bytes,
        windows_compatibility=True,
        fallback_script="latn"
    )
    hinted_font = TTFont(io.BytesIO(hinted_bytes))

    print("  恢复 FiraCode 原版 box-drawing 区 (U+2500-U+259F) hinting 指令...")
    orig_fira = TTFont(base_path)
    restored_count = restore_box_drawing_programs(hinted_font, orig_fira)
    print(f"  成功精确还原 {restored_count} 个制表符字形程序")

    finalize_face(hinted_font, recipe["family"], style, out_path)
    print(f"[{recipe['id']}/{style}] 正体生成成功 -> {out_path} ({os.path.getsize(out_path) // 1024} KB)")


def build_italic(style: str, recipe: dict, base_path, source_path, out_path: str, cjk_scale: float) -> None:
    """端到端构建斜体字体 (Italic / Bold Italic): maple-italic base + CJK 替换"""
    print(f"\n[{recipe['id']}/{style}] === 开始全量构建斜体 ===")
    font = TTFont(base_path)
    upem = font["head"].unitsPerEm
    hhea, os2 = font["hhea"], font["OS/2"]

    # 对齐正体比例 (1800 / 1950 = 0.923)，消除斜体在终端中的基线跳变
    hhea.ascender = round(1800 / 1950 * upem)
    hhea.descender = round(-600 / 1950 * upem)
    hhea.lineGap = 0
    os2.sTypoAscender, os2.sTypoDescender, os2.sTypoLineGap = hhea.ascender, hhea.descender, hhea.lineGap

    # 保持宽松的 win 裁剪值，杜绝上伸部重音被切
    os2.usWinAscent = max(os2.usWinAscent, round(1.02 * upem))
    os2.usWinDescent = max(os2.usWinDescent, round(0.3 * upem))

    # 补齐 cmap 子表：(0,3,4), (0,4,12), (1,0,4)
    widest_cmap = max(font["cmap"].tables, key=lambda t: len(t.cmap)).cmap
    for platform_id, encoding_id, fmt in ((0, 3, 4), (0, 4, 12), (1, 0, 4)):
        subtable = CmapSubtable.newSubtable(fmt)
        subtable.platformID, subtable.platEncID, subtable.language = platform_id, encoding_id, 0
        subtable.cmap = {k: v for k, v in widest_cmap.items() if fmt == 12 or k < 0x10000}
        font["cmap"].tables.append(subtable)

    with TTFont(source_path) as source:
        inject_cps = injection_codepoints(font, source, base_path, source_path)
        print(f"  识别并准备替换 CJK 码位: {len(inject_cps)} 个")
        inject_cjk(font, source, inject_cps, cjk_scale)

    finalize_face(font, recipe["family"], style, out_path)
    print(f"[{recipe['id']}/{style}] 斜体生成成功 -> {out_path} ({os.path.getsize(out_path) // 1024} KB)")


def build_variant(recipe: dict, output_root=None) -> None:
    paths = catalog.font_paths(recipe, output_root)
    scale = recipe["cjk"]["scale"]
    for style in STYLES:
        style_cfg = recipe["styles"][style]
        base_id = style_cfg["base"]
        cjk_source_id = style_cfg.get("cjk_source", recipe["cjk"]["source"])
        base_path = catalog.source_path(base_id, style)
        source_path = catalog.source_path(cjk_source_id, style_cfg["source_style"])
        out_path = str(paths[style])
        os.makedirs(paths[style].parent, exist_ok=True)
        if style_cfg["autohint"]:
            build_upright(style, recipe, base_path, source_path, out_path, scale)
        else:
            build_italic(style, recipe, base_path, source_path, out_path, scale)


def main():
    parser = catalog.recipe_arguments("FontFusionLab recipe-driven font build")
    args = parser.parse_args()
    for recipe in catalog.selected_recipes(args):
        build_variant(recipe, args.output_root)
    print("\n==========================================")
    print("全部指定 variant 四字面构建完成！")
    print("==========================================")


if __name__ == "__main__":
    main()
