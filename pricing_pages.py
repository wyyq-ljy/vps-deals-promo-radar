# ::ILANG [TYPE:python-module][ROLE:standard-pricing-keyword-pages]
# ::RULE{vendor-pricing, named-model-cost, and pairwise comparisons use official USD data}
# ::BOUNDARY{never:invent prices, models, search volume, or promo claims}
"""Generate intent-specific pricing pages from currently verified rows."""
import html
import re
from collections import defaultdict
from decimal import Decimal

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
}
def esc(x):return html.escape(str(x or ""),quote=True)
def slug(x):return re.sub("-+","-",re.sub("[^a-z0-9]+","-",x.lower())).strip("-")
def price(x):return "$"+esc(x["monthly_usd"])+" USD / month"
def model_route(name,x):return slug(name)+"-"+slug(x["model"])+"-cost/"
def row_table(name,items,links=True):
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
def build_pricing(data,save,page):
 ready={p["name"]:rows_of(p) for p in data.get("providers",[])}
 ready={k:v for k,v in ready.items() if v}
 routes=[];redirects=[];changes={};cards={}
 def write(route,title,description,body,rows):
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
     text+=f'<p><a href="/{route}/">{esc(title)}</a>: {esc(purpose)}; {len(group)} listed configurations.</p>'
   text+='</section>'
  text+=(f'<section class="card"><h2>How billing works</h2><p>{esc(NOTES[name])}</p>'
         f'{evidence(items[0])}</section>')
  write(main,f'{name} Pricing {items[0]["checked_at"][:7]} — Official USD Monthly Costs',
        f'Official {name} pricing, RAM, CPU, storage and USD monthly costs across {len(items)} configurations.',text,items)
  for r in items:
   family=r.get("family") or "Other"
   others=sorted((x for x in groups[family] if x["model"]!=r["model"]),key=lambda x:abs(Decimal(x["monthly_usd"])-Decimal(r["monthly_usd"])))[:3]
   context=FAMILIES[family][2] if name=="DigitalOcean" and family in FAMILIES else 'Check your workload requirements against the stated CPU, RAM and storage before ordering.'
   details=(f'<div class="eyebrow">Specific configuration cost</div><h1>{esc(name)} {esc(r["model"])} Cost</h1>'
      f'<p class="lead">Published monthly amount: {price(r)}. This figure applies to this named configuration, not to every model offered by the vendor.</p>'
      '<section class="card"><h2>Exact configuration and rate</h2>'
      f'<p>Model: <strong>{esc(r["model"])}</strong></p><p>Monthly USD: <strong>{price(r)}</strong></p>'
      f'<p>CPU: {esc(r["cpu"])}</p><p>RAM: {esc(r["memory"])}</p><p>SSD: {esc(r["storage"])}</p>'
      f'<p>Transfer: {esc(r.get("transfer") or "See source")}</p></section>'
      f'<section class="card"><h2>Typical fit and billing considerations</h2><p>{esc(context)}. {esc(NOTES[name])}</p>')
   memory=re.search(r'(\d+(?:\.\d+)?)\s*(MiB|MB|GiB|GB)',r["memory"],re.I)
   cpu=re.search(r'(\d+)\s*(?:vCPU|vCore|Core)',r["cpu"],re.I)
   cost=Decimal(r["monthly_usd"])
   if memory:
    m=Decimal(memory.group(1)) / (1024 if memory.group(2).lower() in ("mib","mb") else 1)
    if m>0:details+=f'<p>Monthly USD divided by stated RAM: {cost/m:.2f} USD per GiB (a simple ratio, not a performance benchmark).</p>'
   if cpu and int(cpu.group(1))>0:
    details+=f'<p>Monthly USD divided by stated CPUs: {cost/Decimal(cpu.group(1)):.2f} USD per CPU (not a CPU-speed ranking).</p>'
   details+='</section>'
   if others:details+='<section class="card"><h2>Other nearby sizes in this product family</h2>'+row_table(name,others)+'</section>'
   details+='<section class="card"><h2>Official rate verification</h2>'+evidence(r)+'</section>'
   details+=f'<p><a href="/{main}">Back to {esc(name)} pricing</a></p>'
   route=model_route(name,r)
   write(route,f'{name} {r["model"]} Cost — {r["monthly_usd"]} USD/mo',
         f'{name} {r["model"]}: {r["monthly_usd"]} USD monthly, {r["cpu"]}, {r["memory"]} and {r["storage"]}, official source and verification time.',details,[r])
  if name=="DigitalOcean":
   for fam,(title,path,purpose) in FAMILIES.items():
    group=groups.get(fam,[])
    if len(group)<3:continue
    detail=(f'<div class="eyebrow">Specific Droplet family pricing</div><h1>{esc(title)}</h1>'
            f'<p class="lead">{esc(purpose)}. Each named configuration below has its own published USD amount.</p>'
            '<section class="card"><h2>Standard configurations</h2>'+row_table(name,group)+'</section>'
            '<section class="card"><h2>Selection criteria and source</h2>'
            '<p>Compare the actual CPU entitlement, RAM, SSD and transfer figures. '
            f'{esc(NOTES[name])}</p>'+evidence(group[0])+'</section>'
            '<p><a href="/digitalocean-pricing/">All DigitalOcean price families</a></p>')
    write(path+"/",f'{title} {group[0]["checked_at"][:7]} — USD Table',
          f'{title} with {len(group)} official USD monthly configurations and full CPU, memory and SSD comparisons.',detail,group)
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
 return routes,redirects,changes,cards