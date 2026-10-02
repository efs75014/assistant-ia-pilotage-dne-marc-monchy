import importlib.util, pathlib, unittest, json
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('pipeline',ROOT/'pipeline.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle=p.normalized_reference_bundle(ROOT/'data/reference_2026-10-01')
        cls.rule=json.loads((ROOT/'config/indicator.json').read_text(encoding='utf-8'))
        cls.result=p.build(cls.bundle,cls.rule)
    def test_sources_corrected(self):
        self.assertEqual(self.bundle['production_metadata']['dataset_id'],p.IDS['production'])
        self.assertEqual(self.bundle['beta_metadata']['dataset_id'],p.IDS['beta'])
    def test_main_indicator_uses_production(self):
        self.assertEqual(self.result['weekly']['current']['territories'],32)
        self.assertAlmostEqual(self.result['weekly']['current']['threshold'],0.7660803375366456,places=10)
    def test_persistent_signal(self):
        signals=[r['libelle_aca'] for r in self.result['rows'] if r['signal']=='Signal sur deux semaines']
        self.assertEqual(signals,['Toulouse'])
    def test_beta_is_context(self):
        self.assertEqual(self.result['quality']['beta_total_registrations'],1561)
        self.assertIn('Contexte historique',self.result['interpretation']['beta_role'])
if __name__=='__main__': unittest.main()
