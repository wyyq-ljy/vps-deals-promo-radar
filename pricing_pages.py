# ::ILANG [TYPE:python-module][ROLE:standard-pricing-keyword-pages]
# ::RULE{vendor-pricing, named-model-cost, and pairwise comparisons use official USD data}
# ::BOUNDARY{never:invent prices, models, search volume, or promo claims}
"""Generate intent-specific pricing pages from currently verified rows."""
import html
import re
from collections import defaultdict
from decimal import Decimal
from seo_helpers import breadcrumbs

FAMILIES = {
 "Basic":("DigitalOcean Droplet Pricing","digitalocean-droplet-pricing","Shared CPU for bursty apps, websites, and development"),
 "CPU-Optimized":("DigitalOcean CPU-Optimized Pricing","digitalocean-cpu-optimized-pricing","Dedicated CPU capacity for sustained compute workloads"),
 "General Purpose":("DigitalOcean General Purpose Pricing","digitalocean-general-purpose-pricing","Dedicated CPU and balanced memory for production services"),
 "Memory-Optimized":("DigitalOcean Memory-Optimized Pricing","digitalocean-memory-optimized-pricing","Additional RAM for databases, caches, and memory-heavy services"),
 "Storage-Optimized":("DigitalOcean Storage-Optimized Pricing","digitalocean-storage-optimized-pricing","Larger local NVMe SSD capacity for disk-heavy workloads"),
}
NOTES = {
 "DigitalOcean":"The vendor publishes an hourly usage price and monthly cap. Actual usage charges may differ.",
 "OVHcloud":"The vendor publishes a starting USD monthly price, not a fixed configuration checkout total; location and selections can change it.",
 "BuyVM":"The vendor publishes a named KVM slice monthly rate; stock and any optional extras must be checked separately.",
 "Cloudways":"Published managed DigitalOcean Standard server rates include Cloudways management; taxes and optional backup fees are separate.",
 "Hetzner":"USD monthly cap for US Hillsboro HIL1 location, before VAT and optional IPv4, cross-checked with current first-party pricing JSON. Some configurations may be temporarily unavailable.",
 "Hostinger":"USD introductory rate for prepaid 24-month KVM plans. Renewal costs are higher.",
 "DreamHost":"First-three-month USD promotional prices for VPS Stack plans; regular renewal pricing differs.",
 "IONOS":"First-three-month USD VPS+ introductory rate requires a 12-month contract; remaining months cost more.",
 "Kamatera":"Published recommended configurations; customize server and add-ons at checkout for a different total.",
 "Hostwinds":"Unmanaged Linux VPS standard USD monthly rates; confirm term, taxes and software extras.",
 "HostArmada":"Promotional USD per-month equivalent on the selected 12-month term; renewal pricing can change.",
 "UpCloud":"Global USD Starter and Premium server rates, hourly metering with monthly cap, zero-cost egress subject to fair use.",
}
def esc(x):return html.escape(str(x or ""),quote=True)
def slug(x):return re.sub("-+","-",re.sub("[^a-z0-9]+","-",x.lower())).strip("-")
def price(x):return "$"+esc(x["monthly_usd"])+" USD / month"
def model_route(name,x):return slug(name)+"-"+slug(x["model"])+"-cost/"
def row_table(name,items,links=False):
 head='<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;text-align:left"><thead><tr><th>Model</th><th>Monthly USD</th><th>CPU</th><th>RAM</th><th>SSD</th><th>Transfer</th></tr></thead><tbody>'
 body=''
 for x in items:
  m=esc(x["model"])
  if links:m=f'<a href="/{model_route(name,x)}">{m}</a>'
  vals=[m,price(x),esc(x["cpu"]),esc(x["memory"]),esc(x["storage"]),esc(x.get("transfer") or "See source")]
  body+='<tr>'+''.join(f'<td style="padding:10px;border-bottom:1px solid #e2e5e9">{v}</td>' for v in vals)+'</tr>'
 return head+body+'</tbody></table></div>'
def evidence(x):
 return (f'<p><strong>Source:</strong> <a href="{esc(x["source_url"])}" rel="noopener noreferrer" target="_blank">{esc(x["source_url"])}</a></p>'
         f'<p><strong>Verified UTC:</strong> {esc(x["checked_at"])}</p>'
         f'<p><strong>Billing:</strong> {esc(x["price_note"])}</p>')
