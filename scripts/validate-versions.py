#!/usr/bin/env python3
"""Valida consistencia de versoes e metadados entre marketplace.json e plugin.json.

Verificacoes (na ordem em que rodam):
  1. Versao em marketplace.json == versao em plugin.json
  2. plugin.json possui campo 'platforms' como lista nao-vazia com valores validos
  3. Campo 'platforms' em marketplace.json e plugin.json sao identicos
  4. Plugins com 'cursor' em platforms tem ao menos uma entrada em CURSOR_SKILL_MAP (install.py)
  5. CHANGELOG.md de cada plugin contem entrada para a versao atual ([x.y.z], com colchetes)
  6. 'description' identica em SKILL.md, plugin.json e marketplace.json (+ aviso de tamanho)

Por que a verificacao 6 existe: a description e a UNICA superficie de triggering do
plugin -- e por ela (mais o nome) que o agente decide invocar a skill. Como ela e
duplicada em tres arquivos e nada comparava os tres, elas driftaram: numa auditoria de
2026-08-08, 5 dos 10 plugins com skill tinham tres textos diferentes, um deles com 813
chars no SKILL.md contra 2541 no plugin.json (a description havia virado changelog).
O efeito e pior que cosmetico: o comportamento de triggering passa a depender de QUAL
arquivo o harness le. A fonte canonica e o SKILL.md, porque e a que o Claude Code le
para decidir sobre a skill; para plugins commands-only (sem SKILL.md) a canonica e o
plugin.json e a comparacao cai para dois arquivos.

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

# Tetos vindos do CLAUDE.md deste repo ("Skill description guidelines"): alvo 350, cap
# duro 500. Nao sao numeros inventados aqui -- a politica ja estava escrita e nada a
# media, e foi assim que uma description chegou a 2541 chars. O motivo do cap: quando o
# somatorio das descriptions passa do `skillListingBudgetFraction` do Claude Code, elas
# sao DESCARTADAS em silencio e as skills perdem o trigger.
# Sai como aviso, nao erro: encurtar e decisao de conteudo, e falhar o gate por divida
# pre-existente travaria todo commit do repo sem relacao com a mudanca em curso.
DESCRIPTION_TARGET_CHARS = 350
DESCRIPTION_MAX_CHARS = 500

_CHANGELOG_VER_RE = re.compile(r'\[(\d+\.\d+\.\d+)\]')
_FRONTMATTER_RE = re.compile(r'^---\r?\n(.*?)\r?\n---\r?\n', re.DOTALL)


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


def _read_skill_description(repo_root: Path, name: str) -> 'tuple[str | None, str]':
    """Le a description do frontmatter de plugins/<name>/skills/<name>/SKILL.md.

    Retorna (description, status). status e um de:
      'ok'             -> description lida com confianca
      'no-skill'       -> plugin sem SKILL.md (commands-only); nao e erro
      'no-frontmatter' -> SKILL.md existe mas nao tem bloco --- ... ---
      'yaml-error'     -> frontmatter presente mas nao e YAML valido
      'no-description' -> frontmatter sem a chave description
      'no-yaml'        -> pyyaml ausente; a leitura foi PULADA de proposito

    Sobre 'yaml-error': a causa recorrente e uma description SEM ASPAS contendo `: `
    (dois-pontos + espaco), como em "...auto-routed by stack: Node...". Em YAML isso
    abre um mapeamento aninhado e o arquivo inteiro fica invalido. Parsers lenientes
    (inclusive o do proprio Claude Code) engolem, entao a skill funciona e o defeito
    fica latente ate um consumidor estrito aparecer. Cura: envolver o valor em aspas
    duplas -- muda a sintaxe, nao o valor.

    Sobre 'no-yaml': o valor pode ser um escalar YAML entre aspas (varias skills usam
    "..." e uma delas contem `C:\\Users` com backslash escapado). Um regex ingenuo
    devolve o texto COM as aspas e COM o escape, o que produz divergencia falsa -- foi
    exatamente o que aconteceu na auditoria manual que motivou esta verificacao, que
    acusou 7 plugins quando apenas 5 divergiam. Reimplementar o unescape do YAML a mao
    e a mesma classe de dividia (normalizacao pareada) que a checagem tenta evitar, por
    isso o parse e delegado ao pyyaml e, na ausencia dele, a comparacao com o SKILL.md
    e pulada com aviso VISIVEL em vez de rodar sobre um parse duvidoso.
    """
    skill_path = repo_root / 'plugins' / name / 'skills' / name / 'SKILL.md'
    if not skill_path.exists():
        return None, 'no-skill'
    try:
        import yaml  # opcional: nao e dependencia do resto do script
    except ImportError:
        return None, 'no-yaml'
    m = _FRONTMATTER_RE.match(skill_path.read_text(encoding='utf-8'))
    if not m:
        return None, 'no-frontmatter'
    try:
        data = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return None, 'yaml-error'
    desc = data.get('description')
    if not isinstance(desc, str):
        return None, 'no-description'
    return desc.strip(), 'ok'


def _set_plugin_description(plugin_json_path: Path, new_desc: str) -> None:
    repl = '"description": ' + json.dumps(new_desc, ensure_ascii=False)
    pat = re.compile(r'"description":\s*"(?:[^"\\]|\\.)*"')
    _replace_once(plugin_json_path, pat, lambda _m: repl, 'plugin.json description')


def _set_marketplace_description(marketplace_path: Path, name: str, new_desc: str) -> None:
    """Escopa a substituicao ao bloco do plugin alvo.

    Um match solto em `"description":` atinge as 16 entradas do arquivo e sobrescreve
    todas com o mesmo texto, por isso a ancora inclui name/source/version -- a mesma
    tecnica de _set_marketplace_version.
    """
    repl_tail = '"description": ' + json.dumps(new_desc, ensure_ascii=False)
    pat = re.compile(
        r'("name":\s*"' + re.escape(name) + r'",\s*"source":\s*"[^"]*",\s*'
        r'"version":\s*"[^"]*",\s*)"description":\s*"(?:[^"\\]|\\.)*"'
    )
    _replace_once(
        marketplace_path, pat, lambda m: m.group(1) + repl_tail,
        f'marketplace.json description for {name}',
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
    warnings = []
    notes = []
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

    # Check 6: description is identical across SKILL.md, plugin.json and marketplace.json
    yaml_missing_reported = False
    for entry in plugins:
        name = entry.get('name', '?')
        plugin_json_path = repo_root / 'plugins' / name / '.claude-plugin' / 'plugin.json'
        if not plugin_json_path.exists():
            continue

        plugin_desc = json.loads(plugin_json_path.read_text(encoding='utf-8')).get('description')
        marketplace_desc = entry.get('description')
        skill_desc, status = _read_skill_description(repo_root, name)

        if status == 'no-yaml':
            if not yaml_missing_reported:
                notes.append(
                    '  description check: pyyaml ausente -> a comparacao com SKILL.md foi '
                    'PULADA (plugin.json vs marketplace.json segue valendo). '
                    'Instale pyyaml para o gate completo: pip install pyyaml'
                )
                yaml_missing_reported = True
        elif status == 'yaml-error':
            errors.append(
                f'  {name}: o frontmatter do SKILL.md nao e YAML valido -- causa tipica e '
                f'uma description SEM ASPAS contendo ": " (ex.: "by stack: Node"), que em '
                f'YAML abre um mapeamento aninhado. Envolva o valor em aspas duplas '
                f'(muda a sintaxe, nao o valor). Enquanto isso a description desta skill '
                f'fica FORA do gate de espelhamento'
            )
        elif status in ('no-frontmatter', 'no-description'):
            warnings.append(f'  {name}: SKILL.md existe mas {status} -- description nao verificavel')

        # Canonica: SKILL.md quando existe (e o que o Claude Code le para decidir sobre a
        # skill); plugin.json para plugins commands-only.
        canonical = skill_desc if status == 'ok' else plugin_desc
        source = 'SKILL.md' if status == 'ok' else 'plugin.json'

        if canonical is None:
            errors.append(f'  {name}: nenhuma description encontrada (nem SKILL.md nem plugin.json)')
            continue

        divergentes = []
        if status == 'ok' and plugin_desc != canonical:
            divergentes.append(('plugin.json', plugin_desc))
        if marketplace_desc != canonical:
            divergentes.append(('marketplace.json', marketplace_desc))

        if divergentes:
            if fix_mode:
                for arquivo, _ in divergentes:
                    if arquivo == 'plugin.json':
                        _set_plugin_description(plugin_json_path, canonical)
                    else:
                        _set_marketplace_description(marketplace_path, name, canonical)
                    fixes_applied += 1
                print(f'  FIXED {name}: description <- {source} '
                      f'({len(canonical)} chars) em {", ".join(a for a, _ in divergentes)}')
            else:
                detalhe = '; '.join(
                    f'{a}={len(v) if v is not None else "ausente"} chars' for a, v in divergentes
                )
                errors.append(
                    f'  {name}: description divergente -- {source}={len(canonical)} chars '
                    f'vs {detalhe}. A description e a superficie de triggering; textos '
                    f'diferentes fazem o comportamento depender do arquivo que o harness le'
                )

        if len(canonical) > DESCRIPTION_MAX_CHARS:
            warnings.append(
                f'  {name}: description tem {len(canonical)} chars -- acima do cap duro '
                f'de {DESCRIPTION_MAX_CHARS} do CLAUDE.md (alvo {DESCRIPTION_TARGET_CHARS}). '
                f'Encurte em vez de somar: detalhe vai para o corpo da skill e o CHANGELOG'
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

    # Notes e warnings saem SEMPRE, inclusive num run verde: um gate pulado que nao se
    # anuncia e indistinguivel de um gate que passou.
    if notes:
        print('\nNOTES:')
        for n in notes:
            print(n)

    if warnings:
        print('\nWARNINGS (nao falham o gate):')
        for w in warnings:
            print(w)

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
