import unittest
from argparse import Namespace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from latest import main, validate, validate_bootstrap_and_fixtures, validate_live


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

    def test_bootstrap_and_fixture_validation_does_not_require_live_data(self):
        bootstrap, fixtures, _ = payloads()
        self.assertEqual(validate_bootstrap_and_fixtures(bootstrap, fixtures), 2)

    def test_live_validation_accepts_matching_live_data(self):
        bootstrap, _, live = payloads()
        self.assertIsNone(validate_live(bootstrap, live))

    def test_rejects_empty_live_elements(self):
        bootstrap, fixtures, _ = payloads()
        with self.assertRaises(ValueError):
            validate_live(bootstrap, {'elements': []})

    def test_rejects_mismatched_live_elements(self):
        bootstrap, fixtures, _ = payloads()
        with self.assertRaises(ValueError):
            validate_live(bootstrap, {'elements': [{'id': 1}]})

    def test_rejects_incomplete_fixture(self):
        bootstrap, _, live = payloads()
        with self.assertRaises(ValueError):
            validate(bootstrap, [{}], live)

    def test_rejects_duplicate_bootstrap_elements(self):
        bootstrap, fixtures, live = payloads()
        bootstrap['elements'] = [{'id': 1}, {'id': 1}]
        with self.assertRaises(ValueError):
            validate(bootstrap, fixtures, live)


    def test_main_fetches_live_after_bootstrap_and_fixture_validation(self):
        bootstrap, fixtures, live = payloads()
        args = Namespace(bootstrap_url='bootstrap', fixtures_url='fixtures', live_url='live/{event_id}')
        with TemporaryDirectory() as directory:
            args.out = Path(directory)
            with patch('latest.fetch', side_effect=[bootstrap, fixtures, live]) as fetch:
                main(args)
        self.assertEqual([call.args[0] for call in fetch.call_args_list], ['bootstrap', 'fixtures', 'live/2'])


if __name__ == '__main__':
    unittest.main()
