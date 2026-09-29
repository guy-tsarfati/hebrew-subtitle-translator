# Full bilingual editorial review and continuity

## Persistent glossary

Use one verified glossary per series or franchise, not per release. Keep it outside the installed skill as a saved user project artifact. Load it with `prepare --glossary`. Example:

```json
{
  "schema_version": 1,
  "scope": {"title": "Original example series", "year": 2026},
  "revision": 1,
  "terms": [
    {"source": "Core Relay", "hebrew": "ממסר הליבה", "aliases": [], "category": "technical", "confidence": "high", "evidence": [{"episode": "S01E01", "cue_id": 42}], "notes": "Fictional device, not a radio station"}
  ],
  "style": {"register": "natural spoken Hebrew", "profanity": "preserve intensity", "names": "consistent transliteration"},
  "unresolved": []
}
```

Use title, year and franchise identity to avoid collisions. A glossary is a contextual decision aid, not a blind replacement table. Record evidence and revision for corrections. Do not assume invented or externally suggested terminology is established canon. Do not copy actor gender into character facts. Keep exact cue-to-speaker assignments episode-specific.

## Review contract

Read each review-input batch with the original English, initial Hebrew, context, character bible and glossary. All cues must receive a decision, even omitted ones. Record actual editorial work only. Never manufacture review attestations just to satisfy coverage.

Check meaning, negation, quantities, names, tense, idioms, jokes, insults, relationships, tone, register, speaker/addressee and gender. Prefer unchanged good wording. Check that adjacent split sentences remain in their own time windows. Review original source against cleanup so a removed phrase cannot disappear unnoticed.

Merge batch decisions into this envelope, copying the hashes supplied by the preparation script:

```json
{
  "manifest_sha256": "HASH_FROM_REVIEW_INPUT",
  "translations_sha256": "HASH_FROM_REVIEW_INPUT",
  "decisions": [
    {
      "cue_id": 1,
      "status": "accepted",
      "original_text": "אפשר להתחיל?",
      "text": "אפשר להתחיל?",
      "reason": "Faithful neutral question, fits context and display time",
      "speaker": "unknown",
      "addressee": "unknown",
      "gender_confidence": "unresolved",
      "source_cleanup_checked": true
    }
  ]
}
```

Use `accepted`, `corrected`, or `unresolved`. Supply before/after text and a nonempty reason. Accepted and unresolved rows must preserve original text. Corrected rows must stay inside their cue. A naturally neutral translation can be accepted despite unresolved identity if meaning is preserved. If neutrality would alter meaning, retain the uncertainty for user review rather than invent certainty.

All known original quality warnings require a reasoned decision. Repeated Hebrew can be legitimate (refrains, recurring replies). Foreign scripts, numbers-only cues and technical acronyms may be intentional. Do not invent Hebrew merely to satisfy a detector. If strict validation blocks legitimate non-Hebrew content, inspect it and use non-strict pipeline validation/build with an explicit documented exception. The editorial review CLI currently requires Hebrew on each visible cue and must be adapted or the limitation disclosed for such exceptional files, never falsify completion.

## Reading and layout

Count visible characters, excluding HTML and bidi controls, against original display duration. The 20 CPS warning is a configurable function-level heuristic, not certification. Aim for one or two lines around 42 characters, avoid over 48 where possible. Break at natural syntax boundaries. Never separate a name or article from its phrase needlessly. Preserve speaker dashes for two speakers. Shorten without omitting negatives, quantities, plot facts, humor or emotional intensity. Never retime to make the warning disappear.

## Evaluation

Run synthetic structural tests after script changes. Use `benchmark-cases.json` to translate miniature examples and assess the stated semantic requirements. Accept equally natural alternatives. Include every case when reporting coverage. Distinguish executable structure checks, semantic sample review, and observed player rendering. Do not infer feature-film quality or player compatibility from small synthetic cases.
