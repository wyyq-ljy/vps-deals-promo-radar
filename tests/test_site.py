import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build as site_builder
import scraper
from config import load_config
from pricing_sources import parse_digitalocean, parse_hetzner

ROOT = Path(__file__).resolve().parents[1]


class TestSite(unittest.TestCase):
    def test_config(self):
        site, providers = load_config()
        self.assertEqual(site["locale"], "en-US")
        self.assertGreaterEqual(len(providers), 3)

    def test_config_drives_provider_list(self):
        original = (ROOT / ".ilang/site.ilang").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as directory:
            alt = Path(directory) / "site.ilang"
            alt.write_text(original.replace("Hetzner |", "ChangedProvider |"), encoding="utf-8")
            _, providers = load_config(alt)
        self.assertIn("ChangedProvider", [p["name"] for p in providers])

    def test_digitalocean_requires_named_spec_and_monthly_price(self):
        table = """<h3>Basic Droplets</h3><table>
        <tr><th>Memory</th><th>vCPU</th><th>Transfer</th><th>SSD</th><th>$/hr</th><th>$/mo</th></tr>
        <tr><td>512 MiB</td><td>1 vCPU</td><td>500 GiB</td><td>10 GiB</td><td>$0.00595</td><td>$4.00</td></tr>
        <tr><td>1 GiB</td><td>1 vCPU</td><td>1000 GiB</td><td>25 GiB</td><td>$0.00893</td><td>TBD</td></tr>
        </table>"""
        offers = parse_digitalocean(table, "2026-10-30T00:00:00+00:00")
        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0]["monthly_usd"], "4.00")
        self.assertIn("512 MiB", offers[0]["plan"])
        self.assertEqual(offers[0]["price_type"], "standard_list_price")
        self.assertEqual(parse_digitalocean("<h3>Basic Droplets</h3>From $4", "now"), [])

    def test_hetzner_uses_pinned_region_and_rejects_bad_prices(self):
        fixture = {"Matrix": {
            "Shared - Regular Performance": {
                "CPX22": {"cores": 2, "locations": {
                    "HEL1": {"USD": {"price": "22.99"}},
                    "ASH1": {"USD": {"price": "39.00"}}}},
                "CPX32": {"cores": 4, "locations": {"HEL1": {"USD": {"price": None}}}},
            },
        }}
        offers = parse_hetzner(json.dumps(fixture), "2026-10-30T00:00:00+00:00")
        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0]["id"], "hetzner-cpx22-hel1")
        self.assertEqual(offers[0]["monthly_usd"], "22.99")
        self.assertIn("HEL1", offers[0]["region"])

    def test_no_verified_prices_never_overwrite_existing_dataset(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "offers.json"
            original = '{"offers":[{"id":"prior-verified-record"}]}'
            target.write_text(original, encoding="utf-8")
            with patch.object(scraper, "OUTPUT", target):
                with patch.object(scraper, "read_official", side_effect=PermissionError("blocked")):
                    with self.assertRaisesRegex(RuntimeError, "Zero verified"):
                        scraper.collect()
            self.assertEqual(target.read_text(encoding="utf-8"), original)

    def test_build_without_domain_is_noindex(self):
        site, providers = load_config()
        without_domain = {**site, "domain": "", "base_url": ""}
        try:
            with patch.object(site_builder, "load_config", return_value=(without_domain, providers)):
                site_builder.build()
                homepage = (site_builder.OUT / "index.html").read_text(encoding="utf-8")
                robots = (site_builder.OUT / "robots.txt").read_text(encoding="utf-8")
                self.assertIn("noindex,follow", homepage)
                self.assertIn("Disallow: /", robots)
        finally:
            site_builder.build()

    def test_live_config_produces_one_deal_page_per_verified_plan(self):
        site, _ = load_config()
        data = json.loads((ROOT / "data/offers.json").read_text(encoding="utf-8"))
        site_builder.build()
        homepage = (site_builder.OUT / "index.html").read_text(encoding="utf-8")
        robots = (site_builder.OUT / "robots.txt").read_text(encoding="utf-8")
        sitemap = (site_builder.OUT / "sitemap.xml").read_text(encoding="utf-8")
        base = site.get("base_url", "").rstrip("/")
        offers = data["offers"]
        if base:
            self.assertIn(f'<link rel="canonical" href="{base}/">', homepage)
            self.assertIn("Allow: /", robots)
            self.assertIn(f"Sitemap: {base}/sitemap.xml", robots)
            self.assertEqual(sitemap.count("<loc>"), 6 + len(offers))
            self.assertEqual(sitemap.count("<loc>" + base + "/deals/"), len(offers))
        self.assertEqual(len(list((site_builder.OUT / "deals").glob("*/index.html"))), len(offers))
        self.assertIn("Verified plan list prices", homepage)
        for item in offers:
            html = (site_builder.OUT / "deals" / item["id"] / "index.html").read_text(encoding="utf-8")
            self.assertIn(item["plan"], html)
            self.assertIn(item["source_url"].replace("&", "&amp;"), html)
            self.assertIn(item["verified_at"], html)
            self.assertIn("Standard list price", html)
            self.assertNotIn("limited-time offer", html)


if __name__ == "__main__":
    unittest.main()