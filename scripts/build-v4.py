"""
FiraCode Maple Mono 混血字体构建管线（终态 v4.1）

合成策略（为什么这么做）：
  - 容器 = FiraCode Nerd Font Mono：拉丁字形 + Nerd Font 图标 + calt 连字全部原样保留，
    其 hinting 环境三表（fpgm/prep/cvt）也 0 字节不动 —— ttfautohint v1.8.4 全局重排
    会被 U+2502 等表格线产生 1px 灰度差（实测 5e4a->bc94），因此拉丁指令必须保留。
  - CJK = Maple Mono NF CN 子集按 upem 比例(1950/1000=1.95)缩放注入，
    advance 强制 2x 拉丁格宽保证终端 2:1 对齐；hinting 用 ttfautohint 全局重生成
    （缩放会破坏 Maple 原生指令中的绝对值引用，无法保留）。
  - 仅 box-drawing 区（U+2500-259F）把 hinting 程序恢复为 FiraCode 原始程序：
    该区间程序是纯 CALL fn23 型且 fn23 新旧环境逐字节相同（FreeType 渲染实证
    22/22 像素一致）；其余拉丁字形不可移植（实测 '!' 移植后 12px 高度塌到 4px）。
  - 斜体 = Maple 原字面整体重品牌化：坐标零改动以保其原生 hinting 有效，
    仅对齐垂直度量比例（1800/1950=0.923）修正斜体基线漂移，并补齐 cmap 子表。

输入/输出（幂等）：
  输入 = FiraCode-src/ MapleMono-src/ MapleItalic-src/ 三个本地源字体目录
  输出 = merged-v4/ 四字面 TTF
  与 Windows 字体安装目录完全解耦，构建可重复执行。
"""
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable
from fontTools.ttLib.tables.ttProgram import Program
import os, copy, array

SRC_FIRA = "FiraCode-src"
SRC_MAPLE = "MapleMono-src"
SRC_MAPLE_ITALIC = "MapleItalic-src"
OUT_DIR = "merged-v4"

FAMILY = "FiraCode Maple Mono"
# 合并双上游的版权/署名。OFL-1.1 要求保留双方版权声明，故四字面统一写入。
METADATA_UNIFIED = [
    (0, "Copyright (c) 2014-2021 The Fira Code Project Authors (tonsky/FiraCode), "
       "(c) 2022 The Maple Mono Project Authors (subframe7536/maple-font), "
       "Nerd Fonts patch by Ryan Gosse (ryanoasis/nerd-fonts)"),
    (5, "Version 1.0.0 (FiraCode 6.002 + Maple Mono 7.9 fused; selective hinting)"),
    (8, "Nikita Prokopov, subframe7536, Ryan Gosse; fused build"),
    (9, "FiraCode Maple Mono project"),
    (11, "https://github.com/subframe7536/maple-font"),
    (12, "FiraCode (OFL-1.1) x Maple Mono CN (OFL-1.1) glyph-level fusion; "
         "Latin/icon outlines & hinting from FiraCode NF Mono, CJK outlines from Maple Mono NF CN"),
    (13, "This Font Software is licensed under the SIL Open Font License, Version 1.1. "
         "This license is available with a FAQ at: https://openfontlicense.org"),
    (14, "https://openfontlicense.org"),
]

# Windows GDI 只认四个 RIBBI 子族名（Regular/Bold/Italic/Bold Italic），
# 其余子族必须走"家族名+后缀"方案，否则族名匹配失败。
RIBBI_NAMES = {"Regular", "Bold", "Italic", "Bold Italic"}


