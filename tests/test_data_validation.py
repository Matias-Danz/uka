import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('validate_data', ROOT/'scripts/validate_data.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class ValidationTests(unittest.TestCase):
    def test_existing_data(self):
        module.validate()

    def test_bad_urls(self):
        for value in ('javascript:alert(1)', 'http://example.com', 'https://user:pass@example.com', '//example.com'):
            with self.assertRaises(ValueError):
                module.url(value, 'test')

    def test_invalid_event_date(self):
        with self.assertRaises(ValueError):
            module.event({'id':'a','title':'b','date':'2026-02-30'}, 'test')

    def test_invalid_price(self):
        with self.assertRaises(ValueError):
            module.event({'price': -1}, 'test', partial=True)

    def test_admin_does_not_request_token(self):
        html = (ROOT/'admin.html').read_text()
        self.assertNotIn('github_pat_', html)
        self.assertNotIn('Authorization', html)
        self.assertNotIn('api.github.com', html)

if __name__ == '__main__': unittest.main()
