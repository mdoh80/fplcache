import unittest

from latest import validate


def payloads():
    bootstrap = {
        'elements': [{'id': 1}, {'id': 2}],
        'events': [
            {'id': 1, 'is_current': False},
            {'id': 2, 'is_current': True},
        ],
    }
    fixtures = [{
        'id': 1,
        'event': 1,
        'team_h': 1,
        'team_a': 2,
        'finished': False,
    }]
    live = {'elements': [{'id': 1}, {'id': 2}]}
    return bootstrap, fixtures, live


class ValidateTests(unittest.TestCase):
    def test_accepts_complete_matching_payloads(self):
        self.assertEqual(validate(*payloads()), 2)

    def test_rejects_empty_live_elements(self):
        bootstrap, fixtures, _ = payloads()
        with self.assertRaises(ValueError):
            validate(bootstrap, fixtures, {'elements': []})

    def test_rejects_mismatched_live_elements(self):
        bootstrap, fixtures, _ = payloads()
        with self.assertRaises(ValueError):
            validate(bootstrap, fixtures, {'elements': [{'id': 1}]})

    def test_rejects_incomplete_fixture(self):
        bootstrap, _, live = payloads()
        with self.assertRaises(ValueError):
            validate(bootstrap, [{}], live)

    def test_rejects_duplicate_bootstrap_elements(self):
        bootstrap, fixtures, live = payloads()
        bootstrap['elements'] = [{'id': 1}, {'id': 1}]
        with self.assertRaises(ValueError):
            validate(bootstrap, fixtures, live)


if __name__ == '__main__':
    unittest.main()
