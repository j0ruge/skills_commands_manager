#!/usr/bin/env python3
"""Valida consistencia de versoes e metadados entre marketplace.json e plugin.json.

Verificacoes (na ordem em que rodam):
  1. Versao em marketplace.json == versao em plugin.json
  2. plugin.json possui campo 'platforms' como lista nao-vazia com valores validos
  3. Campo 'platforms' em marketplace.json e plugin.json sao identicos
  4. Plugins com 'cursor' em platforms tem ao menos uma entrada em CURSOR_SKILL_MAP (install.py)
  5. CHANGELOG.md de cada plugin contem entrada para a versao atual ([x.y.z], com colchetes)

Modo --fix (correcao automatica, PRESERVANDO a formatacao do arquivo):
  - Mismatch de versao: NAO copia cegamente o plugin.json para o marketplace. Decide a
    versao verdadeira pelo header [x.y.z] mais recente do CHANGELOG do plugin (o lado que
    NAO bate com o CHANGELOG e o stale) e corrige esse lado. Se o CHANGELOG nao desempata,
    cai para o maior semver e marca o fix como HEURISTIC (confirme a mao). Se nem isso for
    possivel, NAO corrige e reporta como erro.
    Motivacao: o --fix antigo fazia marketplace <- plugin.json sempre, rebaixando o
    marketplace quando o stale era o plugin.json (caso comum de bump propagado pela metade).
  - Mismatch de platforms: alinha o marketplace ao plugin.json.
  As escritas usam substituicao textual dirigida (regex), NAO json.dumps, para nao
  reformatar o arquivo (arrays inline de keywords/platforms permanecem intactos).

Uso:
    python scripts/validate-versions.py
    python scripts/validate-versions.py --fix
"""
import importlib.util
import json
import re
import sys
from pathlib import Path

VALID_PLATFORMS = {'claude-code', 'cursor'}

_CHANGELOG_VER_RE = re.compile(r'\[(\d+\.\d+\.\d+)\]')


def _parse_semver(v: str | None) -> tuple[int, int, int] | None:
    m = re.fullmatch(r'\s*(\d+)\.(\d+)\.(\d+)\s*', v or '')
    return tuple(int(x) for x in m.groups()) if m else None


def _latest_changelog_version(changelog_path: Path) -> str | None:
    """Topmost [x.y.z] em um CHANGELOG (changelogs sao cronologia reversa), ou None."""
    if not changelog_path.exists():
        return None
    m = _CHANGELOG_VER_RE.search(changelog_path.read_text(encoding='utf-8'))
    return m.group(1) if m else None


def _resolve_true_version(
    marketplace_version: str, plugin_version: str, changelog_path: Path
) -> tuple[str | None, str, bool]:
    """Decide a versao autoritativa para um mismatch.

    Retorna (truth, reason, confident). truth e None quando indecidivel.
    """
    cl = _latest_changelog_version(changelog_path)
    if cl in (marketplace_version, plugin_version):
        stale = 'plugin.json' if cl == marketplace_version else 'marketplace.json'
        return cl, f'CHANGELOG top [{cl}] -> {stale} esta stale', True
    mv, pv = _parse_semver(marketplace_version), _parse_semver(plugin_version)
    if mv and pv and mv != pv:
        higher = marketplace_version if mv > pv else plugin_version
        return higher, f'maior semver {higher} (CHANGELOG nao desempatou)', False
    return None, 'impossivel determinar a versao correta pelo CHANGELOG ou semver', False


def _replace_once(path: Path, pattern: 're.Pattern', repl, label: str) -> None:
    text = path.read_text(encoding='utf-8')
    new_text, n = pattern.subn(repl, text, count=1)
    if n != 1:
        raise RuntimeError(f'{label}: esperava exatamente 1 substituicao, fez {n} em {path}')
    path.write_text(new_text, encoding='utf-8')


def _set_plugin_version(plugin_json_path: Path, old: str, new: str) -> None:
    pat = re.compile(r'("version":\s*")' + re.escape(old) + r'(")')
    _replace_once(plugin_json_path, pat, r'\g<1>' + new + r'\g<2>', 'plugin.json version')


def _set_marketplace_version(marketplace_path: Path, name: str, old: str, new: str) -> None:
    pat = re.compile(
        r'("name":\s*"' + re.escape(name) + r'",\s*"source":\s*"[^"]*",\s*"version":\s*")'
        + re.escape(old) + r'(")'
    )
    _replace_once(
        marketplace_path, pat, r'\g<1>' + new + r'\g<2>',
        f'marketplace.json version for {name}',
    )


def _set_marketplace_platforms(marketplace_path: Path, name: str, new_list: list) -> None:
    new_json = json.dumps(new_list)
    pat = re.compile(
        r'("name":\s*"' + re.escape(name) + r'".*?"platforms":\s*)\[[^\]]*\]',
        re.DOTALL,
    )
    _replace_once(
        marketplace_path, pat, lambda m: m.group(1) + new_json,
        f'marketplace.json platforms for {name}',
    )


def _load_cursor_skill_map(repo_root: Path) -> 'list[dict] | None':
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

        # Check 1: version consistency — CHANGELOG-aware, never blind-copies a stale value
        if marketplace_version != plugin_version:
            changelog_path = repo_root / 'plugins' / name / 'CHANGELOG.md'
            truth, reason, confident = _resolve_true_version(
                marketplace_version, plugin_version, changelog_path
            )
            if fix_mode and truth is not None:
                if marketplace_version != truth:
                    _set_marketplace_version(marketplace_path, name, marketplace_version, truth)
                if plugin_version != truth:
                    _set_plugin_version(plugin_json_path, plugin_version, truth)
                    plugin_version = truth
                fixes_applied += 1
                flag = '' if confident else '  [HEURISTIC — confirm manually]'
                print(f'  FIXED {name}: -> v{truth} ({reason}){flag}')
            else:
                cl = _latest_changelog_version(changelog_path)
                hint = f'; suggested truth: v{truth} ({reason})' if truth else ''
                errors.append(
                    f'  {name}: marketplace.json={marketplace_version} '
                    f'!= plugin.json={plugin_version} (CHANGELOG top={cl}){hint}'
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
                    _set_marketplace_platforms(marketplace_path, name, plugin_platforms)
                    fixes_applied += 1
                    print(f'  FIXED {name}: marketplace platforms -> {plugin_platforms}')
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
        print(f'\nApplied {fixes_applied} format-preserving fix(es).')

    if errors:
        print('\nVALIDATION ERRORS FOUND:')
        for err in errors:
            print(err)
        if not fix_mode:
            print(
                '\nRun "python scripts/validate-versions.py --fix" to auto-fix '
                '(version mismatches are resolved via the CHANGELOG, not by copying blindly).'
            )
        sys.exit(1)
    else:
        print('\nAll checks passed.')


if __name__ == '__main__':
    main()
