#!/usr/bin/env python3
"""
Pipeline de pre-processamento de audio e transcricao com Whisper.

Extrai audio de arquivos de video/audio, remove silencios longos,
aplica filtros de melhoria (reducao de ruido, normalizacao, compressao),
segmenta em pedacos menores, e transcreve usando OpenAI Whisper.

Suporta modo offline (whisper local sem internet), 2 passes de idioma
(ex: PT + JA com merge automatico) e reuso de segmentos entre execucoes.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import logging
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# --- Fix UTF-8 (Windows console default eh cp1252 e quebra Whisper com acentos/kanji) ---
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# --- Subprocess helpers (sempre UTF-8 com replace para nao crashar em Windows) ---

def _run_capture(cmd: list[str]) -> subprocess.CompletedProcess:
    """subprocess.run com capture e decoding UTF-8 robusto."""
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=os.environ,
    )


def run_ffmpeg(args: list[str], description: str) -> None:
    """Executa um comando ffmpeg e loga o progresso."""
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "warning"] + args
    log.info(">> %s", description)
    log.debug("Comando: %s", " ".join(cmd))
    t0 = time.time()
    result = _run_capture(cmd)
    elapsed = time.time() - t0
    if result.returncode != 0:
        log.error("ffmpeg falhou (exit=%d):\n%s", result.returncode, result.stderr)
        sys.exit(1)
    log.info("   Concluido em %.1fs", elapsed)


def get_duration(filepath: str) -> float:
    """Retorna a duracao do arquivo em segundos."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        filepath,
    ]
    result = _run_capture(cmd)
    if result.returncode != 0:
        return 0.0
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def format_duration(seconds: float) -> str:
    """Formata segundos em HH:MM:SS."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def extract_audio(input_path: str, output_path: str, sample_rate: int = 16000) -> None:
    run_ffmpeg(
        ["-i", input_path, "-vn", "-ac", "1", "-ar", str(sample_rate),
         "-c:a", "pcm_s16le", output_path],
        f"Extraindo audio ({sample_rate} Hz): {os.path.basename(input_path)}"
    )


def remove_silence(input_path: str, output_path: str,
                   duration: float = 2.0, threshold: str = "-30dB",
                   stop_silence: float = 0.5) -> None:
    # detection=rms + window de 25ms suavizam as emendas: evitam cortes/cliques na
    # fala lenta e de baixo volume (que com detection=peak vira "picotamento").
    silence_filter = (
        f"silenceremove="
        f"stop_periods=-1:"
        f"stop_duration={duration}:"
        f"stop_threshold={threshold}:"
        f"stop_silence={stop_silence}:"
        f"detection=rms:"
        f"window=0.025"
    )
    run_ffmpeg(
        ["-i", input_path, "-af", silence_filter, "-c:a", "pcm_s16le", output_path],
        f"Removendo silencios > {duration}s (threshold: {threshold}, keep: {stop_silence}s)"
    )


def compress_audio(input_path: str, output_path: str,
                   application: str = "audio", bitrate: str = "64k",
                   sample_rate: int = 48000) -> None:
    run_ffmpeg(
        ["-i", input_path, "-c:a", "libopus", "-b:a", bitrate,
         "-ar", str(sample_rate), "-application", application, output_path],
        f"Compactando audio para OPUS ({bitrate}, {application}): {os.path.basename(output_path)}"
    )


def enhance_audio(input_path: str, output_path: str) -> None:
    """Cadeia de melhoria para a TRILHA DE TRANSCRICAO (16 kHz, alimentada ao Whisper).

    Mantida como sempre: highpass + acompressor + loudnorm. Eventual pumping aqui
    nao importa (nenhum humano ouve este arquivo) e ajuda o reconhecedor.
    A copia AUDIVEL e gerada separadamente por build_listenable() (ganho estavel).
    """
    filters = ",".join([
        "highpass=f=100",
        "acompressor=threshold=-18dB:ratio=3:attack=10:release=50",
        "loudnorm=I=-16:LRA=11:TP=-1.5",
    ])
    run_ffmpeg(
        ["-i", input_path, "-af", filters, "-c:a", "pcm_s16le", output_path],
        "Aplicando filtros de melhoria de audio (trilha de transcricao)"
    )


def build_listenable(input_path: str, output_path: str, args) -> None:
    """Gera a copia AUDIVEL (a que o usuario escuta no *_enhanced.opus).

    Desacoplada da trilha de transcricao para eliminar o "picotamento":
      - Le do arquivo ORIGINAL em banda larga (args.listen_sr, default 48 kHz) -> mais
        inteligivel para quem tem dificuldade de fala (preserva consoantes).
      - NAO remove silencio por padrao -> audio continuo, o ouvinte acompanha as pausas
        do locutor e nada e cortado.
      - Ganho ESTAVEL: compressor de release lento (400ms) + makeup fixo + limitador
        true-peak com lookahead. Sem AGC dinamico -> sem "respiracao"/pumping.
        (loudnorm dinamico ou compressor de release rapido = picotamento; comprovado
         em testes A/B com loudnorm two-pass revertendo para 'Dynamic' em fontes que clipam.)
      - Limitador com headroom (default 0.6 ~= -4.4 dBFS) deixa margem para o overshoot
        inter-sample do Opus, mantendo o true-peak final abaixo de 0 dBFS.
    """
    filters = [f"highpass=f={args.listen_highpass}"]

    if args.denoise:
        if args.denoise_model:
            filters.append(f"arnndn=m={args.denoise_model}")
        else:
            # afftdn pode gerar "musical noise"; por isso denoise e opt-in e desligado por padrao.
            nr = max(6, min(24, args.denoise_strength))
            filters.append(f"afftdn=nr={nr}:nf=-30:tn=1")

    if args.trim_listen:
        # Remocao de silencio GENTIL e opcional para a copia de escuta.
        filters.append(
            f"silenceremove=stop_periods=-1:stop_duration={args.silence_duration}"
            f":stop_threshold={args.silence_threshold}:stop_silence={args.silence_keep}"
            f":detection=rms:window=0.025"
        )

    filters.append(
        f"acompressor=threshold={args.listen_comp_threshold}:ratio={args.listen_comp_ratio}"
        f":attack=25:release=400:makeup={args.listen_makeup}"
    )
    filters.append(
        f"alimiter=limit={args.listen_limit}:attack=5:release=60:level=disabled"
    )

    af = ",".join(filters)
    run_ffmpeg(
        ["-i", input_path, "-vn", "-ac", "1", "-ar", str(args.listen_sr),
         "-af", af, "-c:a", "pcm_s16le", output_path],
        f"Gerando audio de escuta (ganho estavel, {args.listen_sr // 1000} kHz, sem AGC)"
    )


def segment_audio(input_path: str, output_dir: str,
                  segment_minutes: int = 10) -> list[str]:
    duration = get_duration(input_path)
    segment_secs = segment_minutes * 60
    segments = []
    idx = 0

    while idx * segment_secs < duration:
        start = idx * segment_secs
        out_path = os.path.join(output_dir, f"segment_{idx:03d}.wav")
        run_ffmpeg(
            ["-i", input_path, "-ss", str(start), "-t", str(segment_secs),
             "-c:a", "pcm_s16le", out_path],
            f"Segmento {idx + 1}: {format_duration(start)} - "
            f"{format_duration(min(start + segment_secs, duration))}"
        )
        segments.append(out_path)
        idx += 1

    log.info("   %d segmentos criados", len(segments))
    return segments


# --- Cache de segmentos por hash do input ---

def input_hash(filepath: str) -> str:
    """Hash curto do (caminho + mtime + size) para identificar input."""
    st = os.stat(filepath)
    key = f"{os.path.abspath(filepath)}|{int(st.st_mtime)}|{st.st_size}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:8]


def intermediate_dir_for(filepath: str) -> str:
    """Diretorio intermediario canonico para este input."""
    base = os.path.splitext(os.path.basename(filepath))[0]
    parent = os.path.dirname(os.path.abspath(filepath))
    return os.path.join(parent, f"{base}_intermediate_{input_hash(filepath)}")


def existing_segments(seg_dir: str) -> list[str]:
    """Retorna lista de segment_NNN.wav ordenados, se existirem."""
    if not os.path.isdir(seg_dir):
        return []
    files = sorted(glob.glob(os.path.join(seg_dir, "segment_*.wav")))
    return files


# --- Modo offline / pre-flight do modelo ---

OFFLINE_ENV = {
    "HF_HUB_OFFLINE": "1",
    "TRANSFORMERS_OFFLINE": "1",
    "HF_HUB_DISABLE_TELEMETRY": "1",
}


MODEL_ALIASES = {
    "turbo": "large-v3-turbo",
    "large": "large-v3",
}


def check_model_cached(model: str) -> tuple[bool, str]:
    """Verifica se o modelo Whisper esta presente em cache local.

    Procura nos caminhos onde o openai-whisper (`whisper.load_model`) baixa por padrao:
    - `~/.cache/whisper/<model>.pt`
    - `~/.cache/whisper/<alias>.pt` (ex.: turbo -> large-v3-turbo)
    E como fallback no cache do HuggingFace Hub.

    Retorna (presente, caminho_ou_dica).
    """
    home = Path.home()
    whisper_cache = home / ".cache" / "whisper"

    names_to_try: list[str] = [model]
    if model in MODEL_ALIASES:
        names_to_try.append(MODEL_ALIASES[model])

    for name in names_to_try:
        pt_path = whisper_cache / f"{name}.pt"
        if pt_path.exists():
            return True, str(pt_path)

    # Fallback HF (alguns setups customizados)
    hf_root = home / ".cache" / "huggingface" / "hub"
    candidates = [hf_root / f"models--openai--whisper-{n}" for n in names_to_try]
    for cand in candidates:
        if cand.is_dir():
            snapshots = cand / "snapshots"
            if snapshots.is_dir() and any(snapshots.iterdir()):
                return True, str(cand)

    expected = whisper_cache / f"{names_to_try[-1]}.pt"
    return False, str(expected)


def apply_offline_env() -> None:
    for k, v in OFFLINE_ENV.items():
        os.environ[k] = v


# --- Transcricao ---

def transcribe_segment(audio_path: str, output_dir: str, language: str,
                       model: str, device: str,
                       initial_prompt: str | None = None,
                       model_dir: str | None = None) -> tuple[str, subprocess.CompletedProcess]:
    """Transcreve um segmento de audio usando Whisper CLI.

    Retorna (texto, completed_process) para permitir surfacing de erros.
    """
    cmd = [
        "whisper", audio_path,
        "--language", language,
        "--model", model,
        "--device", device,
        "--output_dir", output_dir,
        "--temperature", "0",
        "--condition_on_previous_text", "False",
    ]
    if initial_prompt:
        cmd.extend(["--initial_prompt", initial_prompt])
    if model_dir:
        cmd.extend(["--model_dir", model_dir])

    result = _run_capture(cmd)

    base = os.path.splitext(os.path.basename(audio_path))[0]
    txt_path = os.path.join(output_dir, f"{base}.txt")
    text = ""
    if os.path.exists(txt_path):
        try:
            with open(txt_path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            log.error("Falha ao ler txt do whisper (%s): %s", txt_path, e)
    return text, result


def transcribe_segmented(segments: list[str], output_dir: str,
                         language: str, model: str, device: str,
                         initial_prompt: str | None = None,
                         model_dir: str | None = None,
                         label: str = "") -> str:
    all_text = []
    total = len(segments)
    label_prefix = f"[{label}] " if label else ""

    log.info(">> %sTranscrevendo %d segmentos com Whisper (modelo: %s, device: %s, idioma: %s)",
             label_prefix, total, model, device, language)
    t0 = time.time()

    for i, seg_path in enumerate(segments):
        seg_name = os.path.basename(seg_path)
        log.info("   %s[%d/%d] Transcrevendo %s...", label_prefix, i + 1, total, seg_name)

        t1 = time.time()
        text, proc = transcribe_segment(seg_path, output_dir, language, model,
                                        device, initial_prompt, model_dir)
        elapsed = time.time() - t1

        if proc.returncode != 0:
            log.error("   %s[%d/%d] Whisper exit=%d em %s (%.1fs)",
                      label_prefix, i + 1, total, proc.returncode, seg_name, elapsed)
            stderr_tail = (proc.stderr or "")[-800:]
            stdout_tail = (proc.stdout or "")[-300:]
            if stderr_tail:
                log.error("   STDERR (ultimas 800 chars):\n%s", stderr_tail)
            if stdout_tail and not text:
                log.error("   STDOUT (ultimas 300 chars):\n%s", stdout_tail)

        if text.strip():
            all_text.append(text.strip())
            log.info("   %s[%d/%d] Concluido em %.1fs (%d caracteres)",
                     label_prefix, i + 1, total, elapsed, len(text.strip()))
        else:
            stderr_tail = (proc.stderr or "")[-800:]
            if proc.returncode == 0 and stderr_tail:
                log.warning("   %s[%d/%d] Segmento vazio mesmo com exit=0 (%.1fs). STDERR (ultimas 800 chars):\n%s",
                            label_prefix, i + 1, total, elapsed, stderr_tail)
            elif proc.returncode == 0:
                log.warning("   %s[%d/%d] Segmento vazio (%.1fs)",
                            label_prefix, i + 1, total, elapsed)

    total_elapsed = time.time() - t0
    log.info("   %sTranscricao total concluida em %s", label_prefix, format_duration(total_elapsed))

    return "\n\n".join(all_text)


def concat_srts(segments: list[str], transcription_dir: str,
                output_path: str, segment_minutes: int) -> None:
    """Concatena SRTs dos segmentos ajustando timestamps."""
    import re

    def shift_timestamp(ts: str, offset_seconds: float) -> str:
        match = re.match(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})", ts)
        if not match:
            return ts
        h, m, s, ms = int(match[1]), int(match[2]), int(match[3]), int(match[4])
        total_ms = (h * 3600 + m * 60 + s) * 1000 + ms + int(offset_seconds * 1000)
        h2 = total_ms // 3600000
        m2 = (total_ms % 3600000) // 60000
        s2 = (total_ms % 60000) // 1000
        ms2 = total_ms % 1000
        return f"{h2:02d}:{m2:02d}:{s2:02d},{ms2:03d}"

    all_entries = []
    counter = 1

    for i, seg_path in enumerate(segments):
        base = os.path.splitext(os.path.basename(seg_path))[0]
        srt_file = os.path.join(transcription_dir, f"{base}.srt")
        if not os.path.exists(srt_file):
            continue

        offset = i * segment_minutes * 60

        with open(srt_file, "r", encoding="utf-8") as f:
            content = f.read().strip()

        if not content:
            continue

        blocks = content.split("\n\n")
        for block in blocks:
            lines = block.strip().split("\n")
            if len(lines) < 3:
                continue
            ts_match = re.match(
                r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})",
                lines[1]
            )
            if not ts_match:
                continue
            start_ts = shift_timestamp(ts_match[1], offset)
            end_ts = shift_timestamp(ts_match[2], offset)
            text = "\n".join(lines[2:])

            all_entries.append(f"{counter}\n{start_ts} --> {end_ts}\n{text}")
            counter += 1

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(all_entries) + "\n")

    log.info("   SRT concatenado: %d entradas", counter - 1)


# --- Idioma -> codigo ISO-639-1 ---

LANGUAGE_CODES = {
    "portuguese": "pt", "pt": "pt", "pt-br": "pt", "pt-pt": "pt",
    "english": "en", "en": "en",
    "japanese": "ja", "ja": "ja", "jp": "ja",
    "chinese": "zh", "zh": "zh", "mandarin": "zh",
    "korean": "ko", "ko": "ko",
    "spanish": "es", "es": "es",
    "french": "fr", "fr": "fr",
    "german": "de", "de": "de",
    "italian": "it", "it": "it",
    "russian": "ru", "ru": "ru",
    "arabic": "ar", "ar": "ar",
    "dutch": "nl", "nl": "nl",
    "polish": "pl", "pl": "pl",
    "turkish": "tr", "tr": "tr",
    "hindi": "hi", "hi": "hi",
    "vietnamese": "vi", "vi": "vi",
    "indonesian": "id", "id": "id",
    "ukrainian": "uk", "uk": "uk",
    "greek": "el", "el": "el",
    "hebrew": "he", "he": "he",
    "thai": "th", "th": "th",
    "swedish": "sv", "sv": "sv",
    "norwegian": "no", "no": "no",
    "danish": "da", "da": "da",
    "finnish": "fi", "fi": "fi",
    "czech": "cs", "cs": "cs",
    "romanian": "ro", "ro": "ro",
    "hungarian": "hu", "hu": "hu",
}


def language_code(language: str) -> str:
    """Converte nome de idioma (ex.: 'Portuguese') para codigo ISO-639-1 ('pt').

    Fallback: lowercase + primeiros 2 chars (compatibilidade com idiomas nao mapeados).
    """
    key = (language or "").lower().strip()
    if key in LANGUAGE_CODES:
        return LANGUAGE_CODES[key]
    return key[:2] if key else "xx"


# --- Pipeline ---

def preprocess(args, input_path: str, work_dir: str) -> tuple[str, str]:
    """Roda extract -> remove_silence -> enhance (trilha de transcricao) e gera a copia
    de escuta desacoplada. Retorna (processed_wav, listenable_wav)."""
    raw_wav = os.path.join(work_dir, "01_raw.wav")
    extract_audio(input_path, raw_wav, sample_rate=16000)
    current_file = raw_wav

    if not args.skip_silence:
        cleaned_wav = os.path.join(work_dir, "02_silence_removed.wav")
        remove_silence(current_file, cleaned_wav,
                       duration=args.silence_duration,
                       threshold=args.silence_threshold,
                       stop_silence=args.silence_keep)
        current_file = cleaned_wav

        original_duration = get_duration(raw_wav)
        cleaned_duration = get_duration(current_file)
        removed = original_duration - cleaned_duration
        pct = (removed / original_duration) * 100 if original_duration > 0 else 0
        log.info("   Duracao apos remocao de silencio: %s (removidos %s = %.1f%%)",
                 format_duration(cleaned_duration), format_duration(removed), pct)
    else:
        log.info(">> Pulando remocao de silencio (--skip-silence)")

    if not args.skip_enhance:
        enhanced_wav = os.path.join(work_dir, "03_enhanced.wav")
        enhance_audio(current_file, enhanced_wav)
        current_file = enhanced_wav
    else:
        log.info(">> Pulando melhoria de audio (--skip-enhance)")

    processed_path = os.path.join(work_dir, "processed.wav")
    if current_file != processed_path:
        run_ffmpeg(
            ["-i", current_file, "-c:a", "copy", processed_path],
            "Preparando audio para segmentacao"
        )

    # Copia AUDIVEL (independente da trilha de transcricao): gerada a partir do
    # arquivo ORIGINAL, ganho estavel, banda larga, sem corte de silencio por padrao.
    listenable_wav = os.path.join(work_dir, "04_listenable.wav")
    build_listenable(input_path, listenable_wav, args)

    return processed_path, listenable_wav


def cleanup(args, work_dir: str) -> None:
    if args.keep_intermediate:
        log.info("Arquivos intermediarios mantidos em: %s", work_dir)
        return

    import shutil
    if os.path.isdir(work_dir):
        shutil.rmtree(work_dir, ignore_errors=True)
        log.info("Arquivos intermediarios removidos.")


def main():
    parser = argparse.ArgumentParser(
        description="Pre-processamento de audio e transcricao com Whisper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python whisper_preprocess.py aula.mkv
  python whisper_preprocess.py aula.mkv --keep-intermediate
  python whisper_preprocess.py aula.mkv --initial-prompt "Seminario de Antigo Testamento"
  python whisper_preprocess.py aula.mkv --only-preprocess
  python whisper_preprocess.py aula.mkv --skip-silence --model large-v2
  python whisper_preprocess.py aula.mkv --segment-minutes 15

  # Multi-idioma (ex.: reuniao PT + JA)
  python whisper_preprocess.py reuniao.mkv \\
    --language Portuguese --secondary-language Japanese \\
    --initial-prompt "Reuniao tecnica..." \\
    --secondary-initial-prompt "Kusaba Murata UPS"

  # Modo offline (modelo ja baixado em ~/.cache/whisper ou HF cache)
  python whisper_preprocess.py reuniao.mkv --offline

  # Forcar reprocessamento ignorando cache de segmentos
  python whisper_preprocess.py reuniao.mkv --force-reprocess
        """,
    )
    parser.add_argument("input", help="Arquivo de entrada (MKV, MP4, WAV, etc.)")
    parser.add_argument("--language", default="Portuguese", help="Idioma primario (default: Portuguese)")
    parser.add_argument("--secondary-language", default=None,
                        help="Idioma secundario para 2o pass (ex.: Japanese). Gera merge automatico.")
    parser.add_argument("--model", default="turbo", help="Modelo Whisper (default: turbo)")
    parser.add_argument("--model-dir", default=None,
                        help="Diretorio com modelos Whisper (repassado para --model_dir do whisper)")
    parser.add_argument("--device", default="cuda", help="Device: cuda ou cpu (default: cuda)")
    parser.add_argument("--initial-prompt", default=None,
                        help="Prompt inicial com contexto para o pass primario")
    parser.add_argument("--secondary-initial-prompt", default=None,
                        help="Prompt inicial com contexto para o pass secundario")
    parser.add_argument("--silence-duration", type=float, default=2.0,
                        help="Duracao minima de silencio em segundos (default: 2.0)")
    parser.add_argument("--silence-threshold", default="-30dB",
                        help="Threshold de silencio em dB (default: -30dB)")
    parser.add_argument("--silence-keep", type=float, default=0.5,
                        help="Silencio mantido em cada emenda (stop_silence; default: 0.5s)")
    parser.add_argument("--segment-minutes", type=int, default=10,
                        help="Duracao de cada segmento em minutos (default: 10)")

    # --- Copia AUDIVEL (*_enhanced.opus) — desacoplada da transcricao ---
    listen = parser.add_argument_group("audio de escuta (*_enhanced.opus)")
    listen.add_argument("--listen-sr", type=int, default=48000,
                        help="Sample rate do opus de escuta: 48000/24000/16000 (default: 48000)")
    listen.add_argument("--listen-bitrate", default="64k",
                        help="Bitrate do opus de escuta (default: 64k)")
    listen.add_argument("--listen-makeup", type=float, default=5.0,
                        help="Ganho makeup do compressor de escuta em dB; aumente p/ locutor "
                             "muito baixo (default: 5.0)")
    listen.add_argument("--listen-limit", type=float, default=0.6,
                        help="Teto do limitador de escuta 0..1; menor = mais headroom p/ Opus "
                             "(default: 0.6 ~= -4.4 dBFS)")
    listen.add_argument("--listen-highpass", type=int, default=80,
                        help="Highpass (Hz) da copia de escuta (default: 80)")
    listen.add_argument("--listen-comp-threshold", default="-22dB",
                        help="Threshold do compressor de escuta (default: -22dB)")
    listen.add_argument("--listen-comp-ratio", type=float, default=3.0,
                        help="Ratio do compressor de escuta (default: 3.0)")
    listen.add_argument("--trim-listen", dest="trim_listen", action="store_true",
                        help="Tambem remove silencio (gentil) da copia de escuta")
    listen.add_argument("--no-trim-listen", dest="trim_listen", action="store_false")
    listen.set_defaults(trim_listen=False)
    listen.add_argument("--denoise", dest="denoise", action="store_true",
                        help="Reducao de ruido na copia de escuta (afftdn, ou arnndn se "
                             "--denoise-model). DESLIGADO por padrao: afftdn pode gerar 'musical noise'.")
    listen.add_argument("--no-denoise", dest="denoise", action="store_false")
    listen.set_defaults(denoise=False)
    listen.add_argument("--denoise-strength", type=int, default=12,
                        help="afftdn nr em dB (6..24; default: 12)")
    listen.add_argument("--denoise-model", default=None,
                        help="Caminho p/ modelo .rnnn -> usa arnndn (RNNoise) em vez de afftdn")
    parser.add_argument("--skip-enhance", action="store_true",
                        help="Pular etapa de melhoria de audio")
    parser.add_argument("--skip-silence", action="store_true",
                        help="Pular remocao de silencio")
    parser.add_argument("--keep-intermediate", action="store_true",
                        help="Manter arquivos intermediarios para debug")
    parser.add_argument("--only-preprocess", action="store_true",
                        help="Apenas pre-processar, sem transcrever")
    parser.add_argument("--offline", action="store_true",
                        help="Forca uso de modelo local; falha se nao encontrado (tambem ativado por WHISPER_OFFLINE=1)")
    parser.add_argument("--force-reprocess", action="store_true",
                        help="Ignora cache de segmentos e reprocessa do zero")

    args = parser.parse_args()

    if os.environ.get("WHISPER_OFFLINE") == "1":
        args.offline = True

    if args.offline:
        apply_offline_env()

    if not os.path.exists(args.input):
        log.error("Arquivo nao encontrado: %s", args.input)
        sys.exit(1)

    input_dir = os.path.dirname(os.path.abspath(args.input))
    input_base = os.path.splitext(os.path.basename(args.input))[0]

    log.info("=" * 60)
    log.info("Pipeline de Pre-processamento + Transcricao Whisper")
    log.info("=" * 60)
    log.info("Entrada: %s", args.input)

    # Pre-flight: modelo offline disponivel?
    if not args.only_preprocess:
        ok, hint = check_model_cached(args.model)
        if not ok:
            if args.offline:
                log.error("Modo offline: modelo '%s' nao encontrado em cache local.", args.model)
                log.error("Esperado em: %s", hint)
                log.error("Para baixar previamente, conecte-se a internet e rode:")
                log.error("  python -c \"import whisper; whisper.load_model('%s')\"", args.model)
                sys.exit(2)
            else:
                log.warning("Modelo '%s' nao detectado em cache local. Whisper pode tentar baixar.", args.model)
                log.warning("Para evitar isso, baixe antes: python -c \"import whisper; whisper.load_model('%s')\"", args.model)
        else:
            log.info("Modelo '%s' encontrado em cache: %s", args.model, hint)

    original_duration = get_duration(args.input)
    log.info("Duracao original: %s", format_duration(original_duration))

    # Diretorio intermediario com hash do input (permite reuso)
    canonical_tmp = intermediate_dir_for(args.input)
    seg_dir = os.path.join(canonical_tmp, "segments")
    processed_path = os.path.join(canonical_tmp, "processed.wav")
    listenable_wav_path = os.path.join(canonical_tmp, "04_listenable.wav")

    cached_segments = existing_segments(seg_dir)
    use_cache = bool(cached_segments) and not args.force_reprocess and os.path.exists(processed_path)

    if args.keep_intermediate or use_cache:
        os.makedirs(canonical_tmp, exist_ok=True)
        tmp_dir = canonical_tmp
        tmp_obj = None
    else:
        tmp_obj = tempfile.TemporaryDirectory()
        tmp_dir = tmp_obj.name
        seg_dir = os.path.join(tmp_dir, "segments")
        processed_path = os.path.join(tmp_dir, "processed.wav")
        listenable_wav_path = os.path.join(tmp_dir, "04_listenable.wav")

    if use_cache:
        log.info(">> Reusando %d segmentos do cache: %s", len(cached_segments), seg_dir)
        segments = cached_segments
        # enhanced_wav pode nao existir mais (se foi compactado e removido); tudo bem
    else:
        if args.force_reprocess and os.path.isdir(canonical_tmp):
            log.info(">> --force-reprocess: limpando %s", canonical_tmp)
            import shutil
            shutil.rmtree(canonical_tmp, ignore_errors=True)
            os.makedirs(canonical_tmp, exist_ok=True)

        processed_path, listenable_wav_path = preprocess(args, args.input, tmp_dir)

        if args.only_preprocess:
            opus_path = os.path.join(input_dir, f"{input_base}_enhanced.opus")
            compress_audio(listenable_wav_path, opus_path, application="audio",
                           bitrate=args.listen_bitrate, sample_rate=args.listen_sr)
            size_mb = os.path.getsize(opus_path) / (1024 * 1024)
            log.info("=" * 60)
            log.info("Pre-processamento concluido. Audio salvo em:")
            log.info("  %s (%.1f MB)", os.path.basename(opus_path), size_mb)
            log.info("=" * 60)
            cleanup(args, tmp_dir)
            return

        os.makedirs(seg_dir, exist_ok=True)
        segments = segment_audio(processed_path, seg_dir,
                                 segment_minutes=args.segment_minutes)

    # --- Pass primario ---
    primary_tx_dir = os.path.join(tmp_dir, "transcriptions_primary")
    os.makedirs(primary_tx_dir, exist_ok=True)
    primary_text = transcribe_segmented(
        segments, primary_tx_dir,
        language=args.language, model=args.model, device=args.device,
        initial_prompt=args.initial_prompt, model_dir=args.model_dir,
        label=language_code(args.language).upper(),
    )

    lang_tag = language_code(args.language)
    primary_txt = os.path.join(input_dir, f"{input_base}_transcricao_{lang_tag}.txt")
    primary_srt = os.path.join(input_dir, f"{input_base}_transcricao_{lang_tag}.srt")
    with open(primary_txt, "w", encoding="utf-8") as f:
        f.write(primary_text)
    concat_srts(segments, primary_tx_dir, primary_srt, args.segment_minutes)

    output_files = [primary_txt, primary_srt]

    # --- Pass secundario (opcional) ---
    if args.secondary_language:
        secondary_tx_dir = os.path.join(tmp_dir, "transcriptions_secondary")
        os.makedirs(secondary_tx_dir, exist_ok=True)
        secondary_text = transcribe_segmented(
            segments, secondary_tx_dir,
            language=args.secondary_language, model=args.model, device=args.device,
            initial_prompt=args.secondary_initial_prompt, model_dir=args.model_dir,
            label=language_code(args.secondary_language).upper(),
        )

        lang2_tag = language_code(args.secondary_language)
        secondary_txt = os.path.join(input_dir, f"{input_base}_transcricao_{lang2_tag}.txt")
        secondary_srt = os.path.join(input_dir, f"{input_base}_transcricao_{lang2_tag}.srt")
        with open(secondary_txt, "w", encoding="utf-8") as f:
            f.write(secondary_text)
        concat_srts(segments, secondary_tx_dir, secondary_srt, args.segment_minutes)
        output_files.extend([secondary_txt, secondary_srt])

        # Merge via merge_passes
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from merge_passes import merge as merge_passes_merge, script_regex_for
            merged_path = os.path.join(input_dir, f"{input_base}_transcricao_merged.txt")
            script_regex = script_regex_for(args.secondary_language)
            marker = language_code(args.secondary_language).upper()
            merge_passes_merge(
                primary_srt=primary_srt,
                secondary_srt=secondary_srt,
                output_path=merged_path,
                secondary_script_regex=script_regex,
                marker_tag=marker,
            )
            output_files.append(merged_path)
            log.info(">> Merge produzido: %s", os.path.basename(merged_path))
        except Exception as e:
            log.error("Falha ao mesclar passes: %s", e)

    # --- Compactar audio de escuta (se disponivel) ---
    if os.path.exists(listenable_wav_path):
        opus_path = os.path.join(input_dir, f"{input_base}_enhanced.opus")
        compress_audio(listenable_wav_path, opus_path, application="audio",
                       bitrate=args.listen_bitrate, sample_rate=args.listen_sr)
        output_files.append(opus_path)

    log.info("=" * 60)
    log.info("Pipeline concluido!")
    log.info("Arquivos gerados:")
    for path in output_files:
        if os.path.exists(path):
            size = os.path.getsize(path)
            if size > 1024 * 1024:
                log.info("  %s (%.1f MB)", os.path.basename(path), size / (1024 * 1024))
            else:
                log.info("  %s (%.1f KB)", os.path.basename(path), size / 1024)
    log.info("=" * 60)

    cleanup(args, tmp_dir)


if __name__ == "__main__":
    main()
