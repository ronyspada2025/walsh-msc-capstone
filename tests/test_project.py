"""Regression checks for failure handling, explicit matching, and update safety."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0,str(ROOT))
from src.verification import _finite,compare_report,verify_results


class VerificationTests(unittest.TestCase):
    def test_empty_output_is_rejected(self):
        with self.assertRaises(ValueError): verify_results({},ROOT/'reports',ROOT)

    def test_empty_reference_cannot_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            reference=Path(tmp)/'empty.json';reference.write_text('{"source":"test","metrics":[]}')
            with self.assertRaises(ValueError):compare_report({},reference)

    def test_nonfinite_nested_values_and_integer_cluster_keys(self):
        _finite({'clusters':{0:1231,1:4334}})
        with self.assertRaises(ValueError): _finite({'nested':[{'score':float('nan')}]})

    def test_explicit_metric_identity_and_rounding(self):
        fixture={'source':'test','metrics':[
            {'name':'AUC','path':['rq1','auc'],'reported':'.927','decimals':3,'location':'test'},
            {'name':'RQ4 McFadden','path':['rq4','mcfadden'],'reported':'.196','decimals':3,'location':'test'}]}
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'ref.json';p.write_text(json.dumps(fixture))
            result={'rq1':{'auc':.926698},'rq2':{'mcfadden':.196}}
            got=compare_report(result,p)
            self.assertEqual(got['summary'],{'MATCH':1,'DIFFERS':0,'MISSING_OR_INVALID':1})
            self.assertFalse(got['exact_match'])
            result['rq1']['auc']=.9279
            self.assertEqual(compare_report(result,p)['summary']['DIFFERS'],1)

    def test_changed_input_aborts_and_clears_owned_marker(self):
        import final_pipeline as fp
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); data=root/'changed.csv';data.write_text('not the study dataset')
            output=root/'reports';output.mkdir();(output/'existing.txt').write_text('preserve')
            with patch.object(fp,'DATA_PATH',data):
                with self.assertRaises(ValueError): fp.main(['--output',str(output)])
            self.assertEqual(json.loads((output/'execution_status.json').read_text())['status'],'failed')
            self.assertEqual((output/'existing.txt').read_text(),'preserve')
            self.assertTrue((output/'last_failed_run.txt').is_file())

    def test_notebook_cells_are_executable_python_and_correct_repository(self):
        for path in (ROOT/'notebooks').glob('*.ipynb'):
            notebook=json.loads(path.read_text())
            for i,cell in enumerate(notebook['cells']):
                if cell['cell_type']=='code': compile(''.join(cell['source']),str(path)+f':{i}','exec')
        source=(ROOT/'notebooks/06_final_report_pipeline_colab.ipynb').read_text()
        self.assertIn('ronyspada2025/walsh-msc-capstone',source)
        self.assertNotIn('/dev/null',source)


class UpdateSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('update_repository',ROOT/'scripts/update_repository.py')
        cls.updater=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.updater)

    def test_traversal_and_git_metadata_are_rejected(self):
        for name in ['../secret','/absolute','.git/config','payload/../../outside','foo\\bar']:
            with self.assertRaises(ValueError): self.updater.safe_relative(name)

    def test_all_preimages_are_checked_before_writing(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);repo=base/'repo';repo.mkdir();bundle=base/'bundle';(bundle/'payload').mkdir(parents=True)
            (repo/'one.py').write_text('original');(repo/'two.py').write_text('unexpected')
            (bundle/'payload/one.py').write_text('replacement')
            manifest={'base_commit':self.updater.EXPECTED_BASE,'deletions':[],
                'files':[{'path':'one.py','before_sha256':hashlib.sha256(b'original').hexdigest()},
                         {'path':'two.py','before_sha256':hashlib.sha256(b'expected').hexdigest()}]}
            def fake_run(args,**kw):
                return SimpleNamespace(stdout=self.updater.EXPECTED_BASE if 'rev-parse' in args else '')
            with patch.object(self.updater,'run',fake_run):
                with self.assertRaises(ValueError):self.updater.apply_bundle(repo,bundle,manifest)
            self.assertEqual((repo/'one.py').read_text(),'original')


if __name__=='__main__': unittest.main()
