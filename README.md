# Hebrew Subtitle Translator

An agent skill for translating, repairing, and polishing English SRT subtitles into Hebrew. It keeps cue IDs and timing tied to the English source, supports conservative SDH and external subtitle-credit cleanup, and requires a complete bilingual editorial pass before delivery.

The Python tools prepare, validate, build, and audit subtitles. They **do not translate dialogue**. An AI assistant or human translator must write and review the Hebrew text.

## Use the skill

Copy this repository's folder into the skills directory supported by your AI assistant, or download the repository and add `SKILL.md` together with its `scripts/`, `references/`, `agents/`, and `assets/` directories. Invoke `hebrew-subtitle-translator` with an English SRT file. Follow the workflow in [SKILL.md](SKILL.md).

Example request:

> Use the Hebrew Subtitle Translator skill to translate this synchronized English SRT into Hebrew. Preserve timing and IDs, remove verified third-party subtitle credits, and review every cue against the English source.

The command-line helpers require Python 3.10 or newer and use only the standard library. For a first inspection:

```bash
python3 scripts/srt_pipeline.py --help
python3 scripts/srt_pipeline.py prepare input.en.srt --work-dir work --sdh-mode remove
```

The preparation step creates a manifest and translation batches. Translate all dialogue batches, run the editorial review, then build and audit the output as described in `SKILL.md`. The scripts alone cannot produce a translated SRT.

## What it checks

- Cue numbering, source timing, omitted-cue decisions, and UTF-8 BOM output with Hebrew direction controls
- Missing translations, repeated or placeholder text, reading-speed warnings, and suspicious wrappers
- Source-bound credit and SDH decisions, with every original cue included in editorial review
- Character and terminology consistency through optional reusable context files

Structural validation does not prove the translation's meaning, gender choices, or appearance in every player. Inspect the final result in the intended player when practical.

## Run the synthetic tests

```bash
python3 scripts/test_srt_pipeline.py
python3 -m unittest discover -s scripts -p 'test_quality_upgrade.py' -v
```

The repository includes no movie or television subtitle files. See [LICENSE](LICENSE) for the code and skill's license. Your source subtitles and translated outputs may have separate rights.
