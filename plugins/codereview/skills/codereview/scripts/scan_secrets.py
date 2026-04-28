#!/usr/bin/env python3
"""
scan_secrets.py — varredura determinística de secrets contra um unified diff.

Implementa o catálogo de pass 6.10 ("Hardcoded Secrets Detection") da skill
codereview como código real (não como prosa para LLM simular). Saída JSON em
stdout consumível pelo haiku agent em Phase A.

Uso:
    git diff <base>...HEAD --unified=0 | python3 scan_secrets.py
    python3 scan_secrets.py --diff /tmp/some.diff
    python3 scan_secrets.py --base origin/main           # roda git diff sozinho

Exit code:
    0  sempre (achou ou não — gate é decisão do Phase C, ver SKILL.md)

Saída:
    JSON em stdout: { "findings": [...], "scanners": [...], "errors": [...] }

    findings[i] = {
        "file":     "packages/idp/test/integration/operators.int.test.ts",
        "line":     112,
        "kind":     "Generic Password",
        "snippet":  "initialPassword: '***'",   # MASCARADO sempre
        "severity": "HIGH" | "CRITICAL",
        "source":   "regex" | "ggshield" | "gitleaks"
    }
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from typing import Iterable


# ---------------------------------------------------------------------------
# Catálogo de regex — single source of truth para pass 6.10.
#
# Mantenha este catálogo sincronizado com `references/detection-passes.md`.
# Mudou um? Mude o outro. Adicione um teste de smoke quando incluir um novo.
# ---------------------------------------------------------------------------

# Cada entrada: (kind, pattern, severity_default).
# severity_default = "CRITICAL" salvo nuance test-file (decisão pós-match).
PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "Generic Password",
        # Aceita keyword com ou sem prefixo (ex.: `initialPassword:` casa via
        # `password` ao final). Aceita `:`, `=` ou `:=`. Valor entre aspas
        # com 4+ chars. ASCII-insensitive via flag IGNORECASE.
        re.compile(
            r"(?P<kw>[A-Za-z_]*(?:password|passwd|pwd|senha|secret|api[_\-]?key|"
            r"apikey|access[_\-]?token|auth[_\-]?token|client[_\-]?secret))"
            r"\s*[:=]\s*"
            r"(?P<val>[\"'][^\"'\n]{4,}[\"'])",
            re.IGNORECASE,
        ),
        "CRITICAL",
    ),
    (
        "JWT Token",
        re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+"),
        "CRITICAL",
    ),
    (
        "Bearer Token",
        re.compile(r"Bearer\s+(?P<val>[A-Za-z0-9_\-\.]{20,})"),
        "CRITICAL",
    ),
    (
        "PEM Private Key",
        re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA |PGP )?PRIVATE KEY-----"),
        "CRITICAL",
    ),
    (
        "AWS Access Key ID",
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        "CRITICAL",
    ),
    (
        "AWS Secret Access Key",
        re.compile(r"aws_secret_access_key\s*[:=]\s*[\"'][^\"']{20,}[\"']", re.IGNORECASE),
        "CRITICAL",
    ),
    (
        "Google API Key",
        re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"),
        "CRITICAL",
    ),
    (
        "Slack Token",
        re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}\b"),
        "CRITICAL",
    ),
    (
        "GitHub Token",
        re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
        "CRITICAL",
    ),
    (
        "Credentialed Connection String",
        # postgres://user:pwd@host — ":pwd@" é o tell. Captura a parte da senha
        # para podermos mascarar no snippet.
        re.compile(
            r"\b(?P<scheme>postgres|postgresql|mysql|mongodb(?:\+srv)?|redis|amqp)"
            r"://(?P<user>[^:@/\s]+):(?P<pwd>[^@/\s]+)@",
            re.IGNORECASE,
        ),
        "CRITICAL",
    ),
    (
        "Stripe Secret Key",
        re.compile(r"\bsk_(?:live|test)_[A-Za-z0-9]{20,}\b"),
        "CRITICAL",
    ),
    (
        "Env Assignment",
        # Linha com SHAPE de `.env`: KEY=VALUE em arquivos não-template/example.
        # Verificamos o nome do arquivo na fase de filtering.
        re.compile(
            r"^(?P<key>SECRET_KEY|DATABASE_URL|API_KEY|JWT_SECRET|PRIVATE_KEY|"
            r"CLIENT_SECRET|AUTH_TOKEN)\s*=\s*(?P<val>\S.+)$"
        ),
        "CRITICAL",
    ),
]


# Valores que NUNCA viram finding (placeholders e lookups de runtime).
PLACEHOLDER_TOKENS = {
    "",
    "null",
    "undefined",
    "none",
    "change_me",
    "changeme",
    "xxx",
    "***",
    "redacted",
    "your-key-here",
    "replace_me",
    "example",
    "todo",
    "tbd",
}

ENV_LOOKUP_PATTERNS = [
    re.compile(r"\bprocess\.env\.[A-Z][A-Z0-9_]*"),
    re.compile(r"\bimport\.meta\.env\.[A-Z][A-Z0-9_]*"),
    re.compile(r"\bDeno\.env\.get\b"),
    re.compile(r"\bos\.environ\b"),
    re.compile(r"\bos\.getenv\b"),
    re.compile(r"\bConfigurationManager\.AppSettings\b"),
    re.compile(r"\bconfig\.get\s*\(", re.IGNORECASE),
    re.compile(r"\bgetenv\s*\("),
    re.compile(r"\bsecrets?\.get\s*\(", re.IGNORECASE),
]

# Caminhos onde placeholder values são esperados — não disparar Env Assignment
# nem Generic Password se o valor parecer placeholder.
ENV_TEMPLATE_FILE_PATTERNS = [
    re.compile(r"(^|/)\.env\.(example|sample|template|dist)$"),
    re.compile(r"(^|/)\.env-example$"),
]


# ---------------------------------------------------------------------------
# Estruturas de dados.
# ---------------------------------------------------------------------------


@dataclass
class Finding:
    file: str
    line: int
    kind: str
    snippet: str
    severity: str
    source: str = "regex"


@dataclass
class ScanResult:
    findings: list[Finding] = field(default_factory=list)
    scanners: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(
            {
                "findings": [asdict(f) for f in self.findings],
                "scanners": self.scanners,
                "errors": self.errors,
            },
            ensure_ascii=False,
            indent=2,
        )


# ---------------------------------------------------------------------------
# Heurísticas auxiliares.
# ---------------------------------------------------------------------------


def is_env_template_file(path: str) -> bool:
    """`.env.example`/`.env.sample`/`.env.template` aceitam placeholders."""
    return any(p.search(path) for p in ENV_TEMPLATE_FILE_PATTERNS)


def is_test_file(path: str) -> bool:
    return bool(
        re.search(r"(^|/)(__tests__|tests?)/", path)
        or re.search(r"\.(test|spec|int\.test|int\.spec)\.[a-zA-Z]+$", path)
        or path.startswith("test/")
    )


def looks_like_placeholder(raw_value: str) -> bool:
    """Decide se o valor citado é um placeholder/lookup.

    Recebe o valor já com aspas removidas (ou sem aspas para Env Assignment).
    """
    v = raw_value.strip().strip("\"'").lower()
    if v in PLACEHOLDER_TOKENS:
        return True
    if v.startswith("<") and v.endswith(">"):
        return True
    # Templates ${VAR}, ${VAR:?...}, ${VAR:-default} são env-substitution, não literal.
    if v.startswith("${") and v.endswith("}"):
        return True
    return False


def line_has_env_lookup(full_line: str) -> bool:
    return any(p.search(full_line) for p in ENV_LOOKUP_PATTERNS)


def mask_snippet(line: str, value_start: int, value_end: int, max_len: int = 120) -> str:
    """Mascara o intervalo do valor com `***`. Trunca para `max_len`."""
    masked = line[:value_start] + "***" + line[value_end:]
    masked = masked.strip()
    if len(masked) > max_len:
        masked = masked[: max_len - 3] + "..."
    return masked


# ---------------------------------------------------------------------------
# Parser de unified diff.
# ---------------------------------------------------------------------------


_HUNK_HEADER_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(?P<new>\d+)(?:,\d+)? @@")
_FILE_HEADER_RE = re.compile(r"^\+\+\+ b/(?P<path>.+)$")
_DEV_NULL_RE = re.compile(r"^\+\+\+ /dev/null\s*$")


def iter_added_lines(diff_text: str) -> Iterable[tuple[str, int, str]]:
    """Itera (file_path, line_no_in_new_file, content) para cada `+` line.

    Ignora cabeçalhos (`+++`, `---`) e contexto. Mantém line_no atualizado
    via parsing de `@@ -a,b +c,d @@` headers.
    """
    current_file: str | None = None
    new_lineno = 0

    for raw in diff_text.splitlines():
        # Cabeçalho de novo arquivo? Atualiza file ativo.
        m_file = _FILE_HEADER_RE.match(raw)
        if m_file:
            current_file = m_file.group("path")
            continue
        if _DEV_NULL_RE.match(raw):
            current_file = None
            continue

        # Cabeçalho de hunk? Reseta line counter.
        m_hunk = _HUNK_HEADER_RE.match(raw)
        if m_hunk:
            new_lineno = int(m_hunk.group("new")) - 1  # -1 porque incrementamos antes de yield
            continue

        if current_file is None:
            continue

        # Linha de código.
        if raw.startswith("+++") or raw.startswith("---"):
            continue
        if raw.startswith("+"):
            new_lineno += 1
            yield current_file, new_lineno, raw[1:]
        elif raw.startswith(" "):
            new_lineno += 1
        # `-` lines: não incrementam new_lineno.


# ---------------------------------------------------------------------------
# Pipeline de scan.
# ---------------------------------------------------------------------------


def scan_diff(diff_text: str) -> ScanResult:
    result = ScanResult()
    result.scanners.append("regex")

    # Agregação por (file, kind) para detectar systemic leaks (3+ no mesmo file
    # ou 5+ no PR inteiro → escala para CRITICAL).
    per_file_counts: dict[tuple[str, str], int] = {}
    per_kind_counts: dict[str, int] = {}

    for path, lineno, content in iter_added_lines(diff_text):
        # Generic Password / Env Assignment / Bearer / etc.
        for kind, pattern, sev_default in PATTERNS:
            for match in pattern.finditer(content):
                # ----- exceções -----
                if line_has_env_lookup(content):
                    continue

                # Decide se o valor é placeholder.
                if "val" in match.groupdict() and match.group("val") is not None:
                    raw_val = match.group("val")
                else:
                    raw_val = match.group(0)

                if looks_like_placeholder(raw_val):
                    continue

                # `.env.example` etc. NUNCA disparam Env Assignment / Generic
                # Password — mesmo que o valor não pareça placeholder, o
                # arquivo é template, conteúdo é exemplo por contrato.
                if is_env_template_file(path):
                    continue

                # ----- severity calibration -----
                severity = sev_default
                if kind == "Generic Password" and is_test_file(path):
                    severity = "HIGH"  # test-file nuance do pass 6.10

                # ----- snippet mascarado -----
                # Se temos grupo "val" com aspas, mascara só o conteúdo.
                if "val" in match.groupdict() and match.group("val"):
                    val_span = match.span("val")
                    snippet = mask_snippet(content, val_span[0], val_span[1])
                elif "pwd" in match.groupdict() and match.group("pwd"):
                    pwd_span = match.span("pwd")
                    snippet = mask_snippet(content, pwd_span[0], pwd_span[1])
                else:
                    span = match.span()
                    snippet = mask_snippet(content, span[0], span[1])

                result.findings.append(
                    Finding(
                        file=path,
                        line=lineno,
                        kind=kind,
                        snippet=snippet,
                        severity=severity,
                    )
                )
                per_file_counts[(path, kind)] = per_file_counts.get((path, kind), 0) + 1
                per_kind_counts[kind] = per_kind_counts.get(kind, 0) + 1

    # ----- multi-occurrence escalation -----
    # 3+ matches do mesmo (file, kind) → escala todos para CRITICAL.
    # 5+ no PR inteiro de um mesmo kind → idem.
    files_to_escalate = {
        (file, kind) for (file, kind), n in per_file_counts.items() if n >= 3
    }
    kinds_to_escalate = {kind for kind, n in per_kind_counts.items() if n >= 5}

    if files_to_escalate or kinds_to_escalate:
        for f in result.findings:
            if (f.file, f.kind) in files_to_escalate or f.kind in kinds_to_escalate:
                f.severity = "CRITICAL"

    return result


# ---------------------------------------------------------------------------
# Scanners externos (ggshield / gitleaks) — opcionais, fundem se presentes.
# ---------------------------------------------------------------------------


def run_ggshield(repo_root: str, result: ScanResult) -> None:
    """Roda ggshield se instalado; funde findings."""
    if not shutil.which("ggshield"):
        return
    try:
        proc = subprocess.run(
            ["ggshield", "secret", "scan", "path", repo_root, "--json"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if proc.returncode not in (0, 1):  # 1 = findings, 0 = clean
            result.errors.append(f"ggshield exit {proc.returncode}: {proc.stderr.strip()[:200]}")
            return
        data = json.loads(proc.stdout) if proc.stdout.strip() else {}
        result.scanners.append("ggshield")
        # Estrutura ggshield JSON: {"entities_with_incidents": [{"filename", "incidents": [...]}]}
        for entity in data.get("entities_with_incidents", []):
            file_path = entity.get("filename", "<unknown>")
            for incident in entity.get("incidents", []):
                kind = incident.get("type", "ggshield-finding")
                # ggshield retorna line/match em occurrences
                for occ in incident.get("occurrences", []):
                    line = occ.get("line_start", 0)
                    matches = occ.get("matches", [])
                    snippet_match = matches[0].get("match", "") if matches else ""
                    # Mascara se vier valor real
                    if snippet_match:
                        snippet = f"{kind}: ***"
                    else:
                        snippet = kind
                    result.findings.append(
                        Finding(
                            file=file_path,
                            line=line,
                            kind=kind,
                            snippet=snippet,
                            severity="CRITICAL",
                            source="ggshield",
                        )
                    )
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as e:
        result.errors.append(f"ggshield: {type(e).__name__}: {e}")


def run_gitleaks(repo_root: str, result: ScanResult) -> None:
    """Roda gitleaks se instalado; funde findings."""
    if not shutil.which("gitleaks"):
        return
    try:
        proc = subprocess.run(
            ["gitleaks", "detect", "--source", repo_root, "--no-git", "--report-format", "json", "--report-path", "/dev/stdout"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        # gitleaks retorna 1 se achou; 0 se limpo
        if proc.returncode not in (0, 1):
            result.errors.append(f"gitleaks exit {proc.returncode}: {proc.stderr.strip()[:200]}")
            return
        if not proc.stdout.strip():
            result.scanners.append("gitleaks")
            return
        data = json.loads(proc.stdout)
        result.scanners.append("gitleaks")
        for finding in data:
            result.findings.append(
                Finding(
                    file=finding.get("File", "<unknown>"),
                    line=finding.get("StartLine", 0),
                    kind=finding.get("RuleID", "gitleaks-finding"),
                    snippet=f"{finding.get('Description', 'gitleaks')}: ***",
                    severity="CRITICAL",
                    source="gitleaks",
                )
            )
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as e:
        result.errors.append(f"gitleaks: {type(e).__name__}: {e}")


def deduplicate(result: ScanResult) -> None:
    """Dedup por (file, line, kind). Preserva o de severity mais alta."""
    severity_rank = {"CRITICAL": 2, "HIGH": 1, "MEDIUM": 0, "LOW": 0}
    seen: dict[tuple[str, int, str], Finding] = {}
    for f in result.findings:
        key = (f.file, f.line, f.kind)
        if key not in seen or severity_rank.get(f.severity, 0) > severity_rank.get(seen[key].severity, 0):
            seen[key] = f
    result.findings = list(seen.values())
    # Ordena: CRITICAL antes de HIGH, depois por file/line.
    result.findings.sort(
        key=lambda f: (-severity_rank.get(f.severity, 0), f.file, f.line)
    )


# ---------------------------------------------------------------------------
# Entry point.
# ---------------------------------------------------------------------------


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Scan a unified diff for hardcoded secrets.")
    p.add_argument(
        "--diff",
        help="Path to a unified diff file. Default: read from stdin.",
    )
    p.add_argument(
        "--base",
        help="Base ref (e.g. origin/main). If set, runs `git diff <base>...HEAD --unified=0` itself.",
    )
    p.add_argument(
        "--repo-root",
        default=".",
        help="Repository root for ggshield/gitleaks invocation. Default: cwd.",
    )
    p.add_argument(
        "--no-external",
        action="store_true",
        help="Skip ggshield/gitleaks even if installed.",
    )
    return p.parse_args(argv)


def get_diff_text(args: argparse.Namespace) -> str:
    if args.base:
        try:
            proc = subprocess.run(
                ["git", "diff", f"{args.base}...HEAD", "--unified=0"],
                cwd=args.repo_root,
                capture_output=True,
                text=True,
                check=True,
            )
            return proc.stdout
        except subprocess.CalledProcessError as e:
            print(f"git diff failed: {e.stderr}", file=sys.stderr)
            return ""
    if args.diff:
        with open(args.diff, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    return sys.stdin.read()


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    diff_text = get_diff_text(args)

    result = scan_diff(diff_text)

    if not args.no_external:
        run_ggshield(args.repo_root, result)
        run_gitleaks(args.repo_root, result)

    deduplicate(result)
    print(result.to_json())
    return 0


if __name__ == "__main__":
    sys.exit(main())
