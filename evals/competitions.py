"""Edition-specific coverage lookup. Unknown editions never inherit rule support."""
import argparse
import json
from pathlib import Path


def lookup(contest, event, edition):
    records = json.loads(Path(__file__).with_name('competitions.json').read_text())['records']
    exact = [r for r in records if (r['contest'], r['event'], r['edition']) == (contest, event, edition)]
    if len(exact) == 1:
        return exact[0]
    return {'contest': contest, 'event': event, 'edition': edition,
            'status': {'rules': 'unconfirmed', 'workflow': 'not_validated', 'awards': 'uncalibrated'},
            'sources': [], 'note': 'No exact edition record; generic modeling only, no inherited contest compliance.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contest', required=True)
    parser.add_argument('--event', required=True)
    parser.add_argument('--edition', required=True)
    args = parser.parse_args()
    print(json.dumps(lookup(args.contest, args.event, args.edition), ensure_ascii=False, indent=2))
