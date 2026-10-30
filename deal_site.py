"""Deal pages require a demonstrable current official regular-vs-sale price gap."""
from collections import defaultdict
from decimal import Decimal
from html import escape
import json
from pricing_sources import money

def e(x): return escape(str(x if x is not None else ""), quote=True)

def valid_offers(records, providers):
    allowed = {p["name"] for p in providers}
    seen, verified = set(), []
    for item in records:
        if not isinstance(item, dict): continue
        required = ("id", "provider", "plan", "regular_monthly_usd",
                    "promo_monthly_usd", "savings_monthly_usd", "source_url",
                    "offer_url", "verified_at", "contract_note", "pricing_note",
                    "memory", "disk", "vcpus")
        if any(not isinstance(item.get(k), str) or not item[k] for k in required):
            continue
        if (item["provider"] not in allowed
            or item.get("price_type") != "verified_discount"
            or item.get("currency") != "USD"
            or item["id"] in seen or not item["id"].startswith(("hostinger-", "ionos-"))
            or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in item["id"])
            or any(not item[k].startswith("https://") for k in ("source_url","offer_url"))):
            continue
        old, new, saving = (money(item[k]) for k in (
            "regular_monthly_usd", "promo_monthly_usd", "savings_monthly_usd"))
        if old is None or new is None or saving is None or not new < old or old-new != saving:
            continue
        months = item.get("promo_months")
        pct = item.get("discount_percent")
        if type(months) is not int or not 1 <= months <= 48 or type(pct) is not int:
            continue
        calculated = int(((old-new)*Decimal(100)/old).quantize(Decimal("1")))
        if calculated != pct: continue
        seen.add(item["id"])
        verified.append(item)
    return verified

def route_for(item):
    return f'deals/{item["id"]}/'

def short_card(item):
    return (f'<article class="card"><div class="eyebrow">{e(item["provider"])} · Verified discount</div>'
            f'<h2><a href="/{route_for(item)}">{e(item["plan"])}</a></h2>'
            f'<p><del>&#36;{e(item["regular_monthly_usd"])}/mo</del>'
            f' &nbsp; <strong>&#36;{e(item["promo_monthly_usd"])}/mo</strong>'
            f' &nbsp; <strong>Save {e(item["discount_percent"])}%</strong></p>'
            f'<p>{e(item["contract_note"])}</p>'
            f'<p>{e(item["memory"])} · {e(item["disk"])}</p>'
            f'<div class="actions"><a href="/{route_for(item)}">See verified saving and conditions</a></div></article>')

def build_deals(items, page, save, brand):
    routes, grouped = [], defaultdict(list)
    for item in items:
        grouped[item["provider"]].append(item)
        route = route_for(item)
        routes.append(route)
        old, new, saved = (item[k] for k in ("regular_monthly_usd", "promo_monthly_usd", "savings_monthly_usd"))
        title = f'{item["provider"]} {item["plan"]}: save {item["discount_percent"]}% | {brand}'
        description = (f'{item["plan"]} verified official offer: regular USD {old}/mo, '
                       f'promotional USD {new}/mo for {item["promo_months"]} months. '
                       f'Conditions apply; checked {item["verified_at"]}.')
        renewal = (f'<p>Advertised renewal: &#36;{e(item["renewal_monthly_usd"])}/month after the initial term.</p>'
                   if item.get("renewal_monthly_usd") else
                   '<p>Post-promotion rate: confirm in the official checkout before purchase.</p>')
        upfront = (f'<p>Initial payment: &#36;{e(item["upfront_usd"])} prepaid.</p>'
                   if item.get("upfront_usd") else '')
        content = (
            f'<div class="eyebrow">Verified provider discount · checked {e(item["verified_at"])}</div>'
            f'<h1>{e(item["provider"])} {e(item["plan"])} deal</h1>'
            f'<p class="lead">Official regular price <del>&#36;{e(old)}/mo</del> '
            f'→ introductory <strong>&#36;{e(new)}/mo</strong>. '
            f'Actual difference: <strong>&#36;{e(saved)}/mo ({e(item["discount_percent"])}%)</strong>.</p>'
            f'<section class="card"><h2>What you actually save</h2>'
            f'<p>{e(item["contract_note"])}</p>'
            f'<p>Discount applies for {e(item["promo_months"])} months, not indefinitely.</p>'
            f'{upfront}{renewal}'
            f'<p>{e(item["pricing_note"])}</p></section>'
            f'<section class="card"><h2>Server configuration</h2>'
            f'<p>Model: {e(item["plan"])}</p>'
            f'<p>CPU: {e(item["vcpus"])}</p>'
            f'<p>Memory: {e(item["memory"])}</p>'
            f'<p>Storage: {e(item["disk"])}</p>'
            f'<p>Transfer: {e(item.get("transfer","Check provider terms"))}</p>'
            f'<p>Region: {e(item.get("region","Choose in checkout"))}</p></section>'
            f'<section class="card"><h2>How this deal was verified</h2>'
            f'<p>Regular and promotional prices were found together on the same official provider page.</p>'
            f'<p>Verified at (UTC): {e(item["verified_at"])}</p>'
            f'<p>Source: <a href="{e(item["source_url"])}" rel="noopener noreferrer" target="_blank">'
            f'{e(item["source_url"])}</a></p>'
            f'<p><a href="{e(item["offer_url"])}" rel="noopener noreferrer" target="_blank">Check current price with provider ↗</a></p>'
            f'</section>')
        schema = {
            "@context": "https://schema.org", "@type": "Product",
            "name": item["plan"],
            "brand": {"@type": "Brand", "name": item["provider"]},
            "description": description,
            "offers": {
                "@type": "Offer", "price": new,
                "priceCurrency": "USD", "url": item["offer_url"],
                "seller": {"@type": "Organization", "name": item["provider"]},
            },
        }
        content += '<script type="application/ld+json">' + json.dumps(
            schema, ensure_ascii=False).replace("</","<\\/") + "</script>"
        save(route+"index.html", page(title, description, content, route))
    return routes, grouped, "".join(short_card(item) for item in items)