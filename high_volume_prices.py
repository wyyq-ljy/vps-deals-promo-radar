# ::ILANG [TYPE:python-module][ROLE:high-volume-vendor-pricing]
# ::RULE{only same-plan official USD monthly prices + RAM CPU storage}
# ::BOUNDARY{never:guess price, convert currency, relabel provider markup}
"""Official named USD pricing plans for high-intent vendor landing pages."""
import json
import re
from decimal import Decimal
from pricing_sources import plain
from standard_prices import row

HETZNER_SOURCE = "https://www.hetzner.com/cloud/general-purpose/"
HETZNER_JSON = "https://www.hetzner.com/_resources/app/data/bench/cloud_data.json"
CLOUDWAYS_SOURCE = "https://www.cloudways.com/en/vps-hosting.php"

def parse_cloudways(html, checked):
    text=plain(html)
    # Match the explicit Standard USD/mo label and the following configuration
    # in the same consecutive official card, excluding Premium comparison prices.
    pattern=re.compile(
        r'\$\s*([\d,]+)\s+USD/mo\s+\$\s*[\d.]+\s*/hr\s+'
        r'Excluding Taxes\.\s*Includes DO Hosting Charges\.\s+'
        r'(\d+)GB RAM\s+(\d+) Core Processor\s+'
        r'(\d+)GB Storage\s+(\d+)TB Bandwidth',
        re.I
    )
    plans={}
    for m in pattern.finditer(text):
        amount,ram,cpus,disk,transfer=m.groups()
        name=f"DigitalOcean Standard {ram}GB"
        item=row(name,amount.replace(",",""),f"{cpus} Core Processor",
                 f"{ram} GB RAM",f"{disk} GB Storage",f"{transfer} TB Bandwidth",
                 "Official Cloudways managed DigitalOcean Standard monthly hosting rate, "
                 "excluding taxes. This is Cloudways billing, not a DigitalOcean direct price; "
                 "offsite backups and optional services may incur extra charges.",
                 CLOUDWAYS_SOURCE,checked)
        if item and name not in plans:plans[name]=item
    return list(plans.values())

def parse_hetzner(html,pricing_json,checked):
    text=plain(html)
    try:
        data=json.loads(pricing_json)
        matrix=data["Matrix"]["Dedicated - General Purpose"]
    except (KeyError,ValueError,TypeError):return []
    plans=[]
    # One unequivocal region (US Hillsboro) is used to avoid conflating EU
    # and US tariffs; official page + official JSON are cross-checked.
    for name in ("CCX13","CCX23","CCX33","CCX43","CCX53","CCX63"):
        match=re.search(
            rf'\b{name}\s+(\d+)\s+AMD\s+(\d+)\s+GB\s+'
            rf'([\d,]+)\s+GB\s+NVMe',text,re.I
        )
        if not match:continue
        cores,ram,disk=match.groups()
        vendor=matrix.get(name,{})
        if str(vendor.get("cores"))!=cores:continue
        usd=(vendor.get("locations",{}).get("HIL1") or {}).get("USD",{})
        amount=usd.get("price")
        try:
            value=Decimal(str(amount))
            if value<=0:continue
        except Exception:continue
        item=row(name,str(value),f"{cores} dedicated vCPU",f"{ram} GB RAM",
                 f"{disk} GB NVMe", "US region: see provider transfer and bandwidth terms",
                 "Official HIL1 (Hillsboro, USA) USD monthly price cap, excluding VAT and any "
                 "separately charged IPv4. Source cross-check: official plan specification "
                 f"page and current official pricing JSON ({HETZNER_JSON}). "
                 "Hourly metering and region availability apply; checkout may differ.",
                 HETZNER_SOURCE, checked)
        if item:
            item["region"]="US HIL1"
            plans.append(item)
    return plans