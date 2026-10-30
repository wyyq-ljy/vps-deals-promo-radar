# ::ILANG [TYPE:python-module][ROLE:official-deal-collector]
# ::RULE{read:.ilang/site.ilang; only same-page original vs promotion}
# ::BOUNDARY{never:invent prices, currencies, expiry, or bypass robots}
"""First-party source monitor: only proven same-page price reductions are deals."""
import datetime as dt
import json
import os
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser
from config import ROOT, load_config
from pricing_sources import parse_hostinger, parse_ionos
from extra_sources import parse_dreamhost, parse_inmotion, parse_ultahost
from hostarmada_source import parse_hostarmada
from standard_prices import PARSERS as STANDARD_PARSERS
from high_volume_prices import parse_cloudways, parse_hetzner, HETZNER_JSON
from official_pricing_expansion import read_snapshots, verified_snapshot_rows
from dedicated_category import SOURCE as DEDICATED_SOURCE, live_verify as verify_dedicated
from manual_firstparty import read_manual, MANUAL_NAMES

USER_AGENT = "VPSPricingRadar/1.0 (+public pricing directory)"
OUTPUT = ROOT / "data/offers.json"

class Title(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = False
        self.text = []
    def handle_starttag(self, tag, attrs):
        if tag == "title": self.active = True
    def handle_endtag(self, tag):
        if tag == "title": self.active = False
    def handle_data(self, data):
        if self.active: self.text.append(data)

def robots_permit(url):
    address = urlparse(url)
    if address.scheme != "https" or not address.hostname: return False
    try:
        response = urlopen(Request(f"{address.scheme}://{address.netloc}/robots.txt",
                                   headers={"User-Agent": USER_AGENT}), timeout=10)
        with response:
            data = response.read(512001)
        if len(data) > 512000: return False
        rules = RobotFileParser()
        rules.parse(data.decode("utf-8", "replace").splitlines())
        return rules.can_fetch(USER_AGENT, url)
    except Exception:
        return False

def read_official(url):
    if not robots_permit(url):
        raise PermissionError("robots.txt inaccessible or disallows URL")
    with urlopen(Request(url, headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html"}), timeout=22) as response:
        source, target = urlparse(url), urlparse(response.url)
        if target.scheme != "https" or source.hostname != target.hostname:
            raise ValueError("unapproved cross-origin redirect")
        raw = response.read(2000001)
    if len(raw) > 2000000:
        raise ValueError("source exceeds 2 MB")
    return raw.decode("utf-8", "replace")

def collect():
    site, providers = load_config()
    if site.get('locale') != 'en-US' or site.get('currency') != 'USD':
        raise ValueError('This release only supports en-US/USD official pricing; add localized sources first')
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    previous = {}
    if OUTPUT.exists():
        try:
            previous = json.loads(OUTPUT.read_text('utf-8'))
        except (OSError, ValueError):
            pass
    old_offers = {o['id']: o for o in previous.get('offers', []) if isinstance(o, dict) and o.get('id')}
    snapshots = read_snapshots()
    manual = read_manual()
    old_prices = {(p.get('name'), row.get('model')): row
                  for p in previous.get('providers', []) if isinstance(p, dict)
                  for row in p.get('list_prices', []) if isinstance(row, dict) and row.get('model')}
    result = {"offers": [], "providers": [], "warnings": []}
    parsers = {"Hostinger": parse_hostinger, "IONOS": parse_ionos,
               "DreamHost": parse_dreamhost, "InMotion Hosting": parse_inmotion,
               "Ultahost": parse_ultahost, "HostArmada": parse_hostarmada}

    def check_provider(entry):
        row = dict(entry)
        row.update(status="not_checked", page_title="", verified_deal_count=0, list_prices=[])
        if entry["name"] in MANUAL_NAMES:
            # Owner copied these public first-party price tables. No request to a robots-blocked URL.
            row["list_prices"] = manual.get(entry["name"], [])
            row["status"] = ("owner_manual_firstparty_verified" if row["list_prices"]
                             else "manual_quote_expired")
            return row, [], None
        try:
            source_html = read_official(entry["source_url"])
            title = Title()
            title.feed(source_html)
            row["page_title"] = " ".join("".join(title.text).split())[:180]
            parser = parsers.get(entry["name"])
            standard = STANDARD_PARSERS.get(entry["name"])
            if not parser and not standard and entry['name'] not in ('Cloudways','Hetzner') and entry['name'] not in snapshots:
                # A valid official URL is not sufficient to create an indexed page.
                row["status"] = "parser_not_implemented"
                return row, [], None
            offers = parser(source_html, now) if parser else []
            if entry['name'] in snapshots:
                prices = verified_snapshot_rows(entry['name'],source_html,now,entry['source_url'],snapshots)
            elif entry['name'] == 'Cloudways':
                prices = parse_cloudways(source_html, now)
            elif entry['name'] == 'Hetzner':
                prices = parse_hetzner(source_html,read_official(HETZNER_JSON),now)
            else:
                prices = standard(source_html,now) if standard else []
            # A standard-rate comparison requires >=3 distinct complete named
            # configurations. Never export a partial price table as an indexable page.
            if len({p["model"] for p in prices}) >= 3 and all(
                    p["source_url"] == entry["source_url"] and p["currency"] == "USD"
                    for p in prices):
                for item in prices:
                    old = old_prices.get((entry["name"],item["model"]),{})
                    meaningful = (
                        {k:v for k,v in old.items() if k not in ("checked_at","last_changed_at")}
                        == {k:v for k,v in item.items() if k != "checked_at"}
                    )
                    item["last_changed_at"] = (
                        old.get("last_changed_at") or old.get("checked_at") or now
                    ) if meaningful else now
                row["list_prices"] = prices
            row["status"] = (
                "verified_discounts" if offers else
                "standard_prices_verified" if row["list_prices"] else
                "no_verified_discount"
            )
            return row, offers, None
        except Exception as exc:
            row["status"] = "robots_blocked" if isinstance(exc, PermissionError) else "fetch_failed"
            return row, [], f'{entry["name"]}: {type(exc).__name__} - {str(exc)[:110]}'

    # Independent official origins are checked concurrently, to keep the
    # six-hour GitHub Actions job bounded even with 20+ monitored vendors.
    with ThreadPoolExecutor(max_workers=8) as executor:
        scanned = list(executor.map(check_provider, providers))
    seen = set()
    for row, offers, warning in scanned:
        if warning:
            result["warnings"].append(warning)
        for offer in offers:
            if offer["id"] not in seen:
                before = old_offers.get(offer["id"], {})
                meaningfully_equal = (
                    {k:v for k,v in before.items() if k not in ("verified_at","last_changed_at")}
                    == {k:v for k,v in offer.items() if k != "verified_at"}
                )
                offer["last_changed_at"] = (
                    before.get("last_changed_at") or before.get("verified_at") or now
                ) if meaningfully_equal else now
                seen.add(offer["id"])
                result["offers"].append(offer)
                row["verified_deal_count"] += 1
        result["providers"].append(row)
    # Zero verified deals is a valid outcome. In particular, never preserve
    # old "standard_list_price" rows as live deals.
    result["offers"].sort(key=lambda x: (x["provider"], x["plan"]))
    # Physical dedicated servers are not VPS deals. Never retain stale prices.
    try:
        result["dedicated_prices"] = verify_dedicated(read_official(DEDICATED_SOURCE),now)
    except Exception as exc:
        result["dedicated_prices"] = []
        result["warnings"].append('Dedicated category: '+type(exc).__name__)
    result["generated_at"] = now
    if any(previous.get(k) != result[k] for k in ('offers', 'providers', 'warnings', 'dedicated_prices')):
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        staging = OUTPUT.with_suffix(".json.tmp")
        staging.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(staging, OUTPUT)
    return result

if __name__ == "__main__":
    result = collect()
    print("Verified discounts", len(result["offers"]))
    print("By provider", [(p["name"], p["status"], p["verified_deal_count"]) for p in result["providers"]])
    print("Warnings", result["warnings"])