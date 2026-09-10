import json
import sys
from pathlib import Path

import catalog

ROOT = Path(__file__).resolve().parent.parent
STYLES = ('Regular', 'Bold', 'Italic', 'BoldItalic')
VERSION = '2.0.0'


def plan(output_root, release_dir):
    """解析全部 production variant 与输出路径；失败时绝不写出。"""
    recipes = catalog.production_recipes()
    plan = []
    for recipe in recipes:
        fonts = {style: path for style, path in catalog.font_paths(recipe, output_root).items()}
        for style, path in fonts.items():
            if not path.is_file():
                raise FileNotFoundError(f"Missing required font: {path}")
        plan.append((recipe, fonts))
    return plan


def write_variant_readme(recipe):
    lines = [
        f"# {recipe['family']}",
        '',
        f"FontFusionLab 字体融合实验室 variant `{recipe['id']}`。",
        '',
        '| 字面 | 文件 |',
        '|---|---|',
        *[f"| {style} | {catalog.font_paths(recipe)[style].name} |" for style in STYLES],
        '',
        '字体以 SIL Open Font License 1.1 授权，详见 LICENSE。',
        'CJK 字形来源与其授权见 sources/manifest.json 与 recipe.json。',
    ]
    return '\n'.join(lines) + '\n'


def main():
    output_root = ROOT / 'build'
    release_dir = ROOT / 'release'
    argv = sys.argv[1:]
    if '--output-root' in argv:
        output_root = Path(argv[argv.index('--output-root') + 1])
    if '--release-dir' in argv:
        release_dir = Path(argv[argv.index('--release-dir') + 1])
    elif '--release' in argv:
        release_dir = Path(argv[argv.index('--release') + 1])

    plan_data = plan(output_root, release_dir)

    import zipfile
    release_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    for recipe, fonts in plan_data:
        archive_path = release_dir / f"{recipe['file_prefix']}-v{VERSION}.zip"
        entry = {
            'id': recipe['id'],
            'family': recipe['family'],
            'archive': archive_path.name,
            'fonts': {},
        }
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for style in STYLES:
                path = fonts[style]
                zf.write(path, path.name)
                entry['fonts'][style] = {'file': path.name, 'sha256': catalog.sha256(path)}
            zf.writestr('LICENSE', (ROOT / 'LICENSE').read_text(encoding='utf-8'))
            zf.writestr('README.md', write_variant_readme(recipe))
            zf.writestr('recipe.json', json.dumps(recipe, ensure_ascii=False, indent=2) + '\n')
        entry['sha256'] = catalog.sha256(archive_path)
        entries.append(entry)
        print(f"[OK] {recipe['family']}: {archive_path.name} ({archive_path.stat().st_size // 1024} KB)")

    import hashlib
    manifest = {'version': VERSION, 'variants': entries}
    manifest_path = release_dir / 'variants.json'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    sums_path = release_dir / 'SHA256SUMS.txt'
    lines = [f"{entry['sha256']}  {entry['archive']}" for entry in entries]
    lines.append(f"{catalog.sha256(manifest_path)}  variants.json")
    sums_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f"[OK] Release 清单与校验完成: {release_dir}")


if __name__ == '__main__':
    main()
