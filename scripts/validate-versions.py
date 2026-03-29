#!/usr/bin/env python3
"""Valida consistencia de versoes entre marketplace.json e plugin.json.

Compara a versao declarada em .claude-plugin/marketplace.json com a versao
em cada plugins/{name}/.claude-plugin/plugin.json. Falha com exit code 1
se houver inconsistencias.

Uso:
    python scripts/validate-versions.py
    python scripts/validate-versions.py --fix  # corrige marketplace.json automaticamente
"""
import json
import sys
from pathlib import Path


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

    # Also check CHANGELOG has entry for current version
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
        print(f'\nFixed {fixes_applied} version(s) in marketplace.json')

    if errors:
        print('\nVERSION MISMATCHES FOUND:')
        for err in errors:
            print(err)
        print('\nRun "python scripts/validate-versions.py --fix" to auto-fix marketplace.json')
        sys.exit(1)
    else:
        print('\nAll versions consistent.')


if __name__ == '__main__':
    main()
