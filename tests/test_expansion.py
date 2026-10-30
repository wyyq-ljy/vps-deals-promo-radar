# ::ILANG [TYPE:unittest][ROLE:official-pricing-snapshot-regression]
import datetime as dt
import unittest
from unittest.mock import patch
from official_pricing_expansion import (
    MANUAL_PROVIDERS, read_snapshots, live_rows, verified_snapshot_rows)
from config import load_config
from pricing_pages import rows_of

class PricingExpansionTests(unittest.TestCase):
    def test_every_static_vendor_has_three_named_first_party_usd_plans(self):
        site, providers = load_config()
        official = {p["name"]:p["source_url"] for p in providers}
        snapshots = read_snapshots()
        self.assertEqual(set(MANUAL_PROVIDERS),set(snapshots))
        for name,rows in snapshots.items():
            with self.subTest(provider=name):
                self.assertGreaterEqual(len(rows),3)
                self.assertEqual(len({r["model"] for r in rows}),len(rows))
                self.assertTrue(all(r["source_url"]==official[name] for r in rows))
                self.assertTrue(all(r["currency"]=="USD" and r["price_note"] and r["checked_at"] for r in rows))
                self.assertEqual(len(rows_of({"source_url":official[name],"list_prices":rows})),len(rows))

    def test_static_snapshot_never_overrides_current_official_change(self):
        name="Hostwinds"
        rows=read_snapshots()[name]
        source=rows[0]["source_url"]
        verified_at=dt.datetime.now(dt.timezone.utc).isoformat()
        mocked=[dict(r,checked_at=verified_at) for r in rows]
        with patch("official_pricing_expansion.live_rows",return_value=mocked):
            good=verified_snapshot_rows(name,"official text",verified_at,source,{name:rows})
            self.assertEqual(len(good),len(rows))
        mocked[0]["monthly_usd"]="999.99"
        with patch("official_pricing_expansion.live_rows",return_value=mocked):
            self.assertEqual(len(verified_snapshot_rows(name,"official text",verified_at,source,{name:rows})),len(rows)-1)
        with patch("official_pricing_expansion.live_rows",return_value=mocked[:2]):
            self.assertEqual(verified_snapshot_rows(name,"official text",verified_at,source,{name:rows}),[])
        with patch("official_pricing_expansion.live_rows",return_value=mocked):
            self.assertEqual(verified_snapshot_rows(name,"official text",verified_at,
                "https://third-party.invalid/",{name:rows}),[])

    def test_hostwinds_same_card_price_and_specs(self):
        official=("CPU 1 CPU RAM 2 GB Storage 50 GB Bandwidth 2 TB "
                  "Price $ 9.99/mo $ 9.99/mo Order $ 9.99/mo")
        rows=live_rows("Hostwinds",official,"2026-10-30T00:00:00+00:00",
            "https://www.hostwinds.com/vps/unmanaged-linux")
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["monthly_usd"],"9.99")
        self.assertEqual(rows[0]["memory"],"2 GB RAM")
        self.assertEqual(live_rows("Hostwinds",official.replace("Price $ 9.99/mo","Price EUR 9.99/mo"),
            "now","https://www.hostwinds.com/vps/unmanaged-linux"),[])
    def test_physical_server_category_has_actual_hardware_evidence(self):
        from dedicated_category import SOURCE,snapshots,live_verify
        official=snapshots()
        self.assertEqual(len(official),5)
        self.assertTrue(all(x['source_url']==SOURCE for x in official))
        self.assertEqual(live_verify('Unverified placeholder','now'),[])

if __name__=="__main__":unittest.main()
