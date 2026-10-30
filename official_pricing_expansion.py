# ::ILANG [TYPE:python-module][ROLE:verified-official-pricing-snapshots]
# ::BOUNDARY{never:third-party prices; stale static models; currency conversion}
"""Parse live first-party pages and admit only exact matching I-Lang static snapshots."""
import re
from config import ROOT
from pricing_sources import plain, parse_hostinger, parse_ionos
from extra_sources import parse_dreamhost
from standard_prices import row

MANUAL_PROVIDERS = ("Hostinger", "DreamHost", "IONOS", "Kamatera",
                    "Hostwinds", "HostArmada", "UpCloud")
SNAPSHOT_KEYS = ("model", "monthly_usd", "cpu", "memory", "storage", "transfer")
DEFAULT_NOTES = {
    "Hostinger": "24-month prepaid effective promotional monthly price. Higher renewal rate; taxes and region can vary.",
    "DreamHost": "Monthly plan promotional rate for first three months, then advertised renewal rate. Tax may apply.",
    "IONOS": "First three months introductory rate with 12-month contract. Later monthly charges differ.",
    "Kamatera": "Recommended VPS configuration at published monthly rate; add-ons and region choices can affect checkout.",
    "Hostwinds": "Unmanaged Linux VPS advertised USD monthly rate; billing term, taxes and extras require checkout confirmation.",
    "HostArmada": "Promotional effective USD monthly price for the selected 12-month billing cycle; renewal may differ.",
    "UpCloud": "USD global monthly cap with hourly billing; tax excluded and zero-cost egress subject to Fair Transfer Policy.",
}

def live_rows(name, html, checked, source):
    """Complete plan rows only. Values must be co-located on the current official page."""
    results = []
    def add(model, amount, cpu, ram, disk, transfer, note=None):
        item = row(model, str(amount), cpu, ram, disk, transfer,
                   note or DEFAULT_NOTES[name], source, checked)
        if item: results.append(item)

    if name in ("Hostinger", "DreamHost", "IONOS"):
        parser = {"Hostinger": parse_hostinger,
                  "DreamHost": parse_dreamhost, "IONOS": parse_ionos}[name]
        for x in parser(html, checked):
            renewal = x.get("renewal_monthly_usd")
            note = DEFAULT_NOTES[name] + ((" Published renewal: USD " + renewal + "/month.") if renewal else " Subsequent monthly amount must be checked at checkout.")
            add(x["plan"], x["promo_monthly_usd"], x["vcpus"],
                x["memory"], x["disk"], x.get("transfer") or "See provider terms", note)
        return results

    text = plain(html)
    if name == "Kamatera":
        for model in ("Basic", "Standard", "Pro"):
            # The first-party recommendation card itself must contain every field.
            hit = re.search(
                rf"\b{model} \$([\d.]+) /mo Create server (\d+) vCPU"
                r".{0,120}?(\d+) GB RAM \(Memory\) (\d+) GB NVMe SSD Storage "
                r"(\d+) TB Internet Traffic", text)
            if hit:
                price, cpu, ram, disk, traffic = hit.groups()
                add(model, price, cpu+" vCPU", ram+" GB RAM",
                    disk+" GB NVMe SSD", traffic+" TB Internet Traffic")
    elif name == "Hostwinds":
        for cpu, ram, disk, transfer, price in re.findall(
            r"CPU (\d+) CPU RAM (\d+) GB Storage (\d+) GB "
            r"Bandwidth (\d+) TB Price \$ ([\d.]+)/mo", text):
            add("Unmanaged Linux "+ram+" GB / "+cpu+" CPU",price,
                cpu+" CPU",ram+" GB RAM",disk+" GB SSD",transfer+" TB")
    elif name == "HostArmada":
        for model in ("Spark", "Flux", "Fusion", "Ignition"):
            # The selected 12-month card contains sale, regular, CPU, RAM, SSD, transfer.
            m = re.search(
                rf"\b{model} (?:\d+% OFF) \$([\d.]+) /mo "
                r"Regular Price: \$([\d.]+) /mo Specifications "
                r"(\d+) GB NVMe Storage (\d+) Cores? CPU "
                r"(\d+) GB RAM (\d+) TB Bandwidth", text)
            if m:
                price, regular, disk, cpu, ram, transfer=m.groups()
                add(model,price,cpu+" CPU",ram+" GB RAM",
                    disk+" GB NVMe",transfer+" TB",
                    DEFAULT_NOTES[name]+" Official displayed regular price: USD "+regular+"/month.")
    elif name == "UpCloud":
        start=text.find("Memory CPU cores Bandwidth Storage Global Price")
        end=text.find("Starter plans are billed",start)
        if start>=0 and end>start and "Currently showing prices in US dollars" in text:
            for ram,cpu,bandwidth,disk,price in re.findall(
                r"(\d+) GB (\d+) (\d+) Mbit/s (\d+) GB \$([\d.]+)/mo",
                text[start:end]):
                add(f"Starter {ram}GB / {cpu} vCPU / {disk}GB", price,
                    cpu+" vCPU",ram+" GB RAM",disk+" GB SSD",
                    bandwidth+" Mbit/s port; zero-cost egress, fair use")
        start=text.find("Memory CPU cores MaxIOPS Global Price")
        end=text.find("Premium plans are billed",start)
        if start>=0 and end>start and "Currently showing prices in US dollars" in text:
            for ram,cpu,disk,price in re.findall(
                r"(\d+) GB (\d+) (\d+) GB \$([\d.]+)/mo",text[start:end]):
                add(f"Premium {ram}GB / {cpu} vCPU / {disk}GB",price,
                    cpu+" vCPU",ram+" GB RAM",disk+" GB MaxIOPS",
                    "1 Gbps port; zero-cost egress, fair use")
    # Fail closed on duplicate model labels.
    if len({r["model"] for r in results}) != len(results):
        return []
    return results

