#!/usr/bin/env python

"""
Fetch and publish the latest FPL data files.
"""

import argparse
import datetime
import json
import lzma
from pathlib import Path

import requests


def fetch(url):
    response = requests.get(
        url,
        headers={'User-Agent': 'fplcache/latest'},
        timeout=30)
    response.raise_for_status()
    return response.json()


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_elements(elements, name):
    if not isinstance(elements, list) or not elements:
        raise ValueError(f'{name} must contain a non-empty elements list')
    ids = set()
    for element in elements:
        if not isinstance(element, dict) or not _is_int(element.get('id')):
            raise ValueError(f'{name} contains an invalid element')
        if element['id'] in ids:
            raise ValueError(f'{name} contains duplicate element ids')
        ids.add(element['id'])
    return ids


def _validate_fixtures(fixtures):
    if not isinstance(fixtures, list) or not fixtures:
        raise ValueError('fixture data must be a non-empty JSON list')
    ids = set()
    for fixture in fixtures:
        required = ('id', 'event', 'team_h', 'team_a', 'finished')
        if not isinstance(fixture, dict):
            raise ValueError('fixture data contains an invalid fixture')
        if any(key not in fixture for key in required):
            raise ValueError('fixture data contains an incomplete fixture')
        if not _is_int(fixture['id']) or fixture['id'] in ids:
            raise ValueError('fixture data contains invalid or duplicate ids')
        if fixture['event'] is not None and not _is_int(fixture['event']):
            raise ValueError('fixture data contains an invalid gameweek')
        if not _is_int(fixture['team_h']) or not _is_int(fixture['team_a']):
            raise ValueError('fixture data contains invalid team ids')
        if not isinstance(fixture['finished'], bool):
            raise ValueError('fixture data contains an invalid finished flag')
        ids.add(fixture['id'])


def validate_bootstrap_and_fixtures(bootstrap, fixtures):
    if not isinstance(bootstrap, dict):
        raise ValueError('bootstrap data must be a JSON object')
    element_ids = _validate_elements(bootstrap.get('elements'), 'bootstrap data')
    events = bootstrap.get('events')
    if not isinstance(events, list) or not events:
        raise ValueError('bootstrap data must contain a non-empty events list')
    event_ids = set()
    current = []
    for event in events:
        if not isinstance(event, dict) or not _is_int(event.get('id')):
            raise ValueError('bootstrap data contains an invalid event')
        if event['id'] in event_ids:
            raise ValueError('bootstrap data contains duplicate event ids')
        event_ids.add(event['id'])
        if event.get('is_current') is True:
            current.append(event)
    if len(current) != 1 or current[0]['id'] <= 0:
        raise ValueError('bootstrap data must contain one current gameweek')
    _validate_fixtures(fixtures)
    return current[0]['id']


def validate_live(bootstrap, live):
    if not isinstance(bootstrap, dict):
        raise ValueError('bootstrap data must be a JSON object')
    if not isinstance(live, dict):
        raise ValueError('live data must be a JSON object')
    element_ids = _validate_elements(bootstrap.get('elements'), 'bootstrap data')
    live_ids = _validate_elements(live.get('elements'), 'live data')
    if live_ids != element_ids:
        raise ValueError('live data elements do not match bootstrap data')


def validate(bootstrap, fixtures, live):
    current_gameweek = validate_bootstrap_and_fixtures(bootstrap, fixtures)
    validate_live(bootstrap, live)
    return current_gameweek


def write_json(path, data):
    with lzma.open(path, 'wt', encoding='utf-8') as f:
        json.dump(data, f, indent=4, sort_keys=True)



def main(args):
    print('Fetching bootstrap data... ', end='', flush=True)
    bootstrap = fetch(args.bootstrap_url)
    print('OK.')
    print('Fetching fixture data... ', end='', flush=True)
    fixtures = fetch(args.fixtures_url)
    print('OK.')
    current_gameweek = validate_bootstrap_and_fixtures(bootstrap, fixtures)
    print(f'Fetching live gameweek {current_gameweek} data... ', end='', flush=True)
    live = fetch(args.live_url.format(event_id=current_gameweek))
    validate_live(bootstrap, live)
    print('OK.')

    generated_at = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    args.out.mkdir(parents=True, exist_ok=True)
    write_json(args.out / 'bootstrap.json.xz', bootstrap)
    write_json(args.out / 'fixtures.json.xz', fixtures)
    write_json(args.out / 'live.json.xz', live)
    manifest = {
        'generated_at': generated_at.isoformat().replace('+00:00', 'Z'),
        'current_gameweek': current_gameweek,
        'bootstrap': 'bootstrap.json.xz',
        'fixtures': 'fixtures.json.xz',
        'live': 'live.json.xz'
    }
    with (args.out / 'manifest.json').open('w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=4, sort_keys=True)
        f.write('\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Fetch and publish the latest FPL data files.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('--out', type=Path, default=Path('latest-publish'), help='latest output path')
    parser.add_argument('--bootstrap-url', default='https://fantasy.premierleague.com/api/bootstrap-static/', help='bootstrap URL')
    parser.add_argument('--fixtures-url', default='https://fantasy.premierleague.com/api/fixtures/', help='fixtures URL')
    parser.add_argument('--live-url', default='https://fantasy.premierleague.com/api/event/{event_id}/live/', help='live data URL')
    main(parser.parse_args())
