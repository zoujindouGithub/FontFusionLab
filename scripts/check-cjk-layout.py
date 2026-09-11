"""检查生成字体的字面位置，保留源字体的非对称留白与标点位置。按 recipe 驱动。"""
import argparse
from pathlib import Path

from fontTools.ttLib import TTFont

import catalog


def main():
    parser = argparse.ArgumentParser(description='FontFusionLab CJK layout checker')
    parser.add_argument('directory', nargs='?', type=Path, help='Variant output directory (default: build/<recipe-id>)')
    parser.add_argument('--recipe', '--variant', default=catalog.DEFAULT_RECIPE,
                        help=f'Recipe ID or JSON path (default: {catalog.DEFAULT_RECIPE})')
    parser.add_argument('--output-root', type=Path, default=catalog.ROOT / 'build')
    parser.add_argument('--scale', type=float, default=None, help='Override recipe cjk scale')
    parser.add_argument('--center-y', type=float, default=None, help='Override vertical scale anchor (source design units)')
    args = parser.parse_args()

    recipe = catalog.load_recipe(args.recipe)
    directory = args.directory or catalog.font_paths(recipe, args.output_root)['Regular'].parent
    scale = args.scale if args.scale is not None else recipe['cjk']['scale']
    recipe_center_y = args.center_y if args.center_y is not None else recipe['cjk'].get('center_y')
    glyph_prefix = 'cjk'
    errors = []
    for style in ('Regular', 'Bold'):
        style_cfg = recipe['styles'][style]
        source_style = style_cfg['source_style']
        source_id = style_cfg.get('cjk_source', recipe['cjk']['source'])
        source_path = catalog.source_path(source_id, source_style)
        with TTFont(source_path) as source, TTFont(directory / f"{recipe['file_prefix']}-{style}.ttf") as target:
            sc, tc = source.getBestCmap(), target.getBestCmap()
            unit_scale = target['head'].unitsPerEm / source['head'].unitsPerEm
            cell = target['hmtx'][tc[ord('A')]][0]
            center_y = recipe_center_y if recipe_center_y is not None else (source['hhea'].ascender + source['hhea'].descender) / 2
            checked = 0
            for cp, name in tc.items():
                if not name.startswith(glyph_prefix):
                    continue
                original = source['glyf'][sc[cp]]
                glyph = target['glyf'][name]
                advance, lsb = target['hmtx'][name]
                assert advance == 2 * cell, (style, hex(cp), '2:1 advance')
                if not original.numberOfContours:
                    continue
                source_advance = source['hmtx'][sc[cp]][0]
                expected_center = cell + ((original.xMin + original.xMax) / 2 - source_advance / 2) * unit_scale * scale
                actual_center = (glyph.xMin + glyph.xMax) / 2
                expected_width = (original.xMax - original.xMin) * unit_scale * scale
                expected_height = (original.yMax - original.yMin) * unit_scale * scale
                expected_y = (center_y + ((original.yMin + original.yMax) / 2 - center_y) * scale) * unit_scale
                if abs(actual_center - expected_center) > 1 or abs(glyph.xMax-glyph.xMin-expected_width) > 1 or abs(glyph.yMax-glyph.yMin-expected_height) > 1 or abs((glyph.yMin+glyph.yMax)/2-expected_y) > 1 or lsb != glyph.xMin:
                    errors.append((style, f'U+{cp:04X}', round(actual_center-expected_center, 2), round(glyph.xMax-glyph.xMin-expected_width, 2)))
                checked += 1
            print(f'{style}: checked {checked} outlined CJK glyph mappings')
    assert not errors, f'layout mismatches={len(errors)}, first (style, cp, center error, width error)={errors[:8]}'
    print(f"PASS: source-cell centering, {scale:.2f}x uniform scale, LSB and 2:1 advance")


if __name__ == '__main__':
    main()
