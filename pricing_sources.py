"""Provider-specific parsers for official, publicly visible monthly VPS list prices.

No price defaults, estimates, third-party mirrors, or coupon claims.
Every returned row ties a named server configuration to a price on an
explicit, robot-permitted first-party source.
"""
import json
import re
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser

DO_PRICING = "https://www.digitalocean.com/pricing/droplets"
HETZNER_FEED = "https://www.hetzner.com/_resources/app/data/bench/cloud_data.json"
HETZNER_REGION = "HEL1"  # one pinned region; do not mix regions in one price
_HETZNER_GROUPS = ("Shared - Regular Performance", "Dedicated - General Purpose")


def dollars(value):
    """Return a valid USD monthly amount, otherwise reject the row."""
    if not isinstance(value, str) or not re.fullmatch(r"\$?(?:\d{1,3}(?:,\d{3})*|\d+)\.\d{2}", value.strip()):
        return None
    try:
        amount = Decimal(value.strip().replace("$", "").replace(",", ""))
    except InvalidOperation:
        return None
    return f"{amount:.2f}" if Decimal("0") < amount < Decimal("10000") else None


def identifier(value):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", value.lower())).strip("-")


class SimplePricingTables(HTMLParser):
    """Extract table cell text after heading; script/style content is excluded."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.heading = ""
        self._heading_parts = None
        self._table = None
        self._row = None
        self._cell = None
        self._ignore = 0
        self.tables = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._ignore += 1
            return
        if self._ignore:
            return
        if tag == "h3":
            self._heading_parts = []
        if tag == "table":
            self._table = []
        if tag == "tr" and self._table is not None:
            self._row = []
        if tag in ("td", "th") and self._row is not None:
            self._cell = []

    def handle_data(self, data):
        if self._ignore:
            return
        if self._heading_parts is not None:
            self._heading_parts.append(data)
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._ignore = max(0, self._ignore - 1)
            return
        if self._ignore:
            return
        if tag == "h3" and self._heading_parts is not None:
            self.heading = " ".join("".join(self._heading_parts).split())
            self._heading_parts = None
        if tag in ("td", "th") and self._cell is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        if tag == "tr" and self._row is not None and self._table is not None:
            self._table.append(self._row)
            self._row = None
        if tag == "table" and self._table is not None:
            self.tables.append((self.heading, self._table))
            self._table = None


def parse_digitalocean(html_text, verified_at):
    """Basic / Regular CPU only; never mix premium tabs or other tables."""
    parser = SimplePricingTables()
    parser.feed(html_text)
    offers = []
    for heading, rows in parser.tables:
        if heading != "Basic Droplets" or not rows:
            continue
        if rows[0] != ["Memory", "vCPU", "Transfer", "SSD", "$/hr", "$/mo"]:
            continue  # reject page redesign rather than guessing column positions
        for row in rows[1:]:
            if len(row) != 6:
                continue
            memory, cpu, transfer, disk, hourly, monthly = row
            if not (re.fullmatch(r"\d+ (?:MiB|GiB)", memory) and
                    re.fullmatch(r"\d+ vCPUs?", cpu) and
                    re.fullmatch(r"[\d,]+ GiB", transfer) and
                    re.fullmatch(r"[\d,]+ GiB", disk) and
                    re.fullmatch(r"\$0\.\d{5}", hourly)):
                continue
            price = dollars(monthly)
            if not price:
                continue
            label = f"Basic Regular - {memory} RAM / {cpu} / {disk} SSD"
            offers.append({
                "id": "digitalocean-" + identifier(label),
                "provider": "DigitalOcean",
                "plan": label,
                "monthly_usd": price,
                "currency": "USD",
                "period": "month",
                "price_type": "standard_list_price",
                "region": "Region selection at checkout",
                "vcpus": int(cpu.split()[0]),
                "memory": memory,
                "disk": disk,
                "transfer": transfer,
                "source_url": DO_PRICING,
                "offer_url": DO_PRICING,
                "verified_at": verified_at,
                "pricing_note": "Published Basic Regular monthly cap; usage-based billing, taxes and extras may apply. Not a promotional discount.",
            })
        if offers:
            break
    return offers


def parse_hetzner(json_text, verified_at):
    """Only HEL1 USD net monthly amounts in Hetzner's published pricing feed."""
    try:
        data = json.loads(json_text)
        matrix = data["Matrix"]
    except (ValueError, KeyError, TypeError):
        return []
    if not isinstance(matrix, dict):
        return []
    offers = []
    for group in _HETZNER_GROUPS:
        plans = matrix.get(group)
        if not isinstance(plans, dict):
            continue
        for plan_name, details in sorted(plans.items()):
            if not re.fullmatch(r"(?:CPX|CCX)\d{2}", plan_name) or not isinstance(details, dict):
                continue
            location = details.get("locations", {}).get(HETZNER_REGION, {})
            usd = location.get("USD", {}) if isinstance(location, dict) else {}
            price = dollars(usd.get("price")) if isinstance(usd, dict) else None
            cores = details.get("cores")
            if not price or type(cores) is not int or not 1 <= cores <= 64:
                continue
            label = f"{plan_name} - {cores} vCPU ({'shared' if plan_name.startswith('CPX') else 'dedicated'})"
            offers.append({
                "id": "hetzner-" + identifier(plan_name) + "-hel1",
                "provider": "Hetzner",
                "plan": label,
                "monthly_usd": price,
                "currency": "USD",
                "period": "month",
                "price_type": "standard_list_price",
                "region": "Helsinki, Finland (HEL1)",
                "vcpus": cores,
                "source_url": HETZNER_FEED,
                "offer_url": "https://www.hetzner.com/cloud/",
                "verified_at": verified_at,
                "pricing_note": "Published USD monthly net price for HEL1; excludes VAT and primary IPv4. Availability and additional charges must be checked. Not a promotional discount.",
            })
    return offers