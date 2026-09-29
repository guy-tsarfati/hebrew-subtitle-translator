# Hebrew subtitle translation rules

## Translation contract

Translate only the text in each cue's `source` field. Return exactly one output object for every input item:

```json
[
  {"cue_id": 101, "text": "תרגום עברי"},
  {"cue_id": 102, "text": ""}
]
```

Never change `cue_id`. Never add, merge, split, or reorder translation records. Context fields are for understanding only and must never be translated into another cue. Return an empty string when `translate` is false. The builder omits any such non-visible cue from the final SRT instead of creating a blank overlay. In `remove` mode this includes description-only SDH cues.

## Hebrew style

- Produce natural, concise spoken Hebrew rather than literal machine translation.
- Preserve meaning, tone, jokes, ranks, technical terminology, proper names, and continuity.
- Keep established franchise terminology consistent throughout the file.
- Preserve HTML subtitle tags such as `<i>...</i>` when they carry meaningful formatting.
- Use standard Hebrew punctuation at the natural logical end of the sentence.
- Do not manually insert bidi control characters. The builder adds RLE, a trailing RLM punctuation anchor, and PDF around each visible line.
- Keep sentence-final punctuation inside HTML formatting tags when the source formatting logically includes it, but never move punctuation into a neighboring cue.
- Keep each cue to one or two lines where practical.
- Aim for approximately 42 characters per line and avoid exceeding 48 characters unless necessary.
- Do not move a partial sentence into a neighboring cue.
- Do not invent dialogue omitted from the English source.

## Grammatical gender and addressee

Read [gender-consistency.md](gender-consistency.md) before translation.

- Use the character bible, scene participants, and full context windows to infer the speaker and addressee.
- Preserve a character's established grammatical gender and form of address throughout the file.
- Distinguish singular from plural `you` before choosing Hebrew forms.
- Treat names as supporting evidence only, not proof.
- When confidence is low, prefer a natural gender-neutral Hebrew reformulation instead of guessing.
- Never use slash forms such as `אתה/את` or `מוכן/ה`.
- Do not force neutral phrasing when it changes characterization, humor, plot meaning, rank, insult, or relationship information. Mark the cue for semantic review.
- Carry discoveries across batches by updating the character bible before continuing.

## SDH policy

The manifest and batch instructions contain the selected `sdh_mode`.

### Remove mode

- The preparation script removes only recognized descriptions and explicitly reviewed wrapper spans. Unknown wrappers remain for contextual review.
- Translate only the remaining dialogue or lyrics.
- Never reintroduce descriptions such as `(laughs)`, `(phone ringing)`, or `[door opens]`.
- When a cue contains both a description and dialogue, retain and translate only the dialogue.
- When nothing remains after cleaning, return an empty string. The builder must omit this cue from the final remove-mode SRT and preserve the original numbering of later emitted cues.

### Keep mode

- Translate accessibility descriptions naturally into Hebrew.
- Preserve the original wrapper type, either square brackets or parentheses.
- Keep descriptions in the same cue and position relative to dialogue.
- Do not convert a description into spoken dialogue or a speaker label.

## Music and speaker labels

- Remove music-note glyphs such as `♪`, `♫`, `♬`, and `♩` in both modes.
- Retain and translate song lyrics after removing music-note glyphs.
- Do not add speaker labels unless they exist in the source cue.

## Mixed-language text

English proper names, starship names, acronyms, registry numbers, formulas, and fictional terms may remain in Latin characters when transliteration would reduce clarity. The surrounding sentence must still be natural Hebrew.
