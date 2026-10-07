# Install CueIvrit

CueIvrit is an agent skill, not a standalone subtitle translator. Your AI assistant or a human translator supplies and reviews the Hebrew dialogue. The bundled helpers require Python 3.10+ and use only the standard library.

## Install with the skills CLI

Prerequisite: Node.js 22.20.0 or newer and npm, with `npx` available. The verified skills CLI 1.7.1 requires this Node.js minimum. From the project where you want to use CueIvrit:

```bash
npx skills add guy-tsarfati/hebrew-subtitle-translator --skill hebrew-subtitle-translator --agent codex --yes --copy
```

This creates `.agents/skills/hebrew-subtitle-translator/` in that project. It does not configure a browser-only ChatGPT conversation. The public brand is CueIvrit, while the installed skill identifier remains `hebrew-subtitle-translator`.

For a reproducible installer version, replace `npx skills` with `npx skills@1.7.1`. This pins the installer, not the repository revision. The command above follows the repository's default branch. Review the downloaded skill before using it. To disable the CLI's installation telemetry, set `DISABLE_TELEMETRY=1` in your shell before running it.

Verified on Linux with Node.js 24.19.0, npm 11.9.0, skills CLI 1.7.1, and Python 3.12.14. Installation registration and bundled tools were checked for the Codex target. This is not an end-to-end translation test in a Codex session. Other agents and operating systems have not been verified in this launch check.

## Check the installed helpers

Run from the project directory:

```bash
python3 .agents/skills/hebrew-subtitle-translator/scripts/test_srt_pipeline.py
python3 -m unittest discover -s .agents/skills/hebrew-subtitle-translator/scripts -p 'test_quality_upgrade.py' -v
```

On systems where Python is named `python`, substitute that executable. Keep `SKILL.md`, `scripts/`, `references/`, `agents/`, and `assets/` together. The installation also includes the licensed `examples/` directory.

To rebuild the included Sintel example, change into `.agents/skills/hebrew-subtitle-translator/` and follow [examples/README.md](examples/README.md). Use a new work directory for each source.

## Manual installation

Clone or download the repository and place the complete folder in your assistant's supported skill directory. Do not copy only `SKILL.md`. For an exact tested snapshot, check out the commit recorded in [RELEASE_CHECKS.md](RELEASE_CHECKS.md). Read [SKILL.md](SKILL.md) before running a translation.

Ask your assistant:

> Use $hebrew-subtitle-translator to translate this synchronized English SRT into Hebrew. Preserve cue IDs and timing, and review every cue against the source.

Include the English SRT for the same release. For problems or trial feedback, use the [issue forms](https://github.com/guy-tsarfati/hebrew-subtitle-translator/issues/new/choose).
