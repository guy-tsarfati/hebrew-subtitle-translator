#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).with_name("srt_pipeline.py")

SPEAKER_SOURCE = """1
00:00:01,000 --> 00:00:03,000
ALEX: Are you ready?

2
00:00:03,100 --> 00:00:05,000
Maya: I am ready.

3
00:00:05,100 --> 00:00:07,000
ALEX: Then let's go.
"""

SOURCE = """1
00:00:01,000 --> 00:00:03,000
[MUSIC]

2
00:00:03,100 --> 00:00:05,000
[DOOR OPENS] Hello, Captain.

3
00:00:05,100 --> 00:00:07,000
♪ We are exploring the stars ♪

4
00:00:07,100 --> 00:00:09,000
(laughs) Are you ready?

5
00:00:09,100 --> 00:00:11,000
(phone ringing)

6
00:00:11,100 --> 00:00:12,000
_
"""

REMOVE_TRANSLATIONS = [
    {"cue_id": 1, "text": ""},
    {"cue_id": 2, "text": "שלום, קפטן."},
    {"cue_id": 3, "text": "אנחנו חוקרים את Starfleet."},
    {"cue_id": 4, "text": "אפשר להתחיל?"},
    {"cue_id": 5, "text": ""},
    {"cue_id": 6, "text": ""},
]

KEEP_TRANSLATIONS = [
    {"cue_id": 1, "text": "[מוזיקה]"},
    {"cue_id": 2, "text": "[הדלת נפתחת] שלום, קפטן."},
    {"cue_id": 3, "text": "אנחנו חוקרים את Starfleet."},
    {"cue_id": 4, "text": "(צוחק) אפשר להתחיל?"},
    {"cue_id": 5, "text": "(הטלפון מצלצל)"},
    {"cue_id": 6, "text": ""},
]


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        check=True,
        text=True,
        capture_output=True,
    )


