# ::ILANG [TYPE:python-module][ROLE:volume-aligned-pricing-regression]
# ::RULE{only documented >=100 volume subfamily; brand main pages; no per-model cost}
# ::BOUNDARY{never:invent search volumes or normal-price coupons}
import json
import re
import unittest
from collections import Counter
from xml.etree import ElementTree as ET
from config import ROOT
import build
from pricing_pages import model_route,rows_of,build_pricing

NS="{http://www.sitemaps.org/schemas/sitemap/0.9}"

class PricingFamily(unittest.TestCase):
 def setUp(self):
  self.data=json.loads((ROOT/"data/offers.json").read_text("utf8"))
  self.ready={p["name"]:rows_of(p) for p in self.data["providers"] if len(p.get("list_prices",[]))>=3}
 def test_vendor_rows_remain_complete_after_keyword_merging(self):
  self.assertEqual(Counter(r.get("family") for r in self.ready["DigitalOcean"]),
                   {"Basic":7,"CPU-Optimized":6,"General Purpose":6,"Memory-Optimized":6,"Storage-Optimized":6})
  self.assertGreaterEqual(len(self.ready["Hetzner"]),3)
  self.assertGreaterEqual(len(self.ready["Cloudways"]),3)
 def test_sitemap_has_no_database_field_urls_or_unproven_model_pages(self):
  build.build()
  x=ET.fromstring((build.OUT/"sitemap.xml").read_bytes())
  urls=[e.text for e in x.iter(NS+"loc")]
  self.assertEqual(len(urls),len(set(urls)))
  self.assertNotIn("/cost/",''.join(urls))
  self.assertFalse(any(u.rstrip("/").endswith("-cost") for u in urls))
  pricing=[u for u in urls if u.rstrip("/").endswith("-pricing")]
  self.assertFalse(any(re.search(r"mib|vcpu|regular|\\d+-gb",u,re.I) for u in pricing))
  for name in self.ready:
   self.assertIn("https://vps.madebyyong.com/"+name.lower().replace(" ","-")+"-pricing/",urls)
  self.assertIn("https://vps.madebyyong.com/digitalocean-droplet-pricing/",urls)
  self.assertNotIn("https://vps.madebyyong.com/digitalocean-cpu-optimized-pricing/",urls)
  self.assertNotIn("https://vps.madebyyong.com/digitalocean-general-purpose-pricing/",urls)
 def test_all_previously_live_38_model_urls_301_into_pricing(self):
  build.build()
  rules=(build.OUT/"_redirects").read_text("utf8")
  for name in ("DigitalOcean","OVHcloud","BuyVM"):
   for row in self.ready[name]:
    source="/"+model_route(name,row)
    target="/digitalocean-droplet-pricing/" if name=="DigitalOcean" and row.get("family")=="Basic" else "/"+name.lower()+"-pricing/"
    self.assertIn(f"{source} {target} 301",rules)
  for path in ("digitalocean-cpu-optimized-pricing","digitalocean-general-purpose-pricing",
               "digitalocean-memory-optimized-pricing","digitalocean-storage-optimized-pricing"):
   self.assertIn(f"/{path}/ /digitalocean-pricing/ 301",rules)
  for name in self.ready:
   slug=name.lower().replace(" ","-")
   self.assertIn(f"/providers/{slug}/ /{slug}-pricing/ 301",rules)
 def test_each_vendor_main_includes_full_official_table(self):
  build.build()
  for name,records in self.ready.items():
   slug=name.lower().replace(" ","-")
   body=(build.OUT/(slug+"-pricing")/"index.html").read_text("utf8")
   self.assertIn("Official",body)
   self.assertIn(records[0]["source_url"],body)
   self.assertIn("Verified UTC:",body)
   self.assertGreaterEqual(body.count("<tr>"),len(records))
   for x in records:
    self.assertIn(x["model"],body)
    self.assertIn(x["monthly_usd"],body)
   for internal in ("parser_not_implemented","no_verified_discount","scraper_error","fetch_failed"):
    self.assertNotIn(internal,body)
 def test_source_failure_drops_unsupported_vendor_keyword_page(self):
  data=json.loads(json.dumps(self.data))
  for p in data["providers"]:
   if p["name"]=="Cloudways":p["list_prices"]=[]
  routes,redirects,_,cards=build_pricing(data,lambda path,s:None,lambda title,description,body,path:body)
  self.assertNotIn("cloudways-pricing/",routes)
  self.assertNotIn("Cloudways",cards)

if __name__=="__main__":
 unittest.main()