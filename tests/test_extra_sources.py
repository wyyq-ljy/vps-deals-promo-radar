# ::ILANG [TYPE:python-module][ROLE:additional-parsers-regression]
# ::RULE{named model + confirmed same-card numeric reduction + contract}
# ::BOUNDARY{never:publish stand-alone list price as a discount}
import unittest
from config import load_config
from deal_site import provider_slug, valid_offers
from extra_sources import parse_dreamhost, parse_inmotion, parse_ultahost


class AdditionalProviderTests(unittest.TestCase):
    def test_dreamhost_requires_promo_and_renewal_for_same_stack(self):
        sample = """<span class="text-3xl leading-none">Stack 4</span><div>
        On Sale First 3 months at $8.99 /mo SAVE 43% Sign Up Now
        Auto-renews at $15.99 /mo after 3 months.
        2 vCPU AMD EPYC 4 GB RAM 75 GB NVMe SSD Unmetered Bandwidth</div>"""
        rows = parse_dreamhost(sample, "2026-10-30T00:00:00+00:00")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["promo_monthly_usd"], "8.99")
        self.assertEqual(rows[0]["promo_months"], 3)
        self.assertEqual(parse_dreamhost(sample.replace("SAVE 43%", "SAVE 91%"), "now"), [])
        self.assertEqual(parse_dreamhost(sample.replace("Auto-renews at", "Later price"), "now"), [])

    def test_inmotion_requires_same_card_and_term(self):
        sample = """<h3>VPS 4 vCPU</h3><div>
        You Save 41% $9.99 /mo For 24 month term Renews at $16.99 /mo
        4 vCPU Cores 8GB RAM 160GB NVMe SSD 5TB Bandwidth</div>"""
        rows = parse_inmotion(sample, "now")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["regular_monthly_usd"], "16.99")
        self.assertEqual(parse_inmotion(sample.replace("24 month term", "monthly plan"), "now"), [])
        self.assertEqual(parse_inmotion(sample.replace("41%", "98%"), "now"), [])

    def test_ultahost_requires_crossed_price_and_24_months(self):
        sample = """<span class="package-name">VPS Basic</span>
        <div class="uh_plan_discount"><del class="package-real-price-js">$9.19</del> Save 40%</div>
        <div class="uh_plan_price"><b class="package-price-js">$5.52</b> /mo</div>
        <div>Billed for 24 month term. Renews at $5.52 /mo for 2 years.</div>
        1 CPU Core 1 GB RAM DDR5 30 GB NVMe SSD<div class="spFooter">ORDER</div>"""
        offers = parse_ultahost(sample, "now")
        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0]["promo_monthly_usd"], "5.52")
        self.assertEqual(parse_ultahost(sample.replace("$9.19", "$5.52"), "now"), [])
        self.assertEqual(parse_ultahost(sample.replace("24 month term", "no term"), "now"), [])

    def test_provider_slug_hyphens_and_config_count(self):
        _, providers = load_config()
        self.assertEqual(provider_slug("InMotion Hosting"), "inmotion-hosting")
        self.assertEqual(len(providers), 28)
        self.assertEqual(len({p["source_url"] for p in providers}), len(providers))
        self.assertEqual(len({p["name"] for p in providers}), len(providers))


if __name__ == "__main__":
    unittest.main()