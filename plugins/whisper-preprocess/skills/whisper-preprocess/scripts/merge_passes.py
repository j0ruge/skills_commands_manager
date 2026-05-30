#!/usr/bin/env python3
"""
Mescla 2 SRTs (idiomas diferentes) em uma transcricao unificada.

Estrategia: para cada cue do SRT primario, busca trechos sobrepostos no
secundario. Se a fala no trecho tem alta proporcao de caracteres do
script secundario (kanji/hiragana, cirilico, etc.) tanto no primario
(mal transcrito foneticamente) quanto no secundario, prefere o secundario
e marca com [TAG].

CLI:
  python merge_passes.py --primary primary.srt --secondary secondary.srt \\
    --output merged.txt --secondary-script japanese --marker-tag JA

Tambem expoe `merge(...)` como funcao Python.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

# --- Fix UTF-8 (Windows) ---
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# Regex para detectar caracteres "nao-latinos" caracteristicos de cada script.
SCRIPT_REGEX = {
    "japanese": r"[぀-ゟ゠-ヿ一-鿿]",      # hiragana + katakana + CJK unified
    "chinese":  r"[一-鿿]",                 # CJK unified
    "korean":   r"[가-힣ᄀ-ᇿ]",              # hangul + jamo
    "cyrillic": r"[Ѐ-ӿ]",                   # cyrillic block
    "arabic":   r"[؀-ۿݐ-ݿ]",               # arabic + arabic supplement
    "greek":    r"[Ͱ-Ͽ]",                   # greek and coptic
    "hebrew":   r"[֐-׿]",                   # hebrew
    "thai":     r"[฀-๿]",                   # thai
}


def script_regex_for(language: str) -> str:
    """Mapeia nome de idioma (ex.: 'Japanese') para regex de script."""
    key = (language or "").lower()
    aliases = {
        "japanese": "japanese", "ja": "japanese", "jp": "japanese",
        "chinese": "chinese", "zh": "chinese", "mandarin": "chinese",
        "korean": "korean", "ko": "korean",
        "russian": "cyrillic", "ukrainian": "cyrillic", "cyrillic": "cyrillic",
        "arabic": "arabic", "ar": "arabic",
        "greek": "greek", "el": "greek",
        "hebrew": "hebrew", "he": "hebrew",
        "thai": "thai", "th": "thai",
    }
    name = aliases.get(key, key)
    return SCRIPT_REGEX.get(name, "")


def parse_srt(path: str) -> list[tuple[float, float, str]]:
    text = Path(path).read_text(encoding="utf-8").strip()
    entries: list[tuple[float, float, str]] = []
    for block in text.split("\n\n"):
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue
        m = re.match(
            r"(\d{2}):(\d{2}):(\d{2}),(\d{3}) --> (\d{2}):(\d{2}):(\d{2}),(\d{3})",
            lines[1],
        )
        if not m:
            continue
        h1, m1, s1, ms1, h2, m2, s2, ms2 = map(int, m.groups())
        start = h1 * 3600 + m1 * 60 + s1 + ms1 / 1000
        end = h2 * 3600 + m2 * 60 + s2 + ms2 / 1000
        body = " ".join(lines[2:]).strip()
        entries.append((start, end, body))
    return entries


def script_ratio(text: str, pattern: re.Pattern) -> float:
    if not text:
        return 0.0
    matches = len(pattern.findall(text))
    return matches / max(len(text), 1)


def find_overlap(target: tuple[float, float], pool: list[tuple[float, float, str]]) -> str:
    ts, te = target
    parts: list[str] = []
    for s, e, t in pool:
        if e < ts or s > te:
            continue
        overlap = min(te, e) - max(ts, s)
        if overlap > 0.1:
            parts.append(t)
    return " ".join(parts).strip()


def merge(primary_srt: str, secondary_srt: str, output_path: str,
          secondary_script_regex: str, marker_tag: str = "JA",
          script_threshold: float = 0.3,
          primary_script_min: float = 0.1) -> int:
    """Mescla 2 SRTs em um TXT com timestamps [MM:SS].

    Retorna numero de linhas escritas.
    """
    primary = parse_srt(primary_srt)
    secondary = parse_srt(secondary_srt)

    if not secondary_script_regex:
        # Sem regex de script: nao temos como decidir qual eh "estrangeiro".
        # Fallback: so emite o primario.
        pattern = re.compile(r"(?!)")  # nunca casa
    else:
        pattern = re.compile(secondary_script_regex)

    out_lines: list[str] = []
    last_choice: str | None = None

    for start, end, pt_text in primary:
        sec_text = find_overlap((start, end), secondary)
        pt_jp = script_ratio(pt_text, pattern)
        sec_jp = script_ratio(sec_text, pattern)

        if (sec_text and sec_jp > script_threshold
                and (pt_jp > primary_script_min or len(pt_text) < 20)):
            choice = f"[{marker_tag}] {sec_text}"
        else:
            choice = pt_text

        if not choice:
            continue
        if choice == last_choice:
            continue
        last_choice = choice

        ts_str = f"[{int(start // 60):02d}:{int(start % 60):02d}]"
        out_lines.append(f"{ts_str} {choice}")

    Path(output_path).write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    return len(out_lines)


def main():
    parser = argparse.ArgumentParser(
        description="Merge de 2 SRTs em uma transcricao unificada com marcacao de idioma.",
    )
    parser.add_argument("--primary", required=True, help="SRT do idioma primario")
    parser.add_argument("--secondary", required=True, help="SRT do idioma secundario")
    parser.add_argument("--output", required=True, help="Arquivo TXT de saida")
    parser.add_argument("--secondary-script", default="japanese",
                        help="Script do idioma secundario para deteccao automatica "
                             "(japanese, chinese, korean, cyrillic, arabic, greek, hebrew, thai)")
    parser.add_argument("--secondary-script-regex", default=None,
                        help="Regex customizado (sobrescreve --secondary-script)")
    parser.add_argument("--marker-tag", default="JA",
                        help="Tag prefixada aos trechos do secundario (default: JA)")
    parser.add_argument("--script-threshold", type=float, default=0.3,
                        help="Proporcao minima de caracteres do script no secundario para usar o secundario")
    parser.add_argument("--primary-script-min", type=float, default=0.1,
                        help="Proporcao minima de caracteres do script no primario para considerar fala estrangeira")
    args = parser.parse_args()

    if args.secondary_script_regex:
        regex = args.secondary_script_regex
    else:
        regex = SCRIPT_REGEX.get(args.secondary_script, "")
        if not regex:
            print(f"[ERRO] script desconhecido: {args.secondary_script}", file=sys.stderr)
            print(f"Disponiveis: {', '.join(sorted(SCRIPT_REGEX.keys()))}", file=sys.stderr)
            sys.exit(1)

    n = merge(
        primary_srt=args.primary,
        secondary_srt=args.secondary,
        output_path=args.output,
        secondary_script_regex=regex,
        marker_tag=args.marker_tag,
        script_threshold=args.script_threshold,
        primary_script_min=args.primary_script_min,
    )
    print(f"Wrote {args.output} ({n} lines)")


if __name__ == "__main__":
    main()
