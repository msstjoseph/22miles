"""Let the branch Pages build finish before publishing the timestamped feed."""
import json
import os
import time
from urllib.request import Request, urlopen

if os.environ.get('GITHUB_EVENT_NAME') == 'push':
    time.sleep(10)
url = 'https://api.github.com/repos/' + os.environ['GITHUB_REPOSITORY'] + '/actions/runs?per_page=30'
for attempt in range(60):
    request = Request(url, headers={
        'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'Concord22MilesSignage',
    })
    with urlopen(request, timeout=20) as response:
        runs = json.load(response)['workflow_runs']
    pending = [r for r in runs if r['head_sha'] == os.environ['GITHUB_SHA']
               and r['name'] == 'pages build and deployment' and r['status'] != 'completed']
    if not pending:
        break
    print('Waiting for branch Pages publish', flush=True)
    time.sleep(5)
else:
    raise RuntimeError('Branch Pages build has not finished; retry on next scheduled run')