def read_snapshots(path=None):
    """Simple, auditable static data section from .ilang/site.ilang; nothing inferred."""
    content = (path or ROOT/".ilang/site.ilang").read_text(encoding="utf-8")
    part = content.split("::MODULE{PRICING_SNAPSHOTS",1)
    if len(part)!=2:return {}
    body = part[1].split("\n",1)[-1].split("::MODULE{",1)[0]
    output = {}
    for raw in body.splitlines():
        if not raw.startswith("PRICE | "):continue
        fields=[v.strip() for v in raw.split(" | ")]
        if len(fields)!=11:raise ValueError("Snapshot requires 10 fields after PRICE")
        _,provider,model,monthly,cpu,memory,storage,transfer,source,checked,note=fields
        if not all((provider,model,monthly,cpu,memory,storage,transfer,source,checked,note)):
            raise ValueError("Incomplete snapshot")
        if provider not in MANUAL_PROVIDERS or not source.startswith("https://"):
            raise ValueError("Unapproved snapshot provider or source")
        output.setdefault(provider,[]).append(dict(model=model,monthly_usd=monthly,
            currency="USD",cpu=cpu,memory=memory,storage=storage,transfer=transfer,
            source_url=source,checked_at=checked,price_note=note))
    return output

def verified_snapshot_rows(provider, html, checked, source, snapshots):
    """Live revalidation avoids publishing cached pricing when a plan changes."""
    expected = snapshots.get(provider) or []
    current = {x["model"]:x for x in live_rows(provider,html,checked,source)}
    matched=[]
    for saved in expected:
        actual=current.get(saved["model"])
        if (actual and saved["source_url"]==source and saved["currency"]=="USD"
                and all(saved[k]==actual[k] for k in SNAPSHOT_KEYS)
                and saved["price_note"]==actual["price_note"]):
            matched.append(actual)
    return matched if len(matched)>=3 else []
