# ::ILANG [TYPE:python-module][ROLE:static-site-builder]
# ::RULE{read:config + official data; omit unverifiable Offer schema}
# ::BOUNDARY{never:invent canonical origin or price}
"""Build accessible SEO-oriented static landing/provider pages with stdlib."""
import html
import json
from pathlib import Path
from urllib.parse import urlparse
from config import ROOT, load_config
from deal_site import valid_offers, build_deals, short_card

OUT = ROOT/'site'
def e(value): return html.escape(str(value or ''), quote=True)
def slug(s): return ''.join(c.lower() if c.isalnum() else '-' for c in s).strip('-')

def build():
    site, configured = load_config()
    data = json.loads((ROOT/'data/offers.json').read_text('utf-8'))
    OUT.mkdir(exist_ok=True)
    base = site.get('base_url','').rstrip('/')
    host_ok = base.startswith('https://') and bool(urlparse(base).netloc) and base != 'https://example.com'
    name = site.get('brand') or 'VPS Deals'
    labels = site.get('niche') or 'VPS hosting'
    providers = {p['name']:p for p in data.get('providers', [])}
    def page(title, desc, body, path=''):
        canonical = f'{base}/{path}' if host_ok else ''
        meta = f'<link rel="canonical" href="{e(canonical)}">' if host_ok else '<meta name="robots" content="noindex,follow">'
        meta += f'<meta property="og:url" content="{e(canonical)}">' if host_ok else ''
        return f'''<!doctype html><html lang="en-US"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title)}</title><meta name="description" content="{e(desc)}">{meta}<meta property="og:type" content="website"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta name="twitter:card" content="summary_large_image"><link rel="stylesheet" href="/style.css"></head><body><header class="wrap"><a class="logo" href="/">{e(name)}<span> / Verified VPS deals</span></a><nav><a href="/">Providers</a><a href="/compare/">Compare</a></nav></header><main class="wrap">{body}</main><footer class="wrap"><p>Independent informational directory. Links may become affiliate links if explicitly approved; any such link will be disclosed. Always confirm final pricing, taxes and renewal terms with the provider.</p><p>A deal requires the same official page to show both a regular price and a lower promotional price. Verify final checkout totals and renewal terms.</p></footer></body></html>'''
    def save(path, text):
        file = OUT/path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text, encoding='utf-8')
    verified = valid_offers(data.get('offers', []), configured)
    deal_routes, by_provider, deal_markup = build_deals(verified, page, save, name)
    cards=[]
    item_list=[]
    for index, p in enumerate(configured,1):
        name_p = p['name']
        fetched = providers.get(name_p, {})
        route = f'providers/{slug(name_p)}/'
        official = p['source_url']
        plan_rows = by_provider.get(name_p, [])
        count = len(plan_rows)
        card = (f'<article class="card"><div class="eyebrow">Provider {index:02d}</div>'
                f'<h2>{e(name_p)}</h2><p>{count} independently verified live discount offers. '
                f'{"No verified discount currently." if count == 0 else "See the current old-versus-new price comparisons."}</p>'
                f'<div class="actions"><a href="/{route}">Details</a>'
                f'<a class="secondary" href="{e(official)}" rel="noopener noreferrer" target="_blank">Official source ↗</a></div></article>')
        cards.append(card)
        item_list.append({'@type':'ListItem','position':index,'url':f'{base}/{route}' if host_ok else '/'+route})
        body=(f'<div class="eyebrow">Provider overview</div><h1>{e(name_p)} VPS deals</h1>'
              f'<p class="lead">{count} current verified discount offers. '
              f'{"No verified discount currently. Check back after our next source scan." if count == 0 else "Every offer has evidence of a lower price against the same-page regular price."}</p>'
              f'<section class="card"><h2>Official source</h2><p>Source status: {e(fetched.get("status","not checked"))}</p>'
              f'<p><a href="{e(official)}" target="_blank" rel="noopener noreferrer">Open provider price source ↗</a></p></section>'
              f'<section class="grid">{"".join(short_card(item) for item in plan_rows)}</section>'
              f'<p><a href="/compare/">Compare other providers</a></p>')
        save(route+'index.html',page(f'{name_p} VPS Pricing — Official Sources | {name}',f'Official {name_p} VPS pricing source and verification status. No unverified deals or estimates.',body,route))
    cards_markup=''.join(cards)
    item_schema=json.dumps({'@context':'https://schema.org','@type':'ItemList','itemListElement':item_list},ensure_ascii=False).replace('</','<\\/')
    intro=f'<div class="eyebrow">Independent • verified VPS savings • direct official sources</div><h1>Find actual VPS discounts.<br><em>Check the real price difference.</em></h1><p class="lead">We only publish an offer when a provider displays both its regular and lower promotional price for the same VPS plan. Review the first-term commitment, renewal costs, and linked evidence before ordering.</p>'
    grid=f'<section class="grid">{cards_markup}</section>'
    empty = '<p class="lead">No verified discounts currently. We will publish deals only when official regular and promotional prices differ.</p>'
    deal_section = deal_markup if verified else empty
    save('index.html',page(f'{name} — Verified VPS Discounts & Hosting Offers',f'Compare independently verified VPS discounts and their official price evidence.',intro+f'<h2 class="section-title">Verified discounts ({len(verified)})</h2><section class="grid">{deal_section}</section>'+'<h2 class="section-title">Monitored VPS providers</h2>'+grid+f'<script type="application/ld+json">{item_schema}</script>'))
    compare='<div class="eyebrow">Official discounts only</div><h1>Compare real VPS savings</h1><p class="lead">We calculate savings only when the same official source shows both regular and promotional prices. Verify term lengths and renewal pricing.</p><section class="grid">'+deal_section+'</section><h2 class="section-title">Monitored providers</h2><div class="grid">'+cards_markup+'</div>'
    save('compare/index.html',page(f'Compare VPS Providers | {name}','Side-by-side links to official hosting pricing and billing conditions.',compare+'<script type="application/ld+json">'+item_schema+'</script>','compare/'))
    save('style.css',"""*{box-sizing:border-box}body{margin:0;background:#f6f8fb;color:#18243a;font:16px/1.65 ui-sans-serif,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}a{color:#215bc4;text-decoration:none}a:hover{text-decoration:underline}.wrap{max-width:1080px;margin:auto;padding:24px}header{display:flex;align-items:center;justify-content:space-between;gap:20px;border-bottom:1px solid #e0e6ed}.logo{font-weight:800;color:#14223d;font-size:20px}.logo span{font-size:12px;color:#748094;font-weight:500}nav{display:flex;gap:24px}nav a{color:#46536a;font-size:14px}main{padding-top:76px;padding-bottom:70px}.eyebrow{text-transform:uppercase;letter-spacing:.16em;font-weight:700;font-size:11px;color:#2873b8}h1{font-size:clamp(38px,6vw,66px);letter-spacing:-.045em;line-height:1.08;max-width:850px;margin:16px 0 24px}h1 em{font-style:normal;color:#397bd6}.lead{font-size:18px;max-width:760px;color:#5d6a7e}.section-title{margin-top:65px;font-size:25px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;margin-top:30px}.card{background:white;border:1px solid #e3e8ef;border-radius:18px;padding:28px;box-shadow:0 6px 28px #19396008}.card h2{font-size:24px;margin:9px 0}.card p{color:#677386}.actions{display:flex;gap:20px;flex-wrap:wrap;margin-top:24px;font-weight:650;font-size:14px}.secondary{color:#5d697a}footer{border-top:1px solid #dfe5ec;color:#6f7989;font-size:13px;padding-top:26px;padding-bottom:36px}@media(max-width:620px){.wrap{padding:18px}header .logo span{display:none}main{padding-top:52px}.grid{grid-template-columns:1fr}.card{padding:22px}}""")
    save('robots.txt', ('User-agent: *\nAllow: /\nSitemap: '+base+'/sitemap.xml\n') if host_ok else 'User-agent: *\nDisallow: /\n')
    from datetime import date
    # A build date is not a source verification date; no fabricated lastmod.
    routes=['','compare/']+[f'providers/{slug(p["name"])}/' for p in configured]+deal_routes
    sitemap='<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'<url><loc>{e(base+"/"+route)}</loc></url>\n' for route in routes)+'</urlset>' if host_ok else '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>'
    save('sitemap.xml',sitemap)
    print('Built:',len(routes),'pages; canonical configured:',host_ok)

if __name__=='__main__': build()