def exercise(root: Path, mode: str, translations_payload: list[dict[str, object]]) -> None:
    source = root / f"sample-{mode}.en.srt"
    source.write_text(SOURCE, encoding="utf-8")
    work = root / f"work-{mode}"
    translations = root / f"translations-{mode}.json"
    output = root / f"sample-{mode}.he.srt"
    report = root / f"qa-{mode}.json"
    translations.write_text(json.dumps(translations_payload, ensure_ascii=False), encoding="utf-8")

    run("prepare", str(source), "--work-dir", str(work), "--batch-size", "2", "--context-window", "2", "--sdh-mode", mode)
    manifest = json.loads((work / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["cue_count"] == 6
    assert manifest["sdh_mode"] == mode
    assert manifest["context_window"] == 2
    first_batch = json.loads((work / "batches" / "batch_0001.json").read_text(encoding="utf-8"))
    assert first_batch["schema_version"] == 3
    assert isinstance(first_batch["items"][0]["context_after"], list)
    assert len(first_batch["items"][0]["context_after"]) == 2

    if mode == "remove":
        assert manifest["cues"][0]["translate"] is False
        assert manifest["cues"][1]["clean_text"] == "Hello, Captain."
        assert manifest["cues"][3]["clean_text"] == "Are you ready?"
        assert manifest["cues"][4]["translate"] is False
        assert manifest["cues"][5]["translate"] is False
    else:
        assert manifest["cues"][0]["clean_text"] == "[MUSIC]"
        assert manifest["cues"][3]["clean_text"] == "(laughs) Are you ready?"
        assert manifest["cues"][5]["translate"] is False

    run("validate", "--manifest", str(work / "manifest.json"), "--translations", str(translations), "--strict")
    run("build", "--manifest", str(work / "manifest.json"), "--translations", str(translations), "--output", str(output), "--strict")
    run("audit", "--source", str(source), "--target", str(output), "--report", str(report), "--sdh-mode", mode)

    data = output.read_bytes()
    assert data.startswith(b"\xef\xbb\xbf")
    text = data.decode("utf-8-sig")
    assert "♪" not in text
    if mode == "remove":
        assert "\u202bשלום, קפטן.\u200f\u202c" in text
    else:
        assert "\u202b[הדלת נפתחת] שלום, קפטן.\u200f\u202c" in text
    assert "\u202bאנחנו חוקרים את Starfleet.\u200f\u202c" in text
    assert (
        "\u202bאפשר להתחיל?\u200f\u202c" in text
        or "\u202b(צוחק) אפשר להתחיל?\u200f\u202c" in text
    )
    if mode == "remove":
        assert text.count("-->") == 3
        normalized = "\n" + text.lstrip("\ufeff")
        assert "\n1\n00:00:01,000" not in normalized
        assert "\n5\n00:00:09,100" not in normalized
        assert "\n6\n00:00:11,100" not in normalized
        assert "(" not in text and ")" not in text
        assert "[" not in text and "]" not in text
    else:
        assert text.count("-->") == 5
        assert "(צוחק)" in text
        assert "[הדלת נפתחת]" in text

    qa = json.loads(report.read_text(encoding="utf-8"))
    assert qa["passed"] is True
    assert qa["sdh_mode"] == mode
    assert qa["blank_overlay_cues"] == []
    assert qa["rtl_violations"] == []
    assert qa["punctuation_direction_violations"] == []
    if mode == "remove":
        assert qa["source_cues"] == 6
        assert qa["expected_target_cues"] == 3
        assert qa["target_cues"] == 3
        assert qa["omitted_non_dialogue_cues"] == [1, 5, 6]
    else:
        assert qa["expected_target_cues"] == 5
        assert qa["omitted_non_dialogue_cues"] == [6]


def test_import_remove_mode(root: Path) -> None:
    source = root / "import.en.srt"
    source.write_text(SOURCE, encoding="utf-8")
    work = root / "import-work"
    translations = root / "import-translations.json"
    target = root / "import.he.srt"
    imported = root / "imported.json"
    translations.write_text(json.dumps(REMOVE_TRANSLATIONS, ensure_ascii=False), encoding="utf-8")

    run("prepare", str(source), "--work-dir", str(work), "--sdh-mode", "remove")
    run("build", "--manifest", str(work / "manifest.json"), "--translations", str(translations), "--output", str(target), "--strict")
    run("import-target", "--source", str(source), "--target", str(target), "--output", str(imported), "--sdh-mode", "remove")

    payload = json.loads(imported.read_text(encoding="utf-8"))
    records = {item["cue_id"]: item["text"] for item in payload}
    assert records[1] == ""
    assert records[5] == ""
    assert records[6] == ""
    assert records[2] == "שלום, קפטן."
    assert records[3] == "אנחנו חוקרים את Starfleet."


def test_audit_rejects_legacy_blank_and_rlm(root: Path) -> None:
    source = root / "legacy.en.srt"
    source.write_text(
        """1
00:00:01,000 --> 00:00:02,000
[MUSIC]

2
00:00:02,100 --> 00:00:03,000
Hello.
""",
        encoding="utf-8",
    )
    target = root / "legacy.he.srt"
    target.write_text(
        "1\n00:00:01,000 --> 00:00:02,000\n\u200f\n\n"
        "2\n00:00:02,100 --> 00:00:03,000\n\u200fשלום.\u200f\n",
        encoding="utf-8-sig",
    )
    report = root / "legacy-qa.json"
    result = subprocess.run(
        [
            sys.executable, str(SCRIPT), "audit",
            "--source", str(source),
            "--target", str(target),
            "--report", str(report),
            "--sdh-mode", "remove",
        ],
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 2
    qa = json.loads(report.read_text(encoding="utf-8"))
    assert qa["passed"] is False
    assert qa["blank_overlay_cues"] == [1]
    assert qa["unexpected_output_cues"] == [1]

    target.write_text(
        "2\n00:00:02,100 --> 00:00:03,000\n\u200fשלום.\u200f\n",
        encoding="utf-8-sig",
    )
    result = subprocess.run(
        [
            sys.executable, str(SCRIPT), "audit",
            "--source", str(source),
            "--target", str(target),
            "--report", str(report),
            "--sdh-mode", "remove",
        ],
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 2
    qa = json.loads(report.read_text(encoding="utf-8"))
    assert qa["rtl_violations"] == [2]
    assert qa["punctuation_direction_violations"] == [2]


def test_character_template(root: Path) -> None:
    source = root / "speakers.en.srt"
    output = root / "character-bible.json"
    source.write_text(SPEAKER_SOURCE, encoding="utf-8")
    run("character-template", str(source), "--output", str(output))
    payload = json.loads(output.read_text(encoding="utf-8"))
    characters = {item["name"]: item for item in payload["characters"]}
    assert characters["ALEX"]["occurrences"] == 2
    assert characters["Maya"]["occurrences"] == 1
    assert characters["ALEX"]["grammatical_gender"] == "unknown"


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        exercise(root, "remove", REMOVE_TRANSLATIONS)
        exercise(root, "keep", KEEP_TRANSLATIONS)
        test_import_remove_mode(root)
        test_audit_rejects_legacy_blank_and_rlm(root)
        test_character_template(root)

    print("ALL_TESTS_PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
