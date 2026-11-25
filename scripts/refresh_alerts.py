"""Build a timestamped NWS backup feed for the display; fail closed on errors."""
import json
import math
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://api.weather.gov/alerts/active?point=35.4088,-80.5795'


def validate(data):
    if data.get('type') != 'FeatureCollection' or not isinstance(data.get('features'), list):
        raise ValueError('Invalid NWS alert response')
    for feature in data['features']:
        if not isinstance(feature, dict) or not isinstance(feature.get('properties'), dict):
            raise ValueError('Invalid NWS alert feature')
    return data


def fetch_alerts():
    request = Request(URL, headers={
        'Accept': 'application/geo+json',
        'User-Agent': 'Concord22MilesSignage/1.0 (https://github.com/msstjoseph/22miles)',
    })
    for attempt in range(3):
        try:
            with urlopen(request, timeout=20) as response:
                data = validate(json.load(response))
            return {
                'type': 'FeatureCollection',
                'features': data['features'],
                'checkedAt': datetime.now(timezone.utc).isoformat(),
                'source': URL,
            }
        except Exception:
            if attempt == 2:
                raise
            time.sleep(5)


def fetch_temperature():
    url = 'https://api.weather.gov/stations/KJQF/observations?limit=5'
    request = Request(url, headers={
        'Accept': 'application/geo+json',
        'User-Agent': 'Concord22MilesSignage/1.0 (https://github.com/msstjoseph/22miles)',
    })
    with urlopen(request, timeout=20) as response:
        data = validate(json.load(response))
    return temperature_from_observations(data)


def temperature_from_observations(data):
    readings = []
    now = datetime.now(timezone.utc)
    for feature in data['features']:
        p = feature['properties']
        temperature = p.get('temperature') or {}
        value = temperature.get('value')
        if type(value) not in (int, float) or not math.isfinite(value):
            continue
        unit = temperature.get('unitCode')
        if unit == 'wmoUnit:degC':
            fahrenheit = value * 9 / 5 + 32
        elif unit == 'wmoUnit:degF':
            fahrenheit = value
        else:
            continue
        try:
            observed = datetime.fromisoformat(p['timestamp'].replace('Z', '+00:00'))
            age = (now - observed).total_seconds()
        except (KeyError, ValueError, TypeError):
            continue
        if not -60 <= age <= 7200:
            continue
        readings.append({
            'temperatureF': fahrenheit,
            'observedAt': observed.isoformat(),
            'station': 'KJQF',
            'checkedAt': now.isoformat(),
        })
    if not readings:
        raise ValueError('No recent Concord temperature observation')
    return max(readings, key=lambda reading: reading['observedAt'])


def main():
    data = fetch_alerts()  # Do not build or deploy an empty substitute on failure.
    output = ROOT / '_site'
    output.mkdir(exist_ok=True)
    # Preserve all existing public root files, including the older radar URLs.
    for source in ROOT.iterdir():
        if source.is_file() and not source.name.startswith('.'):
            shutil.copy2(source, output / source.name)
    (output / 'alerts-data.json').write_text(json.dumps(data), encoding='utf-8')
    # Weather availability must not interrupt alert publication.
    try:
        weather = fetch_temperature()
    except Exception as error:
        weather = {'temperatureF': None, 'observedAt': None,
                   'checkedAt': datetime.now(timezone.utc).isoformat(), 'station': 'KJQF'}
        print('Temperature unavailable:', type(error).__name__)
    (output / 'weather-data.json').write_text(json.dumps(weather), encoding='utf-8')
    print('Published feed source:', data['checkedAt'], 'alerts:', len(data['features']))


if __name__ == '__main__':
    main()
