import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import load_config
from build import build, OUT

class TestSite(unittest.TestCase):
    def test_config(self):
        site, providers = load_config()
        self.assertEqual(site['locale'],'en-US')
        self.assertGreaterEqual(len(providers),3)
    def test_config_drives_provider_list(self):
        path = Path(__file__).resolve().parents[1]/'.ilang/site.ilang'
        raw=path.read_text('utf-8')
        try:
            path.write_text(raw.replace('Hetzner |', 'ChangedProvider |'),encoding='utf-8')
            _, providers=load_config()
            self.assertIn('ChangedProvider',[p['name'] for p in providers])
        finally:
            path.write_text(raw,encoding='utf-8')
    def test_build_without_domain_is_noindex(self):
        build()
        text=(OUT/'index.html').read_text('utf-8')
        self.assertIn('noindex,follow',text)
        self.assertIn('Official pricing radar',text)
        self.assertNotIn('"@type": "Offer"',text)

if __name__ == '__main__': unittest.main()