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


def test_whatif_lists_legacy_slot_cleanup_without_mutations(tmp_path):
    """旧产线 -vNN 槽残留（同 family 遮蔽源）必须出现在 WhatIf 的 CLEAN 计划里，且零变更。"""
    output = tmp_path / "build"
    for style in STYLES:
        path = output / "firacode-maple" / f"FiraCodeMapleMono-{style}.ttf"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fixture font: " + style.encode())
    font_dir = tmp_path / "local" / "Microsoft" / "Windows" / "Fonts"
    font_dir.mkdir(parents=True)
    stale_regular = font_dir / "FiraCodeMapleMono-Regular-v42.ttf"
    stale_regular.write_bytes(b"legacy shadow regular")
    stale_bold = font_dir / "FiraCodeMapleMono-Bold-v41.ttf"
    stale_bold.write_bytes(b"legacy shadow bold")
    appdata = tmp_path / "roaming"
    settings = appdata / "Code/User/settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text('{"editor.fontFamily":"Keep My Font"}', encoding="utf-8")
    # 只读伪造 HKCU Fonts 镜像（Get-ItemProperty 是读取，不在 mutation guard 拦截语义内）。
    harness = tmp_path / "invoke.ps1"
    harness.write_text(
        "$ErrorActionPreference = 'Stop'\n"
        "function New-ItemProperty { throw 'REGISTRY MUTATION' }\n"
        "function Set-ItemProperty { throw 'REGISTRY MUTATION' }\n"
        "function Remove-ItemProperty { throw 'REGISTRY MUTATION' }\n"
        "function Copy-Item { throw 'FILE MUTATION' }\n"
        "function New-Item { throw 'DIRECTORY MUTATION' }\n"
        "function Add-Type { throw 'NATIVE MUTATION' }\n"
        f"$FakeReg = [pscustomobject]@{{ 'FiraCodeMapleMono-Regular (TrueType)' = '{stale_regular}' }}\n"
        "function Get-ItemProperty { $FakeReg }\n"
        "$params = @{ OutputRoot = $env:INSTALL_OUTPUT; WhatIf = $true }\n"
        "$params['Variant'] = 'firacode-maple'\n"
        "& $env:INSTALL_SCRIPT @params\n",
        encoding="utf-8",
    )
    env = dict(os.environ, LOCALAPPDATA=str(tmp_path / "local"), APPDATA=str(appdata),
               INSTALL_SCRIPT=str(ROOT / "scripts/install.ps1"), INSTALL_OUTPUT=str(output))
    result = subprocess.run([POWERSHELL, "-NoProfile", "-File", str(harness)],
                            cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8")
    combined = result.stdout + result.stderr
    assert result.returncode == 0, combined
    assert "FiraCodeMapleMono-Regular-v42.ttf" in combined
    assert "FiraCodeMapleMono-Regular (TrueType)" in combined
    assert "FiraCodeMapleMono-Bold-v41.ttf" in combined
    assert "CLEAN" in combined
    assert "MUTATION" not in combined
    # 计划阶段零变更：残留文件原样在位，settings 未被触碰
    assert stale_regular.read_bytes() == b"legacy shadow regular"
    assert stale_bold.read_bytes() == b"legacy shadow bold"
    assert settings.read_text(encoding="utf-8") == '{"editor.fontFamily":"Keep My Font"}'


def test_whatif_clean_directory_lists_no_cleanup(tmp_path):
    """真机注册表只读枚举：本机字体目录(临时重定向)干净时，计划不得出现 CLEAN 条目。"""
    result = run_installer(tmp_path, ("Variant", "firacode-maple"), "firacode-maple",
                           "FiraCode Maple Mono", "FiraCodeMapleMono")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "CLEAN" not in result.stdout
    assert "MUTATION" not in result.stdout + result.stderr


def test_whatif_keeps_live_versioned_slot_referenced_by_family_entry(tmp_path):
    """本脚本自用的 family 词形登记项指向 -v42 槽时, 该文件是活注册, 不得进入 CLEAN 计划。"""
    output = tmp_path / "build"
    for style in STYLES:
        path = output / "firacode-sarasa" / f"FiraCodeSarasaMono-{style}.ttf"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fixture font: " + style.encode())
    font_dir = tmp_path / "local" / "Microsoft" / "Windows" / "Fonts"
    font_dir.mkdir(parents=True)
    live_slot = font_dir / "FiraCodeSarasaMono-Regular-v42.ttf"
    live_slot.write_bytes(b"live via family entry")
    legacy = font_dir / "FiraCodeMapleMono-Bold-v99.ttf"
    legacy.write_bytes(b"legacy shadow")
    appdata = tmp_path / "roaming"
    settings = appdata / "Code/User/settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text("{}", encoding="utf-8")
    harness = tmp_path / "invoke.ps1"
    harness.write_text(
        "$ErrorActionPreference = 'Stop'\n"
        "function New-ItemProperty { throw 'REGISTRY MUTATION' }\n"
        "function Set-ItemProperty { throw 'REGISTRY MUTATION' }\n"
        "function Remove-ItemProperty { throw 'REGISTRY MUTATION' }\n"
        "function Copy-Item { throw 'FILE MUTATION' }\n"
        "function New-Item { throw 'DIRECTORY MUTATION' }\n"
        "function Add-Type { throw 'NATIVE MUTATION' }\n"
        f"$FakeReg = [pscustomobject]@{{ 'FiraCode Sarasa Mono Regular (TrueType)' = '{live_slot}'; 'FiraCodeMapleMono-Bold (TrueType)' = '{legacy}' }}\n"
        "function Get-ItemProperty { $FakeReg }\n"
        "$params = @{ OutputRoot = $env:INSTALL_OUTPUT; WhatIf = $true }\n"
        "$params['Variant'] = 'firacode-sarasa'\n"
        "& $env:INSTALL_SCRIPT @params\n",
        encoding="utf-8",
    )
    env = dict(os.environ, LOCALAPPDATA=str(tmp_path / "local"), APPDATA=str(appdata),
               INSTALL_SCRIPT=str(ROOT / "scripts/install.ps1"), INSTALL_OUTPUT=str(output))
    result = subprocess.run([POWERSHELL, "-NoProfile", "-File", str(harness)],
                            cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8")
    combined = result.stdout + result.stderr
    assert result.returncode == 0, combined
    assert "FiraCodeMapleMono-Bold-v99.ttf" in combined          # 旧残留照常列出
    assert "FiraCodeSarasaMono-Regular-v42.ttf" not in combined  # 活槽位文件不进 CLEAN
    assert "MUTATION" not in combined
    assert live_slot.read_bytes() == b"live via family entry"
    assert legacy.read_bytes() == b"legacy shadow"
