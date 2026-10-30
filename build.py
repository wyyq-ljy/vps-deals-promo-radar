# ::ILANG [TYPE:python-module][ROLE:static-site-builder]
# ::RULE{read:config + official data; omit unverifiable Offer schema}
# ::BOUNDARY{never:invent canonical origin or price}
"""Build accessible SEO-oriented static landing/provider pages with stdlib."""
import html
import json
import os
from pathlib import Path
from urllib.parse import urlparse
from config import ROOT, load_config
from deal_site import valid_offers, build_deals, short_card, route_for
from template_engine import render
from seo_helpers import breadcrumbs, itemlist, jsonld, sitemap_xml
from social_card import create_png
from public_copy import public_status
from pricing_pages import build_pricing
from manual_firstparty import with_manual_prices

OUT = ROOT/'site'
def e(value): return html.escape(str(value or ''), quote=True)
def slug(s): return ''.join(c.lower() if c.isalnum() else '-' for c in s).strip('-')

def build():
    site, configured = load_config()
    data = json.loads((ROOT/'data/offers.json').read_text('utf-8'))
    # Fresh owner-transcribed official tables supplement the automated feed.
    # Blocked robots pages are NEVER fetched by this build.
    data = with_manual_prices(data, configured)
    # Production builds start with a clean checkout (site/ is gitignored).
    # Avoid deleting files here: local desktops can forbid bulk file removal.
    OUT.mkdir(exist_ok=True)
    base = site.get('base_url','').rstrip('/')
    parsed_base = urlparse(base)
    host_ok = (parsed_base.scheme == 'https' and bool(parsed_base.netloc)
               and parsed_base.hostname == site.get('domain')
               and not parsed_base.path.strip('/') and not parsed_base.query)
    name = site.get('brand') or 'VPS Deals'
    labels = site.get('niche') or 'VPS hosting'
    providers = {p['name']:p for p in data.get('providers', [])}
    def page(title, desc, body, path=''):
        canonical = f'{base}/{path}' if host_ok else ''
        meta = f'<link rel="canonical" href="{e(canonical)}">' if host_ok else '<meta name="robots" content="noindex,follow">'
        social = ''
        if host_ok:
            meta += f'<meta property="og:url" content="{e(canonical)}">'
            image = base + '/og-card.png'
            social = (f'<meta property="og:image" content="{e(image)}">'
                      f'<meta property="og:image:width" content="1200">'
                      f'<meta property="og:image:height" content="630">'
                      f'<meta name="twitter:card" content="summary_large_image">'
                      f'<meta name="twitter:image" content="{e(image)}">')
        else:
            social = '<meta name="twitter:card" content="summary">'
        return render('base.html', lang=e(site.get('locale') or 'en-US'),
                      title=e(title), description=e(desc), meta=meta,
                      social_meta=social, brand=e(name), body=body)
    def save(path, text):
        file = OUT/path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text, encoding='utf-8')
    create_png(OUT/'og-card.png', name)
    verified = valid_offers(data.get('offers', []), configured)
    affiliate_links = {p['name']:p['affiliate_url'] for p in configured if p.get('affiliate_url')}
    deal_routes, by_provider, deal_markup = build_deals(
        verified, page, save, name, base if host_ok else '', affiliate_links)
    pricing_routes, pricing_redirects, pricing_changes, pricing_cards = build_pricing(data,save,page,base if host_ok else '')
    cards=[]
    item_list=[]
    for index, p in enumerate(configured, 1):
        name_p = p["name"]
        fetched = providers.get(name_p, {})
        route = f"providers/{slug(name_p)}/"
        official = p["source_url"]
        plan_rows = by_provider.get(name_p, [])
        prices = fetched.get("list_prices") or []
        # 3+ independently verified named rows, checked source and USD
        # are mandatory before standard-price content is published.
        valid_prices = [
            x for x in prices if isinstance(x,dict) and
            all(isinstance(x.get(k),str) and x[k] for k in (
                "model","monthly_usd","currency","cpu","memory","storage",
                "price_note","source_url","checked_at"
            )) and x["source_url"] == official and x["currency"] in ("USD", "EUR")
        ]
        if (len(valid_prices) < 3 or len({x["model"] for x in valid_prices}) != len(valid_prices)
                or len({x["currency"] for x in valid_prices}) != 1):
            valid_prices = []
        if not plan_rows and not valid_prices:
            # No factual, index-worthy comparison exists. Do not generate a
            # thin provider page or include it in navigation/sitemap.
            continue
        if valid_prices and not plan_rows:
            cards.append(pricing_cards[name_p])
            continue
        item_list.append(route)
        public = e(public_status(fetched.get("status")))
        service = {
            "@context":"https://schema.org","@type":"Service",
            "name": f"{name_p} VPS hosting",
            "provider":{"@type":"Organization","name":name_p,"url":p["website"]},
        }
        if plan_rows:
            card = (
                f'<article class="card"><div class="eyebrow">Verified discount source</div>'
                f'<h2>{e(name_p)}</h2><p>{len(plan_rows)} verified current VPS discounts, '
                'with first-term and renewal terms where published.</p>'
                f'<div class="actions"><a href="/{route}">View verified offers</a></div></article>'
            )
            service["offers"] = [
                {"@type":"Offer","price":x["promo_monthly_usd"],
                 "priceCurrency":x["currency"],"url":x["offer_url"]}
                for x in plan_rows
            ]
            structured = jsonld(service)
            if host_ok:structured += breadcrumbs(base,[("Home",""),(name_p,route)])
            body = render(
                "provider.html",provider_name=e(name_p),
                count=str(len(plan_rows)),status_message=public,
                source_url=e(official),
                deal_cards="".join(short_card(item) for item in plan_rows),
                structured_data=structured,
            )
            page_title = f"{name_p} verified VPS discounts | {name}"
            description = f"Verify official discounts for {name_p} VPS plans, with actual price differences and billing conditions."
        else:
            card = (
                f'<article class="card"><div class="eyebrow">Official standard pricing</div>'
                f'<h2>{e(name_p)}</h2><p>{len(valid_prices)} specific USD '
                'configurations verified from the provider. These are not discounts.</p>'
                f'<div class="actions"><a href="/{route}">Compare standard rates</a></div></article>'
            )
            lines = "".join(
                "<tr>" + "".join(
                    f'<td style="border-bottom:1px solid #ddd;padding:12px 10px">{e(v)}</td>'
                    for v in (
                        x["model"], "$"+x["monthly_usd"]+"/mo",
                        x["cpu"], x["memory"], x["storage"]
                    )
                ) + "</tr>" for x in valid_prices
            )
            notes = "".join(
                f'<p><strong>{e(x["model"])}:</strong> {e(x["price_note"])} '
                f'Transfer: {e(x.get("transfer","See provider terms"))}.</p>'
                for x in valid_prices
            )
            structured = jsonld(service)
            if host_ok:structured += breadcrumbs(base,[("Home",""),(name_p,route)])
            body = render(
                "provider_standard.html",provider_name=e(name_p),
                public_status=public,
                plan_count=str(len(valid_prices)),
                price_rows=lines,
                price_notes=notes,
                checked_at=e(valid_prices[0]["checked_at"]),
                source_url=e(official),
                structured_data=structured,
            )
            page_title = f"{name_p} standard VPS prices and configurations | {name}"
            description = f"Compare {len(valid_prices)} verified USD standard VPS configurations on the official {name_p} price list. No coupon claims."
        cards.append(card)
        save(route+"index.html", page(page_title,description,body,route))
    cards_markup=''.join(cards)
    item_schema = itemlist(base if host_ok else '', item_list)
    intro=f'<div class="eyebrow">Independent • verified VPS savings • direct official sources</div><h1>Find actual VPS discounts.<br><em>Check the real price difference.</em></h1><p class="lead">We only publish an offer when a provider displays both its regular and lower promotional price for the same VPS plan. Review the first-term commitment, renewal costs, and linked evidence before ordering.</p>'
    grid=f'<section class="grid">{cards_markup}</section>'
    empty = '<p class="lead">No verified discounts currently. We will publish deals only when official regular and promotional prices differ.</p>'
    deal_section = deal_markup if verified else empty
    home_body = render('index.html', intro=intro, deal_count=str(len(verified)),
                       deal_section=deal_section, provider_grid=grid,
                       structured_data=item_schema)
    save('index.html',page(f'{name} — Verified VPS Discounts & Hosting Offers',
                           'Compare independently verified VPS discounts and their official price evidence.',
                           home_body))
    compare_items = [route_for(offer) for offer in verified] if verified else item_list
    compare_schema = itemlist(base if host_ok else '', compare_items)
    if host_ok:
        compare_schema += breadcrumbs(base, [('Home',''), ('Compare','compare/')])
    compare = render('compare.html', deal_section=deal_section,
                     provider_cards=cards_markup, structured_data=compare_schema)
    save('compare/index.html',page(f'Compare VPS Providers | {name}',
         'Side-by-side links to official hosting pricing and billing conditions.',
         compare, 'compare/'))
    save('style.css',"""*{box-sizing:border-box}body{margin:0;background:#f6f8fb;color:#18243a;font:16px/1.65 ui-sans-serif,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}a{color:#215bc4;text-decoration:none}a:hover{text-decoration:underline}.wrap{max-width:1080px;margin:auto;padding:24px}header{display:flex;align-items:center;justify-content:space-between;gap:20px;border-bottom:1px solid #e0e6ed}.logo{font-weight:800;color:#14223d;font-size:20px}.logo span{font-size:12px;color:#748094;font-weight:500}nav{display:flex;gap:24px}nav a{color:#46536a;font-size:14px}main{padding-top:76px;padding-bottom:70px}.eyebrow{text-transform:uppercase;letter-spacing:.16em;font-weight:700;font-size:11px;color:#2873b8}h1{font-size:clamp(38px,6vw,66px);letter-spacing:-.045em;line-height:1.08;max-width:850px;margin:16px 0 24px}h1 em{font-style:normal;color:#397bd6}.lead{font-size:18px;max-width:760px;color:#5d6a7e}.section-title{margin-top:65px;font-size:25px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;margin-top:30px}.card{background:white;border:1px solid #e3e8ef;border-radius:18px;padding:28px;box-shadow:0 6px 28px #19396008}.card h2{font-size:24px;margin:9px 0}.card p{color:#677386}.actions{display:flex;gap:20px;flex-wrap:wrap;margin-top:24px;font-weight:650;font-size:14px}.secondary{color:#5d697a}footer{border-top:1px solid #dfe5ec;color:#6f7989;font-size:13px;padding-top:26px;padding-bottom:36px}@media(max-width:620px){.wrap{padding:18px}header .logo span{display:none}main{padding-top:52px}.grid{grid-template-columns:1fr}.card{padding:22px}}""")
    # Permanently retire the old 20 ordinary-price URLs; they were never deals.
    retired = json.loads((ROOT/'data/retired_deals.json').read_text(encoding='utf-8'))['retired_list_price_pages']
    redirect_lines = []
    for entry in retired:
        identifier = entry['id']
        provider = entry['provider']
        if identifier != slug(identifier) or provider not in ('DigitalOcean', 'Hetzner'):
            raise ValueError('Invalid retired deal redirect')
        destination = f'/{slug(provider)}-pricing/' if provider in pricing_cards else (f'/providers/{slug(provider)}/' if f'providers/{slug(provider)}/' in item_list else '/compare/')
        redirect_lines.append(f'/deals/{identifier}/ {destination} 301')
    # Do not allow formerly published but now unsupported provider shells to
    # remain live merely because a Pages build reused its generated output.
    supported = set(item_list)
    absent = [
        f'providers/{slug(p["name"])}/' for p in configured
        if f'providers/{slug(p["name"])}/' not in supported and p['name'] not in pricing_cards
    ]
    redirect_lines.extend(f'/{route} /compare/ 301' for route in absent)    # Previously published promotions may later fail official verification.
    # Withdraw their old URLs without blocking a legitimately re-verified deal.
    withdrawn = json.loads((ROOT/'data/retired_deals.json').read_text('utf-8')).get('withdrawn_deal_ids', [])
    current_ids = {offer['id'] for offer in verified}
    for identifier in withdrawn:
        if slug(identifier) != identifier:
            raise ValueError('Invalid withdrawn deal slug')
        if identifier not in current_ids:
            redirect_lines.append(f'/deals/{identifier}/ /compare/ 301')

    # A vendor with verified discounts has a real provider page in the sitemap.
    # Do not redirect that provider route to its (separate) pricing table.
    active_provider_urls = {'/' + route for route in item_list}
    redirect_lines.extend(
        line for line in pricing_redirects
        if line.split(' ', 1)[0] not in active_provider_urls
    )
    save('_redirects', '# Retired ordinary-price deals and unsupported provider shells\n'
         + '\n'.join(redirect_lines) + '\n')
    # Cloudflare and GitHub jobs only: generated HTML files can safely be
    # pruned from site/. Do not remove directories or any user-authored files.
    if os.environ.get('CF_PAGES') == '1' or os.environ.get('GITHUB_ACTIONS') == 'true':
        active = set(item_list + deal_routes + pricing_routes)
        for group in ('providers', 'deals'):
            for generated in (OUT/group).glob('*/index.html'):
                relative = generated.relative_to(OUT).as_posix()
                if relative.removesuffix('index.html') not in active:
                    generated.unlink()
    # Retire previously generated keyword URLs if their official price source
    # no longer verifies; never serve stale standalone configuration pages.
    if os.environ.get('CF_PAGES') == '1' or os.environ.get('GITHUB_ACTIONS') == 'true':
        active_keyword = set(pricing_routes)
        for generated in OUT.glob('*/index.html'):
            name_dir = generated.parent.name
            if (name_dir.endswith('-pricing') or name_dir.endswith('-cost')) and (
                generated.relative_to(OUT).as_posix().removesuffix('index.html')
                not in active_keyword
            ):
                generated.unlink()
    save('404.html', '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="robots" content="noindex"></head><body><h1>404 – Page not found</h1><p>This offer may have expired or been withdrawn.</p><a href="/">See verified VPS deals</a></body></html>')
    save('robots.txt', ('User-agent: *\nAllow: /\nSitemap: '+base+'/sitemap.xml\n') if host_ok else 'User-agent: *\nDisallow: /\n')
    routes=['','compare/']+item_list+pricing_routes+deal_routes
    # Source checks do not imply substantial page changes: lastmod tracks
    # initial detection or a changed price/term, not a rebuild/cron timestamp.
    changes = dict(pricing_changes)
    for offer in verified:
        stamp = offer.get('last_changed_at') or offer.get('verified_at')
        changes['/' + route_for(offer)] = stamp
    sitemap = sitemap_xml(base if host_ok else '', ['/'+r for r in routes], changes)
    save('sitemap.xml',sitemap)
    print('Built:',len(routes),'pages; canonical configured:',host_ok)

if __name__=='__main__': build()