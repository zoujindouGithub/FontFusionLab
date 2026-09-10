"""按 recipe 解析产物与源字体的质量门禁与终验套件"""
import argparse
from pathlib import Path

import freetype
from fontTools.ttLib import TTFont

import catalog


def main():
    parser = argparse.ArgumentParser(description="FontFusionLab variant quality gate")
    parser.add_argument('--recipe', '--variant', default=catalog.DEFAULT_RECIPE,
                        help=f'Recipe ID or JSON path (default: {catalog.DEFAULT_RECIPE})')
    parser.add_argument('--output-root', type=Path, default=catalog.ROOT / 'build')
    args = parser.parse_args()

    recipe = catalog.load_recipe(args.recipe)
    paths = catalog.font_paths(recipe, args.output_root)
    family = recipe['family']
    prefix = recipe['file_prefix']
    print("==========================================")
    print(f"开始 {family} 终验门禁审计")
    print("==========================================")
    all_passed = True

    # 1. 四字面文件存在性
    subfamilies = catalog.STYLES
    for sub in subfamilies:
        p = paths[sub]
        if not p.exists():
            print(f"[FAIL] 缺少产物文件: {p}")
            return False
        print(f"[PASS] 产物存在: {p.name} ({p.stat().st_size // 1024} KB)")

    # 2. RIBBI 命名规范检验
    print("\n--- 检验 RIBBI 与元数据命名 ---")
    expected_naming = {
        "Regular": ("Regular",),
        "Bold": ("Bold",),
        "Italic": ("Italic",),
        "BoldItalic": ("Bold Italic",),
    }
    fonts = {}
    for sub, (exp_id2,) in expected_naming.items():
        font = TTFont(paths[sub])
        fonts[sub] = font
        id1 = font["name"].getDebugName(1)
        id2 = font["name"].getDebugName(2)
        id16 = font["name"].getDebugName(16)
        id17 = font["name"].getDebugName(17)

        is_valid = (id1 == family and id2 == exp_id2 and id16 == family and id17 == exp_id2)
        if is_valid:
            print(f"[PASS] {sub:11}: ID1='{id1}' ID2='{id2}' ID16='{id16}' ID17='{id17}'")
        else:
            print(f"[FAIL] {sub:11}: ID1='{id1}' ID2='{id2}' ID16='{id16}' ID17='{id17}' (期望 ID1='{family}', ID2='{exp_id2}')")
            all_passed = False

    # 3. CJK 字符度量与 LSB 居中检验
    print("\n--- 检验 CJK 2:1 Advance 与 LSB 居中 ---")
    reg_font = fonts["Regular"]
    reg_cmap = reg_font.getBestCmap()
    hmtx = reg_font["hmtx"]
    cell = hmtx["A"][0]

    zh_glyph = reg_cmap.get(0x4E2D)
    if not zh_glyph:
        print("[FAIL] 缺少 CJK 字符 0x4E2D '中'")
        all_passed = False
    else:
        advance, lsb = hmtx[zh_glyph]
        coords, _, _ = reg_font["glyf"][zh_glyph].getCoordinates(reg_font["glyf"])
        real_xmin = min((p[0] for p in coords), default=0)

        adv_ok = (advance == 2 * cell)
        lsb_ok = (lsb == round(real_xmin))

        if adv_ok and lsb_ok:
            print(f"[PASS] '中' advance={advance} (2.0x cell), lsb={lsb} 与轮廓 xmin 一致")
        else:
            print(f"[FAIL] '中' advance={advance} (期望 {2*cell}), lsb={lsb} (真实 xmin={real_xmin})")
            all_passed = False

    # 4. Box-Drawing 逐字节还原检验 (仅 FiraCode base 的正体)
    print("\n--- 检验 Box-Drawing (U+2500-U+259F) 原版程序逐字节还原 ---")
    fira_reg_path = catalog.source_path('firacode', 'Regular')
    orig_reg = TTFont(fira_reg_path)
    orig_cmap = orig_reg.getBestCmap()
    bd_same = 0
    bd_diff = 0

    for cp in range(0x2500, 0x25A0):
        g_orig = orig_cmap.get(cp)
        g_target = reg_cmap.get(cp)
        if not g_orig or not g_target:
            continue

        p_orig = getattr(orig_reg["glyf"][g_orig], "program", None)
        p_target = getattr(reg_font["glyf"][g_target], "program", None)
        bc_orig = p_orig.getBytecode() if p_orig else b""
        bc_target = p_target.getBytecode() if p_target else b""

        if bytes(bc_orig) == bytes(bc_target):
            bd_same += 1
        else:
            bd_diff += 1

    if bd_diff == 0 and bd_same >= 150:
        print(f"[PASS] 全部 {bd_same} 个制表符 hinting 程序与 FiraCode 原版 100% 逐字节完全一致！")
    else:
        print(f"[FAIL] 制表符程序存在差异: SAME={bd_same}, DIFF={bd_diff}")
        all_passed = False

    # 5. 斜体垂直度量与子表完整性
    print("\n--- 检验斜体垂直度量比例与 CMap 子表 ---")
    it_font = fonts["Italic"]
    it_upem = it_font["head"].unitsPerEm
    it_ratio = it_font["hhea"].ascender / it_upem
    reg_ratio = reg_font["hhea"].ascender / reg_font["head"].unitsPerEm

    ratio_ok = abs(it_ratio - reg_ratio) < 0.005
    if ratio_ok:
        print(f"[PASS] 斜体 hhea.ascender 比例={it_ratio:.3f}, 正体比例={reg_ratio:.3f} -> 垂直基线一致！")
    else:
        print(f"[FAIL] 比例失衡: 斜体={it_ratio:.3f}, 正体={reg_ratio:.3f}")
        all_passed = False

    expected_cmaps = {(0, 3), (0, 4), (1, 0), (3, 1), (3, 10)}
    actual_cmaps = {(t.platformID, t.platEncID) for t in it_font["cmap"].tables}
    if expected_cmaps <= actual_cmaps:
        print(f"[PASS] 斜体 CMap 子表包含所有标准格式: {sorted(actual_cmaps)}")
    else:
        print(f"[FAIL] 斜体缺少必要子表: 缺少 {expected_cmaps - actual_cmaps}")
        all_passed = False

    # 6. FreeType 实际渲染像素级一致性
    print("\n--- FreeType 实际渲染位图对比 ---")
    def render_glyph(path, cp, px):
        face = freetype.Face(str(path))
        face.set_char_size(px << 6)
        face.load_char(chr(cp), freetype.FT_LOAD_RENDER)
        g = face.glyph
        bm = g.bitmap
        return (bm.width, bm.rows, bytes(bm.buffer) if bm.buffer else b"", g.bitmap_left, g.bitmap_top)

    render_same = 0
    render_diff = 0
    test_chars = [0x41, 0x61, 0x30, 0x2500, 0x2502, 0x251C, 0x253C]
    for cp in test_chars:
        for px in (16, 12):
            r_orig = render_glyph(fira_reg_path, cp, px)
            r_merged = render_glyph(paths["Regular"], cp, px)
            if r_orig == r_merged:
                render_same += 1
            else:
                render_diff += 1

    if render_diff == 0:
        print(f"[PASS] 抽样核心拉丁/数字/制表符渲染位图 100% 逐像素完全一致 ({render_same}/{render_same})！")
    else:
        print(f"[FAIL] 渲染存在像素差异: SAME={render_same}, DIFF={render_diff}")
        all_passed = False

    # 7. OTS/Chrome 兼容: simple glyf flags 不含 OVERLAP_SIMPLE (0x40)
    print("\n--- OTS 兼容性: simple glyph OVERLAP_SIMPLE 标志清零 ---")
    overlap_leaks = []
    for sub in subfamilies:
        font = fonts[sub]
        glyf = font["glyf"]
        for name in glyf.keys():
            glyph = glyf[name]
            if glyph.isComposite():
                continue
            if glyph.numberOfContours == 0:
                continue
            if any(flag & 0x40 for flag in glyph.flags):
                overlap_leaks.append((sub, name))
                break

    if not overlap_leaks:
        print("[PASS] 四字面全部 simple 字形 flags 均不含 OVERLAP_SIMPLE (0x40)")
    else:
        sample = ", ".join(f"{sub}:{name}" for sub, name in overlap_leaks[:5])
        print(f"[FAIL] 存在带 OVERLAP_SIMPLE 的字形 ({len(overlap_leaks)}+): {sample}")
        all_passed = False

    print("\n==========================================")
    if all_passed:
        print(f">>> {family} 本脚本覆盖的检查全部通过。<<<")
    else:
        print(">>> 门禁检验存在未通过项，请排查！<<<")
    print("==========================================")
    return all_passed


if __name__ == "__main__":
    import sys
    sys.exit(0 if main() else 1)
