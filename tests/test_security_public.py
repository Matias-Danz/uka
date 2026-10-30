import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_public', ROOT/'scripts/build_public.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class SecurityChecks(unittest.TestCase):
    def test_url_allowlist(self):
        for bad in ('javascript:alert(1)', 'data:text/html,x', 'http://example.com', 'https://user:pass@example.com', '//example.com', 'https://', 'https://%ZZ'):
            self.assertFalse(mod.safe_url(bad), bad)
        self.assertEqual(mod.safe_url('https://example.com/a'), 'https://example.com/a')

    def test_admin_overrides_allowlist(self):
        source = {'overrides': {'x': {'hidden': False, 'fields': {'title': 'A', 'secret': 'NO', 'ticket_url': 'javascript:alert(1)', 'id': 'evil'}}}, 'custom_events': [{'id': 'x', 'title': 'A', 'date': '2027-01-01', 'private': 'NO', 'image_url': 'data:image/png,abc'}]}
        clean = mod.sanitize_admin_overrides(source)
        self.assertNotIn('secret', clean['overrides']['x']['fields'])
        self.assertNotIn('id', clean['overrides']['x']['fields'])
        self.assertEqual(clean['overrides']['x']['fields']['ticket_url'], '')
        self.assertNotIn('private', clean['custom_events'][0])
        self.assertEqual(clean['custom_events'][0]['image_url'], '')

    def test_public_assets(self):
        mod.main()
        dist = ROOT/'dist'
        self.assertFalse((dist/'admin.html').exists())
        self.assertFalse((dist/'scripts').exists())
        self.assertTrue((dist/'_headers').exists())
        for asset in ('uka-app.js', 'uka-auth.js', 'uka-theme.js', 'uka.css'):
            self.assertTrue((dist/asset).is_file())
        html=(dist/'index.html').read_text()
        self.assertNotIn('onerror=',html)
        self.assertIn('Content-Security-Policy',html)
        events=json.loads((dist/'events.json').read_text())
        self.assertNotIn('price_catalog_cache', events)
        self.assertNotIn('eventlook_cursor', events)
        self.assertTrue(all(set(e)<=mod.PUBLIC_EVENT_FIELDS for e in events['events']))
        for e in events['events']+events['admin_overrides']['custom_events']:
            for k in ('ticket_url','image_url','price_url'):
                self.assertTrue(not e.get(k) or e[k].startswith('https://'))

if __name__=='__main__': unittest.main()
