# ::ILANG [TYPE:python-module][ROLE:thin-provider-page-regressions]
# ::RULE{only real named official prices or verifiable deals are indexable}
# ::BOUNDARY{never:invent rows, promote list prices as deals, expose raw scanner states}
"""Guard against indexable shell pages and misleading pricing."""
import json
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

import build
from config import ROOT
from public_copy import public_status, STATUS_COPY, FALLBACK
from standard_prices import parse_digitalocean, parse_buyvm, parse_ovhcloud

NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
CODES = [
    "parser_not_implemented", "no_verified_discount", "fetch_failed",
    "scraper_error", "no_deal", "not_checked", "robots_blocked",
    "verified_discounts", "standard_prices_verified",
]

class ThinPageTests(unittest.TestCase):
    def test_public_status_is_exhaustive_and_has_unknown_fallback(self):
        self.assertTrue(all(k in STATUS_COPY for k in CODES))
        for code in CODES + ["future_unknown_status", "", None]:
            text = public_status(code)
            self.assertTrue(text and len(text.split()) >= 5)
            self.assertNotIn("not_implemented", text)
            self.assertNotIn("_", text)
        self.assertEqual(public_status("not_known"), FALLBACK)

    def test_digitalocean_rows_require_named_model_specs_and_two_prices(self):
        html = ("<section>Basic Droplets CPU Options Regular Premium Intel Premium AMD "
                "Memory vCPU Transfer SSD $/hr $/mo "
                "512 MiB 1 vCPU 500 GiB 10 GiB $0.00595 $4.00 "
                "1 GiB 1 vCPU 1000 GiB 25 GiB $0.00893 $6.00 "
                "2 GiB 1 vCPU 2000 GiB 50 GiB $0.01786 $12.00 "
                "CPU-Optimized Droplets</section>")
        rows = parse_digitalocean(html, "2026-10-30T13:00:00+00:00")
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["monthly_usd"], "4.00")
        self.assertTrue(all(x["currency"] == "USD" for x in rows))
        self.assertEqual(parse_digitalocean(html.replace("$4.00", "Unavailable"),"now")[0]["monthly_usd"], "6.00")

    def test_buyvm_monthly_slices_only_no_yearly_monthly_conversion(self):
        rows = []
        for ram, disk, price in ((1024,20,"3.50"),(2048,40,"7.00"),(4096,80,"15.00")):
            rows.append(
                f"<h2>SLICE <span>{ram}</span></h2>"
                f"<p>1 Core @ 3.50+ GHz {ram} MB Memory {disk} GB SSD Storage "
                f"Unmetered Bandwidth ${price} per month</p>"
            )
        records = parse_buyvm("".join(rows), "now")
        self.assertEqual(len(records),3)
        self.assertEqual(records[1]["model"],"SLICE 2048")
        self.assertEqual(parse_buyvm("".join(rows).replace("per month","per year"),"now"),[])

    def test_ovh_only_explicit_named_usd_starting_prices(self):
        source = " ".join(
            f"VPS-{i} Starting at ${p} /month Configure {i*2} vCores {i*4} GB RAM {i*40} GB SSD NVMe"
            for i,p in ((1,"4.54"),(2,"8.50"),(3,"12.32"))
        )
        rows = parse_ovhcloud(f"<article>{source}</article>", "now")
        self.assertEqual(len(rows),3)
        self.assertTrue(all("starting" in x["price_note"].lower() for x in rows))
        self.assertEqual(parse_ovhcloud(source.replace("$","€"),"now"),[])

    def test_index_includes_only_supported_factual_provider_pages(self):
        build.build()
        data=json.loads((ROOT/"data/offers.json").read_text("utf-8"))
        soup=ET.fromstring((build.OUT/"sitemap.xml").read_bytes())
        urls=[x.text for x in soup.iter(NS+"loc")]
        providers=[x for x in urls if "/providers/" in x]
        active={p["name"] for p in data["providers"] if p.get("verified_deal_count",0)>0}
        self.assertEqual(len(providers),len(active))
        self.assertNotIn("providers/hetzner/", "".join(providers))
        self.assertNotIn("providers/hostzealot/", "".join(providers))
        self.assertNotIn("providers/digitalocean/", "".join(providers))
        self.assertIn("digitalocean-pricing/", "".join(urls))
        self.assertIn("buyvm-pricing/", "".join(urls))
        self.assertIn("ovhcloud-pricing/", "".join(urls))
        self.assertGreaterEqual(len(urls),60)

    def test_unverified_legacy_provider_urls_redirect_to_real_comparison(self):
        build.build()
        redirects=(build.OUT/"_redirects").read_text("utf-8")
        self.assertIn("/providers/hetzner/ /compare/ 301",redirects)
        self.assertIn("/providers/hostzealot/ /compare/ 301",redirects)
        self.assertIn("/providers/digitalocean/ /digitalocean-pricing/ 301",redirects)
        self.assertIn("/providers/ovhcloud/ /ovhcloud-pricing/ 301",redirects)

    def test_every_indexed_provider_is_real_evidence_not_a_shell(self):
        build.build()
        data=json.loads((ROOT/"data/offers.json").read_text("utf-8"))
        for p in data["providers"]:
            slug=build.slug(p["name"])
            file=build.OUT/"providers"/slug/"index.html"
            # Local output can have old generated files. Sitemap is authoritative.
            sitemap=(build.OUT/"sitemap.xml").read_text("utf-8")
            if f"/providers/{slug}/" not in sitemap:
                continue
            body=file.read_text("utf-8")
            for key in CODES:
                self.assertNotIn(key,body)
            if p.get("verified_deal_count"):
                self.assertIn("See verified saving",body)
                self.assertIn("Official source",body)
            else:
                self.assertGreaterEqual(body.count("<tr>"),3)
                self.assertIn("Last checked (UTC)",body)
                self.assertIn("standard pricing",body.lower())
                self.assertIn(p["source_url"],body)
                self.assertNotIn("Actual difference",body)

if __name__=="__main__":
    unittest.main()