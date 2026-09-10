import array
import io

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

import build


def fixture_font(cp, overlap=False):
    pen = TTGlyphPen(None)
    pen.moveTo((100, 100))
    pen.lineTo((800, 100))
    pen.lineTo((500, 800))
    pen.closePath()
    glyph = pen.glyph()
    if overlap:
        glyph.flags = array.array('B', (flag | 0x40 for flag in glyph.flags))
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(['.notdef', 'A', 'test'])
    fb.setupCharacterMap({65: 'A', cp: 'test'})
    fb.setupGlyf({'.notdef': TTGlyphPen(None).glyph(), 'A': glyph, 'test': glyph})
    fb.setupHorizontalMetrics({'.notdef': (500, 0), 'A': (500, 100), 'test': (1000, 100)})
    fb.setupHorizontalHeader(ascent=900, descent=-300)
    fb.setupNameTable({'familyName':'Fixture', 'styleName':'Regular'})
    fb.setupOS2()
    fb.setupPost()
    fb.setupMaxp()
    return fb.font


def test_injection_normalizes_overlap_without_changing_outline_or_metrics():
    assert hasattr(build, 'inject_cjk'), 'shared injection pipeline is absent'
    target = fixture_font(66)
    source = fixture_font(0x4E2D, overlap=True)
    build.inject_cjk(target, source, {0x4E2D}, 1.0)
    buffer = io.BytesIO()
    target.save(buffer)
    buffer.seek(0)
    with TTFont(buffer) as result:
        name = result.getBestCmap()[0x4E2D]
        glyph = result['glyf'][name]
        coords, endpoints, flags = glyph.getCoordinates(result['glyf'])
        assert list(coords) == [(100, 100), (800, 100), (500, 800)]
        assert list(endpoints) == [2]
        assert list(flags) == [1, 1, 1]
        assert result['hmtx'][name] == (1000, 100)
        assert result.getBestCmap()[65] == 'A'

def test_injection_selection_replaces_existing_cjk_for_distinct_source(tmp_path):
    cp = 0x4E00
    base = fixture_font(cp)
    source = fixture_font(cp)
    base_path = tmp_path / 'base.ttf'
    source_path = tmp_path / 'source.ttf'

    inject_cps = build.injection_codepoints(base, source, base_path, source_path)
    assert inject_cps == {cp}
    build.inject_cjk(base, source, inject_cps, 1.0)

    assert base.getBestCmap()[cp].startswith('cjk')
    assert base['hmtx'][base.getBestCmap()[cp]][0] == 2 * base['hmtx']['A'][0]
    assert build.injection_codepoints(base, source, base_path, base_path) == set()
