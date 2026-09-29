# CueIvrit worked example: Sintel

This small, real-world sample demonstrates a complete English-to-Hebrew cue-locked pass. The [Sintel film](https://studio.blender.org/projects/sintel/) is an open movie by the Blender Foundation. The English SRT here is based on [Wikimedia Commons' English timed text for the 4K release](https://commons.wikimedia.org/w/index.php?title=TimedText:Sintel_movie_4K.webm.en.srt&oldid=175198974). Blender also [provides English SRT subtitles](https://durian.blender.org/download/) on its official download page.

## Files

- `sintel.en.srt` - source, 26 numbered cues. One missing blank separator between cues 19 and 20 on the Commons page was normalized for strict SRT parsing. The words and timecodes were not changed.
- `character-bible.json` - Sintel's feminine grammatical gender follows the [official film description](https://studio.blender.org/projects/sintel/). Scales' gender is left unknown.
- `translations.json` - first Hebrew pass with one record per source cue.
- `reviewed-translations.json` - final cue text after a bilingual review of all 26 cues. Cues 18 and 22 were edited for more natural Hebrew.
- `sintel.he.srt` - final output built by the pipeline, with original IDs and timecodes, UTF-8 BOM, and the skill's RTL controls.

The structural audit passed for all 26 cues: no missing or extra IDs, time changes, empty overlays, RTL violations, or reading-speed warnings. That audit checks structure; it cannot certify translation meaning. The editorial pass used the English SRT and official character context. We have not checked this output visually in a video player. This example has no SDH descriptions or third-party subtitle credits, so it does not exercise those cleanup features.

## Rebuild and verify

Run from the repository root with Python 3.10+:

```bash
python3 scripts/srt_pipeline.py prepare examples/sintel.en.srt --work-dir work/sintel --sdh-mode remove --character-bible examples/character-bible.json
python3 scripts/srt_pipeline.py validate --manifest work/sintel/manifest.json --translations examples/reviewed-translations.json --strict
python3 scripts/srt_pipeline.py build --manifest work/sintel/manifest.json --translations examples/reviewed-translations.json --output work/sintel/rebuilt.he.srt --strict
python3 scripts/srt_pipeline.py audit --source examples/sintel.en.srt --target work/sintel/rebuilt.he.srt --report work/sintel/qa-report.json --sdh-mode remove
```

To repeat the full editorial workflow with your own changes, run `scripts/review_translation.py prepare` on your manifest and first-pass JSON. Review every generated cue, then use the fresh manifest and translation hashes in your review decisions before applying them. Hashes are intentionally bound to the local manifest, so a saved review envelope from another checkout is not portable.

## Attribution and license

Sintel and its published project material are © Blender Foundation under [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/). The English timed text copied from Wikimedia Commons is also subject to the site's [CC BY-SA 4.0 terms for page text](https://commons.wikimedia.org/wiki/Commons:Licensing). Attribution: Blender Foundation and [Wikimedia Commons contributors to this SRT revision](https://commons.wikimedia.org/w/index.php?title=TimedText:Sintel_movie_4K.webm.en.srt&oldid=175198974). The Hebrew subtitle adaptation and the example's translated dialogue JSON are shared under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). The root MIT license applies to the skill, scripts, and project documentation; it does not replace these source-content terms.
