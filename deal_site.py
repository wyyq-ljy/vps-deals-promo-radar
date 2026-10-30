"""Build one static deal page per independently verified price record."""
import html
import json
from collections import defaultdict
from pricing_sources import dollars


def e(value):
    return html.escape(str(value if value is not None else ""), quote=True)


def valid_offers(records, configured):
    providers = {entry["name"] for entry in configured}
    offers, seen = [], set()
    for item in records:
        if not isinstance(item, dict):
            continue
        required = ("id", "provider", "plan", "monthly_usd", "source_url",
                    "offer_url", "verified_at", "pricing_note", "region")
        if any(not isinstance(item.get(k), str) or not item[k] for k in required):
            continue
        if (item["provider"] not in providers or item.get("currency") != "USD"
                or item.get("price_type") != "standard_list_price"
                or not item["source_url"].startswith("https://")
                or not item["offer_url"].startswith("https://")
                or not item["id"].startswith(("hetzner-", "digitalocean-"))
                or item["id"] in seen):
            continue
        if dollars(item["monthly_usd"]) != item["monthly_usd"]:
            continue
        if any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in item["id"]):
            continue
        seen.add(item["id"])
        offers.append(item)
    return offers


def route_for(item):
    return f'deals/{item["id"]}/'


def short_card(item):
    route = route_for(item)
    return (
        f'<article class="card"><div class="eyebrow">{e(item["provider"])} · Standard list price</div>'
        f'<h2><a href="/{e(route)}">{e(item["plan"])}</a></h2>'
        f'<p><strong>&#36;{e(item["monthly_usd"])} USD / month</strong></p>'
        f'<p>{e(item["region"])}</p>'
        f'<div class="actions"><a href="/{e(route)}">Plan details</a>'
        f'<a class="secondary" href="{e(item["source_url"])}" target="_blank" rel="noopener noreferrer">Official price source ↗</a></div>'
        f'</article>'
    )


def build_deals(offers, page, save, site_name):
    by_provider = defaultdict(list)
    routes = []
    for item in offers:
        by_provider[item["provider"]].append(item)
        route = route_for(item)
        routes.append(route)
        title = f'{item["provider"]} {item["plan"]} — USD {item["monthly_usd"]}/mo | {site_name}'
        desc = (f'Official {item["provider"]} published monthly list price for {item["plan"]} '
                f'in {item["region"]}; verified {item["verified_at"]}.')
        body = (
            f'<div class="eyebrow">{e(item["provider"])} · Standard list price, not a discount</div>'
            f'<h1>{e(item["plan"])}</h1>'
            f'<p class="lead"><strong>&#36;{e(item["monthly_usd"])} USD / month</strong></p>'
            f'<section class="card"><h2>Published plan details</h2>'
            f'<p>Provider: {e(item["provider"])}</p>'
            f'<p>Plan / model: {e(item["plan"])}</p>'
            f'<p>Region: {e(item["region"])}</p>'
            f'<p>vCPU: {e(item.get("vcpus", "Not stated"))}</p>'
            f'<p>Memory: {e(item.get("memory", "Not specified in this pricing source"))}</p>'
            f'<p>SSD: {e(item.get("disk", "Not specified in this pricing source"))}</p>'
            f'<p>Included transfer: {e(item.get("transfer", "Not specified in this pricing source"))}</p>'
            f'<p>Price classification: Regular published list price; no promotional discount claimed.</p>'
            f'<p>Last verified (UTC): {e(item["verified_at"])}</p>'
            f'<p>Pricing terms: {e(item["pricing_note"])}</p>'
            f'<p>Official source: <a href="{e(item["source_url"])}" target="_blank" rel="noopener noreferrer">'
            f'{e(item["source_url"])}</a></p>'
            f'<p><a href="{e(item["offer_url"])}" target="_blank" rel="noopener noreferrer">'
            f'Open official plan pricing ↗</a></p></section>'
            f'<p><a href="/providers/{e(item["provider"].lower())}/">More from {e(item["provider"])}</a></p>'
        )
        schema = {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": item["plan"],
            "description": item["pricing_note"],
            "brand": {"@type": "Brand", "name": item["provider"]},
            "offers": {
                "@type": "Offer",
                "price": item["monthly_usd"],
                "priceCurrency": "USD",
                "url": item["offer_url"],
                "seller": {"@type": "Organization", "name": item["provider"]},
            },
        }
        body += '<script type="application/ld+json">' + json.dumps(
            schema, ensure_ascii=False
        ).replace("</", "<\\/") + "</script>"
        save(route + "index.html", page(title, desc, body, route))
    return routes, by_provider, "".join(short_card(item) for item in offers)