# ::ILANG [TYPE:unittest][ROLE:manually-verified-official-multicurrency-pages]
"""Regression: manual first-party quotes, TTL, billing truth, no mixed-currency table."""
import datetime as dt
import unittest
from copy import deepcopy
from pathlib import Path
from config import ROOT, load_config
from manual_firstparty import MANUAL_NAMES, read_manual, with_manual_prices
from pricing_pages import row_table, rows_of
import build


class ManualFirstpartyPricingTests(unittest.TestCase):
    def test_manual_rows_complete_single_currency_and_source(self):
        _, configured = load_config()
        sources = {p["name"]: p["source_url"] for p in configured}
        rows = read_manual()
        self.assertEqual({p:len(x) for p,x in rows.items()},
                         {"Linode":10,"Vultr":11,"Netcup":5})
        for name, plans in rows.items():
            self.assertEqual({x["currency"] for x in plans}, {"EUR" if name=="Netcup" else "USD"})
            self.assertTrue(all(x["source_url"]==sources[name] and x["checked_at"] for x in plans))
            self.assertTrue(all(x["cpu"] and x["memory"] and x["storage"] and x["transfer"] for x in plans))
            self.assertEqual(len({x["model"] for x in plans}), len(plans))
            self.assertEqual(len(rows_of({"source_url":sources[name], "list_prices":plans})),len(plans))

    def test_netcupt_reference_is_not_renewal_or_currency_conversion(self):
        rows=read_manual()["Netcup"]
        self.assertTrue(all(x["rate_kind"]=="term_discount" and x["renewal_monthly"]=="-" for x in rows))
        self.assertEqual([(x["monthly_usd"],x["reference_monthly"]) for x in rows],
                         [("6.94","7.98"),("12.18","14.01"),("22.62","26.01"),
                          ("38.11","43.83"),("56.39","64.84")])

    def test_one_mixed_currency_row_fails_entire_table(self):
        data=read_manual()
        mixed=[deepcopy(data["Netcup"][0]),deepcopy(data["Linode"][0])]
        with self.assertRaisesRegex(ValueError,"Mixed"):
            row_table("Netcup",mixed)
        self.assertEqual(rows_of({"source_url":data["Netcup"][0]["source_url"],"list_prices":
            [data["Netcup"][0], dict(data["Netcup"][1],currency="USD"),data["Netcup"][2]]}),[])

    def test_owner_quotes_expire_instead_of_becoming_stale_fallback(self):
        plans=read_manual()
        checked=dt.datetime.fromisoformat(plans["Linode"][0]["checked_at"])
        expired=read_manual(now=checked+dt.timedelta(days=32))
        self.assertEqual(expired,{})
        data=with_manual_prices({"providers":[]}, now=checked+dt.timedelta(days=32))
        self.assertTrue(all(not p["list_prices"] for p in data["providers"]))

    def test_three_main_pages_show_all_models_exact_currency_and_unknown_renewal(self):
        build.build()
        expected={"Linode":(10,"USD"),"Vultr":(11,"USD"),"Netcup":(5,"EUR")}
        sitemap=(build.OUT/"sitemap.xml").read_text("utf8")
        for name,(count,cur) in expected.items():
            with self.subTest(name=name):
                self.assertIn("/"+name.lower()+"-pricing/",sitemap)
                body=(build.OUT/(name.lower()+"-pricing")/"index.html").read_text("utf8")
                self.assertIn(name+" Pricing ("+cur+")",body)
                self.assertGreaterEqual(body.count("<tr>"),count+1)
                self.assertGreaterEqual(body.count(cur+" / month"),count)
                self.assertIn("Not separately published",body)
                self.assertIn("owner-copied official table",body)
                if name=="Netcup":
                    self.assertIn("€6.94 EUR / month",body)
                    self.assertIn("€7.98 EUR (not renewal)",body)
                    self.assertNotIn("$6.94 USD",body)
                else:
                    self.assertIn("No introductory promotion",body)


if __name__=="__main__":
    unittest.main()