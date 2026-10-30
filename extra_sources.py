# ::ILANG [TYPE:python-module][ROLE:additional-official-discount-parsers]
# ::RULE{one named VPS plan and source-visible sale-vs-reference price per deal}
# ::BOUNDARY{never:invent currency, term, checkout, availability or renewal}
"""Evidence-constrained parsers for three official en-US VPS offer pages."""
import re
from decimal import Decimal
from pricing_sources import plain, first, discount, money, formatted

DREAMHOST = "https://www.dreamhost.com/hosting/vps/"
INMOTION = "https://www.inmotionhosting.com/vps-hosting"
ULTAHOST = "https://ultahost.com/vps-hosting"


def deal_row(provider, model, old, promo, duration, checked, url, *, cpu, ram, disk,
             transfer, renewal, note):
    gap = discount(old, promo)
    if gap is None or not (cpu and ram and disk and duration):
        return None
    regular, current, saved, pct = gap
    if duration not in (3, 6, 12, 24, 36):
        return None
    key = re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", provider.lower() + "-" + model.lower())).strip("-")
    return {
        "id": key, "provider": provider, "plan": model,
        "price_type": "verified_discount", "currency": "USD",
        "regular_monthly_usd": formatted(regular),
        "promo_monthly_usd": formatted(current),
        "savings_monthly_usd": formatted(saved),
        "discount_percent": pct, "promo_months": duration,
        "upfront_usd": "", "renewal_monthly_usd": formatted(money(renewal)) if money(renewal) else "",
        "contract_note": note, "vcpus": cpu, "memory": ram, "disk": disk,
        "transfer": transfer or "See official plan terms",
        "region": "Select at checkout", "source_url": url,
        "offer_url": url, "verified_at": checked,
        "pricing_note": "The official page displays a reference price and a promotional rate for a specific term. Check total charges, tax, region and future renewal conditions before purchase.",
    }


def parse_dreamhost(html, checked):
    marks = [
        m for m in re.finditer(r'<span[^>]*>\s*Stack\s+(4|8|16|32)\s*</span>', html, re.I)
        if "text-3xl" in html[max(0, m.start()-100):m.start()+40]
    ]
    result, seen = [], set()
    for i, m in enumerate(marks):
        model = "Stack " + m.group(1)
        if model in seen:
            continue
        section = html[m.end():min(m.end()+10000, marks[i+1].start() if i+1<len(marks) else len(html))]
        text = plain(section)
        price = re.search(
            r'On Sale\s+First 3 months at\s+\$(\d+\.\d{2})\s*/mo\s+SAVE\s+(\d+)%'
            r'\s+Sign Up Now\s+Auto-renews at\s+\$(\d+\.\d{2})\s*/mo after 3 months',
            text, re.I,
        )
        if not price:
            continue
        current, claim, regular = price.groups()
        diff = discount(regular, current)
        if not diff or abs(diff[3]-int(claim)) > 1:
            continue
        cpu = first(r'(\d+\s+vCPU AMD EPYC)', text)
        ram = first(r'(\d+\s+GB RAM)', text)
        disk = first(r'(\d+\s+GB NVMe SSD)', text)
        bandwidth = first(r'(Unmetered Bandwidth)', text)
        row = deal_row(
            "DreamHost", model, regular, current, 3, checked, DREAMHOST,
            cpu=cpu, ram=ram, disk=disk, transfer=bandwidth, renewal=regular,
            note="Promotional rate for first 3 months; official page lists the subsequent auto-renewal rate",
        )
        if row:
            row["pricing_note"] = (
                "Official page shows the first-three-month promotional price and the higher "
                "auto-renewal rate, with a published SAVE percentage. Confirm actual checkout "
                "term, upfront payment and subsequent charges."
            )
            result.append(row)
            seen.add(model)
    return result


def parse_inmotion(html, checked):
    marks = list(re.finditer(r'<h3[^>]*>\s*VPS\s+(4|8|12|16)\s+vCPU\s*</h3>', html, re.I))
    offers, seen = [], set()
    for i, m in enumerate(marks):
        model = "VPS " + m.group(1) + " vCPU"
        if model in seen:
            continue
        segment = html[m.end():min(m.end()+11000, marks[i+1].start() if i+1<len(marks) else len(html))]
        text = plain(segment)
        sale = re.search(
            r'You Save\s+(\d+)%\s+\$(\d+\.\d{2})\s*/mo\s+'
            r'For\s+(24)\s+month term\s+Renews at\s+\$(\d+\.\d{2})\s*/mo',
            text, re.I,
        )
        if not sale:
            continue
        claim, promo, duration, original = sale.groups()
        diff = discount(original, promo)
        if not diff or abs(diff[3] - int(claim)) > 1:
            continue
        ram = first(r'(\d+\s*GB RAM)', text)
        disk = first(r'(\d+\s*GB NVMe SSD)', text)
        transfer = first(r'(\d+\s*TB Bandwidth|Unlimited Bandwidth)', text)
        row = deal_row(
            "InMotion Hosting", model, original, promo, int(duration), checked, INMOTION,
            cpu=m.group(1)+" vCPU", ram=ram, disk=disk, transfer=transfer, renewal=original,
            note="Discounted 24-month introductory VPS term with stated higher renewal rate",
        )
        if row:
            row["pricing_note"] = (
                "Selected the first displayed 24-month self-managed VPS offer within the "
                "named model card, matching its SAVE percentage and renewal reference. "
                "Other options shown on the same card may have different prices."
            )
            offers.append(row)
            seen.add(model)
    return offers


def parse_ultahost(html, checked):
    marks = list(re.finditer(r'<span class="package-name">\s*(VPS (?:Basic|Business|Professional|Enterprise))\s*</span>',html,re.I))
    result, seen = [], set()
    for i, m in enumerate(marks):
        model = m.group(1)
        if model in seen:
            continue
        section = html[m.end():min(m.end()+7000, marks[i+1].start() if i+1<len(marks) else len(html))]
        first_card = section.split('<div class="spFooter">',1)[0]
        text = plain(section[:5000])
        original = first(r'<del class="package-real-price-js"[^>]*>\$(\d+\.\d{2})</del>', first_card)
        current = first(r'<b class="package-price-js"[^>]*>\$(\d+\.\d{2})</b>', first_card)
        claim = first(r'Save\s+(\d+)%', plain(first_card))
        length = first(r'Billed for\s+(\d+)\s+month term', plain(first_card))
        renewal = first(r'Renews at\s*\$(\d+\.\d{2})\s*/mo', plain(first_card))
        diff = discount(original, current)
        if not diff or not claim or not length or not renewal or abs(diff[3]-int(claim))>2:
            continue
        cpu=first(r'(\d+\s+CPU Cores?)',text)
        ram=first(r'(\d+\s+GB RAM DDR5)',text)
        disk=first(r'(\d+\s+GB NVMe SSD)',text)
        transfer=first(r'(Unlimited Bandwidth)',text)
        row=deal_row(
            "Ultahost",model,original,current,int(length),checked,ULTAHOST,
            cpu=cpu,ram=ram,disk=disk,transfer=transfer,renewal=renewal,
            note=f"Published crossed-out reference price vs {length}-month billed promotional price",
        )
        if row:
            row["pricing_note"] = (
                "Original and discounted amounts are shown together in the named official "
                "plan card, with a 24-month billing term. The page's displayed percentage "
                "may be rounded; savings here use displayed monetary amounts. "
                "The posted renewal amount may equal the displayed promotional amount."
            )
            result.append(row)
            seen.add(model)
    return result