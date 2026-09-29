# Remove third-party subtitle credits conservatively

Remove translator, synchronizer, uploader and subtitle-site promotional insertions. This user preference is independent of SDH keep/remove. Never confuse subtitle authorship with film credits or story content.

## Evidence and classification

1. Inspect candidate wording together with neighboring cues, timing, formatting and narrative context.
2. Strong combinations include a subtitle-specific attribution plus a handle, a subtitle-site promotion, or a credit plus a subtitle-format slogan.
3. Weak signals such as a URL, username, `Created by`, `Thanks`, `sync`, or a position at the opening/end are never sufficient alone.
4. Preserve film title cards, filmmaker credits, character speech about translation, spoken URLs, and lyrics. Preserve uncertain cases and report the cue ID.
5. A two-line credit can name its author on the second line. Review both lines together. Conversely, a credit and dialogue may share a line or cue. Remove only the confirmed credit span.
6. Inspect start/end and isolated promotional inserts even if regex finds nothing. Spaced-out site names and unfamiliar slogans may evade detection. No keyword list can guarantee recall.

## Illustrative example

Suppose an opening cue contains:

`Created by ExampleSubber          Enjoy single-line subs`

The attribution and subtitle-format slogan together suggest an external subtitle credit. Confirm it against the surrounding cues before removing it. Retain the remaining original IDs and timecodes. Do not generalize `Created by` into an unconditional removal rule. This synthetic example is not proof of detection on every site.

## Exact decision format

Use a file with the SHA256 of original source bytes and a `decisions` array. Each record carries `cue_id`, exact `source_text`, a nonempty `reason`, and `credit_spans`:

```json
{
  "cue_id": 1,
  "source_text": "Subtitles by ExampleUser\nHello.",
  "credit_spans": [{"start": 0, "end": 25, "text": "Subtitles by ExampleUser\n"}],
  "reason": "External subtitle attribution, preserve the spoken greeting"
}
```

Offsets are Python character offsets, end-exclusive, in the exact source_text returned by the parser (including tags and line breaks, excluding SRT block metadata). Compute offsets, do not guess. The script validates the original text and every span and rejects overlaps. Include associated formatting tags only when they belong wholly to the removed credit, leaving the remaining dialogue's tags balanced. Never combine wrapper removals and credit spans in the same cue decision. For a mixed cue that also contains recognized SDH, automatic SDH cleanup follows credit removal. For unfamiliar SDH in that cue, preserve it for review rather than falsely mark it as a credit.

Run prepare, import-target when applicable, and audit with the same `--cleanup-decisions` file. Audit retains the decisions. Full editorial review must compare original and cleaned source, including omitted credit-only cues. Do not remove a credit just by returning empty Hebrew while the source cue is still marked translatable.
