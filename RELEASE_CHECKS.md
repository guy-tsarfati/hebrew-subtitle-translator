# First release checks

Checked on 2026-10-07 against public commit `11c36683fc2ef3e2921c2228718dbe04009061dc`. This report records that snapshot. Later documentation and CI changes must pass their own checks before a release is tagged.

## Verified

- A fresh Git clone resolved to the stated commit.
- A project installation from GitHub through skills CLI 1.7.1 succeeded with `--skill hebrew-subtitle-translator --agent codex --yes --copy` in an empty directory. Test telemetry was disabled.
- `skills list --agent codex --json` reported the installed skill and project scope.
- All 22 files in SKILL.md, scripts, references, agents, assets, and examples matched the checkout byte for byte, excluding generated Python caches.
- Pipeline regressions passed, and all 10 quality regression tests passed in both the fresh checkout and the installed copy.
- Sintel was prepared, built, and audited in both locations. All 26 cues retained IDs and timing. The audit reported no structural errors or quality warnings.
- Both rebuilt Hebrew files were byte-identical to the committed example. SHA-256: `72e9ac916ad836d14f9c18d55c62dc36e5f9f7e911ee872034bc57febe646c51`.
- The example's Creative Commons attribution is separate from the skill's MIT license.

Environment: Linux, Python 3.12.14, Node.js 24.19.0, npm 11.9.0, skills CLI 1.7.1.

## Still open

- Visual player validation of the Hebrew SRT against the Sintel film. Neither actual playback nor player compatibility has been verified by this check.
- A full translation task inside the target assistant. CLI registration and helper execution do not establish assistant behavior.
- Tagging the final tested commit and publishing a numbered release.
- Downloading and checking the published release archive.

No numbered release is implied by this report. Structural tests do not prove semantic accuracy, character gender, or universal player compatibility.
