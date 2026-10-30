# ::ILANG [TYPE:python-module][ROLE:keyword-pricing-page-regression]
# ::RULE{every indexable pricing cost page must derive from a source-verified USD row}
# ::BOUNDARY{never:count a list price page as a deal}
import json
import re
import unittest
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET
import build
from config import ROOT
from pricing_pages import model_route, FAMILIES, rows_of
from standard_prices import parse_digitalocean

NS="{http://www.sitemaps.org/schemas/sitemap/0.9}"

class PricingFamily(unittest.TestCase):
    def setUp(self):
        self.data=json.loads((ROOT/"data/offers.json").read_text("utf8"))
        self.priced={p["name"]:rows_of(p) for p in self.data["providers"] if len(p.get("list_prices",[]))>=3}

    def test_real_vendor_tiers_are_distinct(self):
        rows=self.priced["DigitalOcean"]
        groups=Counter(x.get("family") for x in rows)
        self.assertEqual(groups,{"Basic":7,"CPU-Optimized":6,"General Purpose":6,"Memory-Optimized":6,"Storage-Optimized":6})
        self.assertEqual(len({model_route("DigitalOcean",x) for x in rows}),len(rows))

    def test_all_pricing_pages_have_real_plan_evidence(self):
        build.build()
        ns=ET.fromstring((build.OUT/"sitemap.xml").read_bytes())
        locs=[x.text for x in ns.iter(NS+"loc")]
        pricing=[x for x in locs if x.removesuffix("/").endswith(("-pricing","-cost"))]
        self.assertGreaterEqual(len(pricing),40)
        self.assertEqual(len(set(pricing)),len(pricing))
        for url in pricing:
            route=url.removeprefix("https://vps.madebyyong.com/")
            doc=(build.OUT/route/"index.html").read_text("utf8")
            self.assertIn(f'<link rel="canonical" href="{url}">',doc)
            self.assertIn("USD",doc)
            self.assertIn("Source:",doc)
            self.assertIn("Verified UTC:",doc)
            self.assertIn("CPU",doc)
            self.assertTrue("Memory" in doc or "RAM" in doc)
            self.assertIn("SSD",doc)
            for phrase in ("parser_not_implemented","no_verified_discount","scraper_error","fetch_failed"):
                self.assertNotIn(phrase,doc)
        self.assertIn("https://vps.madebyyong.com/digitalocean-droplet-pricing/",locs)
        self.assertIn("https://vps.madebyyong.com/digitalocean-vs-ovhcloud-pricing/",locs)

    def test_each_cost_page_names_real_verified_plan_and_price(self):
        build.build()
        for name,rows in self.priced.items():
            for row in rows:
                route=model_route(name,row)
                doc=(build.OUT/route/"index.html").read_text("utf8")
                self.assertIn(row["model"],doc)
                self.assertIn(row["monthly_usd"],doc)
                self.assertIn(row["source_url"],doc)
                self.assertIn(row["checked_at"],doc)
        # All 3 provider entrypoint URLs must be canonical and their legacy
        # /providers/ URLs must redirect permanently.
        redirects=(build.OUT/"_redirects").read_text("utf8")
        for name in self.priced:
            target=name.lower().replace(" ","-")
            self.assertIn(f"/providers/{target}/ /{target}-pricing/ 301",redirects)

    def test_source_loss_suppresses_price_family(self):
        from pricing_pages import build_pricing
        data=json.loads(json.dumps(self.data))
        for provider in data["providers"]:
            if provider["name"]=="DigitalOcean":
                provider["list_prices"]=[]
        recorded=[]
        routes,redirects,changes,cards=build_pricing(
            data,lambda path,doc: recorded.append(path),
            lambda title,description,body,path:body)
        self.assertFalse(any(route.startswith("digitalocean-") for route in routes))
        self.assertNotIn("DigitalOcean",cards)

if __name__=="__main__":
    unittest.main()