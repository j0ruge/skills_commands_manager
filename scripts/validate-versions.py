#!/usr/bin/env python3
"""Valida consistencia de versoes e metadados entre marketplace.json e plugin.json.

Verificacoes realizadas (na ordem em que rodam):
  1. Versao em marketplace.json == versao em plugin.json  (com --fix corrige marketplace.json)
  2. plugin.json possui campo 'platforms' como lista nao-vazia com valores validos
  3. Campo 'platforms' em marketplace.json e plugin.json sao identicos
  4. Plugins com 'cursor' em platforms tem ao menos uma entrada em CURSOR_SKILL_MAP (install.py)
  5. CHANGELOG.md de cada plugin contem entrada para a versao atual

Uso:
    python scripts/validate-versions.py
    python scripts/validate-versions.py --fix  # corrige marketplace.json automaticamente
"""
import importlib.util
import json
import sys
from pathlib import Path

VALID_PLATFORMS = {'claude-code', 'cursor'}


def _load_cursor_skill_map(repo_root: Path) -> list[dict] | None:
    """Import install.py and return CURSOR_SKILL_MAP. Returns None if install.py is absent."""
    install_py = repo_root / 'install.py'
    if not install_py.exists():
        return None
    spec = importlib.util.spec_from_file_location('install', install_py)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, 'CURSOR_SKILL_MAP', None)


def main():
    fix_mode = '--fix' in sys.argv
    repo_root = Path(__file__).resolve().parent.parent

    marketplace_path = repo_root / '.claude-plugin' / 'marketplace.json'
    if not marketplace_path.exists():
        print('ERROR: .claude-plugin/marketplace.json not found')
        sys.exit(1)

    marketplace = json.loads(marketplace_path.read_text(encoding='utf-8'))
    plugins = marketplace.get('plugins', [])

    errors = []
    fixes_applied = 0

    for entry in plugins:
        name = entry.get('name', '?')
        marketplace_version = entry.get('version', '?')

        plugin_json_path = repo_root / 'plugins' / name / '.claude-plugin' / 'plugin.json'
        if not plugin_json_path.exists():
            errors.append(f'  {name}: plugin.json not found at {plugin_json_path}')
            continue

        plugin_data = json.loads(plugin_json_path.read_text(encoding='utf-8'))
        plugin_version = plugin_data.get('version', '?')

        # Check 1: version consistency
        if marketplace_version != plugin_version:
            if fix_mode:
                entry['version'] = plugin_version
                fixes_applied += 1
                print(f'  FIXED {name}: marketplace {marketplace_version} -> {plugin_version}')
            else:
                errors.append(
                    f'  {name}: marketplace.json={marketplace_version} '
                    f'!= plugin.json={plugin_version}'
                )
        else:
            print(f'  OK {name}: v{plugin_version}')

        # Check 2: platforms field in plugin.json
        plugin_platforms = plugin_data.get('platforms')
        platforms_valid = False
        if plugin_platforms is None:
            errors.append(f'  {name}: plugin.json missing "platforms" field')
        elif not isinstance(plugin_platforms, list):
            errors.append(
                f'  {name}: plugin.json "platforms" must be a list '
                f'(got {type(plugin_platforms).__name__})'
            )
        elif not plugin_platforms:
            errors.append(f'  {name}: plugin.json "platforms" must be a non-empty array')
        else:
            invalid = set(plugin_platforms) - VALID_PLATFORMS
            if invalid:
                errors.append(
                    f'  {name}: plugin.json "platforms" contains invalid values: {sorted(invalid)}'
                    f' (valid: {sorted(VALID_PLATFORMS)})'
                )
            else:
                platforms_valid = True

        # Check 3: platforms consistency between marketplace.json and plugin.json
        marketplace_platforms = entry.get('platforms')
        if platforms_valid and marketplace_platforms is not None:
            if not isinstance(marketplace_platforms, list):
                errors.append(
                    f'  {name}: marketplace.json "platforms" must be a list '
                    f'(got {type(marketplace_platforms).__name__})'
                )
            elif sorted(marketplace_platforms) != sorted(plugin_platforms):
                if fix_mode:
                    entry['platforms'] = plugin_platforms
                    fixes_applied += 1
                    print(
                        f'  FIXED {name}: marketplace platforms '
                        f'{marketplace_platforms} -> {plugin_platforms}'
                    )
                else:
                    errors.append(
                        f'  {name}: marketplace.json platforms={marketplace_platforms} '
                        f'!= plugin.json platforms={plugin_platforms}'
                    )
        elif platforms_valid and marketplace_platforms is None:
            errors.append(
                f'  {name}: marketplace.json missing "platforms" field '
                f'(plugin.json has {plugin_platforms})'
            )

    # Check 5: every plugin with 'cursor' in platforms has at least one entry in CURSOR_SKILL_MAP
    cursor_skill_map = _load_cursor_skill_map(repo_root)
    if cursor_skill_map is not None:
        mapped_plugins = {entry.get('plugin') for entry in cursor_skill_map}
        for entry in plugins:
            name = entry.get('name', '?')
            plugin_json_path = repo_root / 'plugins' / name / '.claude-plugin' / 'plugin.json'
            if not plugin_json_path.exists():
                continue
            plugin_data = json.loads(plugin_json_path.read_text(encoding='utf-8'))
            plugin_platforms = plugin_data.get('platforms') or []
            if 'cursor' in plugin_platforms and name not in mapped_plugins:
                errors.append(
                    f'  {name}: declares "cursor" in platforms but has no entry in '
                    f'CURSOR_SKILL_MAP (install.py) — Cursor users will not see this plugin'
                )

    # Check 4: CHANGELOG has entry for current version
    for entry in plugins:
        name = entry.get('name', '?')
        plugin_json_path = repo_root / 'plugins' / name / '.claude-plugin' / 'plugin.json'
        if not plugin_json_path.exists():
            continue

        plugin_data = json.loads(plugin_json_path.read_text(encoding='utf-8'))
        plugin_version = plugin_data.get('version', '?')

        changelog_path = repo_root / 'plugins' / name / 'CHANGELOG.md'
        if changelog_path.exists():
            changelog = changelog_path.read_text(encoding='utf-8')
            if f'[{plugin_version}]' not in changelog:
                errors.append(
                    f'  {name}: CHANGELOG.md missing entry for v{plugin_version}'
                )

    if fix_mode and fixes_applied > 0:
        marketplace_path.write_text(
            json.dumps(marketplace, indent=2, ensure_ascii=False) + '\n',
            encoding='utf-8',
        )
        print(f'\nFixed {fixes_applied} field(s) in marketplace.json')

    if errors:
        print('\nVALIDATION ERRORS FOUND:')
        for err in errors:
            print(err)
        print('\nRun "python scripts/validate-versions.py --fix" to auto-fix marketplace.json')
        sys.exit(1)
    else:
        print('\nAll checks passed.')


if __name__ == '__main__':
    main()