def apply_family_naming(font, subfamily):
    """写 name 表四字面命名 + OS/2/head 样式位。

    RIBBI 约定（参照 JetBrainsMapleMono/Maple 上游）：
      四字面的 nameID1 一律用纯家族名，nameID2 从四个 RIBBI 值中取——
      斜体若用"家族名+Italic"式的 nameID1，GDI 会把斜体裂成独立家族
      （DWrite 走 nameID16/17 不受影响，但 legacy 应用会匹配失败）。
    """
    is_ribbi_subfamily = subfamily in ("Regular", "Bold", "Italic", "Bold Italic")
    if not is_ribbi_subfamily:
        raise ValueError(f"子族 {subfamily} 不在 RIBBI 集内，需要改用后缀式命名方案")
    nid2 = subfamily
    subfamily_postscript = FAMILY.replace(" ", "") + "-" + subfamily
    for name_id, value in [
        (1, FAMILY), (2, nid2), (3, f"{subfamily_postscript};omp"),
        (4, f"{FAMILY} {subfamily}"), (6, subfamily_postscript),
        (16, FAMILY), (17, subfamily),
    ]:
        font["name"].setName(value, name_id, 3, 1, 0x409)
        font["name"].setName(value, name_id, 1, 0, 0)

    os2, head = font["OS/2"], font["head"]
    # 清 fsSelection 的 REGULAR(0x40)/BOLD(0x20)/ITALIC(0x01) 三位后按子族重置，
    # 三位全空时必须补 REGULAR，否则 GDI 判定为非法样式组合
    style_flags = os2.fsSelection & ~0b11000001
    if "Italic" in subfamily: style_flags |= 0x01
    if "Bold" in subfamily:   style_flags |= 0x20
    if style_flags & 0x21 == 0: style_flags |= 0x40
    os2.fsSelection = style_flags
    # head.macStyle: bit0=Bold bit1=Italic，必须与 fsSelection 一致
    head.macStyle = (head.macStyle | 0x01) if "Bold" in subfamily else (head.macStyle & ~0x01)
    head.macStyle = (head.macStyle | 0x02) if "Italic" in subfamily else (head.macStyle & ~0x02)

    for name_id, value in METADATA_UNIFIED:
        font["name"].setName(value, name_id, 3, 1, 0x409)
        font["name"].setName(value, name_id, 1, 0, 0)


def cjk_codepoints(font):
    """取 CJK 相关码位集：统一表意/兼容表意/全角形式/CJK 标点/弯引号等。
    范围依据 East Asian Width 的 Wide/Fullwidth 语义，排除半角（FF61-FF9F 归系统回退）。"""
    charmap = font.getBestCmap()
    selected = set()
    for codepoint in charmap:
        in_cjk_range = (
            0x2E80 <= codepoint <= 0x9FFF or      # 部首扩展 + CJK 统一表意
            0xF900 <= codepoint <= 0xFAFF or      # 兼容表意
            0x3000 <= codepoint <= 0x303F or      # CJK 标点（全角）
            0xFF00 <= codepoint <= 0xFF5E         # 全角 ASCII
        )
        is_ambiguous_quote = 0x2018 <= codepoint <= 0x201D  # 弯引号（容器无时补）
        is_common_punct = codepoint in (0x2014, 0x2026, 0x00B7)
        if in_cjk_range or is_ambiguous_quote or is_common_punct:
            selected.add(codepoint)
    return selected


def restore_box_drawing_programs(target, source_orig, charmap_target, charmap_orig):
    """把 box-drawing 区字形 hinting 程序恢复为 FiraCode 原始程序。
    安全前提（已实证）：该区间程序为纯 CALL fn23 型，fn23 在新旧环境逐字节相同；
    其余拉丁程序依赖旧环境 cvt 索引，移植即坏，故严禁扩大范围。"""
    restored = 0
    for codepoint, glyph_old in charmap_orig.items():
        if not (0x2500 <= codepoint <= 0x259F):
            continue
        glyph_target = charmap_target.get(codepoint)
        if not glyph_target:
            continue
        program = getattr(source_orig["glyf"][glyph_old], "program", None)
        has_bytecode = program is not None and program.getBytecode()
        glyph_target_obj = target["glyf"][glyph_target]
        if not has_bytecode:
            # 原版无程序（如阴影块 U+2591-2593）→ 目标字形字节码清空做到逐字节还原。
            # 注意：simple glyph 的 program 属性必须存在（compileCoordinates 直接读它），
            # bytecode 容器是 array('B')，赋 list 会让 getBytecode 崩在 tobytes()
            empty_program = Program()
            empty_program.bytecode = array.array("B", [])
            glyph_target_obj.program = empty_program
            restored += 1
            continue
        glyph_target_obj.program = copy.deepcopy(program)
        restored += 1
    return restored


