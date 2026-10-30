# ::ILANG [TYPE:python-module][ROLE:official-price-collector]
# ::RULE{only:verified named plans from public first-party source, respect robots}
# ::BOUNDARY{never:guess prices, manufacture discounts, persist an empty full refresh}
"""Collect current price-listed plans from DigitalOcean and Hetzner."""
import datetime as dt
import json
import os
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

from config import ROOT, load_config
from pricing_sources import DO_PRICING, HETZNER_FEED, parse_digitalocean, parse_hetzner

USER_AGENT = "VPSPricingRadar/1.0 (+public pricing directory)"
OUTPUT = ROOT / "data/offers.json"
MAX_BYTES = 2_000_000


class TitleParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.inside = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self.inside = True

    def handle_endtag(self, tag):
        if tag == "title":
            self.inside = False

    def handle_data(self, data):
        if self.inside:
            self.parts.append(data)


def robots_permit(url):
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        return False
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    parser = RobotFileParser()
    try:
        with urlopen(Request(robots_url, headers={"User-Agent": USER_AGENT}), timeout=10) as response:
            text = response.read(512_000).decode("utf-8", "replace")
        parser.parse(text.splitlines())
        return parser.can_fetch(USER_AGENT, url)
    except Exception:
        return False


def read_official(url):
    if not robots_permit(url):
        raise PermissionError("robots.txt unavailable or disallows requested source")
    with urlopen(
        Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/json"}),
        timeout=20,
    ) as response:
        target = urlparse(response.url)
        expected = urlparse(url)
        if target.scheme != "https" or target.hostname != expected.hostname:
            raise ValueError("unexpected cross-origin redirect")
        raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("source exceeds size limit")
        return raw.decode("utf-8", "replace")


def collect():
    _, providers = load_config()
    previous = {}
    if OUTPUT.exists():
        try:
            previous = json.loads(OUTPUT.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            previous = {}

    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    warnings = []
    provider_rows = []
    offers = []
    seen = set()
    for entry in providers:
        row = dict(entry)
        row["status"] = "not_checked"
        row["page_title"] = ""
        row["verified_plan_count"] = 0
        name = entry["name"]
        source_url = entry["source_url"]
        try:
            html = read_official(source_url)
            if html.lstrip().startswith("{"):
                raise ValueError("provider landing source is not HTML")
            title = TitleParser()
            title.feed(html)
            row["page_title"] = " ".join("".join(title.parts).split())[:180]
            row["status"] = "source_reachable"
            if name == "DigitalOcean":
                # Keep the link config as a source of truth; do not parse marketing
                # promises such as "from $4" without a matching plan row.
                raw_offers = parse_digitalocean(html if source_url == DO_PRICING else read_official(DO_PRICING), now)
            elif name == "Hetzner":
                raw_offers = parse_hetzner(read_official(HETZNER_FEED), now)
            else:
                raw_offers = []
            for item in raw_offers:
                if item["id"] not in seen:
                    seen.add(item["id"])
                    offers.append(item)
                    row["verified_plan_count"] += 1
            if name in ("DigitalOcean", "Hetzner"):
                if not raw_offers:
                    row["status"] = "no_verified_prices"
                    warnings.append(f"{name}: no plan/price pairs validated in official pricing feed")
                else:
                    row["status"] = "prices_verified"
        except Exception as exc:
            row["status"] = "robots_blocked" if isinstance(exc, PermissionError) else "fetch_or_parse_failed"
            warnings.append(f"{name}: {type(exc).__name__} - {str(exc)[:110]}")
        provider_rows.append(row)

    # An empty refresh is an operational failure, NOT an instruction to
    # wipe all historical deals from GitHub/Cloudflare. The workflow fails
    # loudly and leaves the last successful data untouched.
    if not offers:
        raise RuntimeError("Zero verified plan prices. Refusing to overwrite prior dataset.")

    offers.sort(key=lambda item: (item["provider"], float(item["monthly_usd"]), item["id"]))
    result = {
        "offers": offers,
        "providers": provider_rows,
        "warnings": warnings,
        "generated_at": now,
    }
    # Only replace after all provider attempts are complete and at least one
    # official named-plan/current-price pair was verified in this execution.
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temp = OUTPUT.with_suffix(".json.tmp")
    temp.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, OUTPUT)
    return result


if __name__ == "__main__":
    data = collect()
    counts = {p["name"]: p["verified_plan_count"] for p in data["providers"]}
    print("Verified plan counts:", counts)
    print("Total deals:", len(data["offers"]))
    print("Warnings:", "; ".join(data["warnings"]) or "none")