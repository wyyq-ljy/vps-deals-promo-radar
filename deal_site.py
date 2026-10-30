# ::ILANG [TYPE:python-module][ROLE:verified-deal-pages]
# ::RULE{only offer when current regular price exceeds promo for same named plan}
# ::BOUNDARY{never:invent price, inventory, dates, affiliate approvals}
"""One verified VPS discount per provider + model + currency."""
from collections import defaultdict
from decimal import Decimal
from html import escape
import re
from pricing_sources import money
from seo_helpers import breadcrumbs, expired, jsonld, valid_expiry
from template_engine import render


def e(value):
    return escape(str(value if value is not None else ""), quote=True)


def provider_slug(value):
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', value.lower())).strip('-')

def valid_offers(records, providers):
    allowed = {p["name"] for p in providers}
    seen, verified = set(), []
    for item in records:
        if not isinstance(item, dict):
            continue
        required = ("id", "provider", "plan", "regular_monthly_usd",
                    "promo_monthly_usd", "savings_monthly_usd", "source_url",
                    "offer_url", "verified_at", "contract_note", "pricing_note",
                    "memory", "disk", "vcpus")
        if any(not isinstance(item.get(k), str) or not item[k] for k in required):
            continue
        if (item["provider"] not in allowed
                or item.get("price_type") != "verified_discount"
                or item.get("currency") != "USD"
                or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in item["id"])
                or not item["id"].startswith(provider_slug(item["provider"]) + "-")
                or any(not item[k].startswith("https://") for k in ("source_url", "offer_url"))
                or (item.get('valid_until') and not valid_expiry(item['valid_until']))
                or expired(item)):
            continue
        old, new, saving = (money(item[k]) for k in (
            "regular_monthly_usd", "promo_monthly_usd", "savings_monthly_usd"))
        if old is None or new is None or saving is None or not new < old or old-new != saving:
            continue
        months, pct = item.get("promo_months"), item.get("discount_percent")
        if type(months) is not int or not 1 <= months <= 48 or type(pct) is not int:
            continue
        calculated = int(((old-new)*Decimal(100)/old).quantize(Decimal("1")))
        if calculated != pct:
            continue
        # No duplicate display even if a future scraper accidentally assigns
        # different IDs to the same provider/model/currency.
        key = (item["provider"], item["plan"], item["currency"])
        if key in seen:
            continue
        seen.add(key)
        verified.append(item)
    return verified


def route_for(item):
    return f'deals/{item["id"]}/'


def short_card(item):
    return (
        f'<article class="card"><div class="eyebrow">{e(item["provider"])} · Verified discount</div>'
        f'<h2><a href="/{route_for(item)}">{e(item["plan"])}</a></h2>'
        f'<p><del>&#36;{e(item["regular_monthly_usd"])}/mo</del>'
        f' &nbsp; <strong>&#36;{e(item["promo_monthly_usd"])}/mo</strong>'
        f' &nbsp; <strong>Save {e(item["discount_percent"])}%</strong></p>'
        f'<p>{e(item["contract_note"])}</p>'
        f'<p>{e(item["memory"])} · {e(item["disk"])}</p>'
        f'<div class="actions"><a href="/{route_for(item)}">See verified saving and conditions</a></div></article>'
    )


def build_deals(items, page, save, brand, base="", affiliate_links=None):
    affiliate_links = affiliate_links or {}
    routes, grouped = [], defaultdict(list)
    for item in items:
        grouped[item["provider"]].append(item)
        route = route_for(item)
        routes.append(route)
        old, current, saved = (item[k] for k in (
            "regular_monthly_usd", "promo_monthly_usd", "savings_monthly_usd"))
        title = f'{item["provider"]} {item["plan"]}: save {item["discount_percent"]}% for {item["promo_months"]} months | {brand}'
        desc = (f'{item["plan"]} verified official offer: regular USD {old}/mo, '
                f'promotional USD {current}/mo for {item["promo_months"]} months. '
                f'Conditions apply; checked {item["verified_at"]}.')
        renewal = (f'<p>Advertised renewal: &#36;{e(item["renewal_monthly_usd"])}/month after the initial term.</p>'
                   if item.get("renewal_monthly_usd") else
                   '<p>Post-promotion rate: confirm in the official checkout before purchase.</p>')
        upfront = (f'<p>Initial payment: &#36;{e(item["upfront_usd"])} prepaid.</p>'
                   if item.get("upfront_usd") else '')
        offer_schema = {
            "@type": "Offer", "price": current,
            "priceCurrency": item["currency"], "url": item["offer_url"],
            "seller": {"@type": "Organization", "name": item["provider"]},
        }
        # These are optional, and must never be invented.
        date = valid_expiry(item.get("valid_until"))
        if date:
            offer_schema["priceValidUntil"] = date
        if item.get("availability") in (
                "https://schema.org/InStock", "https://schema.org/OutOfStock",
                "https://schema.org/LimitedAvailability"):
            offer_schema["availability"] = item["availability"]
        structured = jsonld({
            "@context": "https://schema.org", "@type": "Product",
            "name": item["plan"],
            "brand": {"@type": "Brand", "name": item["provider"]},
            "description": desc, "offers": offer_schema,
        })
        if base:
            structured += breadcrumbs(base, [
                ("Home", ""), (item["provider"], f'providers/{provider_slug(item["provider"])}/'),
                (item["plan"], route),
            ])
        affiliate_url = affiliate_links.get(item['provider'], '')
        if affiliate_url and not affiliate_url.startswith('https://'):
            raise ValueError('Affiliate links must be explicit HTTPS URLs')
        checkout_url = affiliate_url or item['offer_url']
        checkout_label = ('Check current price with provider (affiliate link) ↗'
                          if affiliate_url else 'Check current price with provider ↗')
        checkout_rel = 'nofollow sponsored noopener noreferrer' if affiliate_url else 'noopener noreferrer'
        body = render(
            "deal.html",
            verified_at=e(item["verified_at"]), provider=e(item["provider"]),
            plan=e(item["plan"]), regular_price=e(old), promo_price=e(current),
            saving=e(saved), saving_percent=e(item["discount_percent"]),
            contract_note=e(item["contract_note"]), promo_months=e(item["promo_months"]),
            upfront_html=upfront, renewal_html=renewal, pricing_note=e(item["pricing_note"]),
            vcpus=e(item["vcpus"]), memory=e(item["memory"]), disk=e(item["disk"]),
            transfer=e(item.get("transfer", "Check provider terms")),
            region=e(item.get("region", "Choose in checkout")),
            source_url=e(item["source_url"]), offer_url=e(checkout_url),
            checkout_label=e(checkout_label), checkout_rel=e(checkout_rel),
            structured_data=structured,
        )
        save(route + "index.html", page(title, desc, body, route))
    return routes, grouped, "".join(short_card(item) for item in items)