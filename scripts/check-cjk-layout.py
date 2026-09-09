"""检查生成字体的字面位置，保留源字体的非对称留白与标点位置。"""
import argparse
from pathlib import Path
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    parser.add_argument('--scale', type=float, default=1.05)
    args = parser.parse_args()
    errors = []
    for style in ('Regular', 'Bold'):
        with TTFont(ROOT / f'MapleMono-src/MapleMono-NF-CN-{style}.ttf') as source, TTFont(args.directory / f'FiraCodeMapleMono-{style}.ttf') as target:
            sc, tc = source.getBestCmap(), target.getBestCmap()
            unit_scale = target['head'].unitsPerEm / source['head'].unitsPerEm
            cell = target['hmtx'][tc[ord('A')]][0]
            # 按源字体排版框中心缩放，避免按每个字形的黑色轮廓居中而移坏标点。
            center_y = (source['hhea'].ascender + source['hhea'].descender) / 2
            checked = 0
            for cp, name in tc.items():
                if not name.startswith('maple'):
                    continue
                original = source['glyf'][sc[cp]]
                glyph = target['glyf'][name]
                advance, lsb = target['hmtx'][name]
                assert advance == 2 * cell, (style, hex(cp), '2:1 advance')
                if not original.numberOfContours:
                    continue
                source_advance = source['hmtx'][sc[cp]][0]
                expected_center = cell + ((original.xMin + original.xMax) / 2 - source_advance / 2) * unit_scale * args.scale
                actual_center = (glyph.xMin + glyph.xMax) / 2
                expected_width = (original.xMax - original.xMin) * unit_scale * args.scale
                expected_height = (original.yMax - original.yMin) * unit_scale * args.scale
                expected_y = (center_y + ((original.yMin + original.yMax) / 2 - center_y) * args.scale) * unit_scale
                if abs(actual_center - expected_center) > 1 or abs(glyph.xMax-glyph.xMin-expected_width) > 1 or abs(glyph.yMax-glyph.yMin-expected_height) > 1 or abs((glyph.yMin+glyph.yMax)/2-expected_y) > 1 or lsb != glyph.xMin:
                    errors.append((style, f'U+{cp:04X}', round(actual_center-expected_center, 2), round(glyph.xMax-glyph.xMin-expected_width, 2)))
                checked += 1
            print(f'{style}: checked {checked} outlined CJK glyph mappings')
    assert not errors, f'layout mismatches={len(errors)}, first (style, cp, center error, width error)={errors[:8]}'
    print(f'PASS: source-cell centering, {args.scale:.2f}x uniform scale, LSB and 2:1 advance')


if __name__ == '__main__':
    main()
