from fontTools.ttLib import TTFont

v4 = TTFont("merged-v4/FiraCodeMapleMono-Regular.ttf")
orig = TTFont("FiraCode-src/FiraCodeNerdFontMono-Regular.ttf")
maple = TTFont("MapleMono-src/MapleMono-NF-CN-Regular.ttf")
ocm, ccm, mcm = orig.getBestCmap(), v4.getBestCmap(), maple.getBestCmap()

samples = {
    "A 拉丁大写": 0x41,
    "g 拉丁小写": 0x67,
    "0 数字": 0x30,
    "= 符号": 0x3D,
    "→ 箭头": 0x2192,
    "中 CJK": 0x4E2D,
    "、 CJK标点": 0x3001,
    "！ 全角": 0xFF01,
    "ア 片假名": 0x30A2,
    "г 西里尔": 0x0433,
    "α 希腊": 0x03B1,
    "é 拉丁扩展": 0xE9,
}

print(f"{'字符':<12}{'FiraCode有':<10}{'Maple有':<9}{'v4注入':<8}{'实际来源'}")
for label, cp in samples.items():
    in_f = cp in ocm
    in_m = cp in mcm
    in_v = cp in ccm
    # v4 注入规则：cp 不在 FiraCode cmap 里才注入 Maple 字形
    # 所以「FiraCode 有」的字形 = FiraCode 来源；「FiraCode 无」= Maple 来源
    if in_f:
        source = "FiraCode"
    elif in_m:
        source = "Maple"
    else:
        source = "缺字(系统回退)"
    print(f"{label:<12}{str(in_f):<10}{str(in_m):<9}{str(in_v):<8}{source}")

# 度量对比：拉丁格宽 vs Maple 拉丁格宽 —— 用户感觉"不对劲"的常见来源是
# 字重/风格差异或 CJK 与拉丁的视觉大小不协调
h = v4["hmtx"]
cell_fira = h["A"][0]
zh = ccm[0x4E2D]
cell_cjk = h[zh][0]
print(f"\nFiraCode 拉丁格宽={cell_fira}, 注入CJK advance={cell_cjk} ({cell_cjk/cell_fira:.2f}x)")

# 字重对比：Maple 原生 CJK 笔画粗细 vs FiraCode Latin 的笔画粗细
# Maple upem=1000 主干宽~90；缩放1.95后=175；FiraCode upem=1950 主干宽~180? 近似即可
# 关键：upem 缩放后的 CJK 视觉密度
mzh = maple["hmtx"]["uni4E2D"]
print(f"Maple 原生中 advance={mzh[0]}@upem1000 → 缩放后应={round(mzh[0]*1.95)}@1950, 实际注入 advance={cell_cjk}")
