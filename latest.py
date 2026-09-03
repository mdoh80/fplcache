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


def validate(bootstrap, fixtures, live):
    if not isinstance(bootstrap, dict):
        raise ValueError('bootstrap data must be a JSON object')
    if not isinstance(bootstrap.get('elements'), list):
        raise ValueError('bootstrap data has no elements list')
    events = bootstrap.get('events')
    if not isinstance(events, list):
        raise ValueError('bootstrap data has no events list')
    current = [event for event in events if event.get('is_current')]
    if len(current) != 1 or not isinstance(current[0].get('id'), int):
        raise ValueError('bootstrap data must contain one current gameweek')
    if not isinstance(fixtures, list):
        raise ValueError('fixture data must be a JSON list')
    if not isinstance(live, dict) or not isinstance(live.get('elements'), list):
        raise ValueError('live data has no elements list')
    return current[0]['id']


def write_json(path, data):
    with lzma.open(path, 'wt', encoding='utf-8') as f:
        json.dump(data, f, indent=4, sort_keys=True)


def historical_path(cache, generated_at, name=''):
    directory = cache / name / Path(
        f'{generated_at.year}/{generated_at.month}/{generated_at.day}')
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f'{generated_at.hour:02d}{generated_at.minute:02d}.json.xz'


def main(args):
    print('Fetching bootstrap data... ', end='', flush=True)
    bootstrap = fetch(args.bootstrap_url)
    print('OK.')
    print('Fetching fixture data... ', end='', flush=True)
    fixtures = fetch(args.fixtures_url)
    print('OK.')
    current_gameweek = validate(bootstrap, fixtures, {'elements': []})
    print(f'Fetching live gameweek {current_gameweek} data... ', end='', flush=True)
    live = fetch(args.live_url.format(event_id=current_gameweek))
    current_gameweek = validate(bootstrap, fixtures, live)
    print('OK.')

    generated_at = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    args.out.mkdir(parents=True, exist_ok=True)
    write_json(args.out / 'bootstrap.json.xz', bootstrap)
    write_json(args.out / 'fixtures.json.xz', fixtures)
    write_json(args.out / 'live.json.xz', live)
    if args.historical_cache:
        write_json(historical_path(args.historical_cache, generated_at), bootstrap)
        write_json(historical_path(args.historical_cache, generated_at, 'fixtures'), fixtures)
        write_json(historical_path(args.historical_cache, generated_at, 'live'), live)

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
    parser.add_argument('--historical-cache', type=Path, default=Path('cache'), help='historical cache path')
    parser.add_argument('--bootstrap-url', default='https://fantasy.premierleague.com/api/bootstrap-static/', help='bootstrap URL')
    parser.add_argument('--fixtures-url', default='https://fantasy.premierleague.com/api/fixtures/', help='fixtures URL')
    parser.add_argument('--live-url', default='https://fantasy.premierleague.com/api/event/{event_id}/live/', help='live data URL')
    main(parser.parse_args())
