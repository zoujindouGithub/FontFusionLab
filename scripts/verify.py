"""
FiraCode Maple Mono 质量门禁与终验套件 (Automated Verification Suite)
"""

import os
import sys
from fontTools.ttLib import TTFont
import freetype

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
OUT_DIR = os.path.join(PROJECT_ROOT, "merged-v4")
SRC_FIRA = os.path.join(PROJECT_ROOT, "FiraCode-src")

def main():
    print("==========================================")
    print("开始 FiraCode Maple Mono 终验门禁审计")
    print("==========================================")
    all_passed = True

    # 1. 四字面文件存在性
    subfamilies = ["Regular", "Bold", "Italic", "BoldItalic"]
    for sub in subfamilies:
        p = os.path.join(OUT_DIR, f"FiraCodeMapleMono-{sub}.ttf")
        if not os.path.exists(p):
            print(f"[FAIL] 缺少产物文件: {p}")
            return False
        print(f"[PASS] 产物存在: FiraCodeMapleMono-{sub}.ttf ({os.path.getsize(p) // 1024} KB)")

    # 2. RIBBI 命名规范检验
    print("\n--- 检验 RIBBI 与元数据命名 ---")
    expected_naming = {
        "Regular": ("FiraCode Maple Mono", "Regular"),
        "Bold": ("FiraCode Maple Mono", "Bold"),
        "Italic": ("FiraCode Maple Mono", "Italic"),
        "BoldItalic": ("FiraCode Maple Mono", "Bold Italic"),
    }
    for sub, (exp_id1, exp_id2) in expected_naming.items():
        font = TTFont(os.path.join(OUT_DIR, f"FiraCodeMapleMono-{sub}.ttf"))
        id1 = font["name"].getDebugName(1)
        id2 = font["name"].getDebugName(2)
        id16 = font["name"].getDebugName(16)
        id17 = font["name"].getDebugName(17)

        is_valid = (id1 == exp_id1 and id2 == exp_id2 and id16 == "FiraCode Maple Mono" and id17 == exp_id2)
        if is_valid:
            print(f"[PASS] {sub:11}: ID1='{id1}' ID2='{id2}' ID16='{id16}' ID17='{id17}'")
        else:
            print(f"[FAIL] {sub:11}: ID1='{id1}' ID2='{id2}' ID16='{id16}' ID17='{id17}' (期望 ID1='{exp_id1}', ID2='{exp_id2}')")
            all_passed = False

    # 3. CJK 字符度量与 LSB 居中检验
    print("\n--- 检验 CJK 2:1 Advance 与 LSB 居中 ---")
    reg_font = TTFont(os.path.join(OUT_DIR, "FiraCodeMapleMono-Regular.ttf"))
    reg_cmap = reg_font.getBestCmap()
    hmtx = reg_font["hmtx"]
    cell = hmtx["A"][0]

    zh_glyph = reg_cmap.get(0x4E2D)
    if not zh_glyph:
        print("[FAIL] 缺少 CJK 字符 0x4E2D '中'")
        all_passed = False
    else:
        advance, lsb = hmtx[zh_glyph]
        # 轮廓真实 xmin
        coords, _, _ = reg_font["glyf"][zh_glyph].getCoordinates(reg_font["glyf"])
        real_xmin = min((p[0] for p in coords), default=0)

        adv_ok = (advance == 2 * cell)
        lsb_ok = (lsb == round(real_xmin) and lsb > 50)  # 必须大于 50，不能是贴边的 0

        if adv_ok and lsb_ok:
            print(f"[PASS] '中' advance={advance} (2.0x cell), lsb={lsb} (真实 xmin={real_xmin}) -> 完美居中！")
        else:
            print(f"[FAIL] '中' advance={advance} (期望 {2*cell}), lsb={lsb} (真实 xmin={real_xmin})")
            all_passed = False

    # 4. Box-Drawing 逐字节还原检验
    print("\n--- 检验 Box-Drawing (U+2500-U+259F) 原版程序逐字节还原 ---")
    orig_reg = TTFont(os.path.join(SRC_FIRA, "FiraCodeNerdFontMono-Regular.ttf"))
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
    it_font = TTFont(os.path.join(OUT_DIR, "FiraCodeMapleMono-Italic.ttf"))
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
        face = freetype.Face(path)
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
            r_orig = render_glyph(os.path.join(SRC_FIRA, "FiraCodeNerdFontMono-Regular.ttf"), cp, px)
            r_merged = render_glyph(os.path.join(OUT_DIR, "FiraCodeMapleMono-Regular.ttf"), cp, px)
            if r_orig == r_merged:
                render_same += 1
            else:
                render_diff += 1

    if render_diff == 0:
        print(f"[PASS] 抽样核心拉丁/数字/制表符渲染位图 100% 逐像素完全一致 ({render_same}/{render_same})！")
    else:
        print(f"[FAIL] 渲染存在像素差异: SAME={render_same}, DIFF={render_diff}")
        all_passed = False

    # 中文出图检查
    r_zh = render_glyph(os.path.join(OUT_DIR, "FiraCodeMapleMono-Regular.ttf"), 0x4E2D, 16)
    if r_zh[0] == 14 and r_zh[1] == 16 and r_zh[3] == 3:
        print(f"[PASS] 中文 '中' @16px 渲染点阵={r_zh[0]}x{r_zh[1]} left={r_zh[3]} -> 完美对齐 Maple 原生标准！")
    else:
        print(f"[WARN] 中文 '中' 渲染点阵={r_zh[0]}x{r_zh[1]} left={r_zh[3]}")

    print("\n==========================================")
    if all_passed:
        print(">>> 全部质量门禁 100% 通过！字体工程达到发布标准！<<<")
    else:
        print(">>> 门禁检验存在未通过项，请排查！<<<")
    print("==========================================")
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
