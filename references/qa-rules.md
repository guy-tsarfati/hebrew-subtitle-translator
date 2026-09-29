# Cue-lock and QA rules

A subtitle is structurally valid only when all of the following are true:

1. In `keep` mode, the target contains every source cue with visible content after reviewed external-credit removal. SDH descriptions remain.
2. In `remove` mode, omit only cues with no visible content after recognized/reviewed SDH removal, external-credit removal, and formatting cleanup.
3. Every emitted target cue retains the exact original numeric index and appears in source order. Gaps caused by omitted non-dialogue cues are valid and must not be renumbered.
4. Every emitted target cue uses the source timing line verbatim, including optional positioning settings.
5. No cue containing dialogue or lyrics is deleted, merged, split, shifted, or assigned to a neighboring cue.
6. No target cue is empty, whitespace-only, or bidi-control-only. Such cues can produce a visible blank subtitle overlay in players.
7. The target file is encoded as UTF-8 with BOM.
8. Every visible Hebrew subtitle line begins with U+202B RIGHT-TO-LEFT EMBEDDING and ends with U+200F RIGHT-TO-LEFT MARK followed by U+202C POP DIRECTIONAL FORMATTING.
9. The trailing U+200F remains after the visible text and closing HTML tags so neutral punctuation and mixed Hebrew-Latin text remain visually anchored.
10. Music-note glyphs are absent from the output.
11. In `remove` mode, confirmed accessibility descriptions are absent. Meaningful parenthetical dialogue remains.
12. In `keep` mode, sampled descriptions are translated and remain in their original cue and wrapper type.
13. Translation JSON has exactly one record per source cue and no duplicate cue IDs, including empty records for cues omitted only at build time.
14. Full bilingual editorial review covers every cue. Additional final spot checks cover the beginning, middle, end, SDH omission boundaries, punctuation-sensitive lines, mixed Hebrew-Latin lines, and grammatical-gender decisions.

## Semantic drift detection

Matching the expected emitted cue count and timecodes does not prove that the translation is synchronized. A file can be structurally correct while Hebrew text belongs to an adjacent English cue.

To prevent this:

- Translate from English cue records, not from a free-form copy of the SRT.
- Work in batches of about 20 to 35 cues.
- Use at least four source cues before and after the current cue as context.
- Require JSON output with immutable cue IDs.
- Validate each batch before merging.
- Never infer missing cue text from the previous or next translation.
- During repair, treat the English SRT as the sole source of truth.
- Align remove-mode targets against the expected emitted cue indexes rather than assuming equal source and target cue counts.
- Compare random source-target pairs after rebuilding.

## Gender-consistency QA

Read [gender-consistency.md](gender-consistency.md) and perform its second-pass audit.

- Confirm every recurring character has a character-bible entry or is explicitly marked unresolved.
- Check speaker and addressee separately.
- Review all low-confidence gender decisions.
- Review direct-address adjectives, participles, imperatives, and second-person verb forms.
- Check singular versus plural interpretations of English `you`.
- Compare each recurring character across early, middle, and late appearances.
- Inspect batch boundaries where a scene continues into the next batch.
- Confirm neutral reformulations preserve meaning and tone.
- Never report full gender consistency when unresolved cues remain.

## SDH-specific QA

For `remove` mode:

- Count all source cues containing square brackets or parentheses before cleanup.
- Review every retained wrapper and confirm no accessibility description remains. Preserve actual dialogue in wrappers.
- Inspect mixed cues to confirm dialogue remains after the description is removed.
- Confirm description-only cues and formatting-artifact-only cues are absent from the final target and listed under `omitted_non_dialogue_cues` in the QA report.
- Confirm `blank_overlay_cues` is empty.

For `keep` mode:

- Sample descriptions from the beginning, middle, and end.
- Confirm each description is translated rather than copied in English.
- Confirm brackets or parentheses are preserved.
- Confirm descriptions remain attached to the correct cue.

## Additional final QA sampling

Review at least:

- First 10 translatable cues
- 10 cues around 25%, 50%, and 75% of runtime
- Last 10 translatable cues
- Every cue immediately before and after an omitted non-dialogue cue
- At least 10 lines ending in periods, commas, question marks, exclamation marks, colons, or ellipses
- At least 5 mixed Hebrew-Latin lines, when available
- At least 10 mixed dialogue-plus-description cues
- Every low-confidence gender cue
- At least three scenes for every recurring character
- Every cue where the validator reports no Hebrew or unusually high English content

## Credit cleanup QA

Inspect each credit decision against the original source, even credit-only cues omitted from output. Confirm exact source hash and spans, preserved mixed dialogue, unchanged timing/IDs, and no blank overlays. Never remove film credits or meaningful URLs based solely on candidate keywords. Use the same cleanup decision file in prepare, import and audit.
