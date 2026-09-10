import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
POWERSHELL = shutil.which("pwsh") or shutil.which("powershell")
pytestmark = pytest.mark.skipif(POWERSHELL is None, reason="PowerShell is required for installer execution")
STYLES = ("Regular", "Bold", "Italic", "BoldItalic")


def run_installer(tmp_path, selector, variant, family, prefix, missing=False):
    output = tmp_path / "build"
    for style in STYLES:
        path = output / variant / f"{prefix}-{style}.ttf"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fixture font: " + style.encode())
    if missing:
        path.unlink()
    local = tmp_path / "local"
    appdata = tmp_path / "roaming"
    local.mkdir()
    settings = appdata / "Code/User/settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text('{"editor.fontFamily":"Keep My Font"}', encoding="utf-8")
    # Mutation guards also catch calls that accidentally rely on cmdlet WhatIf propagation.
    harness = tmp_path / "invoke.ps1"
    harness.write_text(
        "$ErrorActionPreference = 'Stop'\n"
        "function New-ItemProperty { throw 'REGISTRY MUTATION' }\n"
        "function Set-ItemProperty { throw 'REGISTRY MUTATION' }\n"
        "function Remove-ItemProperty { throw 'REGISTRY MUTATION' }\n"
        "function Copy-Item { throw 'FILE MUTATION' }\n"
        "function New-Item { throw 'DIRECTORY MUTATION' }\n"
        "function Add-Type { throw 'NATIVE MUTATION' }\n"
        "$params = @{ OutputRoot = $env:INSTALL_OUTPUT; WhatIf = $true; ConfigureEditors = $true }\n"
        f"$params['{selector[0]}'] = $env:INSTALL_SELECTOR\n"
        "& $env:INSTALL_SCRIPT @params\n",
        encoding="utf-8",
    )
    env = dict(os.environ, LOCALAPPDATA=str(local), APPDATA=str(appdata),
               INSTALL_SCRIPT=str(ROOT / "scripts/install.ps1"), INSTALL_OUTPUT=str(output),
               INSTALL_SELECTOR=selector[1])
    result = subprocess.run([POWERSHELL, "-NoProfile", "-File", str(harness)],
                            cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8")
    assert not list(local.iterdir())
    assert settings.read_text(encoding="utf-8") == '{"editor.fontFamily":"Keep My Font"}'
    return result


@pytest.mark.parametrize("variant,family,prefix", [
    ("firacode-sarasa", "FiraCode Sarasa Mono", "FiraCodeSarasaMono"),
    ("firacode-maple", "FiraCode Maple Mono", "FiraCodeMapleMono"),
])
def test_whatif_resolves_variant_family_without_mutations(tmp_path, variant, family, prefix):
    result = run_installer(tmp_path, ("Variant", variant), variant, family, prefix)
    assert result.returncode == 0, result.stdout + result.stderr
    for style in STYLES:
        registry_style = "Bold Italic" if style == "BoldItalic" else style
        assert f"{family} {registry_style} (TrueType)" in result.stdout
        assert f"{prefix}-{style}.ttf" in result.stdout
    assert "MUTATION" not in result.stdout + result.stderr


def test_whatif_recipe_path_uses_recipe_family_not_file_prefix(tmp_path):
    variant, family, prefix = "firacode-maple", "FiraCode Maple Mono", "FiraCodeMapleMono"
    result = run_installer(tmp_path, ("Recipe", str(ROOT / "recipes" / f"{variant}.json")),
                           variant, family, prefix)
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"{family} Regular (TrueType)" in result.stdout
    assert f"{prefix}-Regular (TrueType)" not in result.stdout


def test_whatif_rejects_missing_font_before_mutations(tmp_path):
    result = run_installer(tmp_path, ("Variant", "firacode-maple"), "firacode-maple",
                           "FiraCode Maple Mono", "FiraCodeMapleMono", missing=True)
    assert result.returncode != 0
    assert "FiraCodeMapleMono-BoldItalic.ttf" in result.stdout + result.stderr
    assert "MUTATION" not in result.stdout + result.stderr
