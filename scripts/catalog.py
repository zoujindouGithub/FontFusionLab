"""Validated public recipes and integrity-checked source resolution."""
import argparse
import hashlib
import json
import tempfile
import urllib.request
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parent.parent
STYLES = ('Regular', 'Bold', 'Italic', 'BoldItalic')
DEFAULT_RECIPE = 'firacode-sarasa'


class RecipeError(ValueError):
    """配方/来源登记协议错误；保留 ValueError 兼容旧调用方。"""


class SourceIntegrityError(ValueError):
    """来源内容完整性错误；校验失败必须熔断而非继续消费。"""


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def validate(data, schema):
    try:
        jsonschema.Draft202012Validator(read_json(schema)).validate(data)
    except jsonschema.ValidationError as exc:
        raise RecipeError(f'Invalid {Path(schema).parent.name}: {exc.message}') from exc


def public_sources(manifest_path=ROOT / 'sources/manifest.json'):
    manifest = read_json(manifest_path)
    validate(manifest, ROOT / 'sources/schema.json')
    return manifest['sources']


def load_recipe(selector=DEFAULT_RECIPE):
    path = Path(selector)
    if path.suffix != '.json':
        if path.name != str(selector):
            raise RecipeError('Recipe selector must be an ID or JSON path')
        path = ROOT / 'recipes' / f'{selector}.json'
    recipe = read_json(path)
    validate(recipe, ROOT / 'recipes/schema.json')
    if recipe['status'] == 'production':
        sources = public_sources()
        for style, config in recipe['styles'].items():
            for sid in (config['base'], config.get('cjk_source', recipe['cjk']['source'])):
                if sid not in sources or config['source_style'] not in sources[sid]['files']:
                    raise RecipeError(f'Production recipe requires public source/style: {sid}/{style}')
    return recipe


def production_recipes():
    return [recipe for path in sorted((ROOT / 'recipes').glob('*.json'))
            if path.name != 'schema.json' and (recipe := load_recipe(path))['status'] == 'production']


def font_paths(recipe, output_root=ROOT / 'build'):
    return {style: Path(output_root) / recipe['id'] / f"{recipe['file_prefix']}-{style}.ttf" for style in STYLES}


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def source_path(source_id, style, manifest_path=ROOT / 'sources/manifest.json',
                local_path=ROOT / 'sources/local.json', root=ROOT):
    sources = public_sources(manifest_path)
    if source_id not in sources:
        local = read_json(local_path).get('sources', {}) if Path(local_path).is_file() else {}
        if source_id not in local or style not in local[source_id]:
            raise RecipeError(f'Unknown source/style: {source_id}/{style}; private sources require sources/local.json')
        path = Path(local[source_id][style]).expanduser()
        if not path.is_absolute():
            path = Path(root) / path
        if not path.is_file():
            raise FileNotFoundError(f'Private source file missing: {source_id}/{style}')
        return path
    entry = sources[source_id]['files'][style]
    root = Path(root).resolve()
    if 'path' in entry:
        # 路径必须留在仓内，避免恶意 manifest 借 ../ 读取任意本机文件。
        path = (root / entry['path']).resolve()
        if not path.is_relative_to(root):
            raise RecipeError('Public source paths must stay inside the repository')
    else:
        # 下载先写随机临时文件，完整校验后原子替换，避免半文件进入缓存被消费。
        path = root / '.cache/sources' / f"{entry['sha256']}.ttf"
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
                temporary = Path(stream.name)
            try:
                urllib.request.urlretrieve(entry['url'], temporary)
                if sha256(temporary) != entry['sha256']:
                    # 哈希不匹配必须熔断，不能把不可信来源留在缓存或交给 fontTools。
                    raise SourceIntegrityError(f'SHA256 mismatch: {source_id}/{style}')
                temporary.replace(path)
            finally:
                temporary.unlink(missing_ok=True)
    if sha256(path) != entry['sha256']:
        # 已有缓存也必须复核，防止外部改写绕过下载阶段的完整性门禁。
        raise SourceIntegrityError(f'SHA256 mismatch: {source_id}/{style}')
    return path


def recipe_arguments(description):
    parser = argparse.ArgumentParser(description=description)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument('--recipe', '--variant', default=DEFAULT_RECIPE,
                           help=f'Recipe ID or JSON path (default: {DEFAULT_RECIPE})')
    selection.add_argument('--all', action='store_true', help='All production variants')
    parser.add_argument('--output-root', type=Path, default=ROOT / 'build')
    return parser


def selected_recipes(args):
    return production_recipes() if args.all else [load_recipe(args.recipe)]
