#!/usr/bin/env python3
"""Prepare and apply a complete, source-bound bilingual editorial review."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import srt_pipeline as pipeline


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def prepare(args):
    manifest = pipeline.load_manifest(Path(args.manifest))
    translations = pipeline.translation_map(Path(args.translations))
    validation = pipeline.validate_translation_set(manifest, translations, strict=True)
    if not validation['passed']:
        raise pipeline.SrtError('Resolve validation errors before editorial review: ' + json.dumps(validation['errors'], ensure_ascii=False))
    folder = Path(args.work_dir)
    folder.mkdir(parents=True, exist_ok=True)
    cues = manifest['cues']
    context = {'manifest_sha256': digest(args.manifest), 'translations_sha256': digest(args.translations)}
    for start in range(0, len(cues), 30):
        batch = cues[start:start + 30]
        payload = dict(context, glossary=manifest.get('glossary'), character_bible=manifest.get('character_bible'),
            instructions='Review EVERY item against source, including omissions. Return one decision per cue with status accepted, corrected, or unresolved. Include original_text, text, reason, speaker, addressee, gender_confidence, and source_cleanup_checked=true. Do not move dialogue between cues. Preserve good wording. Context is not part of the current cue.',
            context_before=cues[max(0, start-4):start], context_after=cues[start+30:start+34],
            items=[{'cue_id': c['index'], 'source': c['source_text'], 'clean_source': c['clean_text'], 'translate': c['translate'], 'timing': c['timing'], 'original_text': translations[c['index']]} for c in batch])
        pipeline.write_json(folder / f'review_input_{start // 30 + 1:04d}.json', payload)
    print(json.dumps(dict(context, cue_count=len(cues), output=str(folder)), indent=2))


def apply(args):
    manifest = pipeline.load_manifest(Path(args.manifest))
    original = pipeline.translation_map(Path(args.translations))
    response = load(args.review)
    for field, path in [('manifest_sha256', args.manifest), ('translations_sha256', args.translations)]:
        if response.get(field) != digest(path):
            raise pipeline.SrtError('Review is stale or belongs to another source: ' + field)
    decisions = response.get('decisions', [])
    expected = {c['index']: c for c in manifest['cues']}
    seen = set()
    revised = dict(original)
    changes, unresolved = [], []
    for row in decisions:
        cid = row.get('cue_id')
        if type(cid) is not int or cid not in expected or cid in seen:
            raise pipeline.SrtError('Unknown or duplicate reviewed cue')
        seen.add(cid)
        if row.get('original_text') != original[cid]:
            raise pipeline.SrtError(f'Stale original_text at cue {cid}')
        status = row.get('status')
        if status not in ('accepted', 'corrected', 'unresolved'):
            raise pipeline.SrtError(f'Missing review status at cue {cid}')
        if row.get('source_cleanup_checked') is not True:
            raise pipeline.SrtError(f'Source cleanup not reviewed at cue {cid}')
        text = row.get('text')
        if not isinstance(text, str) or not isinstance(row.get('reason'), str) or not row['reason'].strip():
            raise pipeline.SrtError(f'Missing text or reason at cue {cid}')
        if not expected[cid]['translate'] and text:
            raise pipeline.SrtError(f'Reprepare source cleanup before restoring omitted cue {cid}')
        if status in ('accepted', 'unresolved') and text != original[cid]:
            raise pipeline.SrtError(f'Only corrected decisions may change cue {cid}')
        if status == 'unresolved':
            unresolved.append({'cue_id': cid, 'reason': row['reason']})
        if text != original[cid]:
            changes.append({'cue_id': cid, 'source': expected[cid]['source_text'], 'before': original[cid], 'after': text, 'reason': row['reason']})
        revised[cid] = text
    if seen != set(expected):
        raise pipeline.SrtError('Review does not cover every source cue')
    validation = pipeline.validate_translation_set(manifest, revised, strict=True)
    if not validation['passed']:
        raise pipeline.SrtError('Edited translation failed validation: ' + json.dumps(validation['errors'], ensure_ascii=False))
    output = Path(args.output)
    report = Path(args.report)
    protected = {Path(p).resolve() for p in (args.manifest, args.translations, args.review)}
    if output.resolve() in protected or report.resolve() in protected or output.resolve() == report.resolve():
        raise pipeline.SrtError('Output and report must be distinct new paths')
    pipeline.write_json(output, [{'cue_id': c['index'], 'text': revised[c['index']]} for c in manifest['cues']])
    pipeline.write_json(report, {'manifest_sha256': digest(args.manifest), 'input_sha256': digest(args.translations), 'output_sha256': digest(output), 'reviewed_cues': len(seen), 'changed_cues': len(changes), 'unresolved': unresolved, 'changes': changes, 'validation': validation, 'semantic_accuracy_guaranteed': False})
    print(json.dumps({'reviewed': len(seen), 'changed': len(changes), 'unresolved': len(unresolved), 'output': str(output)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare')
    app = sub.add_parser('apply')
    for cmd in (prep, app):
        cmd.add_argument('--manifest', required=True)
        cmd.add_argument('--translations', required=True)
    prep.add_argument('--work-dir', required=True)
    prep.set_defaults(func=prepare)
    app.add_argument('--review', required=True)
    app.add_argument('--output', required=True)
    app.add_argument('--report', required=True)
    app.set_defaults(func=apply)
    args = parser.parse_args()
    try:
        args.func(args)
        return 0
    except (pipeline.SrtError, ValueError, OSError, KeyError, TypeError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
