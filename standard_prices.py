# ::ILANG [TYPE:python-module][ROLE:official-standard-vps-prices]
# ::RULE{three-plus specific USD plan prices from exact official page, never a deal}
# ::BOUNDARY{never:infer currency, convert EUR, or claim promotions}
"""Parse separately identifiable USD list-price configurations from official pages."""
import re
from decimal import Decimal, InvalidOperation
from pricing_sources import money, formatted, plain

SOURCES = {
    "DigitalOcean": "https://www.digitalocean.com/pricing/droplets",
    "BuyVM": "https://buyvm.net/kvm-dedicated-server-slices/",
    "OVHcloud": "https://us.ovhcloud.com/vps/",
}

def row(model, price, cpu, memory, storage, transfer, note, source, checked):
    m = money(price)
    if m is None or not all((model, cpu, memory, storage, source, checked)):
        return None
    return {
        "model": model, "monthly_usd": formatted(m), "currency": "USD",
        "cpu": cpu, "memory": memory, "storage": storage,
        "transfer": transfer or "See provider terms",
        "price_note": note, "source_url": source, "checked_at": checked,
    }

def parse_digitalocean(html, checked):
    text = plain(html)
    marker = "Memory vCPU Transfer SSD $/hr $/mo"
    start = text.find(marker)
    end = text.find("CPU-Optimized Droplets",start+len(marker))
    if start < 0 or end < 0: return []
    segment = text[start+len(marker):end]
    pat = re.compile(
        r"\b(512 MiB|\d+ GiB)\s+(\d+ vCPUs?)\s+([\d,]+ GiB)\s+"
        r"([\d,]+ GiB)\s+\$\s*([\d.]+)\s+\$\s*([\d,.]+)"
    )
    results = []
    for x in pat.finditer(segment):
        ram, cpu, transfer, disk, hourly, monthly = x.groups()
        # The official same-row hourly rate and monthly price must both exist.
        try:
            if Decimal(hourly) <= 0:
                continue
        except InvalidOperation:
            continue
        record = row(
            f"Basic Droplet Regular {ram} / {cpu}", monthly.replace(",",""),
            cpu, ram, disk+" SSD", transfer,
            "Official standard Basic/Regular monthly cap; usage is billed per second, with a minimum charge.",
            SOURCES["DigitalOcean"], checked,
        )
        if record: results.append(record)
    return results

def parse_buyvm(html, checked):
    marks = list(re.finditer(r"<h2>\s*SLICE\s*<span>(\d+)</span>\s*</h2>",html,re.I))
    records = []
    for i, m in enumerate(marks):
        model = "SLICE " + m.group(1)
        segment = html[m.end():marks[i+1].start() if i+1<len(marks) else min(m.end()+3800,len(html))]
        t = plain(segment)
        match = re.search(
            r"(\d+\s+Core(?:s)?)\s+@\s+[\d.]+\+\s+GHz[\s\S]*?"
            r"(\d+\s+MB) Memory\s+(\d+\s+GB) SSD Storage[\s\S]*?"
            r"\$(\d+\.\d{2})\s+per month",t,re.I
        )
        if not match:continue
        cpu, ram, disk, amount = match.groups()
        if int(ram.split()[0]) != int(m.group(1)):
            continue
        record = row(model,amount,cpu,ram,disk+" SSD","Unmetered (fair-use conditions apply)",
            "Official listed monthly rate for a KVM slice, not a time-limited discount; availability is not verified.",
            SOURCES["BuyVM"],checked)
        if record:records.append(record)
    return records

def parse_ovhcloud(html, checked):
    t = plain(html)
    records = []
    for size in range(1,9):
        regex = re.compile(
            rf"\bVPS-{size}\s+Starting at\s+\$(\d+\.\d{{2}})\s*/month\s+Configure\s+"
            rf"(\d+\s+vCores?)\s+(\d+\s+GB)\s+RAM\s+(\d+\s+GB)\s+SSD NVMe",
            re.I
        )
        m = regex.search(t)
        if not m:continue
        amount,cpu,ram,disk = m.groups()
        item = row(f"VPS-{size}",amount,cpu,ram+" RAM",disk+" NVMe SSD",
            "See official regional terms",
            "Official USD starting monthly price, not a guaranteed checkout total; taxes and chosen settings may differ.",
            SOURCES["OVHcloud"],checked)
        if item:records.append(item)
    return records

PARSERS = {
    "DigitalOcean": parse_digitalocean,
    "BuyVM": parse_buyvm,
    "OVHcloud": parse_ovhcloud,
}