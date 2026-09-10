import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def catalog():
    assert (ROOT / 'scripts/catalog.py').exists(), 'recipe catalog is not implemented'
    import catalog
    return catalog


def test_production_recipes_have_independent_named_outputs():
    c = catalog()
    recipes = c.production_recipes()
    assert {r['family'] for r in recipes} == {'FiraCode Sarasa Mono', 'FiraCode Maple Mono'}
    paths = [p for r in recipes for p in c.font_paths(r).values()]
    assert len(set(paths)) == 8
    assert all(p.parent.name == r['id'] for r in recipes for p in c.font_paths(r).values())
    for r in recipes:
        assert c.load_recipe(r['id']) == r


def test_source_integrity_is_checked_before_consumption(tmp_path):
    c = catalog()
    source = tmp_path / 'font.ttf'
    source.write_bytes(b'original')
    manifest = tmp_path / 'manifest.json'
    manifest.write_text(json.dumps({'schema_version': 1, 'sources': {'fixture': {'license': 'OFL-1.1', 'files': {'Regular': {'path': 'font.ttf', 'sha256': hashlib.sha256(b'original').hexdigest()}}}}}))
    assert c.source_path('fixture', 'Regular', manifest_path=manifest, root=tmp_path) == source
    source.write_bytes(b'tampered')
    with pytest.raises(ValueError, match='SHA256'):
        c.source_path('fixture', 'Regular', manifest_path=manifest, root=tmp_path)


def test_private_sources_only_resolve_from_local_mapping(tmp_path):
    c = catalog()
    source = tmp_path / 'private.ttf'
    source.write_bytes(b'private')
    manifest = tmp_path / 'manifest.json'
    manifest.write_text(json.dumps({'schema_version': 1, 'sources': {}}))
    local = tmp_path / 'local.json'
    local.write_text(json.dumps({'sources': {'private-test': {'Regular': str(source)}}}))
    assert c.source_path('private-test', 'Regular', manifest_path=manifest, local_path=local) == source
    with pytest.raises(ValueError, match='Unknown source'):
        c.source_path('private-test', 'Regular', manifest_path=manifest, local_path=tmp_path/'absent.json')


def test_recipe_rejects_unknown_fields_and_traversal(tmp_path):
    c = catalog()
    recipe = c.load_recipe('firacode-sarasa')
    recipe['id'] = '../escape'
    path = tmp_path / 'bad.json'
    path.write_text(json.dumps(recipe))
    with pytest.raises(ValueError):
        c.load_recipe(path)
