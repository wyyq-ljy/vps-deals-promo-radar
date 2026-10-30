# ::ILANG [TYPE:python-module][ROLE:official-source-collector]
# ::RULE{only:public provider pages; honor robots and rate limits}
# ::BOUNDARY{never:invent price, parse arbitrary nearby numbers as prices}
"""Conservative official-page fetcher; deliberately refuses speculative prices."""
import datetime as dt
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser
from config import ROOT, load_config

USER_AGENT = 'VPSPricingRadar/1.0 (+public information directory; contact via repository)'
OUTPUT = ROOT / 'data/offers.json'

class TitleParser(HTMLParser):
    def __init__(self): super().__init__(); self.inside = False; self.parts = []
    def handle_starttag(self, tag, attrs):
        if tag == 'title': self.inside = True
    def handle_endtag(self, tag):
        if tag == 'title': self.inside = False
    def handle_data(self, data):
        if self.inside: self.parts.append(data)


def robots_permit(url):
    root = urlparse(url)
    robots = f'{root.scheme}://{root.netloc}/robots.txt'
    rule = RobotFileParser()
    try:
        with urlopen(Request(robots, headers={'User-Agent':USER_AGENT}), timeout=8) as r:
            data = r.read(512_000).decode('utf-8', 'replace')
        rule.parse(data.splitlines())
        return rule.can_fetch(USER_AGENT, url)
    except Exception:
        # Unknown permission is not permission to fetch.
        return False


def collect():
    _, providers = load_config()
    previous = {}
    if OUTPUT.exists():
        try: previous = json.loads(OUTPUT.read_text('utf-8'))
        except (ValueError, OSError): pass
    warnings, results = [], []
    # No price parser by default: provider pages vary substantially and mixed
    # billing terms cannot be safely reduced with a generic price regex.
    for entry in providers:
        row = dict(entry)
        row['status'] = 'unverified'
        row['page_title'] = ''
        url = entry['source_url']
        if not robots_permit(url):
            warnings.append(f'{entry["name"]}: robots.txt unavailable or disallows fetch')
            row['status'] = 'robots_blocked'
        else:
            try:
                with urlopen(Request(url, headers={'User-Agent': USER_AGENT,'Accept':'text/html'}), timeout=12) as r:
                    if urlparse(r.url).netloc != urlparse(url).netloc:
                        raise ValueError('cross-domain redirect')
                    raw = r.read(1_000_000).decode('utf-8', 'replace')
                parser = TitleParser(); parser.feed(raw)
                row['page_title'] = ' '.join(''.join(parser.parts).split())[:180]
                row['status'] = 'source_reachable'
            except Exception as e:
                row['status'] = 'fetch_failed'
                warnings.append(f'{entry["name"]}: fetch failed ({type(e).__name__})')
        results.append(row)
    # Preserve no stale offers. Only positively verified offers may be included.
    offers = []
    # Stable JSON avoids spurious commits every 6 hours.
    contents = {'offers':offers,'providers':results,'warnings':warnings}
    old_subset = {k:previous.get(k) for k in contents}
    if contents != old_subset:
        contents['generated_at'] = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(contents, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    return contents

if __name__ == '__main__':
    result = collect()
    print('Providers:',len(result['providers']),'Verified offers:',len(result['offers']))
    print('Warnings:', '; '.join(result['warnings']) or 'none')