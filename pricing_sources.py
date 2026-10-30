"""Only publish live, same-official-page old-price vs promotional-price differences.

Marketing-only claims, signup credits, standard list prices, missing
billing terms, and unverifiable price displays do not become deals.
"""
from decimal import Decimal, InvalidOperation
from html import unescape
from html.parser import HTMLParser
import re

HOSTINGER_URL = "https://www.hostinger.com/vps-hosting"
IONOS_URL = "https://www.ionos.com/servers/vps.html"

def money(value):
    if not isinstance(value, str) or not re.fullmatch(r"\$?\d{1,5}(?:\.\d{1,2})?", value.strip()):
        return None
    try:
        amount = Decimal(value.strip().lstrip("$"))
    except InvalidOperation:
        return None
    return amount if Decimal("0") < amount < Decimal("100000") else None

def formatted(value):
    return f"{value:.2f}"

def discount(regular_text, promo_text):
    regular, promo = money(regular_text), money(promo_text)
    if regular is None or promo is None or promo >= regular:
        return None
    saving = regular - promo
    return regular, promo, saving, int((saving / regular * 100).quantize(Decimal("1")))

def first(pattern, text, flags=re.S | re.I):
    found = re.search(pattern, text, flags)
    return found.group(1) if found else None

class Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.pieces = []
        self.ignore = 0
    def handle_starttag(self, tag, attrs):
        if tag in ("script","style"):
            self.ignore += 1
    def handle_endtag(self, tag):
        if tag in ("script","style"):
            self.ignore = max(0, self.ignore-1)
    def handle_data(self, data):
        if not self.ignore:
            self.pieces.append(data)
def plain(html):
    p = Text()
    p.feed(html)
    return " ".join(" ".join(p.pieces).split())

def parse_hostinger(html, checked):
    # Each price must be inside the SAME identifiable KVM pricing card,
    # with a crossed original and an advertised monthly current price.
    markers = list(re.finditer(
        r'<div class="h-pricing-card__title[^"]*"[^>]*>[\s\S]{0,200}?KVM\s+([1248])\b',
        html, re.I
    ))
    result = []
    names = set()
    for i, hit in enumerate(markers):
        model = "KVM " + hit.group(1)
        if model in names:
            continue
        end = min(len(html), hit.end() + 30000,
                  markers[i+1].start() if i+1 < len(markers) else len(html))
        section = html[hit.end():end]
        regular = first(r'h-pricing-card__old-price[\s\S]{0,550}?hw-price__value[^>]*>(\d+\.\d{2})<', section)
        promo = first(r'h-pricing-card__current-price[\s\S]{0,550}?hw-price__value[^>]*>(\d+\.\d{2})<', section)
        terms = re.search(
            r'Today you pay \$(\d+\.\d{2}) for (\d+) months\.\s*Renews at \$(\d+\.\d{2})/mo',
            plain(section), re.I,
        )
        differential = discount(regular, promo)
        if not differential or not terms:
            continue
        old, new, saved, percent = differential
        upfront, months, renewal = money(terms.group(1)), int(terms.group(2)), money(terms.group(3))
        if months < 1 or months > 48 or upfront is None or renewal is None:
            continue
        if abs(upfront - new * months) > Decimal("0.05"):
            continue
        text = plain(section)
        cpu = first(r'(\d+\s+vCPU core)', text)
        ram = first(r'(\d+\s+GB RAM)', text)
        disk = first(r'(\d+\s+GB NVMe disk space)', text)
        bandwidth = first(r'(\d+\s+TB bandwidth)', text)
        if not all((cpu, ram, disk, bandwidth)):
            continue
        names.add(model)
        result.append({
            "id": "hostinger-" + model.lower().replace(" ", "-"),
            "provider": "Hostinger", "plan": model, "price_type": "verified_discount",
            "regular_monthly_usd": formatted(old), "promo_monthly_usd": formatted(new),
            "savings_monthly_usd": formatted(saved), "discount_percent": percent,
            "currency": "USD", "promo_months": months, "upfront_usd": formatted(upfront),
            "renewal_monthly_usd": formatted(renewal), "contract_note": f"Prepaid {months}-month introductory term",
            "vcpus": cpu, "memory": ram, "disk": disk, "transfer": bandwidth,
            "region": "Select at checkout", "source_url": HOSTINGER_URL,
            "offer_url": HOSTINGER_URL, "verified_at": checked,
            "pricing_note": "Discounted price is an effective monthly rate billed in full upfront. Renewal rate is higher; taxes and region availability may vary.",
        })
    return result

def parse_ionos(html, checked):
    # Explicit old and current price, with official 'Save $X' validated
    # against the first-three-month difference and an annual commitment.
    markers = list(re.finditer(r'<h3[^>]*>VPS\s+(S|M|L|XL|XXL)\+</h3>', html, re.I))
    offers, names = [], set()
    for i, hit in enumerate(markers):
        model = "VPS " + hit.group(1).upper() + "+"
        if model in names:
            continue
        end = min(len(html), hit.end() + 7000,
                  markers[i+1].start() if i+1 < len(markers) else len(html))
        section = html[hit.end():end]
        boxed = first(r'(<div class="price-box[^"]*"[\s\S]{0,1800}?</div></div></div>)', section)
        if not boxed:
            boxed = section[:1600]
        old = first(r'class="original-price"[^>]*>\$(\d+(?:\.\d{1,2})?)<', boxed)
        current = first(r'class="price_value"[^>]*>(\d+(?:\.\d{1,2})?)<', boxed)
        saving_mark = first(r'Save \$(\d+(?:\.\d{1,2})?)', boxed)
        duration = first(r'for\s+(\d+)\s+months', boxed)
        annual = "with a 1-year term" in boxed
        differential = discount(old, current)
        if not differential or not saving_mark or not duration or not annual:
            continue
        base, promo, saved, percentage = differential
        months = int(duration)
        saved_total = money(saving_mark)
        if months != 3 or saved_total is None or saved_total != saved * months:
            continue
        text = plain(section)
        cpu = first(r'(\d+\s+vCores?)\s+CPU', text)
        ram = first(r'(\d+\s+GB)\s+RAM', text)
        disk = first(r'(\d+\s+GB)\s+NVMe', text)
        if not all((cpu, ram, disk)):
            continue
        names.add(model)
        offers.append({
            "id": "ionos-" + model.lower().replace(" ", "-").replace("+", "-plus"),
            "provider": "IONOS", "plan": model, "price_type": "verified_discount",
            "regular_monthly_usd": formatted(base), "promo_monthly_usd": formatted(promo),
            "savings_monthly_usd": formatted(saved), "discount_percent": percentage,
            "currency": "USD", "promo_months": months, "upfront_usd": "",
            "renewal_monthly_usd": "", "contract_note": "Introductory rate for first 3 months with a 1-year term",
            "vcpus": cpu, "memory": ram + " RAM", "disk": disk + " NVMe", "transfer": "Unlimited traffic (subject to provider terms)",
            "region": "Select at checkout", "source_url": IONOS_URL,
            "offer_url": IONOS_URL, "verified_at": checked,
            "pricing_note": "Advertised 3-month introductory rate with 1-year commitment. Subsequent monthly charge, any fees and taxes must be confirmed at checkout. Do not treat the introductory rate as the full-year rate.",
        })
    return offers