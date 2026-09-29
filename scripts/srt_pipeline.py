#!/usr/bin/env python3
"""Cue-locked SRT preparation, rebuilding, and validation for Hebrew subtitles.

This script deliberately does not call a translation API. It prepares immutable cue
records for translation by ChatGPT, then rebuilds the target SRT from the original
English numbering and timecodes only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable
from quality_checks import remove_known_sdh, wrapper_findings, known_sdh, WRAPPERS, quality_signals, credit_candidates

INPUT_ENCODINGS: dict[str, str] = {}
SDH_DECISIONS: dict[int, dict] = {}

RLM = "\u200f"
RLE = "\u202b"
PDF = "\u202c"
BIDI_CONTROLS = "\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069"
MUSIC_CHARS = "♪♫♬♩"
TIMING_RE = re.compile(
    r"^(?P<start>\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*"
    r"(?P<end>\d{2}:\d{2}:\d{2}[,.]\d{3})(?P<settings>.*)$"
)
BLOCK_RE = re.compile(
    r"^\s*(?P<index>\d+)\s*\n(?P<timing>[^\n]+)\n(?P<text>.*)$",
    re.DOTALL,
)
SPEAKER_LABEL_RE = re.compile(
    r"^\s*(?:[-–—]\s*)?(?:<[^>]+>\s*)*(?P<name>[A-Z][A-Z0-9 .'-]{1,40}|[A-Z][a-z]+(?:[ -][A-Z][a-z]+){0,3})\s*:\s*"
)


class SrtError(RuntimeError):
    pass


@dataclass(frozen=True)
class Cue:
    ordinal: int
    index: int
    timing: str
    start: str
    end: str
    settings: str
    source_text: str
    clean_text: str
    translate: bool
    source_line_count: int


def read_text(path: Path) -> str:
    data = path.read_bytes()
    explicit = INPUT_ENCODINGS.get(str(path.resolve()))
    if explicit:
        try:
            return normalize_newlines(data.decode(explicit))
        except (UnicodeError, LookupError) as exc:
            raise SrtError(f"Cannot decode {path} using {explicit}") from exc
    try:
        return normalize_newlines(data.decode("utf-8-sig"))
    except UnicodeDecodeError:
        # Legacy encodings are ambiguous. Require an explicit choice rather than
        # silently accepting mojibake as valid Latin text.
        raise SrtError(f"Non-UTF-8 input: {path}. Inspect encoding and use --source-encoding or --target-encoding (cp1255, iso-8859-8, cp1252).")


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def parse_srt(path: Path, *, clean_source: bool = True, sdh_mode: str = "remove") -> list[Cue]:
    raw = normalize_newlines(read_text(path)).strip("\n\ufeff")
    if not raw:
        raise SrtError(f"SRT file is empty: {path}")

    blocks = re.split(r"\n{2,}", raw)
    cues: list[Cue] = []
    seen_indexes: set[int] = set()

    for ordinal, block in enumerate(blocks, start=1):
        match = BLOCK_RE.match(block)
        if not match:
            preview = block[:120].replace("\n", " | ")
            raise SrtError(f"Malformed SRT block {ordinal}: {preview}")

        index = int(match.group("index"))
        if index in seen_indexes:
            raise SrtError(f"Duplicate cue index {index}")
        seen_indexes.add(index)

        timing = match.group("timing").strip()
        timing_match = TIMING_RE.match(timing)
        if not timing_match:
            raise SrtError(f"Invalid timing line for cue {index}: {timing}")

        source_text = match.group("text").strip("\n")
        cleaning_input = source_text
        decision = SDH_DECISIONS.get(index) if clean_source else None
        if decision:
            if decision.get("source_text") != source_text or not decision.get("reason"):
                raise SrtError(f"Stale or undocumented cleanup decision at cue {index}")
            # A replacement is allowed only by removing exact complete wrappers.
            for wrapper in decision.get("remove", []) if sdh_mode == "remove" else []:
                if not isinstance(wrapper, str) or not WRAPPERS.fullmatch(wrapper) or wrapper not in cleaning_input:
                    raise SrtError(f"Invalid cleanup span at cue {index}")
                cleaning_input = cleaning_input.replace(wrapper, "")
            # Credits use exact original character offsets and an explicit review.
            spans = decision.get("credit_spans", [])
            previous_end = 0
            for span in sorted(spans, key=lambda x: x["start"]):
                start, end = span.get("start"), span.get("end")
                if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(source_text) or start < previous_end or source_text[start:end] != span.get("text"):
                    raise SrtError(f"Invalid credit span at cue {index}")
                previous_end = end
            if spans and decision.get("remove"):
                raise SrtError("Do not mix SDH wrapper removals and credit spans in one cue decision")
            for span in sorted(spans, key=lambda x: x["start"], reverse=True):
                cleaning_input = cleaning_input[:span["start"]] + cleaning_input[span["end"]:]
        clean_text = clean_sdh(cleaning_input, sdh_mode=sdh_mode) if clean_source else source_text
        source_lines = source_text.splitlines() if source_text else []

        cues.append(
            Cue(
                ordinal=ordinal,
                index=index,
                timing=timing,
                start=timing_match.group("start"),
                end=timing_match.group("end"),
                settings=timing_match.group("settings"),
                source_text=source_text,
                clean_text=clean_text,
                translate=bool(strip_formatting(clean_text).strip()),
                source_line_count=len(source_lines),
            )
        )

    return cues


def strip_bidi(text: str) -> str:
    return text.translate({ord(ch): None for ch in BIDI_CONTROLS})


def strip_formatting(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


def remove_parenthetical_sdh(line: str) -> str:
    return remove_known_sdh(line)


def clean_sdh(text: str, *, sdh_mode: str = "remove") -> str:
    """Clean accessibility text without deleting the cue.

    In remove mode, only recognized SDH wrappers are stripped. Unknown wrappers
    survive for contextual review, protecting meaningful parenthetical dialogue. In keep mode, descriptions
    remain available for translation. Music-note glyphs are removed in both modes,
    but lyric text is retained.
    """
    if sdh_mode not in {"remove", "keep"}:
        raise SrtError(f"Unsupported SDH mode: {sdh_mode}")

    normalized = strip_bidi(normalize_newlines(text))
    if sdh_mode == "remove":
        normalized = remove_known_sdh(normalized)

    cleaned_lines: list[str] = []
    for raw_line in normalized.splitlines():
        line = raw_line.translate({ord(ch): None for ch in MUSIC_CHARS})
        line = re.sub(r"[ \t]+", " ", line).strip()
        line = re.sub(r"\s+([,.;:!?])", r"\1", line)
        line = re.sub(r"(?:\s*(?:--|–|—))\s*$", "", line).strip()
        line = re.sub(r"<i>\s*</i>", "", line, flags=re.IGNORECASE)
        line = re.sub(r"<b>\s*</b>", "", line, flags=re.IGNORECASE)
        visible_line = strip_formatting(line).strip()
        if re.fullmatch(r"(?:_+|[-–—]+)", visible_line):
            continue
        if line:
            cleaned_lines.append(line)
    return "\n".join(cleaned_lines)

def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def context_records(cues: list[Cue], position: int, radius: int, *, before: bool) -> list[dict[str, Any]]:
    if before:
        start = max(0, position - radius)
        positions = range(start, position)
    else:
        positions = range(position + 1, min(len(cues), position + radius + 1))
    return [
        {
            "cue_id": cues[pos].index,
            "start": cues[pos].start,
            "end": cues[pos].end,
            "source": cues[pos].clean_text,
        }
        for pos in positions
    ]


def cue_to_batch_item(cues: list[Cue], position: int, context_window: int) -> dict[str, Any]:
    cue = cues[position]
    return {
        "cue_id": cue.index,
        "ordinal": cue.ordinal,
        "start": cue.start,
        "end": cue.end,
        "source": cue.clean_text,
        "translate": cue.translate,
        "source_line_count": cue.source_line_count,
        "context_before": context_records(cues, position, context_window, before=True),
        "context_after": context_records(cues, position, context_window, before=False),
    }


def load_optional_json(path_value: str | None) -> Any:
    if not path_value:
        return None
    path = Path(path_value).resolve()
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise SrtError(f"Expected a JSON object in {path}")
    return payload


def extract_speaker_labels(cues: list[Cue]) -> list[dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for cue in cues:
        for raw_line in cue.source_text.splitlines():
            line = strip_formatting(raw_line)
            match = SPEAKER_LABEL_RE.match(line)
            if not match:
                continue
            name = re.sub(r"\s+", " ", match.group("name")).strip(" .")
            key = name.casefold()
            entry = found.setdefault(key, {
                "name": name,
                "aliases": [],
                "grammatical_gender": "unknown",
                "confidence": "unresolved",
                "evidence": [],
                "first_cue": cue.index,
                "last_cue": cue.index,
                "occurrences": 0,
                "notes": "",
            })
            entry["last_cue"] = cue.index
            entry["occurrences"] += 1
            if len(entry["evidence"]) < 5:
                entry["evidence"].append({"cue_id": cue.index, "text": raw_line.strip()})
    return sorted(found.values(), key=lambda item: (-item["occurrences"], item["name"].casefold()))


def command_character_template(args: argparse.Namespace) -> int:
    source = Path(args.source).resolve()
    output = Path(args.output).resolve()
    cues = parse_srt(source, clean_source=False, sdh_mode="keep")
    characters = extract_speaker_labels(cues)
    payload = {
        "schema_version": 1,
        "source_filename": source.name,
        "instructions": {
            "purpose": "Resolve recurring character identities and Hebrew grammatical gender before translation.",
            "gender_values": ["masculine", "feminine", "nonbinary", "unknown"],
            "confidence_values": ["high", "medium", "low", "unresolved"],
            "evidence": "Use explicit dialogue, names, titles, relationships, pronouns, official character information, and scene continuity. Do not infer solely from an actor's appearance or name.",
            "unknown_policy": "Keep unknown when evidence is insufficient and prefer natural gender-neutral Hebrew phrasing during translation.",
        },
        "characters": characters,
        "relationships": [],
        "global_notes": [],
    }
    write_json(output, payload)
    print(json.dumps({
        "status": "character_template_created",
        "source": str(source),
        "output": str(output),
        "detected_speaker_labels": len(characters),
    }, ensure_ascii=False, indent=2))
    return 0


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def command_prepare(args: argparse.Namespace) -> int:
    source = Path(args.source).resolve()
    work_dir = Path(args.work_dir).resolve()
    batch_dir = work_dir / "batches"
    batch_dir.mkdir(parents=True, exist_ok=True)

    cues = parse_srt(source, sdh_mode=args.sdh_mode)
    character_bible = load_optional_json(args.character_bible)
    manifest = {
        "schema_version": 3,
        "source_filename": source.name,
        "source_path": str(source),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "cue_count": len(cues),
        "batch_size": args.batch_size,
        "context_window": args.context_window,
        "sdh_mode": args.sdh_mode,
        "sdh_decisions": list(SDH_DECISIONS.values()),
        "character_bible": character_bible,
        "glossary": load_optional_json(getattr(args, "glossary", None)),
        "rtl": {
            "encoding": "utf-8-sig",
            "mode": "embedding",
            "line_prefix": "U+202B RLE",
            "line_suffix": "U+200F RLM + U+202C PDF",
            "empty_cue_policy": "omit cues with no visible text after cleanup",
        },
        "credit_candidates": [{"cue_id": cue.index, "matches": credit_candidates(cue.source_text)} for cue in cues if credit_candidates(cue.source_text)],
        "cleanup_review": [{"cue_id": cue.index, "wrappers": wrapper_findings(cue.source_text)} for cue in cues if wrapper_findings(cue.source_text)],
        "cues": [asdict(cue) for cue in cues],
    }
    write_json(work_dir / "manifest.json", manifest)

    for old in batch_dir.glob("batch_*.json"):
        old.unlink()

    batch_number = 0
    for start in range(0, len(cues), args.batch_size):
        batch_number += 1
        positions = range(start, min(start + args.batch_size, len(cues)))
        payload = {
            "schema_version": 3,
            "batch_number": batch_number,
            "source_filename": source.name,
            "character_bible": character_bible,
            "glossary": load_optional_json(getattr(args, "glossary", None)),
            "instructions": {
                "output": "Return a JSON array with exactly one object per item: {cue_id, text}.",
                "lock": "Do not add, merge, split, reorder, or renumber cues. Keep one translation record per source cue.",
                "empty": "If translate is false, return an empty string. The builder omits that non-visible cue from the final SRT so no blank subtitle overlay appears.",
                "cleanup": (
                    "Do not add square-bracket or parenthetical SDH descriptions. Remove music-note glyphs."
                    if args.sdh_mode == "remove"
                    else "Translate SDH descriptions and preserve their brackets or parentheses. Remove music-note glyphs."
                ),
                "gender": "Use the character bible and the full context windows to keep speaker and addressee gender consistent. When evidence is low, prefer natural gender-neutral Hebrew rather than guessing. Never use slash forms such as אתה/את or מוכן/ה.",
                "continuity": "Carry established speaker, addressee, relationship, title, and grammatical-gender decisions across batches. Record new high-confidence discoveries in the character bible before continuing.",
            },
            "items": [cue_to_batch_item(cues, pos, args.context_window) for pos in positions],
        }
        write_json(batch_dir / f"batch_{batch_number:04d}.json", payload)

    template = [
        {"cue_id": cue.index, "text": ""}
        for cue in cues
    ]
    write_json(work_dir / "translations.template.json", template)

    translatable = sum(1 for cue in cues if cue.translate)
    print(json.dumps({
        "status": "prepared",
        "source": str(source),
        "work_dir": str(work_dir),
        "cue_count": len(cues),
        "translatable_cues": translatable,
        "non_dialogue_cues_to_omit": len(cues) - translatable,
        "batch_count": batch_number,
        "context_window": args.context_window,
        "character_bible_loaded": character_bible is not None,
    }, ensure_ascii=False, indent=2))
    return 0


def load_translation_payload(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, dict) and "translations" in payload:
        payload = payload["translations"]
    if not isinstance(payload, list):
        raise SrtError(f"Translation file must be a JSON array: {path}")
    return payload


def normalize_translation_record(record: Any, source: Path) -> tuple[int, str]:
    if not isinstance(record, dict):
        raise SrtError(f"Invalid translation record in {source}: expected object")
    if "cue_id" not in record or "text" not in record:
        raise SrtError(f"Translation record missing cue_id/text in {source}")
    try:
        cue_id = int(record["cue_id"])
    except (TypeError, ValueError) as exc:
        raise SrtError(f"Invalid cue_id in {source}: {record.get('cue_id')}") from exc
    text = record["text"]
    if text is None:
        text = ""
    if not isinstance(text, str):
        raise SrtError(f"Invalid text for cue {cue_id} in {source}")
    return cue_id, normalize_newlines(text).strip("\n")


def command_merge(args: argparse.Namespace) -> int:
    input_dir = Path(args.input_dir).resolve()
    output = Path(args.output).resolve()
    files = sorted(input_dir.glob("*.json"))
    if not files:
        raise SrtError(f"No JSON files found in {input_dir}")

    merged: dict[int, str] = {}
    for path in files:
        for record in load_translation_payload(path):
            cue_id, text = normalize_translation_record(record, path)
            if cue_id in merged:
                raise SrtError(f"Duplicate cue_id {cue_id} across translated batches")
            merged[cue_id] = text

    write_json(output, [
        {"cue_id": cue_id, "text": merged[cue_id]}
        for cue_id in sorted(merged)
    ])
    print(json.dumps({"status": "merged", "files": len(files), "translations": len(merged), "output": str(output)}, indent=2))
    return 0


def load_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or "cues" not in payload:
        raise SrtError(f"Invalid manifest: {path}")
    return payload


def translation_map(path: Path) -> dict[int, str]:
    result: dict[int, str] = {}
    for record in load_translation_payload(path):
        cue_id, text = normalize_translation_record(record, path)
        if cue_id in result:
            raise SrtError(f"Duplicate cue_id {cue_id} in {path}")
        result[cue_id] = text
    return result


def visible_english_letters(text: str) -> int:
    return len(re.findall(r"[A-Za-z]", strip_formatting(text)))


def visible_hebrew_letters(text: str) -> int:
    return len(re.findall(r"[\u0590-\u05FF]", strip_formatting(text)))


def clean_target_text(text: str, *, sdh_mode: str = "remove") -> str:
    text = clean_sdh(text, sdh_mode=sdh_mode)
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = strip_bidi(raw_line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def wrap_rtl(text: str, *, sdh_mode: str = "remove") -> str:
    """Wrap visible lines in a forced RTL embedding with a trailing RTL mark.

    RLE establishes a stable right-to-left paragraph direction. The trailing RLM
    anchors neutral punctuation before PDF closes the embedding, reducing cases
    where periods, commas, question marks, or mixed Latin text jump to the right.
    Empty text returns an empty string and must never be emitted as an SRT cue.
    """
    cleaned = clean_target_text(text, sdh_mode=sdh_mode)
    if not cleaned:
        return ""
    return "\n".join(f"{RLE}{line}{RLM}{PDF}" for line in cleaned.splitlines())


def should_emit_cue(cue: dict[str, Any], *, sdh_mode: str) -> bool:
    """Return whether a source cue has visible text and belongs in the target SRT."""
    return bool(cue.get("translate"))


def validate_translation_set(manifest: dict[str, Any], translations: dict[int, str], *, strict: bool) -> dict[str, Any]:
    cues = manifest["cues"]
    expected_ids = [int(cue["index"]) for cue in cues]
    expected = set(expected_ids)
    actual = set(translations)

    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    blank_required: list[int] = []
    bracket_violations: list[int] = []
    parenthetical_violations: list[int] = []
    music_violations: list[int] = []
    english_heavy: list[int] = []
    no_hebrew: list[int] = []
    line_warnings: list[dict[str, Any]] = []

    sdh_mode = manifest.get("sdh_mode", "remove")

    for cue in cues:
        cue_id = int(cue["index"])
        if cue_id not in translations:
            continue
        text = translations[cue_id]
        if cue["translate"] and not clean_target_text(text, sdh_mode=sdh_mode):
            blank_required.append(cue_id)
        if sdh_mode == "remove" and any(known_sdh(m[0]) and m[0].startswith("[") for m in WRAPPERS.finditer(text)):
            bracket_violations.append(cue_id)
        if sdh_mode == "remove" and any(known_sdh(m[0]) and m[0].startswith("(") for m in WRAPPERS.finditer(text)):
            parenthetical_violations.append(cue_id)
        if any(ch in text for ch in MUSIC_CHARS):
            music_violations.append(cue_id)
        if cue["translate"] and clean_target_text(text, sdh_mode=sdh_mode):
            he = visible_hebrew_letters(text)
            en = visible_english_letters(text)
            if he == 0:
                no_hebrew.append(cue_id)
            if en > max(12, he):
                english_heavy.append(cue_id)
            lines = clean_target_text(text, sdh_mode=sdh_mode).splitlines()
            if len(lines) > 2 or any(len(strip_formatting(line)) > 48 for line in lines):
                line_warnings.append({"cue_id": cue_id, "line_count": len(lines), "max_length": max(len(strip_formatting(line)) for line in lines)})

    errors = {
        "missing_ids": missing,
        "extra_ids": extra,
        "blank_required": blank_required,
        "bracket_violations": bracket_violations,
        "parenthetical_violations": parenthetical_violations,
        "music_violations": music_violations,
    }
    warnings = {
        "no_hebrew": no_hebrew,
        "english_heavy": english_heavy,
        "readability": line_warnings,
    }
    quality = quality_signals(cues, translations)
    errors.update(quality["errors"])
    warnings.update(quality["warnings"])
    passed = not any(errors.values()) and (not strict or not no_hebrew)
    return {"passed": passed, "strict": strict, "errors": errors, "warnings": warnings}


def command_validate(args: argparse.Namespace) -> int:
    manifest = load_manifest(Path(args.manifest).resolve())
    translations = translation_map(Path(args.translations).resolve())
    report = validate_translation_set(manifest, translations, strict=args.strict)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 2


def command_build(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest).resolve()
    translations_path = Path(args.translations).resolve()
    output = Path(args.output).resolve()

    manifest = load_manifest(manifest_path)
    translations = translation_map(translations_path)
    report = validate_translation_set(manifest, translations, strict=args.strict)
    if not report["passed"]:
        print(json.dumps(report, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SrtError("Translation validation failed; output was not built")

    sdh_mode = manifest.get("sdh_mode", "remove")
    blocks: list[str] = []
    omitted_cues: list[int] = []
    for cue in manifest["cues"]:
        cue_id = int(cue["index"])
        if not should_emit_cue(cue, sdh_mode=sdh_mode):
            omitted_cues.append(cue_id)
            continue
        text = translations.get(cue_id, "")
        rtl_text = wrap_rtl(text, sdh_mode=sdh_mode)
        if not rtl_text:
            raise SrtError(f"Cue {cue_id} would create a blank subtitle overlay")
        blocks.append(f"{cue_id}\n{cue['timing']}\n{rtl_text}")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n\n".join(blocks) + "\n", encoding="utf-8-sig")
    print(json.dumps({
        "status": "built",
        "output": str(output),
        "source_cue_count": len(manifest["cues"]),
        "output_cue_count": len(blocks),
        "omitted_non_dialogue_cues": omitted_cues,
        "encoding": "utf-8-sig",
        "rtl": "RLE prefix with trailing RLM before PDF",
        "validation_warnings": report["warnings"],
    }, ensure_ascii=False, indent=2))
    return 0


def parse_target_raw(path: Path) -> list[dict[str, Any]]:
    raw = normalize_newlines(read_text(path)).strip("\n\ufeff")
    blocks = re.split(r"\n{2,}", raw) if raw else []
    result: list[dict[str, Any]] = []
    for ordinal, block in enumerate(blocks, start=1):
        match = BLOCK_RE.match(block)
        if not match:
            raise SrtError(f"Malformed target SRT block {ordinal}")
        timing = match.group("timing").strip()
        if not TIMING_RE.match(timing):
            raise SrtError(f"Invalid target timing at block {ordinal}: {timing}")
        result.append({
            "ordinal": ordinal,
            "index": int(match.group("index")),
            "timing": timing,
            "text": match.group("text").strip("\n"),
        })
    return result


def command_audit(args: argparse.Namespace) -> int:
    source = Path(args.source).resolve()
    target = Path(args.target).resolve()
    report_path = Path(args.report).resolve() if args.report else None

    source_cues = parse_srt(source, sdh_mode=args.sdh_mode)
    expected_cues = [cue for cue in source_cues if cue.translate]
    target_cues = parse_target_raw(target)

    count_match = len(expected_cues) == len(target_cues)
    expected_indexes = {cue.index for cue in expected_cues}
    target_indexes = {int(cue["index"]) for cue in target_cues}
    missing_output_cues = sorted(expected_indexes - target_indexes)
    unexpected_output_cues = sorted(target_indexes - expected_indexes)
    index_mismatches: list[dict[str, Any]] = []
    timing_mismatches: list[dict[str, Any]] = []
    rtl_violations: list[int] = []
    punctuation_direction_violations: list[int] = []
    blank_overlay_cues: list[int] = []
    bracket_violations: list[int] = []
    parenthetical_violations: list[int] = []
    music_violations: list[int] = []

    for position in range(min(len(expected_cues), len(target_cues))):
        src = expected_cues[position]
        tgt = target_cues[position]
        if src.index != tgt["index"]:
            index_mismatches.append({"ordinal": position + 1, "source": src.index, "target": tgt["index"]})
        if src.timing != tgt["timing"]:
            timing_mismatches.append({"cue_id": src.index, "source": src.timing, "target": tgt["timing"]})
        lines = tgt["text"].splitlines()
        if not lines:
            blank_overlay_cues.append(tgt["index"])
        else:
            for line in lines:
                plain = strip_bidi(line).strip()
                if not plain:
                    blank_overlay_cues.append(tgt["index"])
                    break
                visible = strip_formatting(plain).rstrip()
                needs_punctuation_anchor = bool(
                    re.search(r"[.,;:!?…][\"'»”’)]?$", visible)
                    or re.search(r"[A-Za-z0-9]", visible)
                )
                if not (line.startswith(RLE) and line.endswith(PDF)):
                    rtl_violations.append(tgt["index"])
                    if needs_punctuation_anchor:
                        punctuation_direction_violations.append(tgt["index"])
                    break
                body = line[len(RLE):-len(PDF)]
                if not body.endswith(RLM):
                    rtl_violations.append(tgt["index"])
                    if needs_punctuation_anchor:
                        punctuation_direction_violations.append(tgt["index"])
                    break
        if args.sdh_mode == "remove" and any(known_sdh(m[0]) and m[0].startswith("[") for m in WRAPPERS.finditer(tgt["text"])):
            bracket_violations.append(tgt["index"])
        if args.sdh_mode == "remove" and any(known_sdh(m[0]) and m[0].startswith("(") for m in WRAPPERS.finditer(tgt["text"])):
            parenthetical_violations.append(tgt["index"])
        if any(ch in tgt["text"] for ch in MUSIC_CHARS):
            music_violations.append(tgt["index"])

    quality = quality_signals([asdict(c) for c in source_cues], {c["index"]: c["text"] for c in target_cues})
    has_bom = target.read_bytes().startswith(b"\xef\xbb\xbf")
    omitted_non_dialogue_cues = [cue.index for cue in source_cues if not cue.translate]
    report = {
        "passed": (
            count_match
            and not any(quality["errors"].values())
            and not missing_output_cues
            and not unexpected_output_cues
            and not index_mismatches
            and not timing_mismatches
            and not rtl_violations
            and not punctuation_direction_violations
            and not blank_overlay_cues
            and not bracket_violations
            and not parenthetical_violations
            and not music_violations
            and has_bom
        ),
        "quality": quality,
        "source": str(source),
        "target": str(target),
        "source_cues": len(source_cues),
        "expected_target_cues": len(expected_cues),
        "target_cues": len(target_cues),
        "count_match": count_match,
        "has_utf8_bom": has_bom,
        "omitted_non_dialogue_cues": omitted_non_dialogue_cues,
        "reviewed_cleanup": list(SDH_DECISIONS.values()),
        "missing_output_cues": missing_output_cues,
        "unexpected_output_cues": unexpected_output_cues,
        "index_mismatches": index_mismatches,
        "timing_mismatches": timing_mismatches,
        "rtl_violations": sorted(set(rtl_violations)),
        "punctuation_direction_violations": sorted(set(punctuation_direction_violations)),
        "blank_overlay_cues": sorted(set(blank_overlay_cues)),
        "sdh_mode": args.sdh_mode,
        "bracket_violations": bracket_violations,
        "parenthetical_violations": parenthetical_violations,
        "music_violations": music_violations,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "target_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
    }

    if report_path:
        write_json(report_path, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 2


def command_import_target(args: argparse.Namespace) -> int:
    source = Path(args.source).resolve()
    target = Path(args.target).resolve()
    output = Path(args.output).resolve()
    source_cues = parse_srt(source, sdh_mode=args.sdh_mode)
    expected_cues = [cue for cue in source_cues if cue.translate]
    target_cues = parse_target_raw(target)

    legacy_full_layout = len(target_cues) == len(source_cues)
    if len(target_cues) == len(expected_cues):
        alignment_cues = expected_cues
    elif legacy_full_layout:
        alignment_cues = source_cues
    else:
        raise SrtError(
            "Cue count mismatch after SDH policy: "
            f"expected={len(expected_cues)} or legacy={len(source_cues)} target={len(target_cues)}"
        )

    imported: dict[int, str] = {}
    for src, tgt in zip(alignment_cues, target_cues):
        if src.index != tgt["index"] or src.timing != tgt["timing"]:
            raise SrtError(f"Target is not cue-locked at source cue {src.index}")
        text = clean_target_text(tgt["text"], sdh_mode=args.sdh_mode)
        if not src.translate:
            imported[src.index] = ""
            continue
        if not text:
            raise SrtError(f"Target cue {src.index} is visually blank")
        imported[src.index] = text

    records: list[dict[str, Any]] = []
    for src in source_cues:
        records.append({"cue_id": src.index, "text": imported.get(src.index, "")})

    write_json(output, records)
    print(json.dumps({
        "status": "imported",
        "translations": len(records),
        "legacy_full_layout_detected": legacy_full_layout,
        "omitted_non_dialogue_cues": [cue.index for cue in source_cues if not cue.translate],
        "output": str(output),
    }, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cue-locked Hebrew SRT translation pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare", help="Parse an English SRT and create locked translation batches")
    prepare.add_argument("source")
    prepare.add_argument("--work-dir", required=True)
    prepare.add_argument("--batch-size", type=int, default=30)
    prepare.add_argument("--context-window", type=int, default=4)
    prepare.add_argument("--character-bible")
    prepare.add_argument("--glossary")
    prepare.add_argument("--sdh-mode", choices=("remove", "keep"), default="remove")
    prepare.set_defaults(func=command_prepare)

    character_template = sub.add_parser("character-template", help="Create a character and gender bible template from explicit speaker labels")
    character_template.add_argument("source")
    character_template.add_argument("--output", required=True)
    character_template.set_defaults(func=command_character_template)

    merge = sub.add_parser("merge", help="Merge translated JSON batch files")
    merge.add_argument("--input-dir", required=True)
    merge.add_argument("--output", required=True)
    merge.set_defaults(func=command_merge)

    validate = sub.add_parser("validate", help="Validate translated JSON against a manifest")
    validate.add_argument("--manifest", required=True)
    validate.add_argument("--translations", required=True)
    validate.add_argument("--strict", action="store_true")
    validate.set_defaults(func=command_validate)

    build = sub.add_parser("build", help="Build a Hebrew SRT from locked translations")
    build.add_argument("--manifest", required=True)
    build.add_argument("--translations", required=True)
    build.add_argument("--output", required=True)
    build.add_argument("--strict", action="store_true")
    build.set_defaults(func=command_build)

    audit = sub.add_parser("audit", help="Verify exact numbering/timecodes, RTL, encoding, and cleanup")
    audit.add_argument("--source", required=True)
    audit.add_argument("--target", required=True)
    audit.add_argument("--report")
    audit.add_argument("--sdh-mode", choices=("remove", "keep"), default="remove")
    audit.set_defaults(func=command_audit)

    import_target = sub.add_parser("import-target", help="Import a cue-locked Hebrew SRT into translation JSON")
    import_target.add_argument("--source", required=True)
    import_target.add_argument("--target", required=True)
    import_target.add_argument("--output", required=True)
    import_target.add_argument("--sdh-mode", choices=("remove", "keep"), default="remove")
    import_target.set_defaults(func=command_import_target)

    for command in (prepare, audit, import_target):
        command.add_argument("--cleanup-decisions", "--sdh-decisions", dest="sdh_decisions", help="Source-hash-bound SDH and credit removals")
    for command in (prepare, character_template, audit, import_target):
        command.add_argument("--source-encoding", choices=("utf-8-sig", "cp1255", "iso-8859-8", "cp1252"))
    for command in (audit, import_target):
        command.add_argument("--target-encoding", choices=("utf-8-sig", "cp1255", "iso-8859-8", "cp1252"))
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    for role in ("source", "target"):
        encoding = getattr(args, role + "_encoding", None)
        if encoding:
            INPUT_ENCODINGS[str(Path(getattr(args, role)).resolve())] = encoding
    if getattr(args, "batch_size", 1) < 1:
        parser.error("--batch-size must be at least 1")
    if getattr(args, "context_window", 1) < 1:
        parser.error("--context-window must be at least 1")
    try:
        if getattr(args, "sdh_decisions", None):
            decisions = load_optional_json(args.sdh_decisions)
            if decisions.get("source_sha256") != hashlib.sha256(Path(args.source).read_bytes()).hexdigest():
                raise SrtError("Cleanup decisions belong to another source")
            for row in decisions.get("decisions", []):
                cid = row.get("cue_id")
                if type(cid) is not int or cid in SDH_DECISIONS:
                    raise SrtError("Invalid or duplicate cleanup cue ID")
                SDH_DECISIONS[cid] = row
            source_ids = {c.index for c in parse_srt(Path(args.source), clean_source=False)}
            if not set(SDH_DECISIONS) <= source_ids:
                raise SrtError("Unknown cleanup cue ID")
        return int(args.func(args))
    except (SrtError, OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
