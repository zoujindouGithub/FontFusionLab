import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

ROOT = Path(__file__).resolve().parents[1]
STYLES = ("Regular", "Bold", "Italic", "BoldItalic")
VARIANTS = {
    "firacode-sarasa": ("FiraCode Sarasa Mono", "FiraCodeSarasaMono"),
    "firacode-maple": ("FiraCode Maple Mono", "FiraCodeMapleMono"),
}


def make_font(path, family, style):
    builder = FontBuilder(1000, isTTF=True)
    builder.setupGlyphOrder([".notdef", "space"])
    builder.setupCharacterMap({32: "space"})
    builder.setupGlyf({name: TTGlyphPen(None).glyph() for name in (".notdef", "space")})
    builder.setupHorizontalMetrics({name: (600, 0) for name in (".notdef", "space")})
    builder.setupHorizontalHeader(ascent=800, descent=-200)
    builder.setupNameTable({"familyName": family, "styleName": style})
    builder.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200)
    builder.setupPost()
    builder.setupMaxp()
    path.parent.mkdir(parents=True, exist_ok=True)
    builder.save(path)


@pytest.fixture
def project(tmp_path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    for name in ("package-release.py", "catalog.py"):
        shutil.copy2(ROOT / "scripts" / name, scripts / name)
    for name in ("recipes", "sources"):
        shutil.copytree(ROOT / name, tmp_path / name)
    shutil.copy2(ROOT / "LICENSE", tmp_path / "LICENSE")
    for variant, (family, prefix) in VARIANTS.items():
        for style in STYLES:
            make_font(tmp_path / "build" / variant / f"{prefix}-{style}.ttf", family, style)
    return tmp_path


def package(project, release="release/v2.0.0"):
    return subprocess.run(
        [sys.executable, str(project / "scripts/package-release.py"),
         "--output-root", str(project / "build"), "--release-dir", str(project / release)],
        cwd=project, capture_output=True, text=True,
    )


def test_release_archives_are_independent_and_all_hashes_match(project):
    result = package(project)
    assert result.returncode == 0, result.stdout + result.stderr
    release = project / "release/v2.0.0"
    manifest = json.loads((release / "variants.json").read_text(encoding="utf-8"))
    assert manifest["version"] == "2.0.0"
    assert {entry["id"] for entry in manifest["variants"]} == set(VARIANTS)
    for entry in manifest["variants"]:
        family, prefix = VARIANTS[entry["id"]]
        archive = release / f"{prefix}-v2.0.0.zip"
        assert entry["family"] == family
        assert entry["archive"] == archive.name
        assert entry["sha256"] == hashlib.sha256(archive.read_bytes()).hexdigest()
        with zipfile.ZipFile(archive) as packed:
            font_names = {f"{prefix}-{style}.ttf" for style in STYLES}
            assert set(packed.namelist()) == font_names | {"LICENSE", "README.md", "recipe.json"}
            assert family in packed.read("README.md").decode("utf-8")
            assert json.loads(packed.read("recipe.json"))["id"] == entry["id"]
            assert set(entry["fonts"]) == set(STYLES)
            for style in STYLES:
                name = f"{prefix}-{style}.ttf"
                expected = (project / "build" / entry["id"] / name).read_bytes()
                assert packed.read(name) == expected
                assert entry["fonts"][style] == {"file": name, "sha256": hashlib.sha256(expected).hexdigest()}
    sums = dict(line.split("  ", 1)[::-1] for line in (release / "SHA256SUMS.txt").read_text().splitlines())
    assert set(sums) == {"variants.json", *(f"{prefix}-v2.0.0.zip" for _, prefix in VARIANTS.values())}
    for filename, digest in sums.items():
        assert hashlib.sha256((release / filename).read_bytes()).hexdigest() == digest
    repeat = package(project, "release/repeat")
    assert repeat.returncode == 0, repeat.stdout + repeat.stderr
    for name in (*sums, "SHA256SUMS.txt"):
        assert (release / name).read_bytes() == (project / "release/repeat" / name).read_bytes()


def test_missing_font_rejected_before_release_is_created(project):
    missing = project / "build/firacode-maple/FiraCodeMapleMono-BoldItalic.ttf"
    missing.unlink()
    result = package(project)
    assert result.returncode != 0
    assert missing.name in result.stdout + result.stderr
    assert not (project / "release/v2.0.0").exists()


def test_private_production_recipe_rejected_before_release_is_created(project):
    recipe_path = project / "recipes/firacode-maple.json"
    recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
    recipe["cjk"]["source"] = "private-cjk"
    recipe_path.write_text(json.dumps(recipe), encoding="utf-8")
    result = package(project)
    assert result.returncode != 0
    assert "private-cjk" in result.stdout + result.stderr
    assert not (project / "release/v2.0.0").exists()


def test_zip_members_carry_fixed_timestamps(project):
    assert package(project).returncode == 0
    with zipfile.ZipFile(project / "release" / "v2.0.0" / "FiraCodeMapleMono-v2.0.0.zip") as packed:
        for info in packed.infolist():
            assert info.date_time == (1980, 1, 1, 0, 0, 0), f"{info.filename}: {info.date_time}"


def test_back_to_back_packages_are_byte_identical(project, monkeypatch):
    first = package(project, "release/det1")
    assert first.returncode == 0, first.stdout + first.stderr
    second = package(project, "release/det2")
    assert second.returncode == 0, second.stdout + second.stderr
    for name in ("FiraCodeMapleMono-v2.0.0.zip", "FiraCodeSarasaMono-v2.0.0.zip"):
        assert (project / "release/det1" / name).read_bytes() == (project / "release/det2" / name).read_bytes()
