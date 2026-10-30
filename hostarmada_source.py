# ::ILANG [TYPE:python-module][ROLE:official-hostarmada-promotion-parser]
# ::RULE{selected annual term, price visible both in page text and first-party pricing JSON}
# ::BOUNDARY{never:replace promotion with another billing term or inferred coupon}
"""Parse named HostArmada VPS discounts with dual independent same-page checks."""
import json
import re
from pricing_sources import money, formatted, discount, plain
from extra_sources import deal_row

URL = "https://hostarmada.com/vps-hosting/"
PLAN_NAMES = ("Spark", "Flux", "Fusion", "Ignition")


def parse_hostarmada(html, checked):
    match = re.search(
        r'<script[^>]*type="application/json"[^>]*data-product-pricing[^>]*>'
        r'(\{[\s\S]*?\})\s*</script>', html, re.I
    )
    if not match:
        return []
    try:
        data = json.loads(match.group(1))
    except (ValueError, TypeError):
        return []
    if data.get("recommendedCycle") != "annually":
        return []
    plans = data.get("products", {})
    if not isinstance(plans, dict):
        return []
    text = plain(html)
    rows = []
    for name in PLAN_NAMES:
        spec = re.search(
            rf'\b{re.escape(name)}\s+(\d+)% OFF\s+\$(\d+\.\d{{2}})\s*/mo\s+'
            rf'Regular Price:\s+\$(\d+\.\d{{2}})\s*/mo\s+Specifications\s+'
            rf'(\d+\s+GB NVMe Storage)\s+(\d+\s+Cores?\s+CPU)\s+'
            rf'(\d+\s+GB RAM)\s+(\d+\s+TB Bandwidth)',
            text, re.I
        )
        if not spec:
            continue
        advertised_percent, sale, old, disk, cpu, ram, transfer = spec.groups()
        candidates = [p for p in plans.values()
                      if isinstance(p,dict) and p.get("name") == name
                      and p.get("currency") == "USD"]
        if len(candidates) != 1:
            continue
        annual = candidates[0].get("cycles", {}).get("annually", {})
        if not annual.get("available") or annual.get("months") != 12:
            continue
        regular = annual.get("regular", {})
        signup = annual.get("signup", {})
        renewal = annual.get("renewal", {})
        saving = annual.get("savings", {})
        promo = annual.get("promotion", {})
        if not all(isinstance(p, dict) for p in (regular, signup, renewal, saving, promo)):
            continue
        p_old = money(regular.get("monthlyEquivalent"))
        p_sale = money(signup.get("monthlyEquivalent"))
        p_renew = money(renewal.get("monthlyEquivalent"))
        diff = discount(old, sale)
        if (not diff or p_old != diff[0] or p_sale != diff[1] or
                p_renew != p_old or abs(diff[3] - int(advertised_percent))>1):
            continue
        if money(saving.get("total")) is None or not promo.get("code"):
            continue
        row = deal_row(
            "HostArmada", name, old, sale, 12, checked, URL,
            cpu=cpu, ram=ram, disk=disk, transfer=transfer,
            renewal=regular, note="Official 12-month upfront introductory term, with monthly-equivalent discount versus regular annual rate",
        )
        if row:
            row["pricing_note"] = (
                "The same official page confirms matching plan name, annually billed prices, "
                "regular vs discounted rate, and 12-month duration in both displayed plan "
                "and embedded first-party pricing data. The annual total is charged "
                "at checkout; confirm tax and any restrictions before purchase."
            )
            rows.append(row)
    return rows