"""Conservative, dependency-free subtitle quality signals. No semantic guarantees."""
import re
from collections import defaultdict

WRAPPERS = re.compile(r'\[[^\[\]\n]*\]|\([^()\n]*\)')
# Exact whole descriptions only. Unknown wrappers survive and require contextual review.
SDH = re.compile(r'(?:music|music playing|door opens|door closes|phone ringing|laughs|laughing|chuckles|sighs|gasps|sobs|crying|screams|screaming|cheering|applause|footsteps|silence|inaudible|מוזיקה|הדלת נפתחת|הדלת נסגרת|הטלפון מצלצל|צוחק|צוחקת|צחוק|מחיאות כפיים|אנחות|צעדים)', re.I)
PLACEHOLDER = re.compile(r'^(?:תרגום חסר|נדרש תרגום|טרם תורגם|כאן התרגום|TODO|TBD|translation missing|untranslated)[.!…]*$', re.I)
ARTIFACT = re.compile(r'\\[nr]|```|<truncated\b|["\'](?:cue_id|polished_he|hebrew|index)["\']\s*:|\ufffd')


def known_sdh(wrapper):
    return bool(SDH.fullmatch(wrapper[1:-1].strip()))


def remove_known_sdh(text):
    return WRAPPERS.sub(lambda m: '' if known_sdh(m[0]) else m[0], text)


def wrapper_findings(text):
    return [{'text': m[0], 'classification': 'known_sdh' if known_sdh(m[0]) else 'needs_review'} for m in WRAPPERS.finditer(text)]


def plain(text):
    text = re.sub(r'<[^>]+>', '', text)
    return re.sub('[\u200e\u200f\u202a-\u202e\u2066-\u2069]', '', text)


def seconds(value):
    h, m, s, ms = map(int, re.split(r'[:,.]', value))
    return h * 3600 + m * 60 + s + ms / 1000


def quality_signals(cues, translations, cps_limit=20):
    errors = {'placeholders': [], 'output_artifacts': [], 'invalid_duration': []}
    warnings = {'reading_speed': [], 'suspicious_repetition': [], 'foreign_scripts': [], 'wrappers_for_review': []}
    groups = defaultdict(list)
    sources = {}
    for cue in cues:
        cid = int(cue['index'])
        source = cue.get('clean_text', cue.get('source_text', ''))
        sources[cid] = source
        if not cue.get('translate', True) or cid not in translations:
            continue
        text = plain(translations[cid]).strip()
        if PLACEHOLDER.fullmatch(text):
            errors['placeholders'].append(cid)
        if ARTIFACT.search(text):
            errors['output_artifacts'].append(cid)
        duration = seconds(cue['end']) - seconds(cue['start'])
        if duration <= 0:
            errors['invalid_duration'].append(cid)
        else:
            count = len(re.sub(r'\s+', ' ', text))
            cps = count / duration
            if cps > cps_limit:
                warnings['reading_speed'].append({'cue_id': cid, 'cps': round(cps, 2), 'duration': round(duration, 3), 'limit': cps_limit})
        if re.search('[\u0400-\u04ff\u0600-\u06ff\u4e00-\u9fff]', text):
            warnings['foreign_scripts'].append(cid)
        if WRAPPERS.search(text):
            warnings['wrappers_for_review'].append(cid)
        if text:
            groups[re.sub(r'\s+', ' ', text)].append(cid)
    for text, ids in groups.items():
        if len(ids) >= 3 and len({sources[i].casefold().strip() for i in ids}) >= 3:
            warnings['suspicious_repetition'].append({'cue_ids': ids, 'text': text})
    return {'errors': errors, 'warnings': warnings}

CREDIT_CANDIDATE = re.compile(r'\b(?:subtitles?\s+(?:by|created|provided)|(?:synced|synchronized|translated|corrected|resynced|ripped)\s+(?:and\s+corrected\s+)?by|created\s+by|single[- ]line\s+subs?|opensubtitles|subscene|addic7ed|podnapisi|yts\.[a-z]+|www\.|https?://|support\s+us|download\s+.*subs?)\b', re.I)


def credit_candidates(text):
    """Candidates only: websites and credits can also be spoken/in-film content."""
    return [{'line_index': i, 'text': line, 'classification': 'needs_context_review'} for i, line in enumerate(text.splitlines()) if CREDIT_CANDIDATE.search(plain(line))]
