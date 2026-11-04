"""Regression checks for the registration UI's public-facing example."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class AuthUiTests(unittest.TestCase):
    def test_generic_username_example(self):
        auth = (ROOT / 'uka-auth.js').read_text(encoding='utf-8')
        self.assertIn("username.placeholder='např. hudebnifan23'", auth)
        self.assertNotIn('matias23', auth.lower())

    def test_auth_button_rendering_is_shared(self):
        auth = (ROOT / 'uka-auth.js').read_text(encoding='utf-8')
        self.assertIn('function updateAuthButton()', auth)
        self.assertIn('user=session?.user||null;updateAuthButton()', auth)


if __name__ == '__main__':
    unittest.main()
