# ::ILANG [TYPE:python-module][ROLE:high-intent-pricing-source-tests]
# ::RULE{require official same-plan price+spec and a specified USD location}
# ::BOUNDARY{never:use stale reference prices or guess exchange rates}
import json
import unittest
from high_volume_prices import parse_cloudways,parse_hetzner

class HighVolumePricingSource(unittest.TestCase):
 def test_cloudways_standard_rate_and_specs_same_card(self):
  html=(
   '<p>$11 USD/mo $0.0139 /hr Excluding Taxes. Includes DO Hosting Charges. '
   '1GB RAM 1 Core Processor 25GB Storage 1TB Bandwidth</p>'
   '<p>$24 USD/mo $0.0306 /hr Excluding Taxes. Includes DO Hosting Charges. '
   '2GB RAM 1 Core Processor 50GB Storage 2TB Bandwidth</p>'
   '<p>$46 USD/mo $0.0583 /hr Excluding Taxes. Includes DO Hosting Charges. '
   '4GB RAM 2 Core Processor 80GB Storage 4TB Bandwidth</p>'
  )
  rows=parse_cloudways(html,'2026-10-30T15:00:00+00:00')
  self.assertEqual(len(rows),3)
  self.assertEqual(rows[0]['monthly_usd'],'11.00')
  self.assertEqual(rows[1]['storage'],'50 GB Storage')
  self.assertEqual(parse_cloudways(html.replace('USD/mo','EUR/mo'),"now"),[])
  self.assertEqual(parse_cloudways(html.replace('Includes DO Hosting Charges','Extra charges'),"now"),[])
 def test_hetzner_requires_us_region_and_exact_matching_cores(self):
  html=('CCX13 2 AMD 8 GB 80 GB NVMe; '
        'CCX23 4 AMD 16 GB 160 GB NVMe; '
        'CCX33 8 AMD 32 GB 240 GB NVMe')
  data={"Matrix":{"Dedicated - General Purpose":{
   "CCX13":{"cores":2,"locations":{"HIL1":{"USD":{"price":"50.99"}}}},
   "CCX23":{"cores":4,"locations":{"HIL1":{"USD":{"price":"102.99"}}}},
   "CCX33":{"cores":8,"locations":{"HIL1":{"USD":{"price":"165.99"}}}}
  }}}
  rows=parse_hetzner(html,json.dumps(data),"now")
  self.assertEqual(len(rows),3)
  self.assertEqual(rows[1]['model'],'CCX23')
  self.assertIn('HIL1',rows[2]['price_note'])
  del data['Matrix']['Dedicated - General Purpose']['CCX23']['locations']['HIL1']
  self.assertEqual(len(parse_hetzner(html,json.dumps(data),"now")),2)
  self.assertEqual(parse_hetzner(html.replace('AMD','Intel'),json.dumps(data),'now'),[])
 def test_does_not_count_nominal_reference_price_as_discount(self):
  from deal_site import valid_offers
  from config import load_config
  _,providers=load_config()
  example={"provider":"Hetzner","plan":"CCX13","id":"hetzner-ccx13","price_type":"standard_list_price",
           "currency":"USD","regular_monthly_usd":"50.99","promo_monthly_usd":"50.99"}
  self.assertEqual(valid_offers([example],providers),[])

if __name__=="__main__":unittest.main()