<p align="center"><img src="assets/wordmark.svg" alt="CueIvrit - English to Hebrew subtitles, cue by cue" width="660"></p>

<p align="center">
  <a href="https://github.com/guy-tsarfati/hebrew-subtitle-translator/actions/workflows/tests.yml"><img src="https://github.com/guy-tsarfati/hebrew-subtitle-translator/actions/workflows/tests.yml/badge.svg" alt="Synthetic tests"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-55DBCC" alt="MIT license"></a>
</p>

# CueIvrit

**An open-source agent skill for English-to-Hebrew SRT subtitles.** CueIvrit guides translation, repair, and selective polishing while keeping each subtitle tied to the English cue ID and time window. It includes Python tools for preparation, structural validation, RTL output, and an audit trail.

The scripts **do not translate dialogue**. An AI assistant or human translator writes the Hebrew and reviews **every original cue** against the source. A passing structural check cannot certify meaning, gender choices, or how the subtitle looks in every player.

## At a glance

| What you bring | What the workflow produces |
| --- | --- |
| A synchronized English `.srt` for the same release | Hebrew `.srt` with original timing and IDs |
| Optional existing Hebrew subtitles for repair or polish | Cue-locked translation batches and validation reports |
| Optional series glossary and character context | A recorded bilingual editorial review |

For example, the source cue `12` at `00:01:20,000 --> 00:01:22,000` stays cue `12` at the same time. The translator changes its dialogue to natural Hebrew, then checks it against the English. Confirmed non-dialogue cues may be omitted without renumbering later cues.

See the [26-cue Sintel worked example](examples/README.md) for a licensed English SRT, a reviewed Hebrew output, and the commands used to verify cue integrity.

## Get started

1. Download or clone the repository and install its folder in the skills directory supported by your AI assistant. Keep `SKILL.md` beside `scripts/`, `references/`, `agents/`, and `assets/`.
2. Provide a synchronized English SRT. Ask: “Use `$hebrew-subtitle-translator` to translate this English SRT into Hebrew, preserve cue IDs and timing, and review every cue against the source.”
3. Follow [SKILL.md](SKILL.md) and the [Getting Started wiki guide](https://github.com/guy-tsarfati/hebrew-subtitle-translator/wiki/Getting-Started). The command-line helpers require Python 3.10+ and only the standard library.

```bash
python3 scripts/srt_pipeline.py prepare input.en.srt --work-dir work --sdh-mode remove
```

Preparation creates a manifest and translation batches. Translate every dialogue batch, review every source cue, then build and audit the output as described in the [Translation Workflow](https://github.com/guy-tsarfati/hebrew-subtitle-translator/wiki/Translation-Workflow). The scripts alone cannot produce a translated SRT.

## What makes it useful

- **Cue integrity:** Preserve numbering, order, source timing, and positioning. Never shift dialogue to a neighboring cue.
- **Hebrew output:** Write UTF-8 with BOM and the skill's tested RTL control profile.
- **Careful cleanup:** Review potential external subtitle credits and SDH descriptions against the source before removing them. Keep dialogue and lyrics.
- **Editorial context:** Track character gender, speakers, addressees, and recurring terminology. Review each original cue, including omissions.
- **Repeatable checks:** Flag missing or placeholder translations, suspicious wrappers, reading-speed issues, and structural mismatches.

See the [wiki](https://github.com/guy-tsarfati/hebrew-subtitle-translator/wiki) for setup, credit and SDH decisions, quality checks, and troubleshooting. Video transcription and automatic retiming are outside this workflow.

## Help and project status

See [Support](SUPPORT.md) for questions and useful feedback, the [Roadmap](ROADMAP.md) for priorities, and the [Changelog](CHANGELOG.md) for release history and pending checks.

## Contribute

Found a bug or a Hebrew edge case? Use the [issue templates](https://github.com/guy-tsarfati/hebrew-subtitle-translator/issues/new/choose). Changes to code, rules, or documentation are welcome through pull requests. Read [CONTRIBUTING.md](CONTRIBUTING.md) and follow the [Code of Conduct](CODE_OF_CONDUCT.md), and use short synthetic or permission-cleared subtitle examples. For a security concern, follow [SECURITY.md](SECURITY.md).

Run the synthetic checks locally:

```bash
python3 scripts/test_srt_pipeline.py
python3 -m unittest discover -s scripts -p 'test_quality_upgrade.py' -v
```

The [MIT license](LICENSE) covers this project's skill, code, and documentation. The Sintel example carries separate Creative Commons attribution and licensing, as explained in [its README](examples/README.md). Other source subtitles and translations may have separate rights.
