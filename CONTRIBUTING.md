# Contributing to CueIvrit

Thanks for helping make English-to-Hebrew subtitle work more reliable. Issues, documentation fixes, language edge cases, and focused code changes are welcome.

Please follow the [Code of Conduct](CODE_OF_CONDUCT.md) in all project spaces. It includes a private route for reporting conduct concerns.

## Before opening an issue

- Search existing issues and the [wiki](https://github.com/guy-tsarfati/hebrew-subtitle-translator/wiki).
- Use the bug or feature request form. Include a minimal example with cue IDs and timing when relevant.
- Share only synthetic, self-authored, or permission-cleared subtitle snippets. Do not upload complete third-party subtitle files or private media.
- Report a security vulnerability through the route in [SECURITY.md](SECURITY.md), not a public issue.

## Pull requests

1. Make one focused change and explain the real case it solves.
2. Preserve the contract in [SKILL.md](SKILL.md): cue IDs and source timing stay fixed, dialogue and lyrics are retained, cleanup decisions are source-bound, and a structural PASS is not a claim of semantic accuracy.
3. Add or adjust a synthetic regression case when behavior changes. Keep fixtures small and free of copyrighted dialogue.
4. Run the commands below and describe any player-specific visual check you performed for RTL changes.
5. Update the README or wiki when a contributor-facing workflow changes.

```bash
python3 scripts/test_srt_pipeline.py
python3 -m unittest discover -s scripts -p 'test_quality_upgrade.py' -v
```

For wording or translation-rule proposals, describe the English meaning, the proposed Hebrew, the speaker and addressee context, and the reason for your choice. Keep disagreements about language specific and respectful. Maintainers may ask for a smaller reproduction before merging.
