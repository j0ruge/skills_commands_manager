# Changelog — `whisper-preprocess`

## [1.0.0] — 2026-05-30

Initial packaging of the local `whisper-preprocess` skill into the marketplace. The skill
already carried hard-won Whisper lessons (silence removal before enhancement, -30dB threshold,
10-min segmentation against hallucination cascades, `condition_on_previous_text=False`, UTF-8
on Windows, multilingual 2-pass + merge). This release packages all of that **plus** the
anti-"picotamento" fix proven this session against a real 65-min recording (`Sales Quote
fluxo.m4a`) containing a low-volume, speech-impaired (dysarthric) speaker whose voice came out
choppy/fluttering in the listenable `*_enhanced.opus`.

### Why (the lessons that motivated this)

The listenable `*_enhanced.opus` was being encoded from the **same** `03_enhanced.wav` used for
transcription. That meant the human-listenable file inherited three independent gain-modulation /
chopping sources stacked on top of each other — devastating for a quiet, slow speaker:

1. `silenceremove` at `-30dB` — treats low-volume speech as silence and cuts at the seams.
2. `acompressor … release=50ms` — pumps the gain on every syllable gap.
3. single-pass `loudnorm` — a dynamic AGC that "breathes" (raises gain on pauses, ducks on speech).

A/B measurement on the real file also surfaced two non-obvious traps:

- A 2-pass `loudnorm linear=true` (the textbook anti-pumping move) **silently reverts to
  "Dynamic"** when the source clips (`input_tp = +0.76 dBTP` here) — confirmed via
  `print_format=summary` showing `Normalization Type: Dynamic`. So it does **not** guarantee a
  pump-free result and is not used for the listening copy.
- **Opus encoding adds inter-sample overshoot above the limiter ceiling**: a sample-peak limit
  of `-1.5 dBFS` came back as **+1.3 dBTP** after Opus. The limiter needs real headroom
  (`limit ≈ 0.6`, ~-4.4 dBFS sample) to keep the decoded true-peak below 0 dBFS. The OLD recipe
  actually clipped at **+0.7 dBFS**.

### Added

- **`build_listenable()`** — the listenable `*_enhanced.opus` is now **decoupled** from the
  transcription path and generated from the **original** input:
  - wideband **48 kHz** (configurable) — preserves consonants → more intelligible for an impaired
    speaker;
  - **no silence removal** by default → continuous audio, the listener follows every pause and
    nothing is clipped;
  - **stable gain only**: `highpass=80` → slow-release `acompressor` (`release=400ms`) + fixed
    `makeup` → true-peak `alimiter` (lookahead). **No dynamic AGC** → no breathing/pumping.
    Verified on the real file: `I≈-16.8 LUFS`, `LRA≈6.5`, true-peak `-1.0 dBFS` (no clipping),
    vs the old recipe's `+0.7 dBFS`.
- New CLI flags: `--listen-sr` (default 48000), `--listen-bitrate` (64k), `--listen-makeup`
  (5.0; raise for a very quiet speaker), `--listen-limit` (0.6), `--listen-highpass` (80),
  `--listen-comp-threshold` (-22dB), `--listen-comp-ratio` (3.0), `--trim-listen` /
  `--no-trim-listen` (off), `--denoise` / `--no-denoise` (off), `--denoise-strength` (12),
  `--denoise-model` (arnndn RNNoise model path), `--silence-keep` (0.5).
- **SKILL.md lesson #9** documenting the decoupled listening copy + stable-gain rationale, a
  pipeline-diagram update, a parameters-table expansion, and troubleshooting rows for
  "voz picotando" and "listening copy still too quiet".

### Changed

- `*_enhanced.opus` encoding: `-application voip` → **`-application audio`** at **48 kHz / 64k**
  (voip is narrowband telephony tuning that thins the voice). Configurable via
  `--listen-sr` / `--listen-bitrate`.
- Transcription-path `silenceremove` made gentler: `detection=rms`, `window=0.025`,
  `stop_silence=0.5`, `stop_duration` default `1.5 → 2.0`. The **-30dB threshold is unchanged**
  (background noise above -40dB makes -40 find zero silence — the long-standing lesson #3 still
  holds), and these refinements also help Whisper on slow speakers.

### Not changed / out of scope

- The **transcription enhancement chain** (`highpass=100 → acompressor → loudnorm`) is unchanged.
  Any pumping there is irrelevant (no human listens to that file) and it helps the recognizer.
- **Denoise stays opt-in and off by default.** `afftdn` can introduce "musical noise" (the
  skill's lesson #1); when denoise is wanted, `arnndn` (RNNoise, via `--denoise-model`) is
  preferred and `afftdn` is the documented last resort.
