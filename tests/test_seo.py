# ::ILANG [TYPE:python-module][ROLE:regression-tests]
# ::RULE{verify template usage, same-page discount policy, SEO nofake}
# ::BOUNDARY{never:access external services in unit tests}
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET

import build
import scraper
import template_engine
from config import ROOT, load_config
from deal_site import valid_offers
from seo_helpers import valid_lastmod, sitemap_xml

NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


class SEOAndAutomation(unittest.TestCase):
    def setUp(self):
        self.site, self.providers = load_config()
        self.data = json.loads((ROOT / "data/offers.json").read_text("utf-8"))

    def test_template_is_executed_not_dead_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "templates").mkdir()
            (root / "templates" / "index.html").write_text(
                "Template proof: $deal_count", encoding="utf-8"
            )
            with patch.object(template_engine, "ROOT", root):
                self.assertEqual(
                    template_engine.render("index.html", deal_count="123"),
                    "Template proof: 123",
                )

    def test_provider_change_in_ilang_changes_page(self):
        # Project config is not hard-coded inside build().
        modified = [dict(p) for p in self.providers]
        modified[2]["name"] = "NewBrand"
        with patch.object(build, "load_config", return_value=(self.site, modified)):
            build.build()
        sitemap = (build.OUT / "sitemap.xml").read_text("utf-8")
        self.assertNotIn("/providers/hostinger/", sitemap)
        self.assertNotIn("/providers/newbrand/", sitemap)
        build.build()

    def test_existing_deal_snippets_validate_schema_and_og(self):
        build.build()
        for item in valid_offers(self.data["offers"], self.providers):
            page = (build.OUT / "deals" / item["id"] / "index.html").read_text("utf-8")
            self.assertIn(f'<link rel="canonical" href="{self.site["base_url"]}/deals/{item["id"]}/">', page)
            self.assertIn('property="og:image"', page)
            self.assertIn('name="twitter:card" content="summary_large_image"', page)
            # Extract JSON-LD only; no invented expiry / stock / reviews.
            from html.parser import HTMLParser
            class Scripts(HTMLParser):
                def __init__(self):
                    super().__init__(); self.active = False; self.blocks = []
                def handle_starttag(self, tag, attrs):
                    if tag == "script" and dict(attrs).get("type") == "application/ld+json":
                        self.active = True
                def handle_data(self, data):
                    if self.active: self.blocks.append(data)
                def handle_endtag(self, tag):
                    if tag == "script": self.active = False
            parser = Scripts()
            parser.feed(page)
            nodes = [json.loads(s) for s in parser.blocks]
            prod = next(x for x in nodes if x.get("@type") == "Product")
            self.assertEqual(prod["offers"]["price"], item["promo_monthly_usd"])
            self.assertEqual(prod["offers"]["priceCurrency"], item["currency"])
            self.assertNotIn("priceValidUntil", prod["offers"])
            self.assertNotIn("availability", prod["offers"])
            self.assertTrue(any(x["@type"] == "BreadcrumbList" for x in nodes))
        png = (build.OUT / "og-card.png").read_bytes()
        self.assertTrue(png.startswith(b"\x89PNG\r\n\x1a\n"))

    def test_no_expired_deals_or_guessed_expiration(self):
        original = dict(self.data["offers"][0])
        expired = {**original, "valid_until": "2020-01-01"}
        invalid = {**original, "valid_until": "unverified"}
        self.assertEqual(valid_offers([expired, invalid], self.providers), [])
        future = {**original, "valid_until": (date.today() + timedelta(days=40)).isoformat()}
        self.assertEqual(len(valid_offers([future], self.providers)), 1)

    def test_real_changes_only_sitemap_lastmod(self):
        build.build()
        root = ET.fromstring((build.OUT / "sitemap.xml").read_bytes())
        locs = [u.find(NS + "loc").text for u in root.findall(NS + "url")]
        indexable_count = sum(1 for p in self.data["providers"] if p.get("verified_deal_count",0) or len(p.get("list_prices",[]))>=3)
        self.assertEqual(len(locs), 2 + indexable_count + len(valid_offers(self.data["offers"], self.providers)))
        for row in root.findall(NS + "url"):
            url = row.find(NS + "loc").text
            lm = row.find(NS + "lastmod")
            if "/deals/" in url:
                self.assertIsNotNone(lm)
                self.assertRegex(lm.text, r"^\d{4}-\d{2}-\d{2}$")
            else:
                self.assertIsNone(lm)
        self.assertEqual(len([x for x in locs if "/deals/" in x]), len(self.data["offers"]))

    def test_no_date_from_build_time(self):
        xml = sitemap_xml("https://vps.madebyyong.com",
                          ["/", "/deals/test/"], {"/deals/test/": None})
        self.assertNotIn("<lastmod>", xml)
        self.assertIsNone(valid_lastmod("not a real time"))

    def test_affiliate_requires_explicit_link_and_is_sponsored(self):
        target = {"Hostinger": "https://example.org/approved-partner-ref"}
        with patch.object(build, "load_config", return_value=(
            self.site,
            [{**p, "affiliate_url": target.get(p["name"], "")} for p in self.providers]
        )):
            build.build()
        page = (build.OUT / "deals/hostinger-kvm-1/index.html").read_text("utf-8")
        self.assertIn('rel="nofollow sponsored noopener noreferrer"', page)
        self.assertIn("Check current price with provider (affiliate link)", page)
        self.assertIn("https://www.hostinger.com/vps-hosting", page)
        build.build()


if __name__ == "__main__":
    unittest.main()