def rows_of(provider):
 rows=provider.get("list_prices") or []
 if len(rows)<3:return []
 seen=set()
 for x in rows:
  if not isinstance(x,dict) or any(not x.get(k) for k in ("model","monthly_usd","currency","cpu","memory","storage","checked_at","source_url","price_note")):return []
  if x["currency"]!="USD" or x["source_url"]!=provider.get("source_url") or x["model"] in seen:return []
  try:
   if not 0<Decimal(x["monthly_usd"])<100000:return []
  except Exception:return []
  seen.add(x["model"])
 return sorted(rows,key=lambda r:Decimal(r["monthly_usd"]))
def build_pricing(data,save,page,base=''):
 ready={p["name"]:rows_of(p) for p in data.get("providers",[])}
 ready={k:v for k,v in ready.items() if v}
 routes=[];redirects=[];changes={};cards={}
 def write(route,title,description,body,rows):
  if base:
   body+=breadcrumbs(base, [('Home',''),('Pricing',route)])
  routes.append(route);save(route+"index.html",page(title,description,body,route))
  dates=[r.get("last_changed_at") or r.get("checked_at") for r in rows]
  if dates:changes["/"+route]=max(dates)
 for name,items in ready.items():
  main=slug(name)+"-pricing/"
  redirects.append(f'/providers/{slug(name)}/ /{main} 301')
  cards[name]=(f'<article class="card"><div class="eyebrow">Official USD monthly pricing</div>'
               f'<h2>{esc(name)}</h2><p>{len(items)} individually named and priced configurations.</p>'
               f'<div class="actions"><a href="/{main}">Compare published costs</a></div></article>')
  groups=defaultdict(list)
  for r in items:groups[r.get("family") or "Other"].append(r)
  text=(f'<div class="eyebrow">Provider pricing</div><h1>{esc(name)} Pricing</h1>'
        f'<p class="lead">{len(items)} official USD monthly prices, with CPU, RAM, SSD and transfer values taken from the named plan rows.</p>'
        '<section class="card"><h2>All available published configurations</h2>'
        +row_table(name,items)+'</section>')
  if name=="DigitalOcean":
   text+='<section class="card"><h2>Choose a Droplet family</h2>'
   for fam,group in groups.items():
    if fam in FAMILIES:
     title,route,purpose=FAMILIES[fam]
     if fam=="Basic":
      text+=f'<p><a href="/{route}/">{esc(title)}</a>: {esc(purpose)}; {len(group)} listed configurations.</p>'
     else:
      text+=f'<p><strong>{esc(title)}:</strong> {esc(purpose)}; {len(group)} configurations in the table above.</p>'
   text+='</section>'
  pairs=(("DigitalOcean","OVHcloud"),("DigitalOcean","BuyVM"),("OVHcloud","BuyVM"))
  comparison_links=[(left,right) for left,right in pairs if name in (left,right) and left in ready and right in ready]
  if comparison_links:
   text+='<section class="card"><h2>Compare published prices across providers</h2>'
   for left,right in comparison_links:
    path=f'{slug(left)}-vs-{slug(right)}-pricing/'
    text+=f'<p><a href="/{path}">{esc(left)} vs {esc(right)} pricing</a>: CPU, RAM, SSD and USD monthly rate comparison.</p>'
   text+='</section>'
  legacy=name in ("DigitalOcean","Hetzner","Cloudways","OVHcloud","BuyVM")
  if legacy:
   # Preserve the existing mature-page title and content format.
   text+=(f'<section class="card"><h2>How billing works</h2><p>{esc(NOTES[name])}</p>'
          f'{evidence(items[0])}</section>')
   title=f'{name} Pricing {items[0]["checked_at"][:7]} — Official USD Monthly Costs'
  else:
   terms=list(dict.fromkeys(r['price_note'] for r in items))
   details=''.join(f'<p>{esc(term)}</p>' for term in terms[:8])
   text+=(f'<section class="card"><h2>How billing works</h2><p>{esc(NOTES[name])}</p>'
          +details+f'{evidence(items[0])}</section>')
   title=f'{name} Pricing 2026 — Official USD Monthly Costs'
  write(main,title,
        f'Official {name} pricing, RAM, CPU, storage and USD monthly costs across {len(items)} configurations.',text,items)
  # No individual configuration has a supplied >=100 US monthly search
  # volume. Consolidate every former /...-cost/ URL into its evidence-backed
  # vendor pricing overview (or verified Droplet pricing family).
  for rec in items:
   old=model_route(name,rec)
   target=main
   if name=="DigitalOcean" and rec.get("family")=="Basic":
    target="digitalocean-droplet-pricing/"
   redirects.append(f"/{old} /{target} 301")
  if name=="DigitalOcean":
   # This is the only subfamily with explicit >=100 search volume in the
   # owner-supplied list: "digitalocean droplet pricing" = 590 US monthly.
   family="Basic"
   selection=groups.get(family,[])
   if len(selection)>=3:
    title,path,purpose=FAMILIES[family]
    detail=(f'<div class="eyebrow">DigitalOcean shared CPU Droplets</div><h1>{esc(title)}</h1>'
            f'<p class="lead">{esc(purpose)}. These are regular USD rates for separately '
            'identified configurations, not discounts or interchangeable performance tiers.</p>'
            '<section class="card"><h2>Basic Droplet standard configurations</h2>'
            +row_table(name,selection,links=False)+'</section>'
            f'<section class="card"><h2>Resource tradeoffs and published billing</h2>'
            f'<p>{esc(NOTES[name])}. Compare RAM, CPUs, SSD and included transfer by row.</p>'
            +evidence(selection[0])+'</section>'
            '<p><a href="/digitalocean-pricing/">View all DigitalOcean pricing classes</a></p>')
    write(path+"/",f'{title} — Official USD Monthly Rates',
          f'Official DigitalOcean Basic Droplet USD monthly prices, CPU, RAM, SSD and source for {len(selection)} named sizes.',detail,selection)
   for other,(title,path,purpose) in FAMILIES.items():
    if other != "Basic":
     redirects.append(f"/{path}/ /digitalocean-pricing/ 301")
 for left,right in (("DigitalOcean","OVHcloud"),("DigitalOcean","BuyVM"),("OVHcloud","BuyVM")):
  if left not in ready or right not in ready:continue
  a,b=ready[left][:4],ready[right][:4]
  route=f'{slug(left)}-vs-{slug(right)}-pricing/'
  detail=(f'<div class="eyebrow">Two-provider monthly price comparison</div><h1>{esc(left)} vs {esc(right)} Pricing</h1>'
          '<p class="lead">Compare published USD rates and named hardware configurations. '
          'The entries below are not identical systems: CPU sharing, SSD type and billing can differ.</p>'
          f'<section class="card"><h2>{esc(left)}: lower-price configurations</h2>'+row_table(left,a)+'</section>'
          f'<section class="card"><h2>{esc(right)}: lower-price configurations</h2>'+row_table(right,b)+'</section>'
          '<section class="card"><h2>Important differences and official evidence</h2>'
          f'<p>{esc(left)}: {esc(NOTES[left])}</p><p>{esc(right)}: {esc(NOTES[right])}</p>'
          '<p>Do not infer equal performance from equal prices. Check region, resources, network transfer and checkout charges.</p>'
          +evidence(a[0])+evidence(b[0])+'</section>')
  write(route,f'{left} vs {right} Pricing — USD Cost Comparison',
        f'{left} vs {right} official monthly prices and individual CPU, RAM, SSD configurations with source and UTC verification.',detail,a+b)
 physical=data.get('dedicated_prices') or []
 physical=rows_of({'source_url':'https://www.inmotionhosting.com/dedicated-servers',
                   'list_prices':physical})
 if physical:
  path='dedicated-server-hosting-price/'
  intro=('<div class="eyebrow">Physical dedicated servers: verified USD prices</div>'
         '<h1>Dedicated Server Hosting Price 2026</h1>'
         '<p class="lead">Compare five published InMotion Hosting single-tenant dedicated server configurations, '
         'not VPS instances. Each rate is tied to a 12-month billing term; hardware and renewal prices vary. '
         'Only one physical-server provider has a complete verified table here, so this is not a market-wide lowest-price ranking.</p>')
  detail=(intro+'<section class="card"><h2>Dedicated physical server configurations</h2>'
          +row_table('InMotion Hosting',physical)+'</section>'
          '<section class="card"><h2>Contract, network and renewal conditions</h2>'
          +''.join(f'<p><strong>{esc(x["model"])}:</strong> {esc(x["price_note"])} '
                   f'Transfer: {esc(x["transfer"])}.</p>' for x in physical)
          +evidence(physical[0])+'</section>'
          '<p><a href="/compare/">Compare VPS pricing and provider categories</a></p>')
  write(path,'Dedicated Server Hosting Price 2026 — Official USD Monthly Plans',
        'Compare five confirmed physical dedicated servers with RAM, CPU, disk, bandwidth and official USD 12-month rates.',detail,physical)
 return routes,redirects,changes,cards