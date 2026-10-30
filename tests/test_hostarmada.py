# ::ILANG [TYPE:python-module][ROLE:annual-discount-source-regression]
# ::RULE{same official plan card, annual billing JSON, strict currency/price crosscheck}
# ::BOUNDARY{never:invent promotional expiry or accepted coupon}
import json
import unittest
from hostarmada_source import parse_hostarmada


class HostArmadaTests(unittest.TestCase):
    def example(self):
        d = {
            "recommendedCycle": "annually",
            "products": {
                "22": {
                    "name": "Spark", "currency": "USD",
                    "cycles": {
                        "annually": {
                            "available": True, "months": 12,
                            "regular": {"monthlyEquivalent": "8.20"},
                            "signup": {"monthlyEquivalent": "3.69"},
                            "renewal": {"monthlyEquivalent": "8.20"},
                            "savings": {"total": "54.12", "percentage": "55.00"},
                            "promotion": {"code": "SAMPLE-ONLY"},
                        }
                    }
                }
            }
        }
        return (
            '<script type="application/json" data-product-pricing>'
            + json.dumps(d, separators=(",", ":"))
            + '</script><section>Spark 55% OFF $3.69 /mo '
              'Regular Price: $8.20 /mo Specifications 40 GB NVMe Storage '
              '1 Core CPU 1 GB RAM 2 TB Bandwidth</section>'
        )

    def test_annual_discount_requires_matching_visible_and_structured_prices(self):
        rows = parse_hostarmada(self.example(), "2026-10-30T00:00:00+00:00")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], "hostarmada-spark")
        self.assertEqual(rows[0]["promo_monthly_usd"], "3.69")
        self.assertEqual(rows[0]["regular_monthly_usd"], "8.20")
        self.assertEqual(rows[0]["promo_months"], 12)

    def test_wrong_currency_or_mismatched_display_rejected(self):
        self.assertEqual(parse_hostarmada(self.example().replace('"USD"', '"EUR"'), "now"), [])
        self.assertEqual(parse_hostarmada(self.example().replace("$3.69 /mo", "$6.69 /mo"), "now"), [])
        self.assertEqual(parse_hostarmada(self.example().replace('"annually"', '"monthly"'), "now"), [])


if __name__ == "__main__":
    unittest.main()