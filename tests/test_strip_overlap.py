import array
import io

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

import build


def make_fixture(overlapping_names=('A',)):
    pen = TTGlyphPen(None)
    pen.moveTo((100, 100))
    pen.lineTo((800, 100))
    pen.lineTo((500, 800))
    pen.closePath()
    base = pen.glyph()
    overlap = pen.glyph()
    overlap.flags = array.array('B', (flag | 0x40 for flag in overlap.flags))
    glyphs = {'.notdef': TTGlyphPen(None).glyph(), 'A': base, 'B': base, 'C': base}
    for name in overlapping_names:
        glyphs[name] = overlap
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(['.notdef', 'A', 'B', 'C'])
    fb.setupCharacterMap({65: 'A', 66: 'B', 67: 'C'})
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics({'.notdef': (500, 0), 'A': (600, 100), 'B': (600, 100), 'C': (600, 100)})
    fb.setupHorizontalHeader(ascent=900, descent=-300)
    fb.setupNameTable({'familyName': 'Fixture', 'styleName': 'Regular'})
    fb.setupOS2()
    fb.setupPost()
    fb.setupMaxp()
    return fb.font


def snapshot(font, names=('A', 'B', 'C')):
    buffer = io.BytesIO()
    font.save(buffer)
    buffer.seek(0)
    with TTFont(buffer) as reopened:
        glyf, hmtx = reopened['glyf'], reopened['hmtx']
        return {
            name: (
                list(glyf[name].getCoordinates(glyf)[0]),
                getattr(glyf[name], 'endPtsOfContours', None),
                tuple(hmtx[name]),
            )
            for name in names
        }


def test_strip_clears_all_flags_preserving_outlines_and_metrics():
    assert hasattr(build, 'strip_overlap_flags'), 'pipeline-wide overlap strip is absent'
    font = make_fixture()
    before = snapshot(font)
    build.strip_overlap_flags(font)
    buffer = io.BytesIO()
    font.save(buffer)
    buffer.seek(0)
    with TTFont(buffer) as result:
        for name in ('.notdef', 'A', 'B', 'C'):
            glyph = result['glyf'][name]
            if glyph.numberOfContours > 0 and not glyph.isComposite():
                assert not any(flag & 0x40 for flag in glyph.flags), name
        after = snapshot(result)
        assert after == before
