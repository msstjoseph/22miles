"""Build a timestamped NWS backup feed for the display; fail closed on errors."""
import json
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


def main():
    data = fetch_alerts()  # Do not build or deploy an empty substitute on failure.
    output = ROOT / '_site'
    output.mkdir(exist_ok=True)
    # Preserve all existing public root files, including the older radar URLs.
    for source in ROOT.iterdir():
        if source.is_file() and not source.name.startswith('.'):
            shutil.copy2(source, output / source.name)
    (output / 'alerts-data.json').write_text(json.dumps(data), encoding='utf-8')
    print('Published feed source:', data['checkedAt'], 'alerts:', len(data['features']))


if __name__ == '__main__':
    main()
