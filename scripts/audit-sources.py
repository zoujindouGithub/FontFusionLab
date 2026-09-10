"""按 recipe 审计各抽样码位的实际字形来源（base 注入规则: base 无此码位才注入）。"""
import argparse
from pathlib import Path
from fontTools.ttLib import TTFont

import catalog

SAMPLES = {
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

def main():
    parser = argparse.ArgumentParser(description='FontFusionLab per-codepoint source audit')
    parser.add_argument('--recipe', '--variant', default=catalog.DEFAULT_RECIPE)
    parser.add_argument('--output-root', type=Path, default=catalog.ROOT / 'build')
    args = parser.parse_args()

    recipe = catalog.load_recipe(args.recipe)
    out_path = catalog.font_paths(recipe, args.output_root)['Regular']
    base_path = catalog.source_path(recipe['styles']['Regular']['base'], 'Regular')
    cjk_path = catalog.source_path(recipe['cjk']['source'], 'Regular')

    v4 = TTFont(out_path)
    orig = TTFont(base_path)
    cjk = TTFont(cjk_path)
    ocm, ccm, mcm = orig.getBestCmap(), v4.getBestCmap(), cjk.getBestCmap()

    cjk_label = recipe['cjk']['source']
    print(f"Recipe: {recipe['id']}  family={recipe['family']}")
    print(f"{'字符':<12}{str(recipe['styles']['Regular']['base'])+'有':<14}{cjk_label+'有':<12}{'产物有':<8}实际来源")
    for label, cp in SAMPLES.items():
        in_f = cp in ocm
        in_m = cp in mcm
        in_v = cp in ccm
        if in_f:
            source = recipe['styles']['Regular']['base']
        elif in_m:
            source = cjk_label
        else:
            source = '缺字(系统回退)'
        print(f"{label:<12}{str(in_f):<14}{str(in_m):<12}{str(in_v):<8}{source}")

    h = v4["hmtx"]
    cell_base = h["A"][0]
    zh = ccm[0x4E2D]
    cell_cjk = h[zh][0]
    print(f"\nbase 拉丁格宽={cell_base}, 注入CJK advance={cell_cjk} ({cell_cjk/cell_base:.2f}x)")

    mzh = cjk["hmtx"][mcm[0x4E2D]]
    scale = v4["head"].unitsPerEm / cjk["head"].unitsPerEm
    print(f"{cjk_label} 原生中 advance={mzh[0]}@upem{cjk['head'].unitsPerEm} → 缩放后应={round(mzh[0]*scale)}@{v4['head'].unitsPerEm}, 实际注入 advance={cell_cjk}")


if __name__ == '__main__':
    main()
