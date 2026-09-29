# Hebrew grammatical gender consistency

## Goal

Keep the grammatical gender of speakers and addressees consistent throughout the film or episode. English often omits distinctions that Hebrew requires, so resolve identity and scene context before choosing gendered Hebrew forms.

## Evidence hierarchy

Use evidence in this order:

1. Explicit self-identification, pronouns, kinship terms, titles, or direct statements in the subtitles.
2. Speaker labels and recurring names in the SRT.
3. Dialogue relationships and scene continuity, including who answers whom.
4. Reliable official character or cast information when the title is identifiable and external lookup is available.
5. Name-based inference only as weak supporting evidence. Never treat a name as conclusive.
6. Actor identity or appearance must not be the sole basis for a character's grammatical gender.

Record the evidence and confidence rather than silently guessing.

## Character bible

Create `character-bible.json` before translating. Start with:

```bash
python scripts/srt_pipeline.py character-template INPUT.en.srt \
  --output WORK_DIR/character-bible.json
```

Then review the entire subtitle source in larger narrative chunks and complete the file. Use this structure:

```json
{
  "schema_version": 1,
  "characters": [
    {
      "name": "Maya",
      "aliases": ["Dr. Levin"],
      "grammatical_gender": "feminine",
      "confidence": "high",
      "evidence": [
        {"cue_id": 184, "text": "She is our lead scientist."}
      ],
      "notes": "Usually addressed formally by the security team."
    }
  ],
  "relationships": [
    {
      "from": "Maya",
      "to": "Noah",
      "address_style": "informal singular",
      "notes": "Siblings"
    }
  ],
  "global_notes": []
}
```

Allowed grammatical gender values:

- `masculine`
- `feminine`
- `nonbinary`
- `unknown`

Allowed confidence values:

- `high`
- `medium`
- `low`
- `unresolved`

Update the bible when later dialogue provides stronger evidence. Do not change an established high-confidence decision without recording why.

## Speaker and addressee tracking

For every cue that requires a gendered Hebrew choice, infer both:

- Who is speaking
- Who is being addressed

Use the wider context arrays in each batch. The preceding speaker is not automatically the current addressee. Group exchanges by scene and track turn-taking, names, commands, replies, titles, and relationship terms.

Carry these state variables across batch boundaries:

- Active scene participants
- Last confirmed speaker
- Last confirmed addressee
- Current group or singular addressee
- Formal or informal address
- Recurring relationship terms

When a line begins a new scene or the participant set changes, reset uncertain conversational assumptions but retain the character bible.

## Confidence policy

### High confidence

Use the natural gendered Hebrew form.

### Medium confidence

Inspect at least four cues before and four cues after, plus the character bible and the current scene participants. Use a gendered form only when the combined evidence is persuasive.

### Low or unresolved confidence

Prefer a natural gender-neutral Hebrew reformulation that preserves meaning, tone, and timing. Do not guess merely to produce a direct translation.

Examples:

- `Are you ready?` can become `אפשר להתחיל?`
- `You were right.` can become `צדקת.` because the form is gender-neutral in unvocalized Hebrew
- `I'm glad you're here.` can become `טוב שבאת.` when context supports singular and the written form remains neutral
- `You're a good friend.` can become `איזה מזל שאנחנו חברים.` when a direct adjective would force an unsupported gender choice

Do not use slash forms such as `אתה/את`, `מוכן/ה`, or parentheses such as `מוכן(ה)`. Subtitles must read as natural dialogue.

Do not neutralize a line when doing so changes an important characterization, joke, insult, rank, relationship, or plot fact. Mark it for review instead.

## Group and politeness distinctions

Distinguish singular from plural addressees before selecting Hebrew forms. English `you` may refer to one person, a group, or an institution.

Track whether the line addresses:

- One named character
- Several visible or recently active characters
- A team, audience, public, or organization
- An unknown person over a phone, radio, or intercom

Prefer plural Hebrew only when the scene supports a group addressee. Do not use masculine plural as a default for an unknown singular addressee.

## Second-pass gender audit

After all batches are merged, review the full translation by character and relationship, not only by cue order.

Check:

- Every recurring character at the beginning, middle, and end
- Every cue translated with low or unresolved confidence
- All direct-address adjectives, participles, imperatives, and second-person past or future verbs
- Singular versus plural forms of `you`
- Titles, ranks, kinship terms, and relationship language
- Scenes where the speaker or addressee changes near a batch boundary
- Any character whose gender decision changed during translation

Correct inconsistencies in the translation JSON, rebuild the SRT, and rerun structural audit.

## QA reporting

Add a gender-consistency section to the QA summary containing only checks actually performed:

- Number of recurring characters in the bible
- Number with high, medium, low, or unresolved confidence
- Number of cues neutralized because gender was uncertain
- Number of gender inconsistencies corrected during the second pass
- Remaining unresolved cues, listed by cue ID with a brief reason

Never claim perfect gender accuracy when unresolved cues remain.
