"""
FiraCode Maple Mono v4 终态构建
底：v3（FiraCode NF Mono 容器 + Maple NF CN 的 CJK 字形注入 + ttfautohint 全局 hinting）
本脚本职责：
  1. 正体：把 box-drawing 区（U+2500-U+259F）的字形 hinting 程序恢复为 FiraCode 原始程序
     —— 该区间程序是纯 CALL fn23 型，fn23 新旧环境逐字节相同，移植经渲染实证 22/22 像素一致
  2. 斜体：Maple 原字面重品牌化 + 垂直度量比例对齐正体 + cmap 子表补齐
  3. 四字面统一元数据（双上游署名）与 RIBBI 命名位
"""
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable
import os, copy

FD = r"C:\Users\zouji\AppData\Local\Microsoft\Windows\Fonts"
FAMILY = "FiraCode Maple Mono"
OUTDIR = "merged-v4"

# 家族内统一元数据：正体来自 FiraCode、斜体来自 Maple，不统一会让同一家族自述矛盾
UNIFIED = [
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


def brand(font, sub):
    """RIBBI 规则：nameID2 只允许 Regular/Bold/Italic/Bold Italic，真实子族放 nameID17。
    非 RIBBI 字面的 nameID1 必须带后缀，否则 GDI 会裂出独立家族。"""
    is_ribbi = sub in ("Regular", "Bold")
    nid2 = sub if is_ribbi else ("Bold Italic" if sub == "BoldItalic" else sub)
    nid1 = FAMILY if is_ribbi else f"{FAMILY} {sub}"
    nid6 = FAMILY.replace(" ", "") + "-" + sub
    for nid, val in [(1, nid1), (2, nid2), (3, f"{nid6};omp"), (4, f"{FAMILY} {sub}"),
                     (6, nid6), (16, FAMILY), (17, sub)]:
        font["name"].setName(val, nid, 3, 1, 0x409)
        font["name"].setName(val, nid, 1, 0, 0)
    os2, head = font["OS/2"], font["head"]
    fs = os2.fsSelection & ~0b11000001
    if "Italic" in sub: fs |= 0x01
    if "Bold" in sub:   fs |= 0x20
    if fs & 0x21 == 0:  fs |= 0x40
    os2.fsSelection = fs
    head.macStyle = (head.macStyle | 0x01) if "Bold" in sub else (head.macStyle & ~0x01)
    head.macStyle = (head.macStyle | 0x02) if "Italic" in sub else (head.macStyle & ~0x02)
    for nid, val in UNIFIED:
        font["name"].setName(val, nid, 3, 1, 0x409)
        font["name"].setName(val, nid, 1, 0, 0)


def build_upright(sub):
    """v3 底 + box-drawing 原始程序恢复。
    只恢复 0x2500-0x259F：其余拉丁程序依赖旧环境 cvt 索引，移植会崩（实测 '!' 12px→4px）。"""
    f = TTFont(os.path.join(FD, f"FiraCodeMapleMono-{sub}.ttf"))
    orig = TTFont(f"FiraCode-src/FiraCodeNerdFontMono-{sub}.ttf")
    ocm, ccm = orig.getBestCmap(), f.getBestCmap()
    moved = 0
    for cp, g_old in ocm.items():
        if not (0x2500 <= cp <= 0x259F):
            continue
        t = ccm.get(cp)
        if not t:
            continue
        prog = getattr(orig["glyf"][g_old], "program", None)
        if prog is None or not prog.getBytecode():
            continue
        f["glyf"][t].program = copy.deepcopy(prog)
        moved += 1
    brand(f, sub)
    f.save(f"{OUTDIR}/FiraCodeMapleMono-{sub}.ttf")
    print(f"[{sub}] box-drawing 恢复 {moved}; saved")


def build_italic(sub):
    """斜体只做三件事：度量比例对齐、cmap 子表补齐、重品牌化。
    坐标一律不动 —— 动了就会让 Maple 自带的 ttfautohint(v1.8.4) 指令失效。"""
    f = TTFont(f"MapleItalic-src/MapleMono-NF-CN-{sub}.ttf")
    upem = f["head"].unitsPerEm
    h, o = f["hhea"], f["OS/2"]
    # 正体比例 1800/1950=0.923；Maple 原生 1.020 会让斜体文本基线漂移
    h.ascender, h.descender, h.lineGap = round(1800 / 1950 * upem), round(-600 / 1950 * upem), 0
    o.sTypoAscender, o.sTypoDescender, o.sTypoLineGap = h.ascender, h.descender, h.lineGap
    # win 值保持宽松，防止上伸部字形被 GDI 裁剪
    o.usWinAscent = max(o.usWinAscent, round(1.02 * upem))
    o.usWinDescent = max(o.usWinDescent, round(0.3 * upem))
    src = max(f["cmap"].tables, key=lambda t: len(t.cmap)).cmap
    for (pid, eid, fmt) in ((0, 3, 4), (0, 4, 12), (1, 0, 4)):
        st = CmapSubtable.newSubtable(fmt)
        st.platformID, st.platEncID, st.language = pid, eid, 0
        st.cmap = {k: v for k, v in src.items() if fmt == 12 or k < 0x10000}
        f["cmap"].tables.append(st)
    brand(f, sub)
    f.save(f"{OUTDIR}/FiraCodeMapleMono-{sub}.ttf")
    c = TTFont(f"{OUTDIR}/FiraCodeMapleMono-{sub}.ttf")
    print(f"[{sub}] hhea.asc={c['hhea'].ascender}/{upem}; "
          f"cmap={[(t.platformID, t.platEncID) for t in c['cmap'].tables]}; saved")


if __name__ == "__main__":
    os.makedirs(OUTDIR, exist_ok=True)
    for s in ("Regular", "Bold"):
        build_upright(s)
    for s in ("Italic", "BoldItalic"):
        build_italic(s)
    print("V4 BUILD OK")
