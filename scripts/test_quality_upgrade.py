#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import srt_pipeline as p
from quality_checks import quality_signals, credit_candidates

HERE = Path(__file__).parent

class QualityUpgrade(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        p.INPUT_ENCODINGS.clear()
        p.SDH_DECISIONS.clear()
    def tearDown(self):
        self.tmp.cleanup()
        p.INPUT_ENCODINGS.clear()
        p.SDH_DECISIONS.clear()
    def file(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value, encoding='utf-8')
        return path
    def run_cli(self, script, *args, ok=True):
        res = subprocess.run([sys.executable, str(HERE/script), *map(str,args)], capture_output=True, text=True)
        if ok: self.assertEqual(res.returncode, 0, res.stderr + res.stdout)
        else: self.assertNotEqual(res.returncode, 0)
        return res
    def cue(self, i=1, source='Hello.'):
        return {'index':i,'start':'00:00:01,000','end':'00:00:02,000','timing':'00:00:01,000 --> 00:00:02,000','source_text':source,'clean_text':source,'translate':True}
    def test_meaningful_parentheses_survive(self):
        self.assertEqual(p.clean_sdh('I owe you (not him) $20.'), 'I owe you (not him) $20.')
        self.assertEqual(p.clean_sdh('[DOOR OPENS] Hello (my old friend).'), 'Hello (my old friend).')
        self.assertEqual(p.clean_sdh('(dog barking loudly) Go.'), '(dog barking loudly) Go.')
    def test_placeholder_and_artifact_block(self):
        for text in ['תרגום חסר', 'נדרש תרגום', 'שלום\\nעולם', 'שלום "cue_id": 3', 'שלום �']:
            report = p.validate_translation_set({'cues':[self.cue()]}, {1:text}, strict=True)
            self.assertFalse(report['passed'], text)
    def test_cps_visible_text_only(self):
        report=quality_signals([self.cue()],{1:p.RLE+'<i>'+('א'*21)+'</i>'+p.RLM+p.PDF})
        self.assertEqual(report['warnings']['reading_speed'][0]['cps'],21)
    def test_repetition_is_warning_not_deletion(self):
        cues=[self.cue(i, str(i)) for i in range(1,4)]
        report=quality_signals(cues,{i:'שלום.' for i in range(1,4)})
        self.assertEqual(len(report['warnings']['suspicious_repetition']),1)
        self.assertFalse(any(report['errors'].values()))
    def test_legacy_encoding_requires_explicit_choice(self):
        path=self.root/'legacy.srt'
        path.write_bytes('שלום עולם'.encode('cp1255'))
        with self.assertRaises(p.SrtError): p.read_text(path)
        p.INPUT_ENCODINGS[str(path.resolve())]='cp1255'
        self.assertEqual(p.read_text(path),'שלום עולם')
        path.write_bytes('שלום עולם'.encode('iso-8859-8'))
        p.INPUT_ENCODINGS[str(path.resolve())]='iso-8859-8'
        self.assertEqual(p.read_text(path),'שלום עולם')
    def test_candidate_does_not_delete_dialogue_or_film_credit(self):
        for line in ['Created by Jane Doe','Visit https://example.com for help.','The subtitles were created by my sister.']:
            self.assertEqual(p.clean_sdh(line),line)
        self.assertTrue(credit_candidates('Created by ExampleSubber          Enjoy single-line subs'))
    def test_credit_end_to_end_keep_sdh_mixed_dialogue(self):
        credit='Created by ExampleSubber          Enjoy single-line subs'
        mixed='Subtitles by ExampleUser\nHello.'
        source=self.file('source.srt',f'1\n00:00:01,000 --> 00:00:02,000\n{credit}\n\n2\n00:00:03,000 --> 00:00:04,000\n{mixed}\n\n3\n00:00:05,000 --> 00:00:06,000\nCreated by Jane Doe\n')
        decisions=[]
        for cid,text,end in [(1,credit,len(credit)),(2,mixed,mixed.index('Hello.'))]:
            decisions.append({'cue_id':cid,'source_text':text,'reason':'External subtitle credit verified in context','credit_spans':[{'start':0,'end':end,'text':text[:end]}]})
        dec=self.file('cleanup.json',{'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'decisions':decisions})
        work=self.root/'work'
        self.run_cli('srt_pipeline.py','prepare',source,'--work-dir',work,'--sdh-mode','keep','--cleanup-decisions',dec)
        manifest=json.loads((work/'manifest.json').read_text())
        self.assertFalse(manifest['cues'][0]['translate'])
        self.assertEqual(manifest['cues'][1]['clean_text'],'Hello.')
        self.assertEqual(manifest['cues'][2]['clean_text'],'Created by Jane Doe')
        trans=self.file('translations.json',[{'cue_id':1,'text':''},{'cue_id':2,'text':'שלום.'},{'cue_id':3,'text':'נוצר על ידי ג׳יין דו'}])
        target=self.root/'output.srt'
        self.run_cli('srt_pipeline.py','build','--manifest',work/'manifest.json','--translations',trans,'--output',target,'--strict')
        self.run_cli('srt_pipeline.py','audit','--source',source,'--target',target,'--sdh-mode','keep','--cleanup-decisions',dec)
        self.assertEqual([c['index'] for c in p.parse_target_raw(target)],[2,3])
        decisions[0]['credit_spans'][0]['end']-=1
        bad=self.file('bad.json',{'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'decisions':decisions})
        self.run_cli('srt_pipeline.py','prepare',source,'--work-dir',self.root/'bad','--cleanup-decisions',bad,ok=False)
    def test_reviewed_sdh_and_wrong_source_hash(self):
        source=self.file('source.srt','1\n00:00:01,000 --> 00:00:02,000\n(dog barking loudly) Hello.\n')
        dec=self.file('dec.json',{'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'decisions':[{'cue_id':1,'source_text':'(dog barking loudly) Hello.','remove':['(dog barking loudly)'],'reason':'Verified sound description'}]})
        work=self.root/'work'
        self.run_cli('srt_pipeline.py','prepare',source,'--work-dir',work,'--cleanup-decisions',dec)
        manifest=json.loads((work/'manifest.json').read_text())
        self.assertEqual(manifest['cues'][0]['clean_text'],'Hello.')
        source.write_text(source.read_text().replace('Hello.', 'Goodbye.'))
        self.run_cli('srt_pipeline.py','prepare',source,'--work-dir',work,'--cleanup-decisions',dec,ok=False)
    def test_full_review_and_stale_guard(self):
        m=self.file('manifest.json',{'cues':[self.cue()], 'sdh_mode':'remove'})
        t=self.file('translations.json',[{'cue_id':1,'text':'שלום.'}])
        response={'manifest_sha256':hashlib.sha256(m.read_bytes()).hexdigest(),'translations_sha256':hashlib.sha256(t.read_bytes()).hexdigest(),'decisions':[{'cue_id':1,'original_text':'שלום.','text':'היי.','status':'corrected','reason':'Informal greeting in context','source_cleanup_checked':True}]}
        review=self.file('review.json',response)
        self.run_cli('review_translation.py','prepare','--manifest',m,'--translations',t,'--work-dir',self.root/'review-inputs')
        args=['apply','--manifest',m,'--translations',t,'--review',review,'--output',self.root/'revised.json','--report',self.root/'report.json']
        self.run_cli('review_translation.py',*args)
        report=json.loads((self.root/'report.json').read_text())
        self.assertEqual(report['changed_cues'],1)
        response['decisions']=[]
        self.file('review.json',response)
        self.run_cli('review_translation.py',*args,ok=False)
        response['translations_sha256']='stale'
        self.file('review.json',response)
        self.run_cli('review_translation.py',*args,ok=False)
    def test_review_duplicate_and_unknown_rejected(self):
        m=self.file('m.json',{'cues':[self.cue()]})
        t=self.file('t.json',[{'cue_id':1,'text':'שלום.'}])
        row={'cue_id':1,'original_text':'שלום.','text':'שלום.','status':'accepted','reason':'Checked','source_cleanup_checked':True}
        for rows in ([row,row],[dict(row,cue_id=9)]):
            rev=self.file('r.json',{'manifest_sha256':hashlib.sha256(m.read_bytes()).hexdigest(),'translations_sha256':hashlib.sha256(t.read_bytes()).hexdigest(),'decisions':rows})
            self.run_cli('review_translation.py','apply','--manifest',m,'--translations',t,'--review',rev,'--output',self.root/'out','--report',self.root/'rep',ok=False)

if __name__=='__main__': unittest.main()