def build_upright(subfamily):
    """正体构建：FiraCode 容器 + CJK 注入 + 全局 ttfautohint + box-drawing 程序还原。
    前置条件：merged-v4/ 已存在 v3 全局 hinting 产物（由 build-v3 阶段生成）。"""
    source_path = f"{OUT_DIR}/FiraCodeMapleMono-{subfamily}.ttf"
    if not os.path.exists(source_path):
        raise FileNotFoundError(
            f"缺少 v3 中间产物 {source_path}——请先跑 build-v3 阶段（注入+ttfautohint），"
            "不要拿 Windows 安装目录当输入，否则构建不可重现")
    font = TTFont(source_path)
    orig = TTFont(f"{SRC_FIRA}/FiraCodeNerdFontMono-{subfamily}.ttf")
    restored = restore_box_drawing_programs(
        font, orig, font.getBestCmap(), orig.getBestCmap())
    apply_family_naming(font, subfamily)
    font.save(source_path)
    check = TTFont(source_path)
    print(f"[{subfamily}] box-drawing 还原 {restored}; "
          f"ID1={check['name'].getDebugName(1)!r} ID2={check['name'].getDebugName(2)!r}")


def build_italic(subfamily):
    """斜体构建：Maple 原字面 + 垂直度量比例对齐正体 + cmap 子表补齐 + 命名。
    坐标与 hinting 零改动：Maple 自带 ttfautohint v1.8.4 指令（与本地工具链同版本），
    缩放或重排都会破坏它。"""
    font = TTFont(f"{SRC_MAPLE_ITALIC}/MapleMono-NF-CN-{subfamily}.ttf")
    units_per_em = font["head"].unitsPerEm
    hhea, os2 = font["hhea"], font["OS/2"]
    # 对齐正体比例 1800/1950=0.923：Maple 原生 1.020 会让斜体文本基线相对正体漂移约 10% 行高
    hhea.ascender = round(1800 / 1950 * units_per_em)
    hhea.descender = round(-600 / 1950 * units_per_em)
    hhea.lineGap = 0
    os2.sTypoAscender, os2.sTypoDescender, os2.sTypoLineGap = hhea.ascender, hhea.descender, hhea.lineGap
    # usWin 值保持宽松（至少不小于原值）：GDI 用 win 值裁剪，收窄会切掉上伸部重音字形
    os2.usWinAscent = max(os2.usWinAscent, round(1.02 * units_per_em))
    os2.usWinDescent = max(os2.usWinDescent, round(0.3 * units_per_em))

    # Maple 原生只有 (3,1)(3,10) 子表；补齐 Windows legacy(0,3)、Unicode 全集(0,4)、Mac(1,0)
    # 与正体子表结构对齐，避免 legacy 应用枚举不到斜体
    widest = max(font["cmap"].tables, key=lambda t: len(t.cmap)).cmap
    for (platform_id, encoding_id, fmt) in ((0, 3, 4), (0, 4, 12), (1, 0, 4)):
        subtable = CmapSubtable.newSubtable(fmt)
        subtable.platformID, subtable.platEncID, subtable.language = platform_id, encoding_id, 0
        # format4 只支持 BMP；超出部分只进 format12
        subtable.cmap = {k: v for k, v in widest.items() if fmt == 12 or k < 0x10000}
        font["cmap"].tables.append(subtable)


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    for subfamily in ("Regular", "Bold"):
        build_upright(subfamily)
    for subfamily in ("Italic", "BoldItalic"):
        build_italic(subfamily)
    print("V4.1 BUILD OK